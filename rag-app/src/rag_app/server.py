import hmac
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .config import (
    ANSWER_EFFORT,
    ANSWER_MAX_TOKENS,
    ANSWER_MODEL,
    ANSWER_THINKING,
    NO_THINKING,
    REWRITE_MODEL,
    TOP_CHUNK_COUNT,
)
from .search import get_similar_chunks
from .used_sources import holdback_index, select_sources, split_used_sources
from .prompts import SYSTEM_PROMPT, REWRITE_PROMPT, PERSONA_JUST_THE_ANSWER, PERSONA_EXPLAIN_SIMPLY, PERSONA_GIVE_ME_DETAIL, PERSONA_EMINEM

import os
import json
from dotenv import load_dotenv
import anthropic
from datetime import date
from arize.otel import register
from openinference.instrumentation.anthropic import AnthropicInstrumentor

load_dotenv()

# ---------------------------------
# ------ Arize Obserability -------
# --------------------------------- 
# Enabled only when both keys are present, so the server also boots without them.
if os.getenv("ARIZE_SPACE_ID") and os.getenv("ARIZE_API_KEY"):
    tracer_provider = register(
        space_id=os.getenv("ARIZE_SPACE_ID"),
        api_key=os.getenv("ARIZE_API_KEY"),
        project_name="allanclear",
    )
    AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
else:
    print("Arize keys not set; observability disabled")
# ---------------------------------
# --------------------------------- 

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Query Rewrite sees only the tail of the conversation: three exchanges is
# enough to resolve "what about fees?" without re-sending a long history.
REWRITE_HISTORY_LIMIT = 6
# Sent as a final user turn after the conversation (the API folds it into the
# last user message). Without it the model sometimes carries on the
# conversation as the assistant instead of rewriting the user's message.
REWRITE_INSTRUCTION = (
    "Rewrite my last message above into a standalone retrieval query, following "
    "your instructions. Output only the query."
)

# Shown to the user when the answer stream ends badly. Plain sentences, no
# square brackets, so they cannot be mistaken for the [USED_SOURCES] line.
CUT_SHORT_NOTICE = "\n\n*This answer was cut short. Ask me to continue and I'll pick up where it stopped.*"
NO_ANSWER_NOTICE = "I couldn't produce an answer that time. Please ask again."

PERSONA_MAP = {
    "just_the_answer": PERSONA_JUST_THE_ANSWER,
    "explain_simply": PERSONA_EXPLAIN_SIMPLY,
    "give_me_detail": PERSONA_GIVE_ME_DETAIL,
    "eminem": PERSONA_EMINEM,
}

# ---------------------------------
# ------ Access gate --------------
# ---------------------------------
# The app is private: one shared access code, compared server-side on every
# request. The frontend sends it as a bearer token. See README "Deployment".
ACCESS_CODE = os.getenv("APP_ACCESS_CODE")
if not ACCESS_CODE:
    raise RuntimeError("APP_ACCESS_CODE is not set; refusing to start an unprotected server")

_bearer = HTTPBearer(auto_error=False)


def require_access_code(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    supplied = credentials.credentials if credentials else ""
    if not hmac.compare_digest(supplied.encode(), ACCESS_CODE.encode()):
        raise HTTPException(status_code=401, detail="Invalid access code")


# Built frontend, served from the same origin as the API (no CORS needed).
STATIC_DIR = Path(
    os.getenv("STATIC_DIR", Path(__file__).resolve().parents[3] / "rag-client" / "dist")
)

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/check", dependencies=[Depends(require_access_code)], status_code=204)
def auth_check():
    return Response(status_code=204)


class ChatRequest(BaseModel):
    chat_history: list[dict]
    persona: str = "just_the_answer"

def drop_empty_messages(chat_history: list[dict]) -> list[dict]:
    """Remove messages with no text, such as an earlier assistant turn that
    produced nothing. They would confuse the model and the API rejects them."""
    return [m for m in chat_history if str(m.get("content", "")).strip()]


def rewrite_history(chat_history: list[dict]) -> list[dict]:
    """The last REWRITE_HISTORY_LIMIT messages, trimmed to start on a user turn,
    followed by the rewrite instruction."""
    recent = chat_history[-REWRITE_HISTORY_LIMIT:]
    while recent and recent[0]["role"] != "user":
        recent = recent[1:]
    return recent + [{"role": "user", "content": REWRITE_INSTRUCTION}]


def query_rewrite_llm_call(chat_history: list[dict], system_prompt: str = REWRITE_PROMPT) -> str:
    """Rewrite the latest user message into a standalone retrieval query.

    The conversation is sent as real user and assistant turns so the model can
    tell who asked what. On any failure the raw message is returned: one flaky
    call must not kill the turn."""
    latest_user_message = chat_history[-1]["content"]
    try:
        print(f"Attempting to rewrite query: {latest_user_message}")
        response = client.messages.create(
            model=REWRITE_MODEL,
            max_tokens=512,
            thinking=NO_THINKING,
            system=system_prompt.format(todays_date=date.today().strftime("%B %d, %Y")),
            messages=rewrite_history(chat_history),
        )
        rewritten = "".join(block.text for block in response.content if block.type == "text").strip()
        if not rewritten:
            raise ValueError(f"empty rewrite (stop_reason={response.stop_reason})")
        print(f"Successfully rewritten query: {rewritten}")
        return rewritten
    except Exception as e:
        print(f"Query rewrite failed, retrieving with the raw message: {e}")
        return latest_user_message

def format_chunk(chunk, number: int):
    """Shape a retrieved chunk for the prompt. ``number`` is the 1-based Source
    Number the model reports back in its [USED_SOURCES: ...] line."""
    if chunk["metadata"].get("title"):
        return {
            "Source Number": number,
            "Allan Gray Source Material Type": "Article",
            "Article Title": chunk["metadata"]["title"],
            "Article Author": chunk["metadata"]["author"],
            "Article Category": chunk["metadata"]["category"],
            "Text Relevant to User Question": chunk["metadata"]["chunk"],
            "Article Publication Date": chunk["metadata"]["date"]
        }
    else:
        formatted = {
            "Source Number": number,
            "Allan Gray Source Material Type": "Fund Fact Sheet",
            "Fund Name": chunk["metadata"]["fund"],
            "Fund Fact Sheet Section Title": chunk["metadata"]["section"],
            "Description and Details of Section": chunk["metadata"]["chunk"]
        }
        # Reporting date of the whole fact sheet (see pdf_ingest.extract_as_at_date).
        # Absent on vectors upserted before the field existed.
        if chunk["metadata"].get("as_at"):
            formatted["Fact Sheet Date (figures are as at this date unless stated otherwise)"] = chunk["metadata"]["as_at"]
        return formatted

def build_sources(similar_chunks) -> list[dict]:
    """One entry per distinct article or fact sheet, in retrieval order. Each
    carries ``chunk_numbers``: the Source Numbers (matching format_chunk) of the
    chunks behind it, used later to keep only the sources the answer relied on."""
    sources: dict[str, dict] = {}

    for number, chunk in enumerate(similar_chunks, start=1):
        meta = chunk["metadata"]
        if meta.get("title"):  # article
            key = meta.get("url", "")
            if not key:
                continue
            if key not in sources:
                sources[key] = {
                    "type": "article",
                    "title": meta["title"],
                    "url": key,
                    "label": meta["title"],
                    "chunk_numbers": [],
                }
        else:  # fund fact sheet
            key = meta.get("fund", "Allan Gray Fund")
            if key not in sources:
                display_name = key if "Allan Gray - Orbis" in key else key.removeprefix("Allan Gray ").strip()
                sources[key] = {
                    "type": "fund_fact_sheet",
                    "title": key,
                    "url": None,
                    "label": f"{display_name} Fact Sheet",
                    "chunk_numbers": [],
                }
        sources[key]["chunk_numbers"].append(number)

    return list(sources.values())

def rag_enhanced_llm_call(
    chat_history, similar_chunks, persona_prompt, system_prompt=SYSTEM_PROMPT, max_tokens=ANSWER_MAX_TOKENS
):
    sources = build_sources(similar_chunks)

    formatted_chunks_context = {
        "Relevant context": [
            format_chunk(chunk, number) for number, chunk in enumerate(similar_chunks, start=1)
        ]
    }

    with client.messages.stream(
        model=ANSWER_MODEL,
        max_tokens=max_tokens,
        # Adaptive thinking on every Persona: the model reasons about multi-part
        # questions before answering. Thinking tokens count against max_tokens,
        # hence the large cap (see config.py). text_stream carries text only.
        thinking=ANSWER_THINKING,
        output_config={"effort": ANSWER_EFFORT},
        system=system_prompt.format(
            persona=persona_prompt,
            context=json.dumps(formatted_chunks_context),
            todays_date=date.today().strftime("%B %d, %Y")
        ),
        messages=chat_history,
    ) as stream:
        # The model ends with a "[USED_SOURCES: ...]" line that must not reach the
        # client. Hold back any tail that could be the start of it (see
        # used_sources.holdback_index) and emit the rest as it streams.
        pending = ""
        for text in stream.text_stream:
            pending += text
            cut = holdback_index(pending)
            if cut > 0:
                yield pending[:cut]
                pending = pending[cut:]
        final = stream.get_final_message()

    if not any(block.type == "text" and block.text for block in final.content):
        # Thinking used the whole cap, or the model returned nothing. Say so
        # rather than leave an empty bubble; there is nothing to cite.
        print(f"Answer had no text (stop_reason={final.stop_reason}); sending the fallback line")
        yield NO_ANSWER_NOTICE
        yield f"[SOURCES]{json.dumps([])}"
        return

    tail, used = split_used_sources(pending)
    if tail:
        yield tail
    if final.stop_reason == "max_tokens":
        # The [USED_SOURCES] line is normally lost with the tail, so all
        # retrieved sources are shown for a cut-short answer.
        print("Answer hit the token cap; telling the user it was cut short")
        yield CUT_SHORT_NOTICE
    if used is None:
        print("No [USED_SOURCES] marker in answer; showing all retrieved sources")

    yield f"[SOURCES]{json.dumps(select_sources(sources, used))}"


@app.post("/chat", dependencies=[Depends(require_access_code)])
def chat(request: ChatRequest):
    print(f"Received chat request: {request}")

    chat_history = drop_empty_messages(request.chat_history)
    if not chat_history or chat_history[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="The last message must be a non-empty user message")
    latest_user_message = chat_history[-1]["content"]
    persona_prompt = PERSONA_MAP.get(request.persona, PERSONA_JUST_THE_ANSWER)

    user_messages_count = sum(1 for message in chat_history if message["role"] == "user")

    # Rewrites the user query if there is more than one user message
    if user_messages_count > 1:
        retrieval_query = query_rewrite_llm_call(chat_history)
    else:
        retrieval_query = latest_user_message

    similar_chunks = get_similar_chunks(retrieval_query, TOP_CHUNK_COUNT)

    return StreamingResponse(
        rag_enhanced_llm_call(chat_history, similar_chunks, persona_prompt),
        media_type="text/event-stream"
    )


# Mounted last so API routes take precedence. Skipped when there is no build
# (e.g. local dev, where Vite serves the frontend and proxies /chat here).
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    print(f"No frontend build at {STATIC_DIR}; serving API only")

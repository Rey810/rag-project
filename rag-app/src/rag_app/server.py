from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .search import get_similar_chunks
from .prompts import SYSTEM_PROMPT, REWRITE_PROMPT, PERSONA_JUST_THE_ANSWER, PERSONA_EXPLAIN_SIMPLY, PERSONA_GIVE_ME_DETAIL

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
tracer_provider = register(
    space_id=os.getenv("ARIZE_SPACE_ID"),
    api_key=os.getenv("ARIZE_API_KEY"),
    project_name="allanclear",
)
AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
# ---------------------------------
# --------------------------------- 

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"
TOP_CHUNK_COUNT = 5

PERSONA_MAP = {
    "just_the_answer": PERSONA_JUST_THE_ANSWER,
    "explain_simply": PERSONA_EXPLAIN_SIMPLY,
    "give_me_detail": PERSONA_GIVE_ME_DETAIL,
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    chat_history: list[dict]
    persona: str = "just_the_answer"

def query_rewrite_llm_call(user_query, chat_history, system_prompt=SYSTEM_PROMPT):
    try:
        print(f"Attempting to rewrite query: {user_query}")
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=system_prompt.format(
                user_query=user_query,
                chat_history=json.dumps(chat_history),
                todays_date=date.today().strftime("%B %d, %Y")
            ),
            messages=[{"role": "user", "content": user_query}]
        )
        rewritten = response.content[0].text
        print(f"Successfully rewritten query: {rewritten}")
        return rewritten
    except Exception as e:
        print(f"Query rewrite pipeline failed: {e}")
        raise

def format_chunk(chunk):
    if chunk["metadata"].get("title"):
        return {
            "Allan Gray Source Material Type": "Article",
            "Article Title": chunk["metadata"]["title"],
            "Article Author": chunk["metadata"]["author"],
            "Article Category": chunk["metadata"]["category"],
            "Text Relevant to User Question": chunk["metadata"]["chunk"],
            "Article Publication Date": chunk["metadata"]["date"]
        }
    else:
        return {
            "Allan Gray Source Material Type": "Fund Fact Sheet",
            "Fund Name": chunk["metadata"]["fund"],
            "Fund Fact Sheet Section Title": chunk["metadata"]["section"],
            "Description and Details of Section": chunk["metadata"]["chunk"]
        }

def build_sources(similar_chunks) -> list[dict]:
    seen_articles: set[str] = set()
    seen_funds: set[str] = set()
    sources = []

    for chunk in similar_chunks:
        meta = chunk["metadata"]
        if meta.get("title"):  # article
            url = meta.get("url", "")
            if url and url not in seen_articles:
                seen_articles.add(url)
                sources.append({
                    "type": "article",
                    "title": meta["title"],
                    "url": url,
                    "label": meta["title"],
                })
        else:  # fund fact sheet
            fund = meta.get("fund", "Allan Gray Fund")
            if fund not in seen_funds:
                seen_funds.add(fund)
                display_name = fund if "Allan Gray - Orbis" in fund else fund.removeprefix("Allan Gray ").strip()
                sources.append({
                    "type": "fund_fact_sheet",
                    "title": fund,
                    "url": None,
                    "label": f"{display_name} Fact Sheet",
                })

    return sources

def rag_enhanced_llm_call(chat_history, similar_chunks, persona_prompt, system_prompt=SYSTEM_PROMPT):

    sources = build_sources(similar_chunks)

    formatted_chunks_context = {
        "Relevant context": [format_chunk(chunk) for chunk in similar_chunks]
    }

    with client.messages.stream(
        model=MODEL,
        max_tokens=2048,
        system=system_prompt.format(
            persona=persona_prompt,
            context=json.dumps(formatted_chunks_context),
            todays_date=date.today().strftime("%B %d, %Y")
        ),
        messages=chat_history,
    ) as stream:
        for text in stream.text_stream:
            yield text

    yield f"[SOURCES]{json.dumps(sources)}"


@app.post("/chat")
def chat(request: ChatRequest):
    print(f"Received chat request: {request}")

    chat_history = request.chat_history
    latest_user_message = chat_history[-1]["content"]
    persona_prompt = PERSONA_MAP.get(request.persona, PERSONA_JUST_THE_ANSWER)

    user_messages_count = len([
        message for message in chat_history 
        if message["role"] == "user"
    ])

    # Rewrites the user query if there is more than one user message
    if user_messages_count > 1:
        rewritten_user_query = query_rewrite_llm_call(
            latest_user_message, 
            chat_history, 
            REWRITE_PROMPT
        )

        similar_chunks = get_similar_chunks(rewritten_user_query, TOP_CHUNK_COUNT)

    # Default route
    else:
        similar_chunks = get_similar_chunks(latest_user_message, TOP_CHUNK_COUNT)

    return StreamingResponse(
        rag_enhanced_llm_call(chat_history, similar_chunks, persona_prompt),
        media_type="text/event-stream"
    )


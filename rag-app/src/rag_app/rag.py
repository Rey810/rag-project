"""Legacy interactive CLI. The web app in server.py is the real entry point;
this is kept as a quick terminal smoke test of retrieval + answering."""
import json
import os
from datetime import date

import anthropic
from dotenv import load_dotenv

from .config import ANSWER_EFFORT, ANSWER_MAX_TOKENS, ANSWER_MODEL, ANSWER_THINKING, TOP_CHUNK_COUNT
from .prompts import PERSONA_JUST_THE_ANSWER, SYSTEM_PROMPT
from .search import get_similar_chunks
from .used_sources import split_used_sources

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def single_conversation():
    WELCOME_MESSAGE = "Hi! I'm AllanClear, how can I help you?"
    print(WELCOME_MESSAGE)

    chat_history = [{"role": "assistant", "content": WELCOME_MESSAGE}]

    while True:
        user_input = input("User: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        chat_history.append({"role": "user", "content": user_input})

        similar_chunks = get_similar_chunks(user_input, TOP_CHUNK_COUNT)

        llm_response = rag_enhanced_query(chat_history, similar_chunks)
        chat_history.append({"role": "assistant", "content": llm_response})

        print(f"Assistant: {llm_response}\n")


def rag_enhanced_query(chat_history, similar_chunks, system_prompt=SYSTEM_PROMPT):
    context = json.dumps({
        "Relevant context": [
            {"Source Number": number, **chunk["metadata"]}
            for number, chunk in enumerate(similar_chunks, start=1)
        ]
    })

    # Same cap, thinking and effort as the server's answer call (see config.py).
    response = client.messages.create(
        model=ANSWER_MODEL,
        max_tokens=ANSWER_MAX_TOKENS,
        thinking=ANSWER_THINKING,
        output_config={"effort": ANSWER_EFFORT},
        system=system_prompt.format(
            persona=PERSONA_JUST_THE_ANSWER,
            context=context,
            todays_date=date.today().strftime("%B %d, %Y"),
        ),
        # The welcome message is assistant-first; Claude needs the first turn to be a user turn.
        messages=chat_history[1:],
    )

    # With thinking on, the first content block may be a thinking block.
    text = "".join(block.text for block in response.content if block.type == "text")
    if not text:
        return f"(no answer produced; stop reason {response.stop_reason})"

    # The prompt asks for a trailing [USED_SOURCES: ...] line; the CLI has no
    # source chips, so just drop it.
    answer, _ = split_used_sources(text)
    return answer


if __name__ == "__main__":
    single_conversation()

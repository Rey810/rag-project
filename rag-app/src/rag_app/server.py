from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from search import get_similar_chunks
from prompts import SYSTEM_PROMPT, REWRITE_PROMPT

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"
TOP_CHUNK_COUNT = 10

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    chat_history: list[dict]

def query_rewrite_llm_call(user_query, chat_history, system_prompt=SYSTEM_PROMPT):
    formatted_chat_history = "\n\n".join(
        f"{msg['role']}: {msg['content']}" for msg in chat_history
    )

    try:
        print(f"Attempting to rewrite query: {user_query}")
        response = client.responses.create(
            model=MODEL,
            instructions=system_prompt.format(
                user_query=user_query,  
                chat_history=formatted_chat_history
            ),
            input=user_query
        )

        print(f"Successfully rewritten query: {response.output_text}")
        return response.output_text
    except Exception as e:
        print(f"Query rewrite pipeline failed: {e}")
        raise

def rag_enhanced_llm_call(chat_history, similar_chunks, system_prompt=SYSTEM_PROMPT):
    formatted_chunks_context = "\n\n".join(
        f"Source {i+1}:\n{chunk}" for i, chunk in enumerate(similar_chunks)
    )

    stream = client.responses.create(
        model=MODEL,
        instructions=system_prompt.format(context=formatted_chunks_context),
        input=chat_history,
        stream=True
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta


@app.post("/chat")
def chat(request: ChatRequest):
    print(f"Received chat request: {request}")

    chat_history = request.chat_history
    latest_user_message = chat_history[-1]["content"]

    user_messages_count = len([m for m in chat_history if m["role"] == "user"])

    # TODO: think about routing
        # User -> Rewrite -> RAG
        # User -> RAG
        # User -> Web search (tool?)

    # Rewrites the user query if there is more than one user message
    if user_messages_count > 1:
        rewritten_user_query = query_rewrite_llm_call(latest_user_message, chat_history, REWRITE_PROMPT)
        similar_chunks = get_similar_chunks(rewritten_user_query, TOP_CHUNK_COUNT)

    # Default route
    else:
        similar_chunks = get_similar_chunks(latest_user_message, TOP_CHUNK_COUNT)

    return StreamingResponse(
        rag_enhanced_llm_call(chat_history, similar_chunks),
        media_type="text/event-stream"
    )


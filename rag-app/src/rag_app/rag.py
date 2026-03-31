from search import get_similar_chunks
from prompts import SYSTEM_PROMPT

import os
from dotenv import load_dotenv 
from openai import OpenAI   

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL="gpt-4o-mini"


# add those chunks to the rest of the user prompt
# generate a response
    # prompt schema: system prompt, user prompt, chunks (later: history)

# TODO: add metadata to chunk in a format that makes sense so that the LLM can reference author, date etc...


def user_llm_response():
    user_query = input("Enter a question: ")
    similar_chunks = get_similar_chunks(user_query, 10)

    query_llm(user_query, similar_chunks, SYSTEM_PROMPT)

def query_llm(user_query, similar_chunks, system_prompt):

    formatted_chunks_context = "\n\n".join(
        f"Source {i+1}:\n{chunk}" for i, chunk in enumerate(similar_chunks)
    )

    response = client.responses.create(
        model=MODEL,
        instructions=system_prompt.format(context=formatted_chunks_context),
        input=user_query
    )

    print(response.output_text)
    return response.output_text

if __name__ == "__main__":
    # test 
    user_llm_response()
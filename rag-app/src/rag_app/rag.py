from search import get_similar_chunks
from prompts import SYSTEM_PROMPT

import os
from dotenv import load_dotenv 
from openai import OpenAI   

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL="gpt-4o-mini"




def single_conversation():
    WELCOME_MESSAGE = "Hi! I'm AllanClear, how can I help you?"
    print(f"{WELCOME_MESSAGE}")

    chat_history = []
    chat_history += [{"role": "assistant", "content": WELCOME_MESSAGE }]

    
    while True:
        user_input = input("User: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        chat_history += [{"role": "user", "content": user_input}]

        similar_chunks = get_similar_chunks(user_input, 10)

        llm_response = rag_enhanced_query(chat_history, similar_chunks)
        chat_history.append({"role": "assistant", "content": llm_response})

        print(f"Assistant: {llm_response}\n")


def rag_enhanced_query(user_query, similar_chunks, system_prompt=SYSTEM_PROMPT):
    formatted_chunks_context = "\n\n".join(
        f"Source {i+1}:\n{chunk}" for i, chunk in enumerate(similar_chunks)
    )

    response = client.responses.create(
        model=MODEL,
        instructions=system_prompt.format(context=formatted_chunks_context),
        input=user_query
    )

    return response.output_text

if __name__ == "__main__":
    # test 
    single_conversation()
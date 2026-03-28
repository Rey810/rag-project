import os
from dotenv import load_dotenv 
from pinecone import Pinecone
from openai import OpenAI   

from chunker import chunk_articles

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

MODEL="gpt-4o-mini"

# TO DO: create embedding test and then do for all article chunks
response = client.responses.create(
    model=MODEL,
    input="Good day, say hi back, boss."
)

print(response.output_text)



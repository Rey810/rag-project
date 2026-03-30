import os
import json
from dotenv import load_dotenv 
from pinecone import Pinecone
from openai import OpenAI   

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

PINECONE_INDEX_NAME=os.getenv("PINECONE_INDEX_NAME")
MODEL="gpt-4o-mini"


with open("../../data/chunks.json", "r") as f:
    ALL_CHUNKS = json.load(f)


def get_embeddings(list_of_chunks):
    embeddings = client.embeddings.create(input=list_of_chunks, model="text-embedding-3-small").data

    print(f"{len(embeddings)} embeddings created for {len(list_of_chunks)} chunks")
    return embeddings


def upsert_to_pinecone(list_of_chunks):
# try to add the embedding to Pinecone
    index = pc.Index(PINECONE_INDEX_NAME)
    vectors = [ 
        {
            "id": chunk["chunk_id"],
            "values": chunk["embedding"],
            "metadata": {
                k: v if v is not None else "" 
                for k, v in chunk.items() 
                if k not in ("chunk_id", "embedding")}
        } for chunk in list_of_chunks
    ] 

    index.upsert(vectors=vectors)


def create_and_upsert_embeddings(chunks, batch_size=100):
    try:
        # iterate over the chunks and process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            content_to_embed = [chunk["chunk"] for chunk in batch]
            embeddings = get_embeddings(content_to_embed)
            print(f"Embeddings for batch {i // 100 + 1} created")

            # iterate over the embeddings and add embedding to it's respective chunk
            for embedding, chunk in zip(embeddings, batch):
                chunk["embedding"] = embedding.embedding
            
            upsert_to_pinecone(batch)
            print(f"Batch {i // 100 + 1} upserted to Pinecone")

        print(f"Done. Created {len(chunks)} embeddings and upserted to Pinecone")
    except Exception as e:
        print(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    create_and_upsert_embeddings(ALL_CHUNKS)
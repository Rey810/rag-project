import os
import json
from dotenv import load_dotenv 
from pinecone import Pinecone
from openai import OpenAI   

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

MODEL="gpt-4o-mini"
PINECONE_INDEX_NAME= os.getenv("PINECONE_INDEX_NAME")
INDEX = pc.Index(PINECONE_INDEX_NAME)

import os
import uuid
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter

ARTICLES_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "articles")

# Chunk articles
def chunk_text(text, chunk_size=1950, chunk_overlap=300):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_text(text)
    return chunks

def chunk_articles():
    chunks_with_metadata = []

    for filename in os.listdir(ARTICLES_FILE_PATH):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(ARTICLES_FILE_PATH, filename)

        with open(filepath, "r") as f:
            data = json.load(f)

        article_chunks = chunk_text(data["body"])
        print(f"[{filename}] \"{data['title']}\" -> {len(article_chunks)} chunks")

        for chunk_count, article_chunk in enumerate(article_chunks):
            chunk_id = str(uuid.uuid4())

            # Prepend metadata into the text that gets embedded
            enriched_chunk = (
                f"Article: {data['title']}\n"
                f"Author: {data['author']}\n"
                f"Publication Date: {data['date']}\n"
                f"Category: {data['category']}\n"
                f"---\n"
                f"{article_chunk}"
            )

            chunks_with_metadata.append({
                "title": data["title"],
                "author": data["author"],
                "date": data["date"],
                "category": data["category"],
                "url": data["url"],
                "chunk": enriched_chunk,
                "chunk_id": chunk_id,
                "chunk_count": chunk_count,
                "source_type": "article"
            })

    print(f"\nDone. {len(chunks_with_metadata)} total chunks from {len(os.listdir(ARTICLES_FILE_PATH))} files.")
    return chunks_with_metadata


def get_embeddings(list_of_chunks):
    embeddings = client.embeddings.create(input=list_of_chunks, model="text-embedding-3-small").data

    if len(list_of_chunks) > 1:
        print(f"{len(embeddings)} embeddings created for {len(list_of_chunks)} chunks")
    return embeddings


def upsert_to_pinecone(list_of_chunks):
    # try to add the embedding to Pinecone
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

    INDEX.upsert(vectors=vectors)


def create_and_upsert_embeddings(chunks, batch_size=100, deleteIndex=False):

    if deleteIndex:
        try:
            print(f"Attempting to delete index {PINECONE_INDEX_NAME}")
            INDEX.delete(delete_all=True)
            print(f"Index {PINECONE_INDEX_NAME} successfully deleted")
        
        except Exception as e:
            print(f"Deleting index failed: {e}")
            raise

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
    # Chunk articles and save to file
    chunks = chunk_articles()
    print(f"\nFirst chunk preview:\n{json.dumps(chunks[0], indent=2)}")
    print(f"\nSecond chunk preview:\n{json.dumps(chunks[1], indent=2)}")

    chunks_file = os.path.join(os.path.dirname(__file__), "data", "article_chunks.json")
    with open(chunks_file, "w") as f:
        json.dump(chunks, f)
    print(f"\nChunks saved to {chunks_file}")

    with open(chunks_file, "r") as f:
        ALL_CHUNKS = json.load(f)

    create_and_upsert_embeddings(ALL_CHUNKS)
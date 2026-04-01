import os
import uuid
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter

ARTICLES_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "articles")


def chunk_text(text, chunk_size=1000, chunk_overlap=200):
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
            chunks_with_metadata.append({
                "title": data["title"],
                "author": data["author"],
                "date": data["date"],
                "category": data["category"],
                "url": data["url"],
                "chunk": article_chunk,
                "chunk_id": chunk_id,
                "chunk_count": chunk_count,
                "source_type": "article"
            })

    print(f"\nDone. {len(chunks_with_metadata)} total chunks from {len(os.listdir(ARTICLES_FILE_PATH))} files.")
    return chunks_with_metadata

def create_and_save_chunks():
    with open(os.path.join(os.path.dirname(__file__), "data", "chunks.json"), "w") as f:
        chunks_with_metadata = chunk_articles()
        json.dump(chunks_with_metadata, f, indent=2)

    return chunks_with_metadata


if __name__ == "__main__":
    chunks = create_and_save_chunks()
    print(f"\nFirst chunk preview:\n{json.dumps(chunks[0], indent=2)}")
    print(f"\nSecond chunk preview:\n{json.dumps(chunks[1], indent=2)}")


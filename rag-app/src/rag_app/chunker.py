import os
import uuid
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_text(text)
    return chunks

def chunk_articles():
    chunks_with_metadata = []

    for filename in os.listdir("data/articles/"):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join("data/articles/", filename)

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
                "chunk": article_chunk[1],
                "chunk_id": chunk_id,
                "chunk_count": chunk_count,
                "source_type": "article"
            })

    print(f"\nDone. {len(chunks_with_metadata)} total chunks from {len(os.listdir('data/articles/'))} files.")
    return chunks_with_metadata


if __name__ == "__main__":
    chunks = chunk_articles()
    print(f"\nFirst chunk preview:\n{json.dumps(chunks[0], indent=2)}")
    print(f"\nSecond chunk preview:\n{json.dumps(chunks[1], indent=2)}")


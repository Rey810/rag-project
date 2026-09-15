"""
Article ingestion pipeline.

Chunks the scraped articles in ``data/articles/``, writes them to
``data/article_chunks.json``, then embeds and upserts them to Pinecone.

Run from rag-app/:
    python -m rag_app.pipeline.article_ingest               # chunk, save, embed, upsert
    python -m rag_app.pipeline.article_ingest --chunk-only   # chunk + save only (no API calls)
    python -m rag_app.pipeline.article_ingest --wipe         # delete all vectors first, then upsert
"""
import argparse
import json
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..embeddings import get_embeddings
from ..paths import ARTICLE_CHUNKS_PATH, ARTICLES_DIR
from ..vector_store import get_index

CHUNK_SIZE = 1950
CHUNK_OVERLAP = 300
BATCH_SIZE = 100


def chunk_text(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return text_splitter.split_text(text)


def chunk_articles() -> list[dict]:
    chunks_with_metadata: list[dict] = []

    article_files = sorted(ARTICLES_DIR.glob("*.json"))
    if not article_files:
        print(f"No article JSON files found in {ARTICLES_DIR}")
        return chunks_with_metadata

    for filepath in article_files:
        with filepath.open("r") as f:
            data = json.load(f)

        article_chunks = chunk_text(data["body"])
        print(f"[{filepath.name}] \"{data['title']}\" -> {len(article_chunks)} chunks")

        for chunk_count, article_chunk in enumerate(article_chunks):
            # Deterministic id so re-runs overwrite instead of duplicating.
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{data['url']}#{chunk_count}"))

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

    print(f"\nDone. {len(chunks_with_metadata)} total chunks from {len(article_files)} files.")
    return chunks_with_metadata


def save_chunks(chunks: list[dict]) -> None:
    ARTICLE_CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ARTICLE_CHUNKS_PATH.open("w") as f:
        json.dump(chunks, f)
    print(f"\nChunks saved to {ARTICLE_CHUNKS_PATH}")


def upsert_chunks(chunks: list[dict]) -> None:
    """Upsert already-embedded chunks. Metadata is every key except chunk_id/embedding."""
    vectors = [
        {
            "id": chunk["chunk_id"],
            "values": chunk["embedding"],
            "metadata": {
                k: v if v is not None else ""
                for k, v in chunk.items()
                if k not in ("chunk_id", "embedding")
            },
        }
        for chunk in chunks
    ]

    get_index().upsert(vectors=vectors)


def wipe_index() -> None:
    index = get_index()
    print("=" * 72)
    print("!! WIPE REQUESTED: deleting ALL vectors from the Pinecone index !!")
    print("!! (index.delete(delete_all=True) -- this cannot be undone)      !!")
    print("=" * 72)
    try:
        index.delete(delete_all=True)
        print("All vectors deleted.")
    except Exception as e:
        print(f"Deleting all vectors failed: {e}")
        raise


def create_and_upsert_embeddings(chunks: list[dict], batch_size: int = BATCH_SIZE, wipe: bool = False) -> None:
    if wipe:
        wipe_index()

    try:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1

            content_to_embed = [chunk["chunk"] for chunk in batch]
            embeddings = get_embeddings(content_to_embed)
            print(f"Embeddings for batch {batch_num} created ({len(embeddings)} embeddings for {len(batch)} chunks)")

            for embedding, chunk in zip(embeddings, batch):
                chunk["embedding"] = embedding

            upsert_chunks(batch)
            print(f"Batch {batch_num} upserted to Pinecone")

        print(f"Done. Created {len(chunks)} embeddings and upserted to Pinecone")
    except Exception as e:
        print(f"Pipeline failed: {e}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk scraped articles, then embed and upsert them to Pinecone."
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Delete ALL vectors from the Pinecone index before upserting.",
    )
    parser.add_argument(
        "--chunk-only",
        action="store_true",
        help="Only chunk articles and write article_chunks.json; no OpenAI/Pinecone calls.",
    )
    args = parser.parse_args()

    chunks = chunk_articles()
    if not chunks:
        print("Nothing to do.")
        return

    print(f"\nFirst chunk preview:\n{json.dumps(chunks[0], indent=2)}")
    save_chunks(chunks)

    if args.chunk_only:
        print("--chunk-only: stopping before embedding/upsert.")
        return

    with ARTICLE_CHUNKS_PATH.open("r") as f:
        all_chunks = json.load(f)

    create_and_upsert_embeddings(all_chunks, wipe=args.wipe)


if __name__ == "__main__":
    main()

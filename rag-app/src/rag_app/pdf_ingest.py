"""
Fund fact sheet ingestion pipeline.

Part A: Batch convert all PDFs in data/fund_fact_sheets/ to Markdown.
Part B: Split Markdown files into section chunks.
Part C: Generate contextual descriptions for each chunk using GPT-4o.

Run from rag-app/:
    poetry run python src/rag_app/pdf_ingest.py
"""
import json
import os
import re
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client

from prompts import CONTEXTUAL_ADDITION_PROMPT

PDF_DIR = Path("data/fund_fact_sheets")
MARKDOWN_DIR = PDF_DIR / "markdown"
CHUNKS_PATH = PDF_DIR / "fund_fact_sheet_chunks.json"


def extract_fund_name(markdown: str) -> str | None:
    """Return the fund name from the first ## heading that starts with 'Allan Gray' or 'Orbis'."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading_text = stripped[3:].strip()
            if heading_text.startswith("Allan Gray") or heading_text.startswith("Orbis"):
                return heading_text
    return None


def convert_all_pdfs() -> None:
    from docling.document_converter import DocumentConverter

    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {PDF_DIR.resolve()}")
        return

    print(f"Found {len(pdf_files)} PDF(s) to convert.\n")

    converter = DocumentConverter()

    for i, pdf_path in enumerate(pdf_files, start=1):
        out_path = MARKDOWN_DIR / (pdf_path.stem + ".md")
        print(f"[{i}/{len(pdf_files)}] Converting: {pdf_path.name}")

        result = converter.convert(str(pdf_path))
        markdown = result.document.export_to_markdown()

        out_path.write_text(markdown, encoding="utf-8")

        fund_name = extract_fund_name(markdown)
        if fund_name:
            print(f"           Fund name : {fund_name}")
        print(f"           Saved to  : {out_path}")

    print(f"\nDone. {len(pdf_files)} file(s) converted to {MARKDOWN_DIR}.")


def split_markdown_into_chunks(md_path: Path, fund_name: str) -> list[dict]:
    """Split a Markdown file on ## headings, returning one chunk per section."""
    text = md_path.read_text(encoding="utf-8")

    # Split on lines that start a ## heading; keep the delimiter with the section.
    # re.split with a capturing group keeps the delimiter in the result list.
    parts = re.split(r"(?m)^(## .+)$", text)

    # parts layout: [preamble, heading1, body1, heading2, body2, ...]
    # The preamble (before the first ## heading) is discarded.
    chunks = []
    chunk_index = 0

    for i in range(1, len(parts) - 1, 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        section_name = heading[3:].strip()  # strip leading "## "
        chunk_text = f"{heading}\n\n{body}".strip()

        if len(chunk_text) < 100:
            continue

        chunks.append(
            {
                "chunk_id": str(uuid.uuid4()),
                "source_type": "fund_fact_sheet",
                "fund": fund_name,
                "section": section_name,
                "chunk_index": chunk_index,
                "chunk": chunk_text,
            }
        )
        chunk_index += 1

    return chunks


def split_all_markdowns() -> None:
    md_files = sorted(MARKDOWN_DIR.glob("*.md"))
    if not md_files:
        print(f"No Markdown files found in {MARKDOWN_DIR.resolve()}")
        return

    print(f"Found {len(md_files)} Markdown file(s) to split.\n")

    all_chunks: list[dict] = []

    for md_path in md_files:
        markdown = md_path.read_text(encoding="utf-8")
        fund_name = extract_fund_name(markdown) or md_path.stem.strip()
        chunks = split_markdown_into_chunks(md_path, fund_name)
        all_chunks.extend(chunks)
        print(f"  {md_path.name}: {len(chunks)} chunk(s)  [fund: {fund_name}]")

    CHUNKS_PATH.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Saved to: {CHUNKS_PATH.resolve()}")

    # Show a sample of 3 chunks
    print("\n--- Sample chunks ---")
    for chunk in all_chunks[:3]:
        preview = chunk["chunk"][:100].replace("\n", " ")
        print(
            f"  fund        : {chunk['fund']}\n"
            f"  section     : {chunk['section']}\n"
            f"  chunk_index : {chunk['chunk_index']}\n"
            f"  chunk_id    : {chunk['chunk_id']}\n"
            f"  chunk[:100] : {preview}\n"
        )


def generate_descriptions() -> None:
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    # Skip chunks that already have descriptions (don't start with "## ")
    remaining = [(i, c) for i, c in enumerate(chunks) if c["chunk"].startswith("## ")]
    print(f"Generating descriptions for {len(remaining)}/{len(chunks)} chunks...\n")

    # Build fund name -> full markdown lookup
    md_by_fund: dict[str, str] = {}
    for md_path in MARKDOWN_DIR.glob("*.md"):
        markdown = md_path.read_text(encoding="utf-8")
        fund_name = extract_fund_name(markdown) or md_path.stem.strip()
        md_by_fund[fund_name] = markdown

    client = _get_openai_client()

    for count, (i, chunk) in enumerate(remaining, start=1):
        fund_name = chunk["fund"]
        section_text = chunk["chunk"]
        full_markdown = md_by_fund.get(fund_name, "")

        prompt = CONTEXTUAL_ADDITION_PROMPT.format(
            fund_name=fund_name,
            full_markdown=full_markdown,
            section_text=section_text,
        )

        response = client.responses.create(
            model="gpt-4o",
            input=prompt,
            temperature=0,
        )
        description = response.output_text.strip()
        chunk["chunk"] = f"{description}\n\n{section_text}"

        print(f"[{count}/{len(remaining)}] {fund_name} — {chunk['section']}")

        # Save every 50 chunks
        if count % 50 == 0:
            CHUNKS_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  (saved progress at {count}/{len(remaining)})")

        time.sleep(0.5)

    CHUNKS_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. Updated chunks saved to {CHUNKS_PATH.resolve()}")


def embed_and_upsert(batch_size: int = 100) -> None:
    from article_ingest import get_embeddings, upsert_to_pinecone

    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    print(f"Embedding and upserting {len(chunks)} chunks in batches of {batch_size}...\n")

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        content_to_embed = [chunk["chunk"] for chunk in batch]
        embeddings = get_embeddings(content_to_embed)

        for embedding, chunk in zip(embeddings, batch):
            chunk["embedding"] = embedding.embedding

        upsert_to_pinecone(batch)
        batch_num = i // batch_size + 1
        print(f"  Batch {batch_num} upserted ({len(batch)} vectors)")

    print(f"\nDone. {len(chunks)} vectors upserted to Pinecone.")


if __name__ == "__main__":
    # convert_all_pdfs()
    # split_all_markdowns()
    # generate_descriptions()
    embed_and_upsert()

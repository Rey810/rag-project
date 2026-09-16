"""
Fund fact sheet ingestion pipeline.

Part A (--convert) : Batch convert all PDFs in data/fund_fact_sheets/ to Markdown.
Part B (--split)   : Split Markdown files into section chunks.
Part C (--describe): Generate contextual descriptions for each chunk using Claude.
Part D (--upsert)  : Embed the chunks and upsert them to Pinecone.

Run from rag-app/:
    python -m rag_app.pipeline.pdf_ingest                  # --upsert only (default)
    python -m rag_app.pipeline.pdf_ingest --convert --split --describe --upsert
"""
import argparse
import json
import os
import re
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
import anthropic

from ..embeddings import get_embeddings
from ..paths import (
    FUND_FACT_SHEET_CHUNKS_PATH,
    FUND_FACT_SHEET_MARKDOWN_DIR,
    FUND_FACT_SHEETS_DIR,
)
from ..prompts import CONTEXTUAL_ADDITION_PROMPT
from ..config import NO_THINKING
from .article_ingest import upsert_chunks

load_dotenv()

DESCRIPTION_MODEL = "claude-sonnet-5"

_anthropic_client: anthropic.Anthropic | None = None


def _get_anthropic_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _anthropic_client


# Every fact sheet states its reporting date once, either as "Fact Sheet at
# 28 February 2026" (Orbis sheets) or "Fund information on 28 February 2026"
# (Allan Gray sheets). Stored on each chunk as `as_at` so the chat model can
# date figures that don't carry their own period.
_AS_AT_RE = re.compile(
    r"(?:Fact Sheet at|Fund information on)\s+(\d{1,2} [A-Z][a-z]+ \d{4})", re.IGNORECASE
)


def extract_as_at_date(markdown: str) -> str | None:
    match = _AS_AT_RE.search(markdown)
    return match.group(1) if match else None


PDF_DIR = FUND_FACT_SHEETS_DIR
MARKDOWN_DIR = FUND_FACT_SHEET_MARKDOWN_DIR
CHUNKS_PATH = FUND_FACT_SHEET_CHUNKS_PATH


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


def split_markdown_into_chunks(md_path: Path, fund_name: str, as_at: str | None) -> list[dict]:
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
                "as_at": as_at,
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
        as_at = extract_as_at_date(markdown)
        if not as_at:
            print(f"  WARNING: no 'as at' date found in {md_path.name}")
        chunks = split_markdown_into_chunks(md_path, fund_name, as_at)
        all_chunks.extend(chunks)
        print(f"  {md_path.name}: {len(chunks)} chunk(s)  [fund: {fund_name}, as at: {as_at}]")

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

    client = _get_anthropic_client()

    for count, (i, chunk) in enumerate(remaining, start=1):
        fund_name = chunk["fund"]
        section_text = chunk["chunk"]
        full_markdown = md_by_fund.get(fund_name, "")

        prompt = CONTEXTUAL_ADDITION_PROMPT.format(
            fund_name=fund_name,
            full_markdown=full_markdown,
            section_text=section_text,
        )

        response = client.messages.create(
            model=DESCRIPTION_MODEL,
            max_tokens=300,
            temperature=0,
            thinking=NO_THINKING,
            messages=[{"role": "user", "content": prompt}],
        )
        description = response.content[0].text.strip()
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
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    print(f"Embedding and upserting {len(chunks)} chunks in batches of {batch_size}...\n")

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        content_to_embed = [chunk["chunk"] for chunk in batch]
        embeddings = get_embeddings(content_to_embed)

        for embedding, chunk in zip(embeddings, batch):
            chunk["embedding"] = embedding

        upsert_chunks(batch)
        batch_num = i // batch_size + 1
        print(f"  Batch {batch_num} upserted ({len(batch)} vectors)")

    print(f"\nDone. {len(chunks)} vectors upserted to Pinecone.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fund fact sheet ingestion pipeline (PDF -> Markdown -> chunks -> Pinecone)."
    )
    parser.add_argument("--convert", action="store_true", help="Part A: convert PDFs to Markdown (needs docling).")
    parser.add_argument("--split", action="store_true", help="Part B: split Markdown into section chunks.")
    parser.add_argument("--describe", action="store_true", help="Part C: add Claude-generated contextual descriptions.")
    parser.add_argument("--upsert", action="store_true", help="Part D: embed chunks and upsert to Pinecone.")
    args = parser.parse_args()

    # No flags = just upsert (the previous default behaviour).
    if not (args.convert or args.split or args.describe or args.upsert):
        args.upsert = True

    if args.convert:
        convert_all_pdfs()
    if args.split:
        split_all_markdowns()
    if args.describe:
        generate_descriptions()
    if args.upsert:
        embed_and_upsert()


if __name__ == "__main__":
    main()

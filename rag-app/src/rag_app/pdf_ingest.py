"""
Fund fact sheet ingestion pipeline.

Part A: Batch convert all PDFs in data/fund_fact_sheets/ to Markdown.

Run from rag-app/:
    poetry run python src/rag_app/pdf_ingest.py
"""
import re
from pathlib import Path

from docling.document_converter import DocumentConverter

PDF_DIR = Path("data/fund_fact_sheets")
MARKDOWN_DIR = PDF_DIR / "markdown"


def extract_fund_name(markdown: str) -> str | None:
    """Return the text of the first top-level heading, or None if not found."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def convert_all_pdfs() -> None:
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


if __name__ == "__main__":
    convert_all_pdfs()

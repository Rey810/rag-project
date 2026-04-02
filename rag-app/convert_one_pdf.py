"""
Step 2 validation script: Convert one PDF to Markdown using Docling.
"""
from pathlib import Path
from docling.document_converter import DocumentConverter

PDF_PATH = Path("data/fund_fact_sheets/Allan Gray Balanced Fund.pdf")
OUT_PATH = Path("data/fund_fact_sheets/markdown/Allan Gray Balanced Fund.md")

def main():
    print(f"Converting: {PDF_PATH}")
    converter = DocumentConverter()
    result = converter.convert(str(PDF_PATH))
    markdown = result.document.export_to_markdown()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(markdown, encoding="utf-8")
    print(f"Saved to: {OUT_PATH}")
    print(f"Output length: {len(markdown)} characters")

if __name__ == "__main__":
    main()

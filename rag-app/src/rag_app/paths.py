"""Filesystem locations shared by the pipeline scripts.

Everything lives under ``rag-app/data/`` (gitignored), outside the Python
package, so it never ends up in the deploy image.
"""
from pathlib import Path

RAG_APP_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = RAG_APP_DIR / "data"
ARTICLES_DIR = DATA_DIR / "articles"
ARTICLE_CHUNKS_PATH = DATA_DIR / "article_chunks.json"
FUND_FACT_SHEETS_DIR = DATA_DIR / "fund_fact_sheets"
FUND_FACT_SHEET_MARKDOWN_DIR = FUND_FACT_SHEETS_DIR / "markdown"
FUND_FACT_SHEET_CHUNKS_PATH = FUND_FACT_SHEETS_DIR / "fund_fact_sheet_chunks.json"

"""Retrieval check: do Fund Fact Sheet Chunks reach the model for fund questions?

Runs a fixed list of fund questions through ``get_similar_chunks`` with the
production Chunk count and prints every result. A query passes when a Fund Fact
Sheet Chunk for the expected fund is among the results.

Run from rag-app/ with the venv active::

    PYTHONPATH=src python scripts/retrieval_check.py

Each query costs one embedding call and one rerank request (500/month on the
current Pinecone plan). There are no retries.
"""
from rag_app.config import TOP_CHUNK_COUNT
from rag_app.search import get_similar_chunks, is_article

BALANCED = "Allan Gray Balanced Fund"
STABLE = "Allan Gray Stable Fund"

# (query, expected fund whose Fund Fact Sheet must appear)
CHECKS: list[tuple[str, str]] = [
    ("Allan Gray Balanced Fund fact sheet", BALANCED),
    ("What is the TER of the Balanced Fund?", BALANCED),
    ("Balanced Fund performance over 1, 3, 5 and 10 years", BALANCED),
    ("What is the asset allocation of the Allan Gray Balanced Fund?", BALANCED),
    ("Show me the latest Balanced Fund fact sheet", BALANCED),
    ("Stable Fund annualised returns", STABLE),
    (
        "I live in Spain and earn in euros. I have a lump sum of R200,000 and can "
        "invest R5,000 a month. My brother holds the Balanced Fund and the Tax-Free "
        "Balanced Fund. Should I put the lump sum in the Balanced Fund or a tax-free "
        "account, and is a retirement annuity better than the Orbis Global Equity "
        "Feeder Fund or the Orbis Global Balanced Feeder Fund for a 20-year horizon?",
        BALANCED,
    ),
]


def describe(match) -> str:
    meta = match["metadata"]
    if is_article(match):
        return f"article          | {meta['title']} | {meta.get('date', '')}"
    return f"fund_fact_sheet  | {meta.get('fund', '')} | {meta.get('section', '')} | {meta.get('as_at', '')}"


def main() -> None:
    passed = 0
    for query, expected_fund in CHECKS:
        print(f"\n=== {query}")
        results = get_similar_chunks(query, TOP_CHUNK_COUNT)
        found = False
        for rank, match in enumerate(results, start=1):
            meta = match["metadata"]
            hit = not is_article(match) and meta.get("fund") == expected_fund
            found = found or hit
            print(f"{rank:>2}. {'*' if hit else ' '} {describe(match)}")
        status = "PASS" if found else "FAIL"
        passed += found
        print(f"--- {status}: {expected_fund} Fund Fact Sheet {'found' if found else 'missing'}")

    print(f"\n{passed}/{len(CHECKS)} queries passed")


if __name__ == "__main__":
    main()

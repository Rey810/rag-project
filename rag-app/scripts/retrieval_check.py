"""Retrieval check: do Fund Fact Sheet Chunks reach the model for fund questions?

Runs a fixed list of fund questions through ``get_similar_chunks`` with the
production Chunk count and prints every result. A query passes when a Fund Fact
Sheet Chunk for every expected fund is among the results. A query that expects
no fund is a control: it passes when ``detect_funds`` finds nothing, and the
detected list is printed so a false match is visible.

Run from rag-app/ with the venv active::

    PYTHONPATH=src python scripts/retrieval_check.py

Each query costs one embedding call and one rerank request (500/month on the
current Pinecone plan). There are no retries.
"""
from rag_app.config import TOP_CHUNK_COUNT
from rag_app.funds import detect_funds
from rag_app.search import get_similar_chunks, is_article

BALANCED = "Allan Gray Balanced Fund"
STABLE = "Allan Gray Stable Fund"
TAX_FREE_BALANCED = "Allan Gray Tax-Free Balanced Fund"
ORBIS_EQUITY_FEEDER = "Allan Gray - Orbis Global Equity Feeder Fund"
ORBIS_BALANCED_FEEDER = "Allan Gray - Orbis Global Balanced Feeder Fund"

# (query, funds whose Fund Fact Sheet must all appear; empty = no fund expected)
CHECKS: list[tuple[str, tuple[str, ...]]] = [
    ("Allan Gray Balanced Fund fact sheet", (BALANCED,)),
    ("What is the TER of the Balanced Fund?", (BALANCED,)),
    ("Balanced Fund performance over 1, 3, 5 and 10 years", (BALANCED,)),
    ("What is the asset allocation of the Allan Gray Balanced Fund?", (BALANCED,)),
    ("Show me the latest Balanced Fund fact sheet", (BALANCED,)),
    ("Stable Fund annualised returns", (STABLE,)),
    (
        "I live in Spain and earn in euros. I have a lump sum of R200,000 and can "
        "invest R5,000 a month. My brother holds the Balanced Fund and the Tax-Free "
        "Balanced Fund. Should I put the lump sum in the Balanced Fund or a tax-free "
        "account, and is a retirement annuity better than the Orbis Global Equity "
        "Feeder Fund or the Orbis Global Balanced Feeder Fund for a 20-year horizon?",
        (BALANCED, TAX_FREE_BALANCED, ORBIS_EQUITY_FEEDER, ORBIS_BALANCED_FEEDER),
    ),
    ("Compare the Stable Fund and the Balanced Fund over 10 years", (STABLE, BALANCED)),
    ("What does Allan Gray think about South African equities?", ()),
]


def describe(match) -> str:
    meta = match["metadata"]
    if is_article(match):
        return f"article          | {meta['title']} | {meta.get('date', '')}"
    return f"fund_fact_sheet  | {meta.get('fund', '')} | {meta.get('section', '')} | {meta.get('as_at', '')}"


def main() -> None:
    passed = 0
    for query, expected_funds in CHECKS:
        print(f"\n=== {query}")
        detected = detect_funds(query)
        print(f"detected funds: {detected}")
        results = get_similar_chunks(query, TOP_CHUNK_COUNT)
        print(f"chunks: {len(results)}")
        found: set[str] = set()
        for rank, match in enumerate(results, start=1):
            meta = match["metadata"]
            hit = not is_article(match) and meta.get("fund") in expected_funds
            if hit:
                found.add(meta["fund"])
            print(f"{rank:>2}. {'*' if hit else ' '} {describe(match)}")
        if expected_funds:
            missing = [fund for fund in expected_funds if fund not in found]
            ok = not missing
            detail = "all found" if ok else f"missing {missing}"
            print(f"--- {'PASS' if ok else 'FAIL'}: {len(expected_funds)} expected Fund Fact Sheet(s), {detail}")
        else:
            ok = not detected
            print(f"--- {'PASS' if ok else 'FAIL'}: control query, {'no fund detected' if ok else f'false match {detected}'}")
        passed += ok

    print(f"\n{passed}/{len(CHECKS)} queries passed")


if __name__ == "__main__":
    main()

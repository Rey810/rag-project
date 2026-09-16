from collections import Counter
from collections.abc import Sequence

from .config import MAX_CHUNK_COUNT
from .embeddings import get_embeddings
from .funds import detect_funds
from .vector_store import get_client, get_index

# Dense search alone tends to return near-identical sections from sibling funds
# (Balanced vs Tax-Free Balanced vs Stable). So we over-fetch RERANK_CANDIDATES
# by embedding similarity, score them with Pinecone's hosted cross-encoder, and
# fuse the two rankings (reciprocal rank fusion). The reranker is very good at
# telling funds apart but over-favours prose articles on its own; the dense rank
# keeps it honest. Measured on sample queries: fusion put the right fact-sheet
# section first where rerank alone buried it under articles.
#
# Article Chunks are ~90% of the index and many carry a fund's name in their
# title, so they crowd Fund Fact Sheet Chunks out of the dense top 20 entirely
# ("Stable Fund annualised returns" returned 20 Articles). A second, Fund Fact
# Sheet only query guarantees the reranker sees some, and capping Chunks per
# Article stops one Article filling several of the final slots.
#
# When the query names several funds, one embedding expresses only one blend
# of the names and the longer Orbis names win: the best Balanced Fund Chunk
# sat at rank 18 of the Fund Fact Sheet only list on a four-fund question. So
# each fund detected in the query text also gets a small fund-filtered query,
# which guarantees it a place in the candidate set at dense rank 1.
RERANK_MODEL = "bge-reranker-v2-m3"
RERANK_CANDIDATES = 20
FACT_SHEET_CANDIDATES = 10
FUND_CANDIDATES = 3
MAX_CHUNKS_PER_ARTICLE = 2
FACT_SHEET_FILTER = {"source_type": {"$eq": "fund_fact_sheet"}}


def get_query_embedding(query: str) -> list[float]:
    return get_embeddings([query])[0]


def search_vectordb(query_embedding: list[float], top_k: int = 3, metadata_filter: dict | None = None):
    return get_index().query(
        vector=query_embedding, top_k=top_k, include_metadata=True, filter=metadata_filter
    )


def is_article(match) -> bool:
    return bool(match["metadata"].get("title"))


def dedupe_articles(matches, limit: int = MAX_CHUNKS_PER_ARTICLE):
    """Keep at most ``limit`` Chunks per Article URL, in the given order (so the
    higher-scoring ones survive). Fund Fact Sheet Chunks are never dropped:
    each section is distinct information."""
    per_article: Counter[str] = Counter()
    kept = []
    for match in matches:
        url = match["metadata"].get("url") if is_article(match) else None
        if url:
            if per_article[url] >= limit:
                continue
            per_article[url] += 1
        kept.append(match)
    return kept


def fund_filter(fund: str) -> dict:
    return {"fund": {"$eq": fund}}


def gather_candidates(query_embedding: list[float], top_k: int, funds: Sequence[str]):
    """Union of the general dense top-N, a Fund Fact Sheet only dense top-N and,
    per named fund, a fund-filtered dense top-FUND_CANDIDATES, all with the
    same embedding, deduped by Chunk id, then capped per Article.

    The union is ordered by each Chunk's best rank in any list, not by raw
    score: Fund Fact Sheet Chunks score lower on cosine similarity than Article
    prose for the same question, so sorting the union by score would put every
    fact sheet behind every Article and the fusion below would bury them
    again. Ties keep the higher score first."""
    general = search_vectordb(query_embedding, max(top_k, RERANK_CANDIDATES)).matches
    fact_sheets = search_vectordb(
        query_embedding, FACT_SHEET_CANDIDATES, metadata_filter=FACT_SHEET_FILTER
    ).matches
    per_fund = [
        search_vectordb(query_embedding, FUND_CANDIDATES, metadata_filter=fund_filter(fund)).matches
        for fund in funds
    ]

    by_id = {}
    best_rank: dict[str, int] = {}
    for ranked in (general, fact_sheets, *per_fund):
        for rank, match in enumerate(ranked):
            by_id.setdefault(match["id"], match)
            best_rank[match["id"]] = min(best_rank.get(match["id"], rank), rank)
    ordered = sorted(by_id.values(), key=lambda m: (best_rank[m["id"]], -m["score"]))
    return dedupe_articles(ordered)


def rerank_text(match) -> str:
    """Text the reranker scores. Article chunks already carry their title and
    metadata; fact-sheet chunks get the fund and section prepended so the
    reranker can tell sibling funds apart."""
    meta = match["metadata"]
    if is_article(match):
        return meta["chunk"]
    return f"{meta.get('fund', '')}\n{meta.get('section', '')}\n{meta['chunk']}"


def rerank(query: str, matches, top_k: int, rrf_k: int = 60):
    """Reorder dense matches by reciprocal rank fusion of the dense rank and the
    hosted reranker's rank, and keep the best top_k. Falls back to the dense
    order if the rerank call fails, so retrieval keeps working when the
    reranker is unavailable or over quota."""
    if len(matches) <= 1:
        return matches[:top_k]
    try:
        result = get_client().inference.rerank(
            model=RERANK_MODEL,
            query=query,
            documents=[{"id": m["id"], "text": rerank_text(m)} for m in matches],
            top_n=len(matches),
            return_documents=False,
            # Long fact-sheet tables can exceed the reranker's token limit; without
            # this the call 400s and every such query silently falls back.
            parameters={"truncate": "END"},
        )
    except Exception as e:
        print(f"Rerank failed, falling back to dense order: {e}")
        return matches[:top_k]

    rerank_rank = {row.index: rank for rank, row in enumerate(result.data)}
    fused = sorted(
        range(len(matches)),
        key=lambda i: 1 / (rrf_k + i) + 1 / (rrf_k + rerank_rank.get(i, len(matches))),
        reverse=True,
    )
    return [matches[i] for i in fused[:top_k]]


def chunk_count(top_k: int, fund_count: int) -> int:
    """``top_k`` is the base Chunk count. With two or more named funds each
    extra fund adds FUND_CANDIDATES so the fund-filtered Chunks do not push
    each other out, capped at MAX_CHUNK_COUNT (four funds and a base of 10
    give 19). Zero or one fund leaves ``top_k`` unchanged."""
    if fund_count < 2:
        return top_k
    return min(top_k + FUND_CANDIDATES * (fund_count - 1), MAX_CHUNK_COUNT)


def get_similar_chunks(query: str, top_k: int = 3):
    """Top Chunks for ``query``. ``top_k`` is the base count; a query naming
    several funds returns more (see ``chunk_count``). Fund names are detected
    in ``query`` itself, so the caller should pass the retrieval query (the
    rewritten one from the second turn onward), not the raw message."""
    try:
        funds = detect_funds(query)
        query_embedding = get_query_embedding(query)
        candidates = gather_candidates(query_embedding, top_k, funds)
        return rerank(query, candidates, chunk_count(top_k, len(funds)))
    except Exception as e:
        print(f"Query embedding and chunking retrieval pipeline failed: {e}")
        raise


if __name__ == "__main__":
    for chunk in get_similar_chunks("hello I am looking for investment advice", 5):
        print(chunk["metadata"].get("title") or chunk["metadata"].get("fund"), "|", chunk["metadata"]["chunk"][:80])

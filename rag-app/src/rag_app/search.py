from .embeddings import get_embeddings
from .vector_store import get_client, get_index

# Dense search alone tends to return near-identical sections from sibling funds
# (Balanced vs Tax-Free Balanced vs Stable). So we over-fetch RERANK_CANDIDATES
# by embedding similarity, score them with Pinecone's hosted cross-encoder, and
# fuse the two rankings (reciprocal rank fusion). The reranker is very good at
# telling funds apart but over-favours prose articles on its own; the dense rank
# keeps it honest. Measured on sample queries: fusion put the right fact-sheet
# section first where rerank alone buried it under articles.
RERANK_MODEL = "bge-reranker-v2-m3"
RERANK_CANDIDATES = 20


def get_query_embedding(query: str) -> list[float]:
    return get_embeddings([query])[0]


def search_vectordb(query_embedding: list[float], top_k: int = 3):
    return get_index().query(vector=query_embedding, top_k=top_k, include_metadata=True)


def rerank_text(match) -> str:
    """Text the reranker scores. Article chunks already carry their title and
    metadata; fact-sheet chunks get the fund and section prepended so the
    reranker can tell sibling funds apart."""
    meta = match["metadata"]
    if meta.get("title"):
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


def get_similar_chunks(query: str, top_k: int = 3):
    try:
        query_embedding = get_query_embedding(query)
        candidates = search_vectordb(query_embedding, max(top_k, RERANK_CANDIDATES)).matches
        return rerank(query, candidates, top_k)
    except Exception as e:
        print(f"Query embedding and chunking retrieval pipeline failed: {e}")
        raise


if __name__ == "__main__":
    for chunk in get_similar_chunks("hello I am looking for investment advice", 5):
        print(chunk["metadata"].get("title") or chunk["metadata"].get("fund"), "|", chunk["metadata"]["chunk"][:80])

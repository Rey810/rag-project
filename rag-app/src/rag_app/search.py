from .embeddings import get_embeddings
from .vector_store import get_index


def get_query_embedding(query: str) -> list[float]:
    return get_embeddings([query])[0]


def search_vectordb(query_embedding: list[float], top_k: int = 3):
    return get_index().query(vector=query_embedding, top_k=top_k, include_metadata=True)


def get_similar_chunks(query: str, top_k: int = 3):
    try:
        query_embedding = get_query_embedding(query)
        vectordb_response = search_vectordb(query_embedding, top_k)
        return vectordb_response.matches
    except Exception as e:
        print(f"Query embedding and chunking retrieval pipeline failed: {e}")
        raise


if __name__ == "__main__":
    query_embedding = get_query_embedding("hello I am looking for investment advice")
    pinecone_response = search_vectordb(query_embedding)
    print(pinecone_response.matches[0]["metadata"]["chunk"])

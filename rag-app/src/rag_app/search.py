import os
from dotenv import load_dotenv 
from ingest import get_embeddings
from pinecone import Pinecone

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
PINECONE_INDEX_NAME= os.getenv("PINECONE_INDEX_NAME")

def get_query_embedding(query):
    return get_embeddings([query])[0].embedding

def search_vectordb(query_embedding, top_k=3):
    return pc.Index(PINECONE_INDEX_NAME).query(vector=query_embedding, top_k=top_k, include_metadata=True)

def get_similar_chunks(query, top_k=3):
    try: 
        query_embedding = get_query_embedding(query)
        vectordb_response = search_vectordb(query_embedding, top_k)
        return [chunk["metadata"]["chunk"] for chunk in vectordb_response.matches]
    
    except Exception as e:
        print(f"Query embedding and chunking retrieval pipeline failed: {e}")
        raise

if __name__ == "__main__":
    # test 
    query_embedding = get_query_embedding("hello I am looking for investment advice")
    pinecone_response = search_vectordb(query_embedding)
    print(pinecone_response.matches[0]["metadata"]["chunk"])
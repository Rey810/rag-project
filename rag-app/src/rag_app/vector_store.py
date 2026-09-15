"""Pinecone client and index handle, shared by search and the ingest pipeline."""
import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

_client = None
_index = None


def get_client() -> Pinecone:
    global _client
    if _client is None:
        _client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return _client


def get_index():
    global _index
    if _index is None:
        _index = get_client().Index(PINECONE_INDEX_NAME)
    return _index

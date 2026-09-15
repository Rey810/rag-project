"""Pinecone index handle, shared by search and the ingest pipeline."""
import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

_index = None


def get_index():
    global _index
    if _index is None:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        _index = pc.Index(PINECONE_INDEX_NAME)
    return _index

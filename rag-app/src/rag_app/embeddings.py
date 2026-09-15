"""OpenAI embeddings, shared by the serving path (query embedding) and the
ingest pipeline (chunk embedding)."""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per input, in order."""
    response = _get_client().embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]

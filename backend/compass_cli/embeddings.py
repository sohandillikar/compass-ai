from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def _ensure_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)


def _client() -> OpenAI:
    _ensure_env()
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text: str) -> list[float]:
    """Return a single embedding vector for *text*."""
    client = _client()
    resp = client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
    return resp.data[0].embedding


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Return embedding vectors for a batch of texts (max ~2048 per call)."""
    client = _client()
    resp = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    return [d.embedding for d in resp.data]


def review_text(course: str | None, comment: str) -> str:
    """Build the string that gets embedded for a review row."""
    prefix = f"{course} | " if course else ""
    return f"{prefix}{comment}"

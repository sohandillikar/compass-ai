"""Batch-embed all review comments that don't yet have embeddings.

Usage:
    python -m etl.generate_embeddings          # from backend/
    python etl/generate_embeddings.py          # from backend/

Set BATCH_SIZE env var to control how many reviews are embedded per OpenAI
API call (default 256, max ~2048).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compass_cli.db import get_supabase_client
from compass_cli.embeddings import get_embeddings_batch, review_text

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "256"))
PAGE_SIZE = 1000


def fetch_unembedded_reviews(supabase, offset: int = 0) -> list[dict]:
    """Return reviews where embedding IS NULL and comment IS NOT NULL."""
    resp = (
        supabase.table("reviews")
        .select("id,comment,course")
        .is_("embedding", "null")
        .neq("comment", "")
        .range(offset, offset + PAGE_SIZE - 1)
        .execute()
    )
    return [r for r in (resp.data or []) if r.get("comment")]


CONN_REFRESH_INTERVAL = 500


def update_embeddings(ids: list[str], embeddings: list[list[float]]) -> None:
    """Write embeddings back to Supabase, refreshing the client periodically
    to avoid HTTP/2 connection-terminated errors on long runs."""
    for i in range(0, len(ids), CONN_REFRESH_INTERVAL):
        chunk_ids = ids[i : i + CONN_REFRESH_INTERVAL]
        chunk_embs = embeddings[i : i + CONN_REFRESH_INTERVAL]
        client = get_supabase_client()
        for row_id, emb in zip(chunk_ids, chunk_embs):
            retries = 0
            while True:
                try:
                    client.table("reviews").update({"embedding": emb}).eq("id", row_id).execute()
                    break
                except Exception as e:
                    retries += 1
                    if retries > 3:
                        raise
                    print(f"    Update retry {retries} for {row_id}: {e}")
                    time.sleep(2 ** retries)
                    client = get_supabase_client()


def main() -> None:
    total_embedded = 0
    offset = 0

    while True:
        supabase = get_supabase_client()
        rows = fetch_unembedded_reviews(supabase, offset)
        if not rows:
            break

        for batch_start in range(0, len(rows), BATCH_SIZE):
            batch = rows[batch_start : batch_start + BATCH_SIZE]
            texts = [
                review_text(r.get("course"), r["comment"])
                for r in batch
            ]
            ids = [r["id"] for r in batch]

            retries = 0
            while True:
                try:
                    embeddings = get_embeddings_batch(texts)
                    break
                except Exception as e:
                    retries += 1
                    if retries > 3:
                        print(f"  Failed after {retries} retries: {e}")
                        raise
                    wait = 2 ** retries
                    print(f"  Retry {retries} in {wait}s: {e}")
                    time.sleep(wait)

            update_embeddings(ids, embeddings)
            total_embedded += len(batch)
            print(f"  Embedded {total_embedded} reviews so far…")

        offset += PAGE_SIZE

    print(f"\nDone — {total_embedded} reviews embedded.")


if __name__ == "__main__":
    main()

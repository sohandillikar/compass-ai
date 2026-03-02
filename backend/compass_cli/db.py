from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


def _load_env() -> None:
    # Load .env from repo root if present (matches existing ETL pattern)
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)


def _first_env(*names: str) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    key: str


def load_supabase_config() -> SupabaseConfig:
    _load_env()
    url = _first_env("SUPABASE_URL")
    key = _first_env("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY")

    if not url or not key:
        missing = []
        if not url:
            missing.append("SUPABASE_URL")
        if not key:
            missing.append("SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_KEY / SUPABASE_KEY)")
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
    return SupabaseConfig(url=url, key=key)


def get_supabase_client(config: SupabaseConfig | None = None) -> Client:
    cfg = config or load_supabase_config()
    return create_client(cfg.url, cfg.key)


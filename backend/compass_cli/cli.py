from __future__ import annotations

import argparse
import logging
import os
import sys
import warnings

# Suppress noisy dependency warnings and logs (must run before any langchain/requests/transformers import)
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
warnings.filterwarnings("ignore", module="requests")
warnings.filterwarnings("ignore", message=".*supported version.*")
warnings.filterwarnings("ignore", message=".*PyTorch.*TensorFlow.*Flax.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

from compass_cli.agent import build_agent
from compass_cli.db import get_supabase_client


def _check_supabase_reachable() -> bool:
    """Return True if Supabase is reachable, False otherwise."""
    try:
        client = get_supabase_client()
        client.table("departments").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="compass-cli",
        description="CLI assistant to help UC Davis students pick professors.",
    )
    parser.add_argument(
        "--once",
        type=str,
        default=None,
        help="Ask a single question and exit.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override OpenAI model name (otherwise uses OPENAI_MODEL or a default).",
    )
    return parser.parse_args(argv)


def _print_startup_help() -> None:
    print("Compass AI (CLI)")
    print("Type your question, or 'exit' to quit.")
    print()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    agent = build_agent(model_name=args.model)

    if not _check_supabase_reachable():
        print("Warning: Could not reach Supabase. Course/professor lookups may fail.", file=sys.stderr)

    if args.once:
        try:
            result = agent.invoke({"messages": [{"role": "user", "content": args.once}]})
        except Exception as e:
            err_msg = str(e).split("\n")[0] if str(e) else type(e).__name__
            print(f"Error: {err_msg}", file=sys.stderr)
            print("Check your internet connection and that Supabase/OpenAI are reachable.", file=sys.stderr)
            return 1
        # create_agent returns a dict-like structure; "messages" contains final AI message.
        messages = result.get("messages") if isinstance(result, dict) else None
        if messages:
            print(messages[-1].content)
        else:
            print(result)
        return 0

    _print_startup_help()
    while True:
        try:
            user_text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            return 0

        try:
            result = agent.invoke({"messages": [{"role": "user", "content": user_text}]})
        except Exception as e:  # e.g. httpx.ConnectError, OpenAI errors
            err_msg = str(e).split("\n")[0] if str(e) else type(e).__name__
            print(f"Error: {err_msg}")
            print("Check your internet connection and that Supabase/OpenAI are reachable.")
            print()
            continue

        messages = result.get("messages") if isinstance(result, dict) else None
        if messages:
            print(messages[-1].content)
        else:
            print(result)
        print()


if __name__ == "__main__":
    raise SystemExit(main())


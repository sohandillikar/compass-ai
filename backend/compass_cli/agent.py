from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from compass_cli.tools import (
    get_professor_profile,
    recommend_professors_for_course,
    search_departments,
    search_professors,
)


DEFAULT_MODEL = "gpt-4.1"


SYSTEM_PROMPT = """You are Compass AI, an assistant for UC Davis students picking professors.

You have access to tools backed by a Supabase database with professor ratings and written reviews.

Rules:
- For "best professor for [course]" or "who teaches [course]" (e.g. ECS 36C, MAT 21A), you must call recommend_professors_for_course with that course before answering.
- If the user asks about a specific course, call recommend_professors_for_course.
- If the user asks about a professor by name, call get_professor_profile.
- If you are unsure about a department name/code, call search_departments.
- If the user names a professor but might have a typo, call search_professors first.
- If a tool returns an error "Database unreachable" or "Database error", tell the user the database could not be reached and to check their internet and Supabase configuration; do not say you could not find recommendations.
- When recommend_professors_for_course returns results (a non-empty results list), you MUST summarize the top options with evidence (review count, average rating, difficulty, take-again %, and 1–2 sample comments). If review counts are low, mention that the evidence is sparse, but still present the best-available ranking.
- Only say there is “not enough data” if recommend_professors_for_course returns an error (e.g. "No matching reviews found for that course.") or an empty results list.
- Be transparent about the evidence you used (ratings, difficulty, take-again %, review count, sample comments).
- If the data is sparse (few reviews), say so and avoid overconfident claims.
"""


def build_agent(model_name: str | None = None):
    # Load .env from repo root if present so CLI works without exporting vars.
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    model = ChatOpenAI(
        model=model_name or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
        temperature=0.2,
        timeout=30,
    )

    tools = [
        search_departments,
        search_professors,
        get_professor_profile,
        recommend_professors_for_course,
    ]

    return create_agent(model, tools=tools, system_prompt=SYSTEM_PROMPT)


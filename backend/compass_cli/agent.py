from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from compass_cli.tool_logging import ToolCallPrintHandler
from compass_cli.tools import (
    get_professor_profile,
    recommend_professors_for_course,
    search_departments,
    search_professors,
    semantic_search_reviews,
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
- For open-ended or subjective questions about teaching style, student experience, or qualitative traits (e.g. "professors who explain well", "engaging lecturers", "tough but fair grading", "best office hours"), call semantic_search_reviews. This tool finds reviews by meaning, not exact text match.
- You may combine semantic_search_reviews with recommend_professors_for_course or get_professor_profile for richer, more evidence-backed answers.
- Prefer structured tools (recommend_professors_for_course, get_professor_profile) for factual queries about ratings, difficulty, or specific courses. Use semantic_search_reviews when the question is about subjective qualities or when you need to find relevant student comments.
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
        semantic_search_reviews,
    ]

    agent = create_agent(model, tools=tools, system_prompt=SYSTEM_PROMPT)

    handler = ToolCallPrintHandler()
    try:
        # Preferred: attach callbacks at construction time so both CLI & API get it.
        agent = agent.with_config({"callbacks": [handler]})
        try:
            setattr(agent, "_compass_tool_logging_attached", True)
        except Exception:
            pass
    except Exception:
        # Fallback: callers may pass callbacks via invoke config.
        try:
            setattr(agent, "_compass_tool_logging_attached", False)
            setattr(agent, "_compass_tool_logging_handler", handler)
        except Exception:
            pass

    return agent


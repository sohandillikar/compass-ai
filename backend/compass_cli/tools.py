from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

import httpx
from langchain.tools import tool

from compass_cli.db import get_supabase_client
from compass_cli.embeddings import get_embedding
from compass_cli.fuzzy import Match, best_match, course_variants, normalize_course, normalize_course_canonical, normalize_text, top_matches


def _db_error_payload(message: str, detail: str) -> str:
    """Return JSON string for database unreachable so the agent can relay it."""
    return json.dumps(
        {"error": message, "detail": detail},
        indent=2,
        sort_keys=True,
    )


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except Exception:
        return None


def _safe_int(v: Any) -> int | None:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


@dataclass(frozen=True)
class ProfessorRow:
    id: str
    name: str
    department_id: str | None
    overall_rating: float | None
    difficulty_rating: float | None
    would_take_again_percentage: int | None
    profile_url: str | None


def _fetch_departments() -> list[dict[str, Any]]:
    supabase = get_supabase_client()
    resp = supabase.table("departments").select("id,name,code").execute()
    return list(resp.data or [])


def _fetch_professors() -> list[ProfessorRow]:
    supabase = get_supabase_client()
    resp = (
        supabase.table("professors")
        .select(
            "id,name,department_id,overall_rating,difficulty_rating,would_take_again_percentage,profile_url"
        )
        .execute()
    )
    out: list[ProfessorRow] = []
    for r in (resp.data or []):
        out.append(
            ProfessorRow(
                id=str(r.get("id")),
                name=str(r.get("name") or ""),
                department_id=(str(r["department_id"]) if r.get("department_id") else None),
                overall_rating=_safe_float(r.get("overall_rating")),
                difficulty_rating=_safe_float(r.get("difficulty_rating")),
                would_take_again_percentage=_safe_int(r.get("would_take_again_percentage")),
                profile_url=(str(r["profile_url"]) if r.get("profile_url") else None),
            )
        )
    return out


def _fetch_reviews_for_course(course_query: str, limit: int = 5000) -> list[dict[str, Any]]:
    supabase = get_supabase_client()
    variants = course_variants(course_query)
    if not variants:
        return []

    # Supabase/PostgREST OR filter syntax: "col.op.value,col.op.value"
    # We keep it broad; final matching is done locally using normalize_course.
    # Use more variants now that course_variants() includes padded/unpadded forms.
    or_filter = ",".join([f"course.ilike.%{v}%" for v in variants[:12]])

    q = (
        supabase.table("reviews")
        .select("professor_id,rating,difficulty,comment,course,tags")
        .or_(or_filter)
        .limit(limit)
    )
    resp = q.execute()
    return list(resp.data or [])


@tool
def search_departments(query: str, limit: int = 5) -> str:
    """Fuzzy-search UC Davis departments by name or code."""
    try:
        depts = _fetch_departments()
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        return _db_error_payload(
            "Database unreachable",
            f"{type(e).__name__}: {e}. Check internet and Supabase.",
        )
    except Exception as e:
        return _db_error_payload("Database error", f"{type(e).__name__}: {e}.")

    choices: list[str] = []
    for d in depts:
        name = str(d.get("name") or "").strip()
        code = str(d.get("code") or "").strip()
        if name:
            choices.append(name)
        if code:
            choices.append(code)

    matches = top_matches(query, choices, limit=limit)
    return _json(
        {
            "query": query,
            "matches": [{"value": m.value, "score": m.score} for m in matches],
        }
    )


@tool
def search_professors(query: str, department: str | None = None, limit: int = 5) -> str:
    """Fuzzy-search professors by name; optionally constrain to a department."""
    try:
        professors = _fetch_professors()
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        return _db_error_payload(
            "Database unreachable",
            f"{type(e).__name__}: {e}. Check internet and Supabase.",
        )
    except Exception as e:
        return _db_error_payload("Database error", f"{type(e).__name__}: {e}.")

    dept_id: str | None = None

    if department:
        try:
            depts = _fetch_departments()
        except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
            return _db_error_payload(
                "Database unreachable",
                f"{type(e).__name__}: {e}. Check internet and Supabase.",
            )
        except Exception as e:
            return _db_error_payload("Database error", f"{type(e).__name__}: {e}.")
        dept_name_choices = [str(d.get("name") or "") for d in depts if d.get("name")]
        dept_code_choices = [str(d.get("code") or "") for d in depts if d.get("code")]
        dept_choice = best_match(department, dept_name_choices + dept_code_choices, score_cutoff=70.0)
        if dept_choice:
            # find department row
            for d in depts:
                if d.get("name") == dept_choice.value or d.get("code") == dept_choice.value:
                    dept_id = str(d.get("id"))
                    break

    if dept_id:
        professors = [p for p in professors if p.department_id == dept_id]

    name_choices = [p.name for p in professors if p.name]
    matches = top_matches(query, name_choices, limit=limit)

    # attach lightweight stats for each match
    by_name = {p.name: p for p in professors}
    enriched: list[dict[str, Any]] = []
    for m in matches:
        p = by_name.get(m.value)
        if not p:
            continue
        enriched.append(
            {
                "name": p.name,
                "match_score": m.score,
                "overall_rating": p.overall_rating,
                "difficulty_rating": p.difficulty_rating,
                "would_take_again_percentage": p.would_take_again_percentage,
                "profile_url": p.profile_url,
            }
        )

    return _json(
        {
            "query": query,
            "department": department,
            "results": enriched,
        }
    )


@tool
def get_professor_profile(professor_name: str) -> str:
    """Get a professor's metrics and a small sample of recent reviews."""
    try:
        professors = _fetch_professors()
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        return _db_error_payload(
            "Database unreachable",
            f"{type(e).__name__}: {e}. Check internet and Supabase.",
        )
    except Exception as e:
        return _db_error_payload("Database error", f"{type(e).__name__}: {e}.")

    name_choices = [p.name for p in professors if p.name]
    m = best_match(professor_name, name_choices, score_cutoff=75.0)
    if not m:
        suggestions = top_matches(professor_name, name_choices, limit=5, score_cutoff=60.0)
        return _json(
            {
                "error": "Professor not found",
                "query": professor_name,
                "suggestions": [{"value": s.value, "score": s.score} for s in suggestions],
            }
        )

    prof = next((p for p in professors if p.name == m.value), None)
    if not prof:
        return _json({"error": "Professor not found after match", "query": professor_name})

    try:
        supabase = get_supabase_client()
        rev = (
            supabase.table("reviews")
            .select("rating,difficulty,comment,review_date,course,tags")
            .eq("professor_id", prof.id)
            .order("created_at", desc=True)
            .limit(8)
            .execute()
        )
        reviews = list(rev.data or [])
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        return _db_error_payload(
            "Database unreachable",
            f"{type(e).__name__}: {e}. Check internet and Supabase.",
        )
    except Exception as e:
        return _db_error_payload("Database error", f"{type(e).__name__}: {e}.")

    return _json(
        {
            "matched_name": prof.name,
            "match_score": m.score,
            "overall_rating": prof.overall_rating,
            "difficulty_rating": prof.difficulty_rating,
            "would_take_again_percentage": prof.would_take_again_percentage,
            "profile_url": prof.profile_url,
            "sample_reviews": reviews,
        }
    )


def _score_professor(
    *,
    preference: str,
    overall_rating: float | None,
    review_avg_rating: float | None,
    would_take_again: int | None,
    avg_difficulty: float | None,
    review_count: int,
) -> float:
    pref = normalize_text(preference)

    w_overall = 0.45
    w_review = 0.45
    w_take_again = 0.10

    diff_penalty = 0.22
    if pref in {"easy", "easy a", "easy-a", "gpa", "low workload"}:
        diff_penalty = 0.38
    elif pref in {"challenging", "rigorous", "hard", "learn a lot"}:
        diff_penalty = 0.10

    s = 0.0
    if overall_rating is not None:
        s += w_overall * (overall_rating / 5.0)
    if review_avg_rating is not None:
        s += w_review * (review_avg_rating / 5.0)
    if would_take_again is not None:
        s += w_take_again * max(0.0, min(1.0, would_take_again / 100.0))
    if avg_difficulty is not None:
        # difficulty ratings in reviews are 1..5; normalize and subtract
        s -= diff_penalty * (max(1.0, min(5.0, avg_difficulty)) / 5.0)

    # confidence scaling by review volume
    confidence = math.log1p(max(0, review_count)) / math.log1p(50)
    return s * (0.6 + 0.4 * confidence)


@tool
def recommend_professors_for_course(
    course: str,
    preference: str = "balanced",
    limit: int = 5,
) -> str:
    """Recommend professors for a course using ratings + written reviews. Use this as the primary way to answer 'best professor for [course]' or 'who teaches [course]'."""
    try:
        reviews = _fetch_reviews_for_course(course)
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        return _db_error_payload(
            "Database unreachable",
            f"{type(e).__name__}: {e}. Check internet and Supabase.",
        )
    except Exception as e:
        return _db_error_payload(
            "Database error",
            f"{type(e).__name__}: {e}. Check Supabase configuration.",
        )

    if not reviews:
        return _json(
            {
                "course_query": course,
                "error": "No matching reviews found for that course.",
                "note": "Try a different formatting (e.g., 'ECS 36C' vs 'ECS36C').",
            }
        )

    try:
        want = normalize_course_canonical(course)
        filtered: list[dict[str, Any]] = []
        for r in reviews:
            c = r.get("course")
            if not c:
                continue
            if want and normalize_course_canonical(str(c)) == want:
                filtered.append(r)

        # If strict filter removed everything, fall back to the broad supabase filter results.
        use_reviews = filtered or reviews

        by_prof: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in use_reviews:
            pid = r.get("professor_id")
            if pid:
                by_prof[str(pid)].append(r)

        professors = _fetch_professors()
        prof_by_id = {p.id: p for p in professors}

        scored: list[dict[str, Any]] = []
        for pid, rs in by_prof.items():
            p = prof_by_id.get(pid)
            if not p:
                continue

            ratings = [_safe_float(x.get("rating")) for x in rs]
            diffs = [_safe_float(x.get("difficulty")) for x in rs]
            ratings_f = [x for x in ratings if x is not None]
            diffs_f = [x for x in diffs if x is not None]

            review_avg = (sum(ratings_f) / len(ratings_f)) if ratings_f else None
            diff_avg = (sum(diffs_f) / len(diffs_f)) if diffs_f else None

            score = _score_professor(
                preference=preference,
                overall_rating=p.overall_rating,
                review_avg_rating=review_avg,
                would_take_again=p.would_take_again_percentage,
                avg_difficulty=diff_avg,
                review_count=len(rs),
            )

            # pick a few representative comments
            comments: list[str] = []
            for r in rs:
                c = str(r.get("comment") or "").strip()
                if c and c.lower() not in {"no comments", "n/a"}:
                    comments.append(c)
                if len(comments) >= 3:
                    break

            scored.append(
                {
                    "professor_name": p.name,
                    "professor_id": p.id,
                    "score": round(score, 4),
                    "overall_rating": p.overall_rating,
                    "professor_difficulty_rating": p.difficulty_rating,
                    "would_take_again_percentage": p.would_take_again_percentage,
                    "review_count_for_course": len(rs),
                    "avg_review_rating_for_course": (round(review_avg, 2) if review_avg is not None else None),
                    "avg_review_difficulty_for_course": (round(diff_avg, 2) if diff_avg is not None else None),
                    "profile_url": p.profile_url,
                    "sample_comments": comments,
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[: max(1, min(20, limit))]

        return _json(
            {
                "course_query": course,
                "preference": preference,
                "results": top,
                "note": "Results are based on both professor-level metrics and course-specific review aggregates when available.",
            }
        )
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        return _db_error_payload(
            "Database unreachable",
            f"{type(e).__name__}: {e}. Check internet and Supabase.",
        )
    except Exception as e:
        return _db_error_payload(
            "Database error",
            f"{type(e).__name__}: {e}. Check Supabase configuration.",
        )


@tool
def semantic_search_reviews(query: str, limit: int = 10, threshold: float = 0.5) -> str:
    """Search professor reviews by meaning using semantic similarity.

    Use this for open-ended questions about teaching style, student experience,
    or subjective topics (e.g. "professors who explain well", "engaging
    lecturers", "tough but fair grading").
    """
    try:
        query_embedding = get_embedding(query)
    except Exception as e:
        return _db_error_payload(
            "Embedding error",
            f"Could not embed query: {type(e).__name__}: {e}",
        )

    try:
        supabase = get_supabase_client()
        resp = supabase.rpc(
            "match_reviews",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit,
            },
        ).execute()
        matches = list(resp.data or [])
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        return _db_error_payload(
            "Database unreachable",
            f"{type(e).__name__}: {e}. Check internet and Supabase.",
        )
    except Exception as e:
        return _db_error_payload("Database error", f"{type(e).__name__}: {e}.")

    if not matches:
        return _json(
            {
                "query": query,
                "results": [],
                "note": "No semantically similar reviews found. Try rephrasing or lowering the threshold.",
            }
        )

    try:
        professors = _fetch_professors()
        prof_by_id = {p.id: p for p in professors}
    except Exception:
        prof_by_id = {}

    results: list[dict[str, Any]] = []
    for m in matches:
        prof = prof_by_id.get(str(m.get("professor_id")))
        results.append(
            {
                "professor_name": prof.name if prof else None,
                "professor_id": m.get("professor_id"),
                "course": m.get("course"),
                "comment": m.get("comment"),
                "rating": m.get("rating"),
                "difficulty": m.get("difficulty"),
                "tags": m.get("tags"),
                "similarity": round(float(m.get("similarity", 0)), 4),
                "overall_rating": prof.overall_rating if prof else None,
                "profile_url": prof.profile_url if prof else None,
            }
        )

    return _json(
        {
            "query": query,
            "results": results,
        }
    )


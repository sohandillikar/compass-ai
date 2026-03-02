from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from rapidfuzz import fuzz, process


_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")
# Strip leading zeros from numeric part of course code (e.g. mat021a -> mat21a)
_CANONICAL_COURSE_RE = re.compile(r"^([a-z]+)(0+)([1-9].*)$")


def normalize_text(s: str) -> str:
    s2 = (s or "").casefold().strip()
    s2 = _WHITESPACE_RE.sub(" ", s2)
    return s2


def normalize_course(s: str) -> str:
    """Normalize course strings for matching (e.g., 'ECS 36C' -> 'ecs36c')."""
    s2 = normalize_text(s)
    s2 = _NON_ALNUM_RE.sub("", s2)
    return s2


def normalize_course_canonical(s: str) -> str:
    """Normalize course for matching, stripping leading zeros in the number part (e.g. MAT021A -> mat21a)."""
    c = normalize_course(s)
    if not c:
        return c
    m = _CANONICAL_COURSE_RE.match(c)
    if m:
        return m.group(1) + m.group(3)
    return c


@dataclass(frozen=True)
class Match:
    value: str
    score: float


def best_match(
    query: str,
    choices: Sequence[str],
    *,
    score_cutoff: float = 75.0,
) -> Match | None:
    q = normalize_text(query)
    if not q or not choices:
        return None

    res = process.extractOne(
        q,
        choices,
        scorer=fuzz.WRatio,
        processor=normalize_text,
        score_cutoff=score_cutoff,
    )
    if not res:
        return None
    choice, score, _idx = res
    return Match(value=str(choice), score=float(score))


def top_matches(
    query: str,
    choices: Sequence[str],
    *,
    limit: int = 5,
    score_cutoff: float = 65.0,
) -> list[Match]:
    q = normalize_text(query)
    if not q or not choices or limit <= 0:
        return []

    res = process.extract(
        q,
        choices,
        scorer=fuzz.WRatio,
        processor=normalize_text,
        limit=limit,
        score_cutoff=score_cutoff,
    )
    out: list[Match] = []
    for choice, score, _idx in res:
        out.append(Match(value=str(choice), score=float(score)))
    return out


def course_variants(user_course: str) -> list[str]:
    """Generate a few likely DB substrings for Supabase ilike/or filters."""
    c = normalize_course(user_course)
    if not c:
        return []

    # Attempt to split into dept letters + rest
    m = re.match(r"^([a-z]+)([0-9].*)$", c)
    variants: set[str] = set()
    variants.add(c)
    if m:
        dept = m.group(1)
        num = m.group(2)
        variants.add(f"{dept}{num}")
        variants.add(f"{dept} {num}")
        variants.add(dept)
        # Include number-only so we match DB rows with course "21A" when user says "MAT 21A"
        variants.add(num)
    return sorted(variants)


def normalize_many(values: Iterable[str]) -> list[str]:
    return [normalize_text(v) for v in values]


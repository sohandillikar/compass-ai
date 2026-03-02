from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from rapidfuzz import fuzz, process


_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")
# Parse leading course token: DEPT + DIGITS + optional suffix letters.
# Accept some whitespace/non-alnum between parts; ignore trailing text (e.g. "ECS036C - Data Structures").
_COURSE_TOKEN_RE = re.compile(r"^([a-z]+)\s*([0-9]{1,6})\s*([a-z]{0,4}).*$")


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
    """Normalize course for matching, using a stable 3-digit padded number key.

    Examples:
    - "ECS 36C" -> "ecs036c"
    - "ECS036C - Data Structures" -> "ecs036c"
    - "MAT 21A" -> "mat021a"
    """

    def _parse_course_token(raw: str) -> tuple[str, str, str] | None:
        t = normalize_text(raw)
        if not t:
            return None
        # Keep letters/digits/spaces so we can ignore trailing course names cleanly.
        t = re.sub(r"[^0-9a-z ]+", " ", t)
        t = _WHITESPACE_RE.sub(" ", t).strip()
        m = _COURSE_TOKEN_RE.match(t)
        if not m:
            return None
        dept, digits, suffix = m.group(1), m.group(2), m.group(3)
        if not dept or not digits:
            return None
        return dept, digits, suffix or ""

    parsed = _parse_course_token(s)
    if not parsed:
        return normalize_course(s)

    dept, digits, suffix = parsed
    # Pad to 3 digits when the numeric part is 1–2 digits; keep longer numbers as-is.
    try:
        n = int(digits)
        digits_norm = str(n).zfill(3) if n < 1000 else str(n)
    except Exception:
        digits_norm = digits.zfill(3) if len(digits) < 3 else digits

    return f"{dept}{digits_norm}{suffix}"


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
    def _parse_course_token(raw: str) -> tuple[str, str, str] | None:
        t = normalize_text(raw)
        if not t:
            return None
        t = re.sub(r"[^0-9a-z ]+", " ", t)
        t = _WHITESPACE_RE.sub(" ", t).strip()
        m = _COURSE_TOKEN_RE.match(t)
        if not m:
            return None
        dept, digits, suffix = m.group(1), m.group(2), m.group(3)
        if not dept or not digits:
            return None
        return dept, digits, suffix or ""

    parsed = _parse_course_token(user_course)
    c = normalize_course(user_course)
    if not c and not parsed:
        return []

    # Preserve ordering: most specific -> least specific.
    out: list[str] = []
    seen: set[str] = set()

    def _add(v: str) -> None:
        v2 = (v or "").strip()
        if not v2 or v2 in seen:
            return
        seen.add(v2)
        out.append(v2)

    if parsed:
        dept, digits_raw, suffix = parsed
        # Compute padded + unpadded numbers for matching mixed storage.
        try:
            n = int(digits_raw)
            digits_unpadded = str(n)
        except Exception:
            digits_unpadded = digits_raw.lstrip("0") or "0"
        digits_padded = digits_unpadded.zfill(3) if len(digits_unpadded) < 3 else digits_unpadded

        token_padded = f"{dept}{digits_padded}{suffix}"
        token_unpadded = f"{dept}{digits_unpadded}{suffix}"

        # Full token variants (no-space + space between dept/number).
        _add(token_padded)
        _add(f"{dept} {digits_padded}{suffix}")
        _add(token_unpadded)
        _add(f"{dept} {digits_unpadded}{suffix}")

        # Number-only variants (helps if DB has "36C" or "036C" without dept).
        _add(f"{digits_padded}{suffix}")
        _add(f"{digits_unpadded}{suffix}")

        # Dept-only fallback.
        _add(dept)

    # Keep legacy behavior as a last resort: normalized alnum-only whole input.
    _add(c)
    return out


def normalize_many(values: Iterable[str]) -> list[str]:
    return [normalize_text(v) for v in values]


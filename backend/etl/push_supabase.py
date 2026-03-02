import ast
import math
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ── Load .env (walks up from this script to find it) ──────────────────────────
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL        = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SECRET_KEY")  # must be service-role, not anon
PROFESSORS_CSV      = os.getenv("PROFESSORS_CSV", "ucdavis_professors.csv")
REVIEWS_CSV         = os.getenv("REVIEWS_CSV",    "ucdavis_professor_reviews.csv")
BATCH_SIZE          = int(os.getenv("BATCH_SIZE", "500"))

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    sys.exit(
        "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in your .env file."
    )

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(val):
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def safe_int(val):
    try:
        f = float(val)
        return None if math.isnan(f) else int(round(f))
    except (TypeError, ValueError):
        return None


def parse_tags(val) -> list:
    """Convert tag strings like "['Good lectures', 'Clear grading']" to a list."""
    if not val or (isinstance(val, float) and math.isnan(val)):
        return []
    s = str(val).strip()
    if s.startswith("["):
        try:
            return ast.literal_eval(s)
        except Exception:
            pass
    return [t.strip() for t in s.split(",") if t.strip()]


def sanitize(row: dict) -> dict:
    """Replace float NaN/inf (pandas leftovers) with None so JSON serialization works."""
    cleaned = {}
    for k, v in row.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        elif isinstance(v, str) and v.lower() in ("nan", "none", "null", ""):
            cleaned[k] = None
        elif isinstance(v, list):
            cleaned[k] = [
                None if (isinstance(i, float) and (math.isnan(i) or math.isinf(i))) else i
                for i in v
            ]
        else:
            cleaned[k] = v
    return cleaned


def chunk(lst, size=500):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def resolve_csv_path(filename: str) -> Path:
    """Look for the CSV relative to this script, then project root, then cwd."""
    candidates = [
        Path(filename),                                          # absolute or cwd-relative
        Path(__file__).parent / filename,                        # scripts/
        Path(__file__).parent.parent / filename,                 # project root
    ]
    for p in candidates:
        if p.exists():
            return p
    sys.exit(f"Could not find CSV file: {filename}\n   Tried: {[str(c) for c in candidates]}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # ── 1. Load CSVs ──────────────────────────
    prof_path   = resolve_csv_path(PROFESSORS_CSV)
    review_path = resolve_csv_path(REVIEWS_CSV)

    print(f"Loading professors CSV : {prof_path}")
    print(f"Loading reviews CSV    : {review_path}")

    prof_df   = pd.read_csv(prof_path,   dtype=str)
    review_df = pd.read_csv(review_path, dtype=str)

    prof_df.columns   = [c.strip().lower() for c in prof_df.columns]
    review_df.columns = [c.strip().lower() for c in review_df.columns]

    print(f"  Professors : {len(prof_df):,} rows")
    print(f"  Reviews    : {len(review_df):,} rows")

    # ── 2. Departments ────────────────────────
    dept_names = set()
    for df in (prof_df, review_df):
        if "department" in df.columns:
            dept_names.update(df["department"].dropna().str.strip().unique())
    dept_names.discard("")

    existing = supabase.table("departments").select("id,name").execute()
    dept_map: dict[str, str] = {r["name"]: r["id"] for r in (existing.data or [])}

    new_depts = [
        {
            "id":         str(uuid.uuid4()),
            "created_at": now_iso(),
            "name":       name,
            "code":       re.sub(r"[^A-Z0-9]", "", name.upper())[:20],
        }
        for name in dept_names
        if name not in dept_map
    ]

    if new_depts:
        print(f"\nUpserting {len(new_depts)} department(s)…")
        for batch in chunk(new_depts, BATCH_SIZE):
            supabase.table("departments").upsert(batch, on_conflict="name").execute()

    # Refresh map
    all_depts = supabase.table("departments").select("id,name").execute()
    dept_map = {r["name"]: r["id"] for r in (all_depts.data or [])}

    # ── 3. Professors ─────────────────────────
    existing_profs = supabase.table("professors").select("id,name").execute()
    prof_name_to_id: dict[str, str] = {r["name"]: r["id"] for r in (existing_profs.data or [])}

    new_profs = []

    for _, row in prof_df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name or name in prof_name_to_id:
            continue
        dept_name = str(row.get("department", "")).strip()
        new_id    = str(uuid.uuid4())
        prof_name_to_id[name] = new_id
        new_profs.append(sanitize({
            "id":                          new_id,
            "created_at":                  now_iso(),
            "name":                        name,
            "department_id":               dept_map.get(dept_name),
            "overall_rating":              safe_float(row.get("overall_rating")),
            "difficulty_rating":           safe_float(row.get("difficulty_rating")),
            "would_take_again_percentage": safe_int(row.get("would_take_again_percentage")),
            "profile_url":                 row.get("profile_url") or None,
        }))

    # Stubs for professors that only appear in reviews
    for _, row in review_df.iterrows():
        name = str(row.get("professor_name", "")).strip()
        if not name or name in prof_name_to_id:
            continue
        dept_name = str(row.get("department", "")).strip()
        new_id    = str(uuid.uuid4())
        prof_name_to_id[name] = new_id
        new_profs.append(sanitize({
            "id":            new_id,
            "created_at":    now_iso(),
            "name":          name,
            "department_id": dept_map.get(dept_name),
        }))

    if new_profs:
        print(f"Upserting {len(new_profs):,} professor(s)…")
        for batch in chunk(new_profs, BATCH_SIZE):
            supabase.table("professors").upsert(batch, on_conflict="name,department_id").execute()

    # ── 4. Reviews ────────────────────────────
    reviews_to_insert = []

    for _, row in review_df.iterrows():
        prof_name = str(row.get("professor_name", "")).strip()
        prof_uuid = prof_name_to_id.get(prof_name)

        if not prof_uuid:
            print(f"  ⚠  No UUID for '{prof_name}' — skipping", file=sys.stderr)
            continue

        course_code = str(row.get("course_code", "") or "").strip()
        course_name = str(row.get("course_name", "") or "").strip()
        course_str  = " - ".join(filter(None, [course_code, course_name])) or None

        quality = safe_float(row.get("quality_rating"))
        clarity = safe_float(row.get("clarity_rating"))
        helpful = safe_float(row.get("helpful_rating"))
        vals    = [v for v in [quality, clarity, helpful] if v is not None]
        avg_rating = round(sum(vals) / len(vals)) if vals else None

        reviews_to_insert.append(sanitize({
            "id":           str(uuid.uuid4()),
            "created_at":   now_iso(),
            "professor_id": prof_uuid,
            "rating":       avg_rating,
            "difficulty":   safe_int(row.get("difficulty_rating")),
            "comment":      row.get("comment") or None,
            "review_date":  None,
            "course":       course_str,
            "tags":         parse_tags(row.get("rating_tags")),
        }))

    if reviews_to_insert:
        total = len(reviews_to_insert)
        print(f"Inserting {total:,} review(s)…")
        for i, batch in enumerate(chunk(reviews_to_insert, BATCH_SIZE)):
            supabase.table("reviews").insert(batch).execute()
            done = min((i + 1) * BATCH_SIZE, total)
            print(f"  {done:,} / {total:,}", end="\r")
        print()

    print("\nDone!")


if __name__ == "__main__":
    main()
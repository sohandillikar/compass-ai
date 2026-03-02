"""
Fetch individual student comments/reviews for UC Davis professors from RateMyProfessors.
Reads ucdavis_professors.csv, fetches each professor's ratings (comment, quality, difficulty, etc.),
and writes ucdavis_professor_reviews.csv with one row per review.

Run from repo root. Uses same GraphQL API and headers as scrape_ucdavis_professors.py.
"""

import base64
import csv
import os
import re
import time

import requests

GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
PROFESSORS_CSV = "ucdavis_professors.csv"
REVIEWS_CSV = "ucdavis_professor_reviews.csv"
RATINGS_PER_PROFESSOR = 100  # max ratings per request; pagination could be added later

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/json",
    "Origin": "https://www.ratemyprofessors.com",
    "Referer": "https://www.ratemyprofessors.com/search/professors/1073?q=*",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
}

# Full ratings including comment text (matches RMP GraphQL Rating type)
TEACHER_REVIEWS_QUERY = """
query TeacherReviewsQuery($id: ID!, $count: Int!) {
  node(id: $id) {
    ... on Teacher {
      firstName
      lastName
      department
      ratings(first: $count) {
        edges {
          node {
            comment
            difficultyRating
            qualityRating
            clarityRating
            helpfulRating
            grade
            ratingTags
            courseType
            class
          }
        }
      }
    }
  }
}
"""


def legacy_id_from_profile_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"/professor/(\d+)", url)
    return m.group(1) if m else None


def fetch_reviews(legacy_id: str) -> list[dict] | None:
    """Fetch up to RATINGS_PER_PROFESSOR reviews for a professor. Returns list of rating dicts or None on error."""
    teacher_id = base64.b64encode(f"Teacher-{legacy_id}".encode()).decode()
    payload = {
        "query": TEACHER_REVIEWS_QUERY,
        "variables": {"id": teacher_id, "count": RATINGS_PER_PROFESSOR},
    }
    try:
        r = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("errors"):
            return None
        node = (data.get("data") or {}).get("node")
        if not node:
            return None
        ratings = node.get("ratings") or {}
        edges = ratings.get("edges") or []
        return [edge.get("node") for edge in edges if edge.get("node")]
    except Exception:
        return None


def format_rating_tags(tags) -> str:
    """Turn ratingTags (list of strings or tag objects) into a single string for CSV."""
    if not tags:
        return ""
    out = []
    for t in tags:
        if isinstance(t, str):
            out.append(t)
        elif isinstance(t, dict) and "tagName" in t:
            out.append(t["tagName"])
        elif isinstance(t, dict):
            out.append(str(t))
        else:
            out.append(str(t))
    return "; ".join(out)


def main():
    # Read professor list
    try:
        with open(PROFESSORS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            professors = list(reader)
    except FileNotFoundError:
        print(f"Missing {PROFESSORS_CSV}. Run from repo root and ensure the professors CSV exists.")
        return

    if not professors:
        print("No rows in professors CSV.")
        return

    fieldnames = [
        "professor_id",
        "professor_name",
        "department",
        "comment",
        "quality_rating",
        "clarity_rating",
        "difficulty_rating",
        "helpful_rating",
        "grade",
        "rating_tags",
        "course_code",
        "course_name",
    ]

    # Resume: skip professors already in the reviews file
    done_ids: set[str] = set()
    if os.path.isfile(REVIEWS_CSV):
        try:
            with open(REVIEWS_CSV, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    pid = row.get("professor_id", "").strip()
                    if pid:
                        done_ids.add(pid)
        except Exception:
            pass
        if done_ids:
            print(f"Resuming: {len(done_ids)} professors already in {REVIEWS_CSV}, skipping them.")

    professors_to_fetch = [
        row for row in professors
        if legacy_id_from_profile_url(row.get("profile_url", "")) not in done_ids
    ]
    total_profs = len(professors_to_fetch)
    if total_profs == 0:
        print("All professors already have reviews. Nothing to fetch.")
        return

    total_reviews = 0
    print(f"Fetching reviews for {total_profs} professors (up to {RATINGS_PER_PROFESSOR} each)...")

    file_exists = os.path.isfile(REVIEWS_CSV)
    with open(REVIEWS_CSV, "a" if file_exists else "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for i, row in enumerate(professors_to_fetch):
            name = row.get("name", "").strip()
            dept = row.get("department", "").strip()
            url = row.get("profile_url", "")
            legacy_id = legacy_id_from_profile_url(url)
            if not legacy_id:
                continue
            reviews = fetch_reviews(legacy_id)
            if reviews is None:
                continue
            for r in reviews:
                comment = str(r.get("comment") or "").strip().replace("\n", " ")
                writer.writerow({
                    "professor_id": legacy_id,
                    "professor_name": name,
                    "department": dept,
                    "comment": comment,
                    "quality_rating": r.get("qualityRating") if r.get("qualityRating") is not None else "",
                    "clarity_rating": r.get("clarityRating") if r.get("clarityRating") is not None else "",
                    "difficulty_rating": r.get("difficultyRating") if r.get("difficultyRating") is not None else "",
                    "helpful_rating": r.get("helpfulRating") if r.get("helpfulRating") is not None else "",
                    "grade": str(r.get("grade") or "").strip(),
                    "rating_tags": format_rating_tags(r.get("ratingTags") or []),
                    "course_code": str(r.get("courseType") or "").strip(),
                    "course_name": str(r.get("class") or "").strip(),
                })
                total_reviews += 1
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{total_profs} professors, {total_reviews} reviews so far")
            time.sleep(0.4)

    print(f"Done. Wrote {total_reviews} reviews to {REVIEWS_CSV}.")


if __name__ == "__main__":
    main()

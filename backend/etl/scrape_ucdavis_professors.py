"""
Scrape UC Davis professor data from RateMyProfessors GraphQL API and save to CSV.
Uses browser-like headers to avoid 403. No third-party RMP package required.

Output: ucdavis_professors.csv with name, department, ratings, profile_url, courses.
"""

import base64
import csv
import json
import time

import requests

# RateMyProfessor: UC Davis legacy ID from URL /school/1073
# GraphQL expects base64("School-1073") for schoolID in teacher search
UC_DAVIS_LEGACY_ID = "1073"
UC_DAVIS_SCHOOL_ID = base64.b64encode(f"School-{UC_DAVIS_LEGACY_ID}".encode()).decode()
GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
RMP_PROFESSOR_URL = "https://www.ratemyprofessors.com/professor"
OUTPUT_CSV = "ucdavis_professors.csv"
PAGE_SIZE = 100  # max teachers per request

# Browser-like headers to avoid 403
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/json",
    "Origin": "https://www.ratemyprofessors.com",
    "Referer": f"https://www.ratemyprofessors.com/search/professors/{UC_DAVIS_LEGACY_ID}?q=*",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
}


def build_search_query(first: int, after: str) -> str:
    # GraphQL query for teacher search at a school (matches RMP frontend)
    # Use escaped "after" for embedding in the query string
    after_val = json.dumps(after)
    return (
        "query TeacherSearchResultsPageQuery(\n"
        "  $query: TeacherSearchQuery!\n"
        "  $schoolID: ID\n"
        "  $includeSchoolFilter: Boolean!\n"
        ") {\n"
        "  search: newSearch {\n"
        "    ...TeacherSearchPagination_search_1ZLmLD\n"
        "  }\n"
        "  school: node(id: $schoolID) @include(if: $includeSchoolFilter) {\n"
        "    __typename\n"
        "    ... on School { name id }\n"
        "  }\n"
        "}\n\n"
        "fragment TeacherSearchPagination_search_1ZLmLD on newSearch {\n"
        f"  teachers(query: $query, first: {first}, after: {after_val}) {{\n"
        "    didFallback\n"
        "    edges { cursor node { ...TeacherCard_teacher id __typename } }\n"
        "    pageInfo { hasNextPage endCursor }\n"
        "    resultCount\n"
        "  }\n"
        "}\n\n"
        "fragment TeacherCard_teacher on Teacher {\n"
        "  id legacyId avgRating numRatings\n"
        "  ...CardFeedback_teacher ...CardSchool_teacher ...CardName_teacher\n"
        "}\n"
        "fragment CardFeedback_teacher on Teacher { wouldTakeAgainPercent avgDifficulty }\n"
        "fragment CardSchool_teacher on Teacher { department school { name id } }\n"
        "fragment CardName_teacher on Teacher { firstName lastName }\n"
    )


# Teacher profile query: get ratings (each has a course) by teacher global id
TEACHER_RATINGS_QUERY = """
query TeacherRatingsListQuery($id: ID!, $count: Int!) {
  node(id: $id) {
    ... on Teacher {
      ratings(first: $count) {
        edges {
          node {
            courseCode
            class
            course
          }
        }
      }
    }
  }
}
"""


def fetch_teacher_courses(legacy_id) -> list[str]:
    """Fetch unique course codes/names for a teacher from their ratings. Returns empty list on error."""
    if legacy_id is None:
        return []
    teacher_global_id = base64.b64encode(f"Teacher-{legacy_id}".encode()).decode()
    variables = {"id": teacher_global_id, "count": 100}
    payload = {"query": TEACHER_RATINGS_QUERY, "variables": variables}
    try:
        r = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("errors"):
            return []
        node = (data.get("data") or {}).get("node")
        if not node:
            return []
        ratings = node.get("ratings") or {}
        edges = ratings.get("edges") or []
        courses = set()
        for edge in edges:
            n = edge.get("node") or {}
            for key in ("courseCode", "class", "course"):
                val = n.get(key)
                if val and str(val).strip():
                    courses.add(str(val).strip())
        return sorted(courses)
    except Exception:
        return []


def fetch_page(search_text: str, after: str = "") -> dict:
    """Fetch one page of teachers for UC Davis. Returns GraphQL response payload."""
    query = build_search_query(PAGE_SIZE, after)
    variables = {
        "query": {
            "text": search_text,
            "schoolID": UC_DAVIS_SCHOOL_ID,
            "fallback": True,
            "departmentID": None,
        },
        "schoolID": UC_DAVIS_SCHOOL_ID,
        "includeSchoolFilter": False,  # skip node(id) to avoid base64 requirement
    }
    payload = {"query": query, "variables": variables}
    r = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data


def fetch_teachers_for_query(search_text: str) -> list[dict]:
    """Fetch all pages of teachers for one search query (e.g. a letter or empty string)."""
    results = []
    after = ""
    while True:
        data = fetch_page(search_text, after=after)
        search = data.get("data", {}).get("search", {})
        teachers = search.get("teachers", {})
        edges = teachers.get("edges", [])
        page_info = teachers.get("pageInfo", {})

        for edge in edges:
            node = edge.get("node")
            if node:
                results.append(node)

        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor") or ""
        if not after:
            break
        time.sleep(0.25)
    return results


def fetch_all_teachers() -> list[dict]:
    """Fetch all teachers at UC Davis by searching a-z and empty string, then deduplicate."""
    seen_ids = set()
    all_teachers = []
    # Search by each letter + empty string to cover all names
    search_terms = [""] + [c for c in "abcdefghijklmnopqrstuvwxyz"]
    for i, term in enumerate(search_terms):
        label = repr(term) if term else "(empty)"
        teachers = fetch_teachers_for_query(term)
        new = 0
        for node in teachers:
            tid = node.get("id") or node.get("legacyId")
            if tid is not None and tid not in seen_ids:
                seen_ids.add(tid)
                all_teachers.append(node)
                new += 1
        print(f"  Search {label}: got {len(teachers)} (new: {new}, total: {len(all_teachers)})")
        time.sleep(0.2)
    return all_teachers


def main():
    print("Fetching UC Davis professors from RateMyProfessors (GraphQL)...")
    try:
        teachers = fetch_all_teachers()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            print("Got 403 Forbidden. RateMyProfessors may be blocking this request.")
            print("Try running from a different network or later.")
        raise
    except Exception as e:
        print(f"Request failed: {e}")
        raise

    if not teachers:
        print("No professors returned. Writing header only.")
    else:
        print(f"Writing {len(teachers)} professors to {OUTPUT_CSV}")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "name",
            "department",
            "overall_rating",
            "difficulty_rating",
            "would_take_again_percentage",
            "num_ratings",
            "profile_url",
            "courses",
        ])
        for i, node in enumerate(teachers):
            first = node.get("firstName") or ""
            last = node.get("lastName") or ""
            name = f"{first} {last}".strip() or "Unknown"
            dept = node.get("department") or ""
            legacy_id = node.get("legacyId")
            profile_url = f"{RMP_PROFESSOR_URL}/{legacy_id}" if legacy_id else ""

            avg_rating = node.get("avgRating")
            avg_diff = node.get("avgDifficulty")
            would_take = node.get("wouldTakeAgainPercent")
            num_ratings = node.get("numRatings")
            if avg_rating is not None and avg_rating < 0:
                avg_rating = None
            if avg_diff is not None and avg_diff < 0:
                avg_diff = None
            if would_take is not None and would_take < 0:
                would_take = None
            if num_ratings is not None and num_ratings < 0:
                num_ratings = None

            # Fetch courses from teacher's ratings (one extra request per professor)
            courses_list = fetch_teacher_courses(legacy_id) if legacy_id else []
            courses_str = "; ".join(courses_list) if courses_list else ""

            writer.writerow([
                name,
                dept,
                str(round(avg_rating, 1)) if avg_rating is not None else "",
                str(round(avg_diff, 1)) if avg_diff is not None else "",
                str(int(would_take)) if would_take is not None else "",
                str(int(num_ratings)) if num_ratings is not None else "",
                profile_url,
                courses_str,
            ])
            if (i + 1) % 50 == 0:
                print(f"  Written {i + 1}/{len(teachers)} professors (with courses)")
            time.sleep(0.35)  # rate limit: one teacher-detail request per professor

    print("Done.")


if __name__ == "__main__":
    main()

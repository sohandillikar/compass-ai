"""
Add num_ratings column to ucdavis_professors.csv by fetching from RateMyProfessors GraphQL API.
Reads existing CSV, extracts professor ID from profile_url, fetches numRatings per row, writes updated CSV.
Run from repo root. Uses same headers as scrape_ucdavis_professors.py.
"""

import base64
import csv
import re
import time

import requests

GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
INPUT_CSV = "ucdavis_professors.csv"
OUTPUT_CSV = "ucdavis_professors.csv"  # overwrite in place; change to another path if you prefer backup

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

NUM_RATINGS_QUERY = """
query TeacherNumRatings($id: ID!) {
  node(id: $id) {
    ... on Teacher {
      numRatings
    }
  }
}
"""


def legacy_id_from_profile_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"/professor/(\d+)", url)
    return m.group(1) if m else None


def fetch_num_ratings(legacy_id: str) -> int | None:
    teacher_id = base64.b64encode(f"Teacher-{legacy_id}".encode()).decode()
    payload = {"query": NUM_RATINGS_QUERY, "variables": {"id": teacher_id}}
    try:
        r = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("errors"):
            return None
        node = (data.get("data") or {}).get("node")
        if not node:
            return None
        num = node.get("numRatings")
        return int(num) if num is not None and num >= 0 else None
    except Exception:
        return None


def main():
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "num_ratings" in fieldnames:
        print(f"{INPUT_CSV} already has num_ratings. Exiting.")
        return

    # Insert num_ratings after would_take_again_percentage to match scraper output
    if "would_take_again_percentage" in fieldnames:
        idx = fieldnames.index("would_take_again_percentage") + 1
        new_fieldnames = fieldnames[:idx] + ["num_ratings"] + fieldnames[idx:]
    else:
        new_fieldnames = fieldnames + ["num_ratings"]

    total = len(rows)
    print(f"Enriching {total} rows with num_ratings from RateMyProfessors...")

    for i, row in enumerate(rows):
        url = row.get("profile_url", "")
        legacy_id = legacy_id_from_profile_url(url)
        if legacy_id:
            num = fetch_num_ratings(legacy_id)
            row["num_ratings"] = str(num) if num is not None else ""
        else:
            row["num_ratings"] = ""
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{total}")
        time.sleep(0.35)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {OUTPUT_CSV} with num_ratings.")


if __name__ == "__main__":
    main()

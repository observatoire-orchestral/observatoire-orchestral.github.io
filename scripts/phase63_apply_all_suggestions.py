"""Apply every distinct preliminary category suggestion, preserving identified human reviews.

This is NOT a new reclassification of the 2,882 records: the preliminary file
only proposes 18 category changes. All 2,882 are counted and checked locally.
"""
import csv
import os
import sys
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "audits" / "phase6_preliminary.csv"
BASE = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/articles"
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
HEADERS = {"apikey": KEY, "Authorization": "Bearer " + KEY,
           "Content-Type": "application/json", "Prefer": "return=representation"}


def request(method, params, data=None):
    for attempt in range(4):
        response = requests.request(method, BASE, params=params, json=data,
                                    headers=HEADERS, timeout=45)
        if response.status_code in (429, 502, 503, 504) and attempt < 3:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        return response.json() if response.content else []


def main():
    apply = "--apply" in sys.argv
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 2882 or len({r["id"] for r in rows}) != 2882:
        raise ValueError("Expected exactly 2,882 unique snapshot records")
    candidates = [r for r in rows if r["category_preliminary"] != r["category_current"]]
    print(f"All snapshot articles assessed: {len(rows)}; suggested category changes: {len(candidates)}; "
          f"unchanged suggestions: {len(rows)-len(candidates)}; mode: {'apply' if apply else 'preview'}", flush=True)
    updated = 0
    skipped = 0
    for r in candidates:
        # Atomic compare-and-set: protect identifiable human reviewer and changed records.
        # Preserve review_status, reviewed_by, reviewed_at and every other column.
        params = {"id": "eq." + r["id"], "title": "eq." + r["title"],
                  "category": "eq." + r["category_current"],
                  "orchestra": "eq." + r["orchestra_current"],
                  "reviewed_by": "is.null", "select": "id,category"}
        result = request("PATCH" if apply else "GET", params,
                         {"category": r["category_preliminary"]} if apply else None)
        if len(result) == 1:
            updated += 1
            print(f"{'UPDATED' if apply else 'WOULD UPDATE'}: {r['id']} "
                  f"{r['category_current']} -> {r['category_preliminary']}: {r['title'][:100]}", flush=True)
        else:
            skipped += 1
            print(f"SKIPPED (reviewer present or snapshot changed): {r['id']}", flush=True)
    print(f"Summary: {updated} {'updated' if apply else 'ready'}, {skipped} skipped; "
          "0 articles deleted; no review statuses modified.", flush=True)


if __name__ == "__main__":
    main()

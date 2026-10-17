"""Conservative, reversible, snapshot-guarded application of Phase 6.1 category suggestions."""
import csv, os, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / 'audits' / 'phase6_preliminary.csv'
BASE = os.environ['SUPABASE_URL'].rstrip('/') + '/rest/v1/'
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
HEADERS = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}

def req(method, table, **kwargs):
    for attempt in range(4):
        resp = requests.request(method, BASE + table, headers=HEADERS, timeout=45, **kwargs)
        if resp.status_code in (429, 502, 503, 504) and attempt < 3:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp.json() if resp.content else []

def main():
    apply = '--apply' in sys.argv
    with CSV.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 2882 or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Historical audit file does not match expected 2,882 unique articles')
    eligible = [r for r in rows if r['category_current'] != r['category_preliminary']
                and r['confidence'] == 'élevée'
                and r['editorial_action'] == 'Proposition forte, à confirmer']
    print(f'Candidate high-confidence changes: {len(eligible)}; mode: {"apply" if apply else "preview"}', flush=True)
    changed = 0; skipped = 0
    for r in eligible:
        # Match snapshot AND original unreviewed status. No existing reviewed record is touched.
        params = {'id': 'eq.' + r['id'], 'title': 'eq.' + r['title'],
                  'category': 'eq.' + r['category_current'],
                  'orchestra': 'eq.' + r['orchestra_current'],
                  'review_status': 'eq.unreviewed', 'reviewed_by': 'is.null',
                  'select': 'id,title,category,orchestra,review_status,reviewed_by'}
        if apply:
            result = req('PATCH', 'articles', params=params, json={'category': r['category_preliminary']})
        else:
            result = req('GET', 'articles', params=params)
        if len(result) == 1:
            changed += 1
            print(f'{"UPDATED" if apply else "WOULD UPDATE"}: {r["id"]} {r["category_current"]} -> {r["category_preliminary"]}: {r["title"][:90]}', flush=True)
        else:
            skipped += 1
            print(f'SKIPPED (reviewed or snapshot changed): {r["id"]}', flush=True)
    print(f'Eligible and {"updated" if apply else "ready"}: {changed}; skipped: {skipped}; no statuses or reviewers modified.', flush=True)

if __name__ == '__main__':
    main()

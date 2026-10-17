"""Read-only report of possible misclassifications and duplicate stories.

Run locally with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set,
or in a manually dispatched GitHub workflow. No database writes.
"""
import csv
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
import requests
from classification import classify, organisations

def normalize_title(title):
    t = unicodedata.normalize('NFKD', (title or '').casefold())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r'[^a-z0-9]+', ' ', t).strip()
    # Only remove trailing publisher suffixes if the source matches.
    return t

def report(rows, output):
    candidates = []
    groups = defaultdict(list)
    for row in rows:
        title = row.get('title') or ''
        summary = row.get('summary') or ''
        old_cat = row.get('category') or ''
        suggested_cat = classify(title, summary, old_cat, row.get('source') or '', row.get('url') or '')
        names = organisations(title, summary)
        current = row.get('organizations') or []
        # A report, not an automatic correction.
        reasons = []
        if old_cat != suggested_cat:
            reasons.append('category_candidate_review_manually')
        if set(names) - set(current):
            reasons.append('additional_organization_candidate')
        if reasons:
            candidates.append({'id': row['id'], 'title': title, 'url': row.get('url'),
                'current_category': old_cat, 'suggested_category': suggested_cat,
                'current_organizations': ' | '.join(current),
                'suggested_organizations': ' | '.join(names),
                'review_status': row.get('review_status'), 'reasons': ' | '.join(reasons)})
        key = (normalize_title(title), (row.get('source') or '').casefold().strip())
        if len(key[0]) >= 22:
            groups[key].append(row)
    duplicates = []
    for (title, source), items in groups.items():
        if len(items) < 2: continue
        urls = {i.get('url') for i in items}
        if len(urls) < 2: continue
        for i in items:
            duplicates.append({'group_title': title, 'source': source, 'id': i['id'], 'url': i.get('url')})
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    for name, data, fields in [
        ('classification_candidates.csv', candidates, ['id','title','url','current_category','suggested_category','current_organizations','suggested_organizations','review_status','reasons']),
        ('duplicate_candidates.csv', duplicates, ['group_title','source','id','url'])]:
        with (output / name).open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(data)
    return len(candidates), len(duplicates)

def fetch():
    url = os.environ['SUPABASE_URL'].rstrip('/')
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    session = requests.Session()
    session.headers.update({'apikey': key, 'Authorization': 'Bearer ' + key})
    results = []
    for start in range(0, 100000, 500):
        response = session.get(url + '/rest/v1/articles', params={
            'select': 'id,url,title,summary,source,orchestra,organizations,category,review_status',
            'order': 'found_at.asc', 'offset': start, 'limit': 500}, timeout=35)
        response.raise_for_status()
        page = response.json(); results.extend(page)
        if len(page) < 500: break
    return results

if __name__ == '__main__':
    n, d = report(fetch(), 'phase2_reports')
    print(f'Read-only audit: {n} classification candidates, {d} duplicate candidate rows.')
    print('No database records changed. See phase2_reports/*.csv')

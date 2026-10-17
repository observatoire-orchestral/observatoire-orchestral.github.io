"""Import suggestions into a separate read-only editorial table; never update articles."""
import csv, os, sys, time
from pathlib import Path
import requests

BASE = os.environ['SUPABASE_URL'].rstrip('/')
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
HEADERS = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}
PATH = Path('audits/phase6_preliminary.csv')

def request(method, path, **kwargs):
    for attempt in range(4):
        headers = kwargs.pop('headers', HEADERS)
        resp = requests.request(method, BASE + '/rest/v1/' + path, headers=headers, timeout=45, **kwargs)
        if resp.status_code in (429, 502, 503, 504) and attempt < 3:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp

def main():
    with PATH.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 2882 or len({r['id'] for r in rows}) != 2882:
        raise ValueError('Expected exactly 2,882 distinct historical records')
    current = {}
    offset = 0
    while True:
        response = request('GET', 'articles', params={'select':'id,title,category,orchestra', 'limit':500,'offset':offset,'order':'id.asc'})
        page = response.json()
        current.update({r['id']:r for r in page})
        if len(page) < 500: break
        offset += 500
    prepared=[]; skipped=0
    for r in rows:
        a=current.get(r['id'])
        if not a or a['title'] != r['title'] or a['category'] != r['category_current'] or a['orchestra'] != r['orchestra_current']:
            skipped+=1
            continue
        prepared.append({'article_id':r['id'], 'title_snapshot':r['title'], 'category_snapshot':r['category_current'],
          'proposed_category':r['category_preliminary'], 'orchestra_snapshot':r['orchestra_current'],
          'proposed_orchestra':r['orchestra_audit_suggestion'], 'relevance':r['relevance_preliminary'],
          'relevance_reason':r['relevance_reason'], 'confidence':r['confidence'],
          'category_reason':r['category_reason'], 'editorial_action':r['editorial_action']})
    print(f'Historical records: {len(rows)}; matching current articles: {len(prepared)}; skipped (changed/missing): {skipped}',flush=True)
    if '--apply' not in sys.argv:
        print('Preview only; no database writes.')
        return
    headers=dict(HEADERS, Prefer='resolution=merge-duplicates,return=minimal')
    for start in range(0,len(prepared),100):
        batch=prepared[start:start+100]
        resp=request('POST','editorial_suggestions',json=batch,headers=headers)
    print(f'Imported {len(prepared)} suggestions; public.articles unchanged.')

if __name__ == '__main__': main()

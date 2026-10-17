"""Preview/apply full editorial recategorization. Does not alter review metadata."""
import csv, os, sys, time, json
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
CSV=ROOT/'audits'/'phase64_full_reclassification.csv'
BASE=os.environ['SUPABASE_URL'].rstrip('/')+'/rest/v1/articles'
KEY=os.environ['SUPABASE_SERVICE_ROLE_KEY']
HEAD={'apikey':KEY,'Authorization':'Bearer '+KEY,'Content-Type':'application/json','Prefer':'return=representation'}

def req(method,params,data=None):
 for attempt in range(4):
  r=requests.request(method,BASE,params=params,json=data,headers=HEAD,timeout=40)
  if r.status_code in (429,502,503,504) and attempt<3:time.sleep(2**attempt);continue
  r.raise_for_status();return r.json() if r.content else []

def main():
 apply='--apply' in sys.argv
 with CSV.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 assert len(rows)==2882 and len({r['id'] for r in rows})==2882,'Snapshot mismatch'
 candidates=[r for r in rows if r['category_current']!=r['category_proposed']]
 print(f'Full editorial decisions: {len(rows)}; proposed changes: {len(candidates)}; mode: {"apply" if apply else "preview"}',flush=True)
 report=[]
 for i,r in enumerate(candidates,1):
  params={'id':'eq.'+r['id'],'title':'eq.'+r['title'],'category':'eq.'+r['category_current'],'orchestra':'eq.'+r['orchestra_current'],'reviewed_by':'is.null','select':'id,category'}
  try:
   out=req('PATCH' if apply else 'GET',params,{'category':r['category_proposed']} if apply else None)
   status=('UPDATED' if apply else 'READY') if len(out)==1 else 'SKIPPED (changed or human-reviewed)'
  except Exception as e:
   status='ERROR: '+str(e);report.append((r['id'],status));print(status,flush=True);break
  report.append((r['id'],status))
  if i%50==0 or i==len(candidates):print(f'Processed {i}/{len(candidates)}; last: {status}',flush=True)
 path=ROOT/'audits'/'phase64_last_run.csv'
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['id','result']);w.writerows(report)
 from collections import Counter
 print('Result:',dict(Counter(s for _,s in report)),'; articles not deleted; review metadata untouched.',flush=True)
 if any(s.startswith('ERROR') for _,s in report):sys.exit(1)
if __name__=='__main__':main()

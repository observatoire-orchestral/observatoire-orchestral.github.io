"""Historical article audit. Preview by default; apply requires an approved CSV and explicit confirmation."""
import argparse
import csv
import io
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classification import classify, organisations, SECTOR
from relevance import assess

FIELDS = ['id','title','summary','source','url','orchestra','category','review_status','reviewed_by','organizations']
PREVIEW_FIELDS = ['id','action','old_category','new_category','old_orchestra','new_orchestra','reason','title','url']
APPROVE_FIELDS = ['id','action','old_category','new_category','old_orchestra','new_orchestra','reason','title','url']


def candidate(article):
    # Protect any record with a human review, even if review_status is inconsistent.
    if article.get('reviewed_by') or article.get('review_status') in ('approved','rejected','validated','reviewed'):
        return None
    title = article.get('title') or ''
    summary = article.get('summary') or ''
    source = article.get('source') or ''
    url = article.get('url') or ''
    decision = assess(title, summary, source, url, article.get('orchestra') or '')
    names = organisations(title, summary)
    current_orchestra = article.get('orchestra') or SECTOR
    # Only replace a generic label when precisely one organization is detected.
    proposed_orchestra = names[0] if len(names) == 1 and current_orchestra == SECTOR else current_orchestra
    proposed_category = classify(title, summary, article.get('category') or 'Autres', source, url)
    if not decision.accept:
        action = 'flag_irrelevant'  # never delete or reject automatically
    elif proposed_category != article.get('category') or proposed_orchestra != current_orchestra:
        action = 'reclassify'
    else:
        return None
    return {'id':article['id'],'action':action,'old_category':article.get('category') or '',
            'new_category':proposed_category,'old_orchestra':current_orchestra,
            'new_orchestra':proposed_orchestra,'reason':decision.reason,'title':title,'url':url}


def get_all(session, base):
    result=[]
    start=0
    while True:
        response=session.get(base+'/rest/v1/articles',params={'select':','.join(FIELDS),'order':'id.asc','limit':'500','offset':str(start)},timeout=45)
        response.raise_for_status()
        batch=response.json()
        result.extend(batch)
        if len(batch)<500: break
        start+=len(batch)
    return result


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)


def apply_approved(session,base,all_rows,approved_path):
    current={str(row['id']):row for row in all_rows}
    with approved_path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not set(APPROVE_FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('Approval CSV does not have the required columns')
        approved=list(reader)
    if len({r['id'] for r in approved})!=len(approved):
        raise ValueError('Approval CSV contains duplicate IDs')
    changed=Counter()
    for row in approved:
        if row['action'] != 'reclassify':
            changed['skipped_non_reclassify']+=1;continue
        original=current.get(row['id'])
        if original is None or original.get('reviewed_by') or original.get('review_status') in ('approved','rejected','validated','reviewed'):
            changed['skipped_protected_or_missing']+=1;continue
        if original.get('category')!=row['old_category'] or (original.get('orchestra') or SECTOR)!=row['old_orchestra']:
            changed['skipped_changed_since_preview']+=1;continue
        # Recalculate, rather than blindly trust values in a potentially edited CSV.
        expected=candidate(original)
        if not expected or expected['action']!='reclassify' or any(str(expected[k])!=str(row[k]) for k in ('new_category','new_orchestra','title','url')):
            changed['skipped_stale_or_modified']+=1;continue
        payload={}
        if row['new_category']!=row['old_category']:payload['category']=row['new_category']
        if row['new_orchestra']!=row['old_orchestra']:payload['orchestra']=row['new_orchestra']
        if not payload:continue
        # Optimistic conditions guard against concurrent editorial changes.
        response=session.patch(base+'/rest/v1/articles',params={'id':'eq.'+row['id'], 'category':'eq.'+row['old_category'],
            'orchestra':'eq.'+row['old_orchestra'],'reviewed_by':'is.null','review_status':'eq.'+(original.get('review_status') or 'unreviewed'),
            'select':'id'},headers={'Prefer':'return=representation'},json=payload,timeout=45)
        response.raise_for_status()
        if len(response.json())==1:changed['updated']+=1
        else:changed['skipped_concurrent_change']+=1
    return changed


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['preview','apply'],default='preview')
    parser.add_argument('--approved',default='audits/approved_reclassification.csv')
    parser.add_argument('--out',default='reclassification_report')
    parser.add_argument('--confirm',default='')
    args=parser.parse_args(argv)
    if args.mode=='apply' and args.confirm!='APPLY_APPROVED_CHANGES':
        parser.error('Apply requires --confirm APPLY_APPROVED_CHANGES')
    base=os.environ['SUPABASE_URL'].rstrip('/')
    key=os.environ['SUPABASE_SERVICE_ROLE_KEY']
    session=requests.Session()
    session.headers.update({'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    all_rows=get_all(session,base)
    print('Rows read:',len(all_rows))
    if args.mode=='preview':
        proposals=[p for article in all_rows if (p:=candidate(article))]
        out=Path(args.out)
        write_csv(out/'preview.csv',PREVIEW_FIELDS,proposals)
        write_csv(out/'backup.csv',FIELDS,all_rows)
        counts=Counter(p['action'] for p in proposals)
        print('Preview proposals:',dict(counts))
        print('Saved preview.csv and backup.csv (no database writes)')
    else:
        approved=Path(args.approved)
        if not approved.is_file():raise FileNotFoundError('Missing approved CSV: '+str(approved))
        print('Apply results:',dict(apply_approved(session,base,all_rows,approved)))

if __name__=='__main__':main()

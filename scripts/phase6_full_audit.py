"""Non-destructive full audit: every Supabase article receives a recommendation, never an editorial decision."""
import csv
import os
from collections import Counter
from pathlib import Path
import requests
from reclassify_history import get_all, FIELDS
from classification import classify, organisations, SECTOR
from relevance import assess

COLUMNS = ['id','review_status','reviewed_by','title','url','source','old_category','suggested_category','old_orchestra','suggested_orchestra','relevance','confidence','reason','suggestion','summary']

def analyse(a):
    title, summary = a.get('title') or '', a.get('summary') or ''
    decision = assess(title, summary, a.get('source') or '', a.get('url') or '', a.get('orchestra') or '')
    names = organisations(title, summary)
    old_orch = a.get('orchestra') or SECTOR
    new_orch = names[0] if len(names) == 1 and old_orch == SECTOR else old_orch
    old_cat = a.get('category') or 'Autres'
    new_cat = classify(title, summary, old_cat, a.get('source') or '', a.get('url') or '')
    protected = bool(a.get('reviewed_by')) or a.get('review_status') in ('approved','rejected','validated','reviewed')
    suggestion = 'Décision humaine conservée' if protected else ('Classement à examiner' if old_cat != new_cat or old_orch != new_orch else ('Pertinence à vérifier' if not decision.accept else 'Aucune correction proposée'))
    return dict(id=a['id'], review_status=a.get('review_status') or '', reviewed_by=a.get('reviewed_by') or '', title=title,url=a.get('url') or '',source=a.get('source') or '',old_category=old_cat,suggested_category=new_cat,old_orchestra=old_orch,suggested_orchestra=new_orch,relevance='Probablement pertinent' if decision.accept else 'À vérifier (non confirmé)',confidence=decision.confidence,reason=decision.reason,suggestion=suggestion,summary=summary)

def main():
    base=os.environ['SUPABASE_URL'].rstrip('/')
    key=os.environ['SUPABASE_SERVICE_ROLE_KEY']
    session=requests.Session()
    session.headers.update({'apikey':key,'Authorization':'Bearer '+key})
    articles=get_all(session,base)
    out=Path('phase6_audit');out.mkdir(exist_ok=True)
    rows=[analyse(a) for a in articles]
    with (out/'all_articles.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(rows)
    counts=Counter(r['suggestion'] for r in rows)
    report='\n'.join(['Audit complet (lecture seule)',f'Articles lus : {len(articles)}',*('%s : %s'%(k,v) for k,v in sorted(counts.items())),'Aucun article modifié, supprimé ou écarté automatiquement.'])
    (out/'summary.txt').write_text(report+'\n',encoding='utf-8')
    print(report)

if __name__=='__main__':main()

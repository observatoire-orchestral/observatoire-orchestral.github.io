"""Reproducible full-snapshot editorial classification, based on headlines and summaries."""
import re, csv, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'audits'/'phase64_source_snapshot.csv'
OUT=ROOT/'audits'/'phase64_full_reclassification.csv'

def norm(s):
 s=unicodedata.normalize('NFKD',s.lower());return ''.join(c for c in s if not unicodedata.combining(c))

def hit(s,patterns):return any(re.search(p,s) for p in patterns)
PATTERNS=[
 ('Mobilisation et grève', [r'\bgreve\b',r'\bsyndicat',r'\bmobilis',r'\bmanifest',r'\bpreavis',r'\bdebray',r'\bprotest',r'\bpiquet de greve',r'\bconflit social',r'\bnegociations? social',r'\bpersonnel[s]? en colere',r'\bmusiciens? en colere',r'\bintermittents? en lutte',r'\btract syndical']),
 ('Conditions de travail',[r'conditions? de travail',r'\bsouffrance au travail',r'\bharcelement',r'\brisques? psychosociaux',r'\bprecarite',r'\bsurcharge de travail',r'\btemps de travail',r'\bremuneration',r'\bsalaires?\b',r'\bmal[- ]etre',r'\bsante au travail',r'\bepuisement professionnel',r'\baccusations? de (harcelement|violence)',r'\bviolences? sexistes']),
 ('Budget et subventions',[r'\bbudget',r'\bsubvention',r'\bfinanc',r'\bdeficit',r'\beconomies?\b',r'\bcoupes? budget',r'\brestrictions? budget',r'\bdotations?\b',r'\bmillions? d.euros',r'\bmilliers? d.euros',r'\bcrise financiere',r'\bfaillite',r'\bdetournement',r'\bcomptes? (publics?|annuels?)',r'\bperte de financement',r'\bdesengagement',r'\bausterite']),
 ('Emploi et recrutement',[r'\brecrut',r'\baudition[s]? (de|pour) (recrut|poste)',r'\bconcours de recrutement',r'\bpostes? vacants?',r'\bsuppressions? de postes?',r'\blicenci',r'\bembauch',r'\bcontrats? de travail',r'\bemploi[s]?\b',r'\boffres? d.emploi',r'\bposte a pourvoir',r'\bappel a candidatures?']),
 ('Gouvernance',[r'\bnomme (directeur|directrice|chef)',r'\bnommee (directrice|directeur)',r'\bnomination',r'\bnouveau directeur',r'\bnouvelle directrice',r'\bdirecteur musical',r'\bdirectrice musicale',r'\bdirection musicale',r'\bdirecteur general',r'\bdirectrice generale',r'\bpresidence',r'\bpresident',r'\bdemission',r'\brevocation',r'\blimoge',r'\brenvoi du directeur',r'\bconseil d.administration',r'\bconseil de surveillance',r'\breorganisation',r'\bgouvernance',r'\bcrise a la direction',r'\bprojet artistique',r'\bchangement de direction',r'\bprend la tete',r'\bprendra la tete',r'\ba la tete de l.orchestre',r'\bdirigera l.orchestre',r'\bnouveau chef permanent',r'\bnouvelle cheffe permanente',r'\bchef principal',r'\bcheffe principale']),
]
CRIT=[r'\bcritique\b',r'\bcompte rendu\b',r'\brecension\b',r'\bchronique musicale',r'\bconcert (?:magistral|sublime|remarquable|eblouissant|decevant|bouleversant)',r'\binterpretation (?:magistrale|sublime|remarquable)',r'\btriomphe (?:a|de|pour|au)',r'\bune (?:soir[eé]e|production) (?:magistrale|sublime|remarquable|eblouissante)',r'\b(?:mozart|verdi|wagner|puccini|rossini|donizetti|bizet|gluck|strauss|bellini|haendel|handel|massenet|debussy|ravel|berlioz|grieg|prokofiev|bach),?\s+[^:]{2,65}\s+[–-]\s+[^:]{2,65}']
REVIEW_SOURCES=['bachtrack','forum opera','olyrix','resmusica','concertclassic','classiquenews','opera online','opera magazine']
EXCLUSION=[r'\bfootball\b',r'\bpolice nationale\b',r'\bsenegal\b',r'\bonpl a la dic',r'\bchampionnat\b',r'\bligue 1\b',r'\bbasketball\b',r'\brugby\b']

def classify(r):
 title=norm(r['title']); summary=norm(r['summary']); source=norm(r['source']); text=title+' '+(summary if summary!=title else '')
 for p in EXCLUSION:
  if re.search(p,text):return 'Autres','Hors champ apparent', 'Exclusion contextuelle; vérifier si nécessaire'
 # headline-driven category, avoid spurious secondary keywords in RSS descriptions
 for cat,patterns in PATTERNS:
  if hit(title,patterns):
   if cat=='Mobilisation et grève' and not hit(text,[r'\borchestre\b',r'\bopera\b',r'\bmusique\b',r'\bmusicien',r'\bculture\b',r'\btheatre\b',r'\bscala\b',r'\bfenice\b']):continue
   if cat=='Budget et subventions' and hit(title,[r'\borchestre du titanic\b',r'\bimmobilier\b',r'\bfrais de notaire\b']):continue
   return cat,'Signal explicite', 'Thème explicite dans le titre'
 # critical review of a performance: opinionated title or specialist publication with work / location
 if hit(title,CRIT):return 'Critique musicale','Signal explicite','Compte rendu ou critique identifiable dans le titre'
 if any(x in source+' '+title for x in REVIEW_SOURCES):
  if r['old_category']=='Critique musicale' and not hit(title,[r'\blisting\b',r'\btickets?\b',r'\bbilletterie\b',r'\bagenda\b',r'\bcalendrier\b',r'\bannonce\b',r'\bprogramme de la saison\b',r'\bstatistiques\b',r'\bentretien avec\b',r'\binterview\b',r'\bportrait\b']):
   return 'Critique musicale','Conservation contextualisée','Critique existante dans un média spécialisé, sans indice de simple annonce'
  if hit(title,[r'\b(?:mozart|verdi|wagner|puccini|rossini|donizetti|bizet|gluck|strauss|bellini|haendel|handel|massenet|debussy|ravel|berlioz|grieg|prokofiev|bach|beethoven|mahler|bruckner|tchaikovski|chostakovitch|schubert),?\s+[^\n]{3,65}[–-]',r'\b(?:a|au|aux) (?:paris|toulouse|lyon|nantes|bordeaux|montpellier|strasbourg|lille|marseille|rouen|dijon|nice|angers|metz|tours|rennes|bayreuth|milan|geneve)\b',r'\b(?:saison|concert|recital|opera|symphonie|festival|representation)\b']):
   return 'Critique musicale','Interprétation éditoriale','Publication spécialisée, événement ou œuvre musicale; à confirmer'
 if hit(title,[r'\b(?:orchestre|philharmoni|symphoni|opera|musicien|cheffe? d.orchestre)\b']) and hit(summary,PATTERNS[0][1]+PATTERNS[1][1]+PATTERNS[2][1]+PATTERNS[3][1]+PATTERNS[4][1]):
  for cat,patterns in PATTERNS:
   if hit(summary,patterns):return cat,'Signal secondaire','Thème repéré dans le résumé, pas dans le titre'
 return 'Autres','Classification générale','Aucun thème spécifique suffisamment étayé par le titre/résumé'

def main():
 with SRC.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 if len(rows)!=2882 or len(set(r['id'] for r in rows))!=2882:raise ValueError('Snapshot incomplet ou dupliqué')
 fields=['id','title','url','source','category_current','category_proposed','category_changed','confidence','reason','review_status','reviewed_by','orchestra_current','summary']
 with OUT.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:
   cat,conf,reason=classify(r)
   w.writerow(dict(id=r['id'],title=r['title'],url=r['url'],source=r['source'],category_current=r['old_category'],category_proposed=cat,category_changed=int(cat!=r['old_category']),confidence=conf,reason=reason,review_status=r['review_status'],reviewed_by=r['reviewed_by'],orchestra_current=r['old_orchestra'],summary=r['summary']))
 print('Wrote',len(rows),'editorial decisions to',OUT)
if __name__=='__main__':main()

"""Conservative classification. A lack of keywords is not evidence for 'Autres'."""
import re
import unicodedata
from urllib.parse import urlparse

SECTOR = 'Secteur orchestral français'
CATEGORIES = ('Autres', 'Budget et subventions', 'Conditions de travail', 'Critique musicale', 'Emploi et recrutement', 'Gouvernance', 'Mobilisation et grève')
ALIASES = {
 'ONPL': ('ONPL','Orchestre National des Pays de la Loire','Orchestre des Pays de la Loire'),
 'Angers Nantes Opéra': ('Angers Nantes Opéra','Angers-Nantes Opéra'),
 'Orchestre de Paris': ('Orchestre de Paris',),
 'Orchestre national de France': ('Orchestre national de France',),
 'Orchestre philharmonique de Radio France': ('Orchestre philharmonique de Radio France',),
 'Orchestre national de Lyon': ('Orchestre national de Lyon',),
 'Orchestre national de Lille': ('Orchestre national de Lille',),
 'Orchestre national de Bordeaux Aquitaine': ('Orchestre national Bordeaux Aquitaine','Orchestre national de Bordeaux Aquitaine','ONBA'),
 'Orchestre national du Capitole de Toulouse': ('Orchestre national du Capitole',),
 'Orchestre philharmonique de Strasbourg': ('Orchestre philharmonique de Strasbourg',),
 'Orchestre national de Metz': ('Orchestre national de Metz',),
 'Orchestre national de Bretagne': ('Orchestre national de Bretagne',),
 'Orchestre national de Montpellier': ('Orchestre national Montpellier','Orchestre national de Montpellier'),
 'Orchestre de l’Opéra de Nice': ('Orchestre Philharmonique de Nice',"Orchestre de l'Opéra de Nice"),
 'Orchestre national d’Île-de-France': ("Orchestre national d'Île-de-France",'ONDIF'),
 'Orchestre de l’Opéra de Marseille': ('Orchestre Philharmonique de Marseille',"Orchestre de l'Opéra de Marseille"),
 'Orchestre national Avignon-Provence': ('Orchestre national Avignon-Provence',"Orchestre national d'Avignon-Provence"),
 'Orchestre national de Cannes': ('Orchestre national de Cannes',),
 'Orchestre national de Mulhouse': ('Orchestre national de Mulhouse',),
 'Orchestre national de Nancy': ("Orchestre de l'Opéra national de Lorraine",'Orchestre de l’Opéra national de Lorraine'),
 'Orchestre national Auvergne-Rhône-Alpes': ('Orchestre national Auvergne-Rhône-Alpes',),
 'Orchestre de chambre de Paris': ('Orchestre de chambre de Paris',),
 'Orchestre de chambre de Toulouse': ('Orchestre de chambre de Toulouse',),
 'Orchestre de Picardie': ('Orchestre de Picardie',),
 'Orchestre symphonique de Bretagne': ('Orchestre symphonique de Bretagne',),
 'Orchestre symphonique de Mulhouse': ('Orchestre symphonique de Mulhouse',),
 'Orchestre symphonique de Saint-Étienne': ('Orchestre symphonique Saint-Étienne',),
 'Orchestre de l’Opéra de Rouen Normandie': ("Orchestre de l'Opéra de Rouen Normandie",),
}
KEYWORDS = {
 'Budget et subventions': ('budget','subvention','subventions','deficit','financement','dotation','coupe budgetaire','baisse de financement','aide publique','desengagement financier','fonds de roulement'),
 'Conditions de travail': ('conditions de travail','temps de travail','remuneration','salaire','salaires','convention collective','risques psychosociaux','souffrance au travail','harcelement','heures supplementaires','charge de travail','sante au travail','repos hebdomadaire'),
 'Emploi et recrutement': ('recrutement','licenciement','suppression de poste','suppression de postes','gel des recrutements','offre d emploi','concours de recrutement','auditions et concours','postes vacants','non remplacement','non renouvellement'),
 'Gouvernance': ('gouvernance','directeur general','nomination','demission','restructuration','reorganisation','conseil d administration','audit','direction generale','chambre regionale des comptes','nouvelle directrice','nouveau directeur','directeur musical','directrice musicale','renouvellement de mandat','nomme a la tete','nommee a la tete'),
 'Mobilisation et grève': ('greve','preavis de greve','mobilisation','manifestation','syndicat','syndical','petition','mouvement social','debrayage'),
}

REVIEW = ('critique', 'compte rendu', 'recension', 'concert review', 'opera review', 'chronique musicale', 'notre critique')
NOT_REVIEW = ('billetterie', 'agenda', 'calendrier', 'programme de saison', 'abonnement', 'event listing', 'listing and tickets', 'tickets', 'reservation de billets', 'archives des', 'parcours de visite', 'maquette', 'programme complet')
REVIEW_SITES = ('bachtrack.com','resmusica.com','forumopera.com','concertclassic.com','classykeo.com','olyrix.com')
GOVERNANCE_TITLES = ('nouvelle directrice', 'nouveau directeur', 'nomme directeur', 'nommee directrice', 'renouvele a la tete', 'reconduit a la tete', 'prend la direction', 'direction de l orchestre', 'directeur musical nomme', 'directrice musicale nommee')
BUDGET_TITLES = ('trop chers', 'trop cher', 'coutent trop', 'financement en baisse')
# Narrow, title-based exclusion only. We avoid discarding uncertain articles.
IRRELEVANT_TITLES = ('listing and tickets', 'ouverture de la billetterie', 'reservation de billets', 'archives des', 'parcours de visite', 'programme complet', 'acheter vos billets', 'billets disponibles', 'calendrier des concerts')

def fold(value):
 value = unicodedata.normalize('NFKD',str(value or '').casefold())
 return re.sub(r'[^a-z0-9]+',' ',''.join(x for x in value if not unicodedata.combining(x))).strip()
def has(text,phrase):
 p=fold(phrase)
 return bool(p and re.search(r'(?<!\w)'+re.escape(p)+r'(?!\w)',text))
def is_review_source(source='',url=''):
 domain=urlparse(url or '').hostname or ''
 domain=domain.lower().removeprefix('www.')
 return any(domain == site or domain.endswith('.'+site) for site in REVIEW_SITES) or any(has(fold(source),site.split('.')[0]) for site in REVIEW_SITES)
def clearly_irrelevant(title, summary='', source='', url=''):
 heading=fold(title)
 if any(has(heading,x) for x in IRRELEVANT_TITLES):
  return True
 # Avoid rejecting actual reporting just because it mentions a concert.
 if ('jumping de bordeaux' in heading and 'equestre' in heading) or 'asm rugby' in heading:
  return True
 return False

def classify(title,summary='',suggested='Autres',source='',url=''):
 heading,body=fold(title),fold(summary)
 scores={k:3*sum(has(heading,w) for w in words)+sum(has(body,w) for w in words) for k,words in KEYWORDS.items()}
 if any(has(heading,x) for x in GOVERNANCE_TITLES): scores['Gouvernance']+=6
 if any(has(heading,x) for x in BUDGET_TITLES) and ('orchestre' in heading or 'musicien' in heading): scores['Budget et subventions']+=6
 # Subject-matter reporting outranks source reputation or review wording.
 best=max(scores,key=scores.get)
 if scores[best]: return best
 excluded=any(has(heading,x) for x in NOT_REVIEW)
 if not excluded and any(has(heading,x) for x in REVIEW): return 'Critique musicale'
 # Source alone does not prove the article is a performance review.
 # Preserve an explicit upstream review designation only if not an obvious listing.
 if suggested=='Critique musicale' and not excluded and any(has(heading,x) for x in ('compte rendu','critique','recital','concert','opera','symphonie','representation')): return suggested
 if suggested in CATEGORIES and suggested!='Critique musicale': return suggested
 return 'Autres'
def organisations(title,summary=''):
 t=fold(title+' '+summary)
 return [name for name,aliases in ALIASES.items() if any(has(t,a) for a in aliases)]
def prepare(article):
 item=dict(article)
 title,summary=item.get('title',''),item.get('summary','')
 item['category']=classify(title,summary,item.get('category','Autres'),item.get('source',''),item.get('url',''))
 names=organisations(title,summary)
 item['orchestra']=names[0] if len(names)==1 else SECTOR
 item['organizations']=names
 item['is_auto']=True
 item['review_status']='unreviewed'
 item.pop('reviewed_by',None);item.pop('reviewed_at',None)
 return item

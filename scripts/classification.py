"""Shared, conservative classification for newly discovered articles.

No paid APIs. The database remains the source of truth for human decisions.
"""
import re
import unicodedata

SECTOR = 'Secteur orchestral français'
CATEGORIES = ('Autres', 'Budget et subventions', 'Conditions de travail',
              'Critique musicale', 'Emploi et recrutement', 'Gouvernance',
              'Mobilisation et grève')

# Prefer distinctive organisation names. Do not infer participation from a venue.
ALIASES = {
    'ONPL': ('ONPL', 'Orchestre National des Pays de la Loire', 'Orchestre des Pays de la Loire'),
    'Angers Nantes Opéra': ('Angers Nantes Opéra', 'Angers-Nantes Opéra'),
    'Orchestre de Paris': ('Orchestre de Paris',),
    'Orchestre national de Lyon': ('Orchestre national de Lyon',),
    'Orchestre national de Lille': ('Orchestre national de Lille',),
    'Orchestre national de Bordeaux Aquitaine': ('Orchestre national Bordeaux Aquitaine', 'Orchestre national de Bordeaux Aquitaine', 'ONBA'),
    'Orchestre national du Capitole de Toulouse': ('Orchestre national du Capitole',),
    'Orchestre philharmonique de Strasbourg': ('Orchestre philharmonique de Strasbourg',),
    'Orchestre national de Metz': ('Orchestre national de Metz',),
    'Orchestre national de Bretagne': ('Orchestre national de Bretagne',),
    'Orchestre national de Montpellier': ('Orchestre national Montpellier', 'Orchestre national de Montpellier'),
    'Orchestre de l’Opéra de Nice': ('Orchestre Philharmonique de Nice', "Orchestre de l'Opéra de Nice"),
    'Orchestre national d’Île-de-France': ("Orchestre national d'Île-de-France", 'ONDIF'),
    'Orchestre de l’Opéra de Marseille': ('Orchestre Philharmonique de Marseille', "Orchestre de l'Opéra de Marseille"),
    'Orchestre national Avignon-Provence': ('Orchestre national Avignon-Provence', "Orchestre national d'Avignon-Provence"),
    'Orchestre national de Cannes': ('Orchestre national de Cannes',),
}

KEYWORDS = {
    'Budget et subventions': ('budget', 'subvention', 'deficit', 'financement', 'dotation', 'coupe budgetaire', 'baisse de financement', 'aide publique'),
    'Conditions de travail': ('conditions de travail', 'temps de travail', 'remuneration', 'salaire', 'convention collective', 'risques psychosociaux', 'souffrance au travail'),
    'Emploi et recrutement': ('recrutement', 'licenciement', 'suppression de poste', 'suppression de postes', 'gel des recrutements', 'offre d emploi', 'concours de recrutement', 'effectifs'),
    'Gouvernance': ('gouvernance', 'directeur general', 'nomination', 'demission', 'restructuration', 'reorganisation', 'conseil d administration', 'audit'),
    'Mobilisation et grève': ('greve', 'preavis de greve', 'mobilisation', 'manifestation', 'syndicat', 'syndical', 'petition', 'mouvement social'),
}
REVIEW = ('critique', 'compte rendu', 'recension', 'concert review', 'opera review', 'chronique musicale')
PERFORMANCE = ('concert', 'opera', 'symphonie', 'concerto', 'recital', 'representation', 'production', 'interpretation')
NOT_REVIEW = ('billetterie', 'agenda', 'calendrier', 'programme de saison', 'abonnement', 'event listing', 'veranstaltungskalender')

def fold(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(x for x in value if not unicodedata.combining(x))).strip()

def has(text, phrase):
    p = fold(phrase)
    return bool(p and re.search(r'(?<!\w)' + re.escape(p) + r'(?!\w)', text))

def classify(title, summary='', suggested='Autres'):
    heading, body = fold(title), fold(summary)
    if not any(has(heading, x) for x in NOT_REVIEW) and any(has(heading, x) for x in REVIEW) and any(has(heading+' '+body, x) for x in PERFORMANCE):
        return 'Critique musicale'
    scores = {}
    for category, words in KEYWORDS.items():
        scores[category] = sum(3 for x in words if has(heading, x)) + sum(1 for x in words if has(body, x))
    highest = max(scores.values(), default=0)
    if highest:
        return max(scores, key=lambda k: scores[k])
    # A dedicated review collector can supply a cautiously checked review label.
    if suggested == 'Critique musicale' and not any(has(heading, x) for x in NOT_REVIEW):
        return 'Critique musicale'
    return 'Autres'

def organisations(title, summary=''):
    t = fold(title+' '+summary)
    return [name for name, aliases in ALIASES.items() if any(has(t, a) for a in aliases)]

def prepare(article):
    """Prepare a fresh record without adding columns or changing human decisions."""
    item = dict(article)
    title, summary = item.get('title',''), item.get('summary','')
    item['category'] = classify(title, summary, item.get('category', 'Autres'))
    names = organisations(title, summary)
    if len(names) == 1:
        item['orchestra'] = names[0]
    elif len(names) > 1:
        # Existing schema cannot store multiple organisations; don't invent one.
        item['orchestra'] = SECTOR
    else:
        item['orchestra'] = SECTOR
    item['is_auto'] = True
    item['review_status'] = 'unreviewed'
    item.pop('reviewed_by', None)
    item.pop('reviewed_at', None)
    return item

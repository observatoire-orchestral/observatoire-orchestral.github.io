"""Conservative editorial relevance gate for French professional orchestral monitoring.

Never interpret a city, generic 'chef d'orchestre', or a source's reputation
as sufficient proof of relevance. Uncertain items are kept for human review
only when a real classical-music institutional context is present.
"""
from dataclasses import dataclass
from classification import fold, has, organisations, is_review_source

FRENCH_ORCHESTRA = ('orchestre national', 'orchestre philharmonique', 'orchestre de chambre',
                    'orchestre symphonique', 'orchestre de paris', 'orchestre des',
                    'opera de', 'opera national', 'operas de', 'radio france',
                    'concert de la loge', 'les siecles', 'orchestre pasdeloup',
                    'ensemble intercontemporain', 'orchestre regional', 'orchestre permanent',
                    'orchestre professionnel', 'musiciens permanents')
INSTITUTION = ('orchestre', 'opera', 'musiciens', 'musiciennes', 'chef d orchestre',
               'cheffe d orchestre', 'directeur musical', 'direction musicale',
               'conservatoire', 'symphonique', 'philharmonique', 'ch ur')
FRANCE_CONTEXT = ('france', 'francais', 'francaise', 'paris', 'nantes', 'angers', 'strasbourg',
                  'bretagne', 'lille', 'lyon', 'rouen', 'toulouse', 'cannes', 'bordeaux',
                  'marseille', 'montpellier', 'avignon', 'nice', 'mulhouse', 'metz',
                  'lorraine', 'saint etienne', 'ile de france', 'radio france')
EXCLUDE = ('listing and tickets', 'tickets and listings', 'acheter vos billets',
           'billets disponibles', 'ouverture de la billetterie', 'reservation de billets',
           'programme tv', 'resume de l episode', 'archives des', 'etiquette',
           'tag archives', 'parcours de visite', 'calendrier des concerts',
           'programme complet', 'cinema et musique classique')
METAPHOR = ('orchestre du titanic', 'chef d orchestre des championnats',
            'chef d orchestre du football', 'chef d orchestre du gouvernement',
            'chef d orchestre des maires', 'jumping de bordeaux')
FOREIGN = ('rotterdam philharmonic', 'carnegie hall', 'new york', 'bayreuth',
           'geneve', 'gen ve', 'madrid', 'teatro real', 'fenice', 'venise',
           'berlin philharmonic', 'london symphony')
SECTOR = ('greve', 'mobilisation', 'syndicat', 'budget', 'subvention', 'financement',
          'licenciement', 'recrutement', 'direction', 'gouvernance', 'suppression de postes',
          'conditions de travail', 'nomination', 'demission', 'renouvellement',
          'renouvele', 'prolonge', 'quitte', 'fait ses adieux', 'conflit social')

@dataclass(frozen=True)
class Decision:
    accept: bool
    reason: str
    confidence: float


def assess(title, summary='', source='', url='', orchestra=''):
    heading, body = fold(title), fold(summary)
    text = heading + ' ' + body
    if not heading:
        return Decision(False, 'empty_title', 1.0)
    if any(has(heading, word) for word in EXCLUDE):
        return Decision(False, 'listing_or_index', 0.99)
    if any(has(heading, word) for word in METAPHOR):
        return Decision(False, 'metaphorical_or_unrelated', 0.99)
    if ('football' in heading or 'fecafoot' in heading or 'rugby' in heading) and not organisations(text):
        return Decision(False, 'sport_not_orchestral', 0.99)
    names = organisations(text)
    explicit = bool(names) or any(has(heading, w) for w in FRENCH_ORCHESTRA)
    institutional = any(has(heading, w) for w in INSTITUTION)
    sector = any(has(heading, w) for w in SECTOR)
    french = any(has(text, w) for w in FRANCE_CONTEXT)
    foreign = any(has(heading, w) for w in FOREIGN)
    if foreign and not explicit and not french:
        return Decision(False, 'foreign_without_french_connection', 0.95)
    if explicit:
        return Decision(True, 'named_orchestral_institution', 0.95)
    if institutional and sector and french:
        return Decision(True, 'french_sector_news', 0.85)
    if institutional and french and ('orchestre' in heading or 'opera' in heading):
        return Decision(True, 'french_orchestral_context', 0.75)
    # Reviews without an orchestra connection are not in scope, even when from a review site.
    if is_review_source(source, url) and not explicit:
        return Decision(False, 'review_without_french_orchestra', 0.9)
    return Decision(False, 'insufficient_orchestral_evidence', 0.75)

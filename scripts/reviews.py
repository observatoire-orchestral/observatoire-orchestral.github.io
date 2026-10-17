"""Collect public Google News links to reviews of listed French orchestras.

Called by collect.py via run(store, google_news). Does not scrape publishers,
read paywalled content, or change the existing news collectors.
"""
import re
import time
import unicodedata

# Canonical labels match collect.py ORCHESTRAS keys.
ALIASES = {
    'ONPL': ('ONPL', 'Orchestre National des Pays de la Loire'),
    'Orchestre de Paris': ('Orchestre de Paris',),
    'Orchestre national de Lyon': ('Orchestre national de Lyon',),
    'Orchestre national de Lille': ('Orchestre national de Lille',),
    'Orchestre national de Bordeaux Aquitaine': (
        'Orchestre national Bordeaux Aquitaine', 'Orchestre national de Bordeaux Aquitaine', 'ONBA',
    ),
    'Orchestre national du Capitole de Toulouse': (
        'Orchestre national du Capitole', 'Orchestre du Capitole de Toulouse',
    ),
    'Orchestre philharmonique de Strasbourg': ('Orchestre philharmonique de Strasbourg',),
    'Orchestre national de Metz': ('Orchestre national de Metz', 'Orchestre national de Metz Grand Est'),
    'Orchestre national de Bretagne': ('Orchestre national de Bretagne',),
    'Orchestre national de Montpellier': (
        'Orchestre national Montpellier', 'Orchestre national de Montpellier',
    ),
    'Orchestre de l’Opéra de Nice': ('Orchestre de l’Opéra de Nice', 'Orchestre de l\'Opéra de Nice'),
    'Orchestre national d’Île-de-France': (
        'Orchestre national d’Île-de-France', 'Orchestre national d\'Ile-de-France', 'ONDIF',
    ),
    'Orchestre de l’Opéra de Marseille': (
        'Orchestre de l’Opéra de Marseille', 'Orchestre de l\'Opéra de Marseille',
    ),
    'Orchestre national Avignon-Provence': (
        'Orchestre national Avignon-Provence', 'Orchestre national d’Avignon-Provence',
    ),
    'Orchestre national de Cannes': ('Orchestre national de Cannes',),
}

REVIEW_SOURCES = ('bachtrack', 'resmusica', 'forumopera', 'forum opera', 'concertclassic')
REVIEW_TERMS = (
    'critique', 'compte rendu', 'chronique', 'recension', 'review',
    'on a assiste', 'nous avons assiste', 'a l ecoute',
)
PERFORMANCE_TERMS = (
    'concert', 'symphonie', 'concerto', 'interpretation', 'direction musicale',
    'opera', 'representation', 'production', 'spectacle', 'festival',
)


def fold(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in value if not unicodedata.combining(c))).strip()


def contains_phrase(text, phrase):
    return re.search(r'(?<!\w)' + re.escape(fold(phrase)) + r'(?!\w)', text) is not None


def matches_orchestra(article, names):
    text = fold(article.get('title', '') + ' ' + article.get('summary', ''))
    return any(contains_phrase(text, name) for name in names)


def is_review(article):
    text = fold(article.get('title', '') + ' ' + article.get('summary', ''))
    source = fold(article.get('source', ''))
    # Explicit review terminology, or specialist publisher plus performance context.
    return (any(contains_phrase(text, term) for term in REVIEW_TERMS)
            or (any(contains_phrase(source, name) for name in REVIEW_SOURCES)
                and any(contains_phrase(text, term) for term in PERFORMANCE_TERMS)))


def run(store, google_news):
    """Return number of candidate articles submitted; duplicates are ignored by store()."""
    count = 0
    for orchestra, names in ALIASES.items():
        # Search the canonical name plus one short alias where useful.
        search_names = [names[0]]
        if len(names) > 1 and len(names[0]) <= 5:
            search_names.append(names[1])
        name_query = '(' + ' OR '.join('"' + n + '"' for n in search_names) + ')'
        queries = (
            name_query + ' ("critique" OR "compte rendu" OR "review") concert',
            name_query + ' ("critique" OR "compte rendu" OR "review") (opéra OR opera)',
        )
        seen = set()
        for query in queries:
            try:
                for article in google_news(query, orchestra):
                    if article['url'] in seen:
                        continue
                    seen.add(article['url'])
                    if not matches_orchestra(article, names) or not is_review(article):
                        continue
                    article['orchestra'] = orchestra
                    article['category'] = 'Critique musicale'
                    store(article)
                    count += 1
            except Exception as exc:
                print(f'REVIEW WARNING {orchestra}: {exc}')
            time.sleep(0.3)
    print(f'Review discovery: {count} candidates submitted (duplicates ignored)')
    return count

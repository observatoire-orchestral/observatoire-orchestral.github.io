"""Review discovery for French professional orchestras (concerts and opera).

Uses the existing Google News RSS reader from collect.py. No direct scraping,
paid API, or paywall access. Call run(store, google_news) from collect.py.
"""
import re
import time
import unicodedata

# Canonical labels MUST match the orchestra values in collect.py.
# Short ambiguous abbreviations (ONL, ONB, etc.) are deliberately omitted.
ALIASES = {
    'ONPL': ('Orchestre National des Pays de la Loire', 'ONPL'),
    'Orchestre de Paris': ('Orchestre de Paris',),
    'Orchestre national de Lyon': ('Orchestre national de Lyon',),
    'Orchestre national de Lille': ('Orchestre national de Lille',),
    'Orchestre national de Bordeaux Aquitaine': (
        'Orchestre national Bordeaux Aquitaine',
        'Orchestre national de Bordeaux Aquitaine', 'ONBA',
    ),
    'Orchestre national du Capitole de Toulouse': (
        'Orchestre national du Capitole de Toulouse',
        'Orchestre national du Capitole', 'Orchestre du Capitole de Toulouse',
    ),
    'Orchestre philharmonique de Strasbourg': ('Orchestre philharmonique de Strasbourg',),
    'Orchestre national de Metz': (
        'Orchestre national de Metz', 'Orchestre national de Metz Grand Est',
    ),
    'Orchestre national de Bretagne': ('Orchestre national de Bretagne',),
    'Orchestre national de Montpellier': (
        'Orchestre national Montpellier', 'Orchestre national de Montpellier',
        'Orchestre national Montpellier Occitanie',
    ),
    'Orchestre de l’Opéra de Nice': (
        "Orchestre de l'Opéra de Nice", 'Orchestre Philharmonique de Nice',
    ),
    'Orchestre national d’Île-de-France': (
        "Orchestre national d'Île-de-France", 'ONDIF',
    ),
    'Orchestre de l’Opéra de Marseille': (
        "Orchestre de l'Opéra de Marseille", 'Orchestre Philharmonique de Marseille',
    ),
    'Orchestre national Avignon-Provence': (
        'Orchestre national Avignon-Provence', "Orchestre national d'Avignon-Provence",
    ),
    'Orchestre national de Cannes': ('Orchestre national de Cannes',),
}

# Sources to prioritise in searches. We do not assume every article from these
# publishers is a review: a review signal is still required.
REVIEW_DOMAINS = (
    'classiquenews.com', 'classykeo.com', 'resmusica.com',
    'bachtrack.com', 'forumopera.com', 'concertclassic.com',
)
REVIEW_TERMS = (
    'critique', 'compte rendu', 'chronique', 'recension', 'review',
    'nous avons assiste', 'on a assiste', 'concert review',
)
PERFORMANCE_TERMS = (
    'concert', 'symphonie', 'concerto', 'opera', 'representation',
    'recital', 'spectacle', 'festival', 'interpretation', 'production',
)
NON_REVIEW_TERMS = (
    'annonce', 'billetterie', 'appel a candidature', 'recrutement',
    'offre d emploi', 'programme de saison',
)


def fold(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(
        c for c in value if not unicodedata.combining(c)
    )).strip()


def contains_phrase(text, phrase):
    target = fold(phrase)
    return bool(target and re.search(r'(?<!\w)' + re.escape(target) + r'(?!\w)', text))


def matches_orchestra(article, names):
    text = fold((article.get('title') or '') + ' ' + (article.get('summary') or ''))
    return any(contains_phrase(text, name) for name in names)


def is_review(article):
    text = fold((article.get('title') or '') + ' ' + (article.get('summary') or ''))
    if any(contains_phrase(text, word) for word in NON_REVIEW_TERMS):
        return False
    # Explicit review language is strongest. A specialist source alone is not
    # enough: news, interviews and announcements are also published there.
    return (any(contains_phrase(text, term) for term in REVIEW_TERMS)
            and any(contains_phrase(text, term) for term in PERFORMANCE_TERMS))


def search_queries(names):
    # Prefer the full name, then an abbreviation if it is distinctive.
    main = names[0]
    aliases = [main]
    aliases.extend(name for name in names[1:] if len(name) <= 5)
    expression = '(' + ' OR '.join('"' + name + '"' for name in aliases) + ')'
    yield expression + ' ("critique" OR "compte rendu" OR "review") concert'
    yield expression + ' ("critique" OR "compte rendu" OR "review") (opéra OR opera)'
    # Prioritise the two publishers already yielding real reviews in this project.
    for domain in REVIEW_DOMAINS[:2]:
        yield 'site:' + domain + ' "' + main + '" (critique OR concert OR opéra)'


def run(store, google_news):
    """Submit new review candidates; existing URLs remain untouched by store()."""
    count, seen = 0, set()
    for orchestra, names in ALIASES.items():
        orchestra_count = 0
        for query in search_queries(names):
            try:
                for article in google_news(query, orchestra):
                    url = article.get('url')
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    if not matches_orchestra(article, names) or not is_review(article):
                        continue
                    article['orchestra'] = orchestra
                    article['category'] = 'Critique musicale'
                    store(article)
                    count += 1
                    orchestra_count += 1
            except Exception as exc:
                print(f'REVIEW WARNING {orchestra}: {exc}')
            time.sleep(0.3)
        print(f'REVIEW {orchestra}: {orchestra_count} candidates submitted')
    print(f'Review discovery: {count} candidates submitted (duplicates ignored by store)')
    return count

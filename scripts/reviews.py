"""Discover public concert and opera reviews of French professional orchestras.

Uses collect.py's existing google_news(query, orchestra) and store(article).
No direct publisher scraping, paywall access, or paid API.
"""
import re
import time
import unicodedata

# Canonical names must match collect.py / the website's orchestra filter.
ALIASES = {
    'ONPL': ('Orchestre National des Pays de la Loire', 'ONPL', 'Orchestre des Pays de la Loire'),
    'Orchestre de Paris': ('Orchestre de Paris',),
    'Orchestre national de Lyon': ('Orchestre national de Lyon',),
    'Orchestre national de Lille': ('Orchestre national de Lille',),
    'Orchestre national de Bordeaux Aquitaine': ('Orchestre national Bordeaux Aquitaine', 'Orchestre national de Bordeaux Aquitaine', 'ONBA'),
    'Orchestre national du Capitole de Toulouse': ('Orchestre national du Capitole de Toulouse', 'Orchestre national du Capitole', 'Orchestre du Capitole de Toulouse'),
    'Orchestre philharmonique de Strasbourg': ('Orchestre philharmonique de Strasbourg',),
    'Orchestre national de Metz': ('Orchestre national de Metz', 'Orchestre national de Metz Grand Est'),
    'Orchestre national de Bretagne': ('Orchestre national de Bretagne',),
    'Orchestre national de Montpellier': ('Orchestre national Montpellier', 'Orchestre national de Montpellier', 'Orchestre national Montpellier Occitanie'),
    'Orchestre de l’Opéra de Nice': ("Orchestre de l'Opéra de Nice", 'Orchestre Philharmonique de Nice'),
    'Orchestre national d’Île-de-France': ("Orchestre national d'Île-de-France", 'ONDIF'),
    'Orchestre de l’Opéra de Marseille': ("Orchestre de l'Opéra de Marseille", 'Orchestre Philharmonique de Marseille'),
    'Orchestre national Avignon-Provence': ('Orchestre national Avignon-Provence', "Orchestre national d'Avignon-Provence"),
    'Orchestre national de Cannes': ('Orchestre national de Cannes',),
}

REVIEW_DOMAINS = ('classiquenews.com', 'classykeo.com', 'resmusica.com',
                  'bachtrack.com', 'forumopera.com', 'concertclassic.com')
REVIEW_SIGNALS = ('critique', 'compte rendu', 'review', 'recension', 'chronique',
                  'nous avons assiste', 'on a assiste', 'a l affiche',
                  'concert review', 'opera review')
PERFORMANCE_SIGNALS = ('concert', 'symphonie', 'concerto', 'opera', 'representation',
                       'recital', 'festival', 'interpretation', 'production',
                       'direction', 'brahms', 'beethoven', 'mozart', 'mahler',
                       'debussy', 'ravel', 'verdi', 'wagner', 'puccini', 'massenet')
# Print a small sample of rejected ONPL results for troubleshooting.
# Set to 0 after diagnosis to disable these extra log lines.
DEBUG_ORCHESTRA = 'ONPL'
DEBUG_SAMPLE_LIMIT = 6

# Possible reviews require an explicitly named orchestra, a specialist publisher,
# and a performance clue. They remain unpublished until an admin reviews them.
POSSIBLE_REVIEW_SOURCES = ('classiquenews', 'classykeo', 'resmusica',
                           'bachtrack', 'forumopera', 'forum opera',
                           'concertclassic')

EXCLUDE = ('billetterie', 'appel a candidature', 'recrutement', 'offre d emploi',
           'programme de saison', 'annonce de saison', 'abonnement saison')


def fold(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def has_phrase(normalized_text, phrase):
    target = fold(phrase)
    return bool(target and re.search(r'(?<!\w)' + re.escape(target) + r'(?!\w)', normalized_text))


def article_text(article):
    return fold((article.get('title') or '') + ' ' + (article.get('summary') or ''))


def orchestra_matches(article, names):
    text = article_text(article)
    return any(has_phrase(text, alias) for alias in names)


def is_review(article):
    title = fold(article.get('title'))
    text = article_text(article)
    if any(has_phrase(title, word) for word in EXCLUDE):
        return False
    # A clear review marker in the title is sufficient: titles often omit
    # generic words such as 'concert' even for actual performance reviews.
    if any(has_phrase(title, word) for word in REVIEW_SIGNALS):
        return True
    # Otherwise require both review language and performance context.
    return (any(has_phrase(text, word) for word in REVIEW_SIGNALS)
            and any(has_phrase(text, word) for word in PERFORMANCE_SIGNALS))



def is_possible_review(article):
    """A specialist performance article needing human review, not publication."""
    title = fold(article.get('title'))
    text = article_text(article)
    source = fold(article.get('source'))
    if any(has_phrase(title, word) for word in EXCLUDE):
        return False
    if not any(has_phrase(source, name) for name in POSSIBLE_REVIEW_SOURCES):
        return False
    # Avoid treating orchestra season previews and calendar listings as reviews.
    if any(has_phrase(title, term) for term in (
        'saison 2026 2027', 'saison 2025 2026', 'saison 2027 2028',
        'agenda', 'calendrier', 'programme', 'a venir', 'prochain concert',
        'ven 25', 'sam 26', 'dim 27', 'reservation', 'dates des concerts',
    )):
        return False
    return any(has_phrase(text, word) for word in PERFORMANCE_SIGNALS)


def search_queries(names):
    # Limit network calls so the scheduled GitHub Action remains practical.
    # Broad discovery first, then targeted searches for specialist reviews.
    variants = list(dict.fromkeys(names))
    main = '"' + variants[0].replace('"', '') + '"'
    yield main + ' (critique OR review OR "compte rendu")'
    yield main + ' (concert OR opéra OR opera) critique'
    for alias in variants[1:3]:
        quoted = '"' + alias.replace('"', '') + '"'
        yield quoted + ' (critique OR review)'
    # Alternate specialist sites on successive searches; the broad searches
    # above are not publisher-restricted and can find any of the six sources.
    for domain in ('classiquenews.com', 'classykeo.com', 'resmusica.com'):
        yield 'site:' + domain + ' ' + main


def run(store, google_news):
    """Search, validate and submit candidates; store() handles duplicate URLs."""
    total_submitted = 0
    global_seen = set()
    for orchestra, names in ALIASES.items():
        stats = {'fetched': 0, 'duplicate': 0, 'no_name': 0,
                 'not_review': 0, 'submitted': 0, 'possible': 0, 'errors': 0}
        debug_samples = {'no_orchestra_match': [], 'not_review': []}
        for query in dict.fromkeys(search_queries(names)):
            try:
                for article in google_news(query, orchestra):
                    stats['fetched'] += 1
                    url = article.get('url')
                    if not url:
                        continue
                    # Don't mark an article as seen before checking whether it
                    # matches: another query might have better metadata.
                    if url in global_seen:
                        stats['duplicate'] += 1
                        continue
                    if not orchestra_matches(article, names):
                        stats['no_name'] += 1
                        if orchestra == DEBUG_ORCHESTRA and len(debug_samples['no_orchestra_match']) < DEBUG_SAMPLE_LIMIT:
                            debug_samples['no_orchestra_match'].append((query, article.get('title', ''), article.get('source', '')))
                        continue
                    confirmed = is_review(article)
                    possible = not confirmed and is_possible_review(article)
                    if not confirmed and not possible:
                        stats['not_review'] += 1
                        if orchestra == DEBUG_ORCHESTRA and len(debug_samples['not_review']) < DEBUG_SAMPLE_LIMIT:
                            debug_samples['not_review'].append((query, article.get('title', ''), article.get('source', '')))
                        continue
                    article['orchestra'] = orchestra
                    article['category'] = 'Critique musicale'
                    article['review_status'] = 'validated' if confirmed else 'unreviewed'
                    store(article)
                    global_seen.add(url)
                    if confirmed:
                        stats['submitted'] += 1
                    else:
                        stats['possible'] += 1
                    total_submitted += 1
            except Exception as exc:
                stats['errors'] += 1
                print(f'REVIEW WARNING {orchestra}: {query[:90]}: {exc}', flush=True)
            time.sleep(0.15)
        print(f'REVIEW {orchestra}: fetched={stats["fetched"]}, '
              f'duplicate_in_run={stats["duplicate"]}, '
              f'no_orchestra_match={stats["no_name"]}, '
              f'not_review={stats["not_review"]}, '
              f'confirmed={stats["submitted"]}, possible_unreviewed={stats["possible"]}, errors={stats["errors"]}', flush=True)
        if orchestra == DEBUG_ORCHESTRA:
            for reason, examples in debug_samples.items():
                for i, (query, title, source) in enumerate(examples, 1):
                    # Keep logs short and readable; only public article metadata.
                    safe_title = ' '.join(str(title).split())[:180]
                    safe_source = ' '.join(str(source).split())[:60]
                    print(f'REVIEW DEBUG {orchestra} {reason} #{i}: '
                          f'{safe_title!r} | source={safe_source!r} | query={query[:100]!r}',
                          flush=True)
    print(f'Review discovery: {total_submitted} candidates submitted '
          '(existing database URLs may be ignored by store)', flush=True)
    return total_submitted

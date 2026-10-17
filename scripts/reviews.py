"""Public concert/opera review discovery for Observatoire Orchestral.

Compatible with collect.py: run(store, google_news). Attempts to inspect public
publisher article HTML after safe redirects; does not bypass access controls,
paywalls, robots restrictions, or require additional Python dependencies.
"""
import html
import re
import time
import unicodedata
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

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

SOURCES = ('classiquenews', 'classykeo', 'resmusica', 'bachtrack',
           'forumopera', 'concertclassic')
REVIEW_TERMS = ('critique', 'compte rendu', 'recension', 'review',
                'concert review', 'opera review')
PERFORMANCE_TERMS = ('concert', 'opera', 'symphonie', 'concerto', 'representation',
                     'interpretation', 'production', 'direction', 'recital')
EXCLUDE = ('billetterie', 'appel a candidature', 'recrutement',
           'programme de saison', 'annonce de saison', 'abonnement saison')
UA = 'ObservatoireOrchestral/1.0 (public review monitoring)'
MAX_BYTES = 650_000
MAX_FETCHES_PER_ORCHESTRA = 12
DEBUG_ORCHESTRA = 'ONPL'
DEBUG_LIMIT = 5


def fold(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def has(text, phrase):
    target = fold(phrase)
    return bool(target and re.search(r'(?<!\w)' + re.escape(target) + r'(?!\w)', text))


def named(text, aliases):
    return any(has(text, alias) for alias in aliases)


def specialist(article):
    return any(word in fold(article.get('source')) for word in SOURCES)


def looks_review(title, summary, body):
    t = fold(title)
    combined = fold(title + ' ' + summary + ' ' + body[:12000])
    if any(has(t, word) for word in EXCLUDE):
        return False
    if any(has(t, word) for word in REVIEW_TERMS):
        return True
    # A review marker in the full body is useful only with performance context.
    return (any(has(combined, word) for word in REVIEW_TERMS)
            and any(has(combined, word) for word in PERFORMANCE_TERMS))


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.ignored = 0
        self.in_article = 0
        self.in_main = 0
        self.article_text = []
        self.main_text = []
        self.paragraphs = []
        self.in_p = 0
        self.meta = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript', 'nav', 'footer', 'header'):
            self.ignored += 1
        if tag == 'article':
            self.in_article += 1
        if tag == 'main':
            self.in_main += 1
        if tag == 'p':
            self.in_p += 1
        if tag == 'meta' and (attrs.get('property') or attrs.get('name') or '').lower() in ('og:description', 'description'):
            self.meta.append(attrs.get('content', ''))

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'nav', 'footer', 'header') and self.ignored:
            self.ignored -= 1
        if tag == 'article' and self.in_article:
            self.in_article -= 1
        if tag == 'main' and self.in_main:
            self.in_main -= 1
        if tag == 'p' and self.in_p:
            self.in_p -= 1

    def handle_data(self, data):
        if self.ignored:
            return
        if self.in_article:
            self.article_text.append(data)
        if self.in_main:
            self.main_text.append(data)
        if self.in_p:
            self.paragraphs.append(data)

    def text(self):
        parts = self.article_text or self.main_text or self.paragraphs
        return re.sub(r'\s+', ' ', html.unescape(' '.join(parts))).strip()[:18000]


def publisher_host(host):
    host = (host or '').lower().removeprefix('www.')
    return any(host == domain or host.endswith('.' + domain)
               for domain in ('classiquenews.com', 'classykeo.com',
                              'resmusica.com', 'bachtrack.com',
                              'forumopera.com', 'concertclassic.com'))


def robots_allowed(host, url, cache):
    if host not in cache:
        robot = RobotFileParser()
        robot.set_url('https://' + host + '/robots.txt')
        try:
            robot.read()
            cache[host] = robot
        except Exception:
            cache[host] = None
    robot = cache[host]
    return robot is not None and robot.can_fetch(UA, url)


def public_body(session, url, robots_cache):
    """Best-effort public HTML extraction; never fetch a publisher before robots check."""
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        return '', 'unsupported_url'
    if parsed.hostname == 'news.google.com':
        # Google RSS links often show a Google landing page rather than redirect.
        # Do not guess an article URL from unrelated links on that page.
        try:
            response = session.get(url, timeout=10, allow_redirects=False,
                                   headers={'User-Agent': UA})
            try:
                if response.status_code not in (301, 302, 303, 307, 308):
                    return '', 'google_link_not_resolved'
                from urllib.parse import urljoin
                url = urljoin(url, response.headers.get('location', ''))
                parsed = urlparse(url)
            finally:
                response.close()
        except requests.RequestException:
            return '', 'google_link_not_resolved'
    if parsed.scheme != 'https' or not parsed.hostname or not publisher_host(parsed.hostname):
        return '', 'other_publisher'
    if not robots_allowed(parsed.hostname, url, robots_cache):
        return '', 'robots_unavailable_or_disallowed'
    try:
        response = session.get(url, timeout=10, stream=True, allow_redirects=False,
                               headers={'User-Agent': UA, 'Accept': 'text/html'})
        try:
            if response.status_code != 200 or 'html' not in response.headers.get('content-type', '').lower():
                return '', 'not_accessible'
            chunks, total = [], 0
            for chunk in response.iter_content(32768):
                total += len(chunk)
                if total > MAX_BYTES:
                    return '', 'too_large'
                chunks.append(chunk)
            parser = ArticleParser()
            parser.feed(b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace'))
            body = parser.text()
            return (body, 'read') if len(body) >= 150 else ('', 'no_article_body')
        finally:
            response.close()
    except (requests.RequestException, ValueError, UnicodeError):
        return '', 'fetch_failed'


def search_queries(names):
    main = '"' + names[0] + '"'
    yield main + ' (critique OR review OR "compte rendu")'
    yield main + ' (concert OR opéra OR opera) critique'
    for alias in names[1:3]:
        yield '"' + alias + '" (critique OR review)'
    for domain in ('classiquenews.com', 'classykeo.com', 'resmusica.com'):
        yield 'site:' + domain + ' ' + main


def run(store, google_news):
    session = requests.Session()
    robots_cache = {}
    seen = set()
    total = 0
    for orchestra, aliases in ALIASES.items():
        stats = {'fetched': 0, 'body_read': 0, 'no_body': 0,
                 'no_orchestra_match': 0, 'not_review': 0,
                 'confirmed': 0, 'possible_unreviewed': 0, 'errors': 0}
        samples = []
        attempted = 0
        for query in dict.fromkeys(search_queries(aliases)):
            try:
                for article in google_news(query, orchestra):
                    stats['fetched'] += 1
                    url = article.get('url', '')
                    if not url or url in seen:
                        continue
                    title = article.get('title') or ''
                    summary = article.get('summary') or ''
                    snippet = fold(title + ' ' + summary)
                    # Fetch only promising results, and bound total HTTP traffic.
                    candidate = named(snippet, aliases) or specialist(article)
                    body, fetch_status = '', 'skipped'
                    if candidate and attempted < MAX_FETCHES_PER_ORCHESTRA:
                        attempted += 1
                        body, fetch_status = public_body(session, url, robots_cache)
                        stats['body_read' if body else 'no_body'] += 1
                    combined = fold(title + ' ' + summary + ' ' + body)
                    if not named(combined, aliases):
                        stats['no_orchestra_match'] += 1
                        if orchestra == DEBUG_ORCHESTRA and len(samples) < DEBUG_LIMIT:
                            samples.append(('no_match', title, fetch_status))
                        continue
                    confirmed = looks_review(title, summary, body)
                    possible = not confirmed and specialist(article) and (
                        any(has(combined, term) for term in PERFORMANCE_TERMS))
                    if not confirmed and not possible:
                        stats['not_review'] += 1
                        continue
                    article['orchestra'] = orchestra
                    article['category'] = 'Critique musicale'
                    article['review_status'] = 'validated' if confirmed else 'unreviewed'
                    # Keep original URL to preserve duplicate handling in Supabase.
                    store(article)
                    seen.add(url)
                    stats['confirmed' if confirmed else 'possible_unreviewed'] += 1
                    total += 1
            except Exception as exc:
                stats['errors'] += 1
                print(f'REVIEW WARNING {orchestra}: {str(exc)[:160]}', flush=True)
            time.sleep(0.15)
        print('REVIEW ' + orchestra + ': ' + ', '.join(
            f'{key}={value}' for key, value in stats.items()), flush=True)
        if orchestra == DEBUG_ORCHESTRA:
            for reason, title, status in samples:
                print(f'REVIEW DEBUG ONPL {reason}: {title[:125]!r} body={status}', flush=True)
    print(f'Review discovery: {total} candidates submitted (database duplicates may be ignored)', flush=True)
    return total

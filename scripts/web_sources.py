"""Public website discovery for Observatoire SUD ONPL.

Visits configured HTTPS landing pages and a limited number of same-site HTML
publication pages. No login, paywall bypass, recursive crawling or PDF downloads.
"""
import html
import json
import re
import time
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests

SECTOR = 'Secteur orchestral français'
MUSIC = ('orchestre', 'orchestral', 'symphonique', 'philharmonique', 'musicien',
         'spectacle vivant', 'musique', 'opera', 'operas', 'lyrique', 'instrumentiste')
SOCIAL = ('budget', 'financement', 'subvention', 'dotation', 'rapport', 'audit',
          'emploi', 'recrutement', 'concours', 'poste', 'effectif', 'licenciement',
          'syndicat', 'syndical', 'greve', 'mobilisation', 'preavis', 'conditions de travail',
          'remuneration', 'salaire', 'convention collective', 'deliberation',
          'politique culturelle', 'finances', 'reorganisation', 'restructuration',
          'suppression', 'direction', 'appel a candidature', 'communique', 'bilan',
          'aide publique', 'economie', 'deficit', 'fermeture', 'tutelle', 'fusion',
          'negociation', 'mouvement social')
TOPICS = [
 ('Budget et subventions', ('budget','subvention','financement','dotation','finances','deficit')),
 ('Emploi et recrutement', ('recrutement','emploi','concours','effectif','licenciement','poste')),
 ('Mobilisation et grève', ('syndical','syndicat','greve','mobilisation','preavis')),
 ('Conditions de travail', ('salaire','remuneration','conditions de travail','convention collective')),
 ('Gouvernance', ('direction','reorganisation','restructuration','deliberation','audit')),
]
HEADERS = {'User-Agent': 'Observatoire-SUD-ONPL/4.0 (public-source-monitoring)',
           'Accept': 'text/html,application/xhtml+xml'}
MAX_BYTES = 2_000_000


def tidy(value):
    return re.sub(r'\s+', ' ', html.unescape(str(value or ''))).strip()[:1200]


def norm(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    return ''.join(ch for ch in value if not unicodedata.combining(ch))


def contains(text, words):
    return any(word in text for word in words)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.href = None
        self.anchor_text = []
        self.body_text = []
        self.ignored = 0
        self.title_text = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ('script', 'style', 'noscript'):
            self.ignored += 1
        if tag == 'title':
            self.in_title = True
        if tag == 'a':
            self.href = dict(attrs).get('href')
            self.anchor_text = []

    def handle_data(self, data):
        if self.ignored:
            return
        if self.in_title:
            self.title_text.append(data)
        if self.href is not None:
            self.anchor_text.append(data)
        self.body_text.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ('script', 'style', 'noscript') and self.ignored:
            self.ignored -= 1
        if tag == 'title':
            self.in_title = False
        if tag == 'a' and self.href is not None:
            self.links.append((self.href, tidy(' '.join(self.anchor_text))))
            self.href = None
            self.anchor_text = []


def identify_orchestra(text, default):
    text = norm(text)

    if (
        re.search(r'\bonpl\b', text)
        or 'orchestre national des pays de la loire' in text
        or 'orchestre national des pays-de-la-loire' in text
    ):
        return 'ONPL'

    return default

def topic(text):
    text = norm(text)
    for label, words in TOPICS:
        if contains(text, words):
            return label
    return 'Autres'


def get_page(session, url):
    # requests follows redirects: validate final location and content type too.
    response = session.get(url, timeout=20, headers=HEADERS, stream=True)
    try:
        response.raise_for_status()
        if urlparse(response.url).scheme != 'https':
            raise ValueError('Redirected to a non-HTTPS page')
        if 'html' not in response.headers.get('Content-Type', '').lower():
            raise ValueError('Not an HTML page')
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError('HTML page exceeds size limit')
            chunks.append(chunk)
        encoding = response.encoding or 'utf-8'
        parser = PageParser()
        parser.feed(b''.join(chunks).decode(encoding, errors='replace'))
        return response.url, parser
    finally:
        response.close()


def is_candidate(title, url):
    if len(title) < 12 or len(title) > 400:
        return False
    path = urlparse(url).path.lower()
    if path.endswith(('.jpg','.jpeg','.png','.gif','.svg','.zip','.doc','.docx','.mp3','.mp4')):
        return False
    if any(x in path for x in ('/contact', '/mentions-legales', '/confidentialite', '/cookies', '/billetterie')):
        return False
    return True


def relevant(title, url, source, page_text=''):
    snippet = norm(title + ' ' + urlparse(url).path.replace('-', ' ').replace('_', ' '))
    context = norm(page_text[:12000])
    named = source.get('orchestra') and source['orchestra'] != SECTOR
    # A specific orchestra site is already strongly contextualised.
    if named:
        return contains(snippet + ' ' + context, SOCIAL) or contains(snippet, MUSIC)
    # On general sites, the article's own text must connect music and the issue.
    combined = snippet + ' ' + context
    return contains(combined, MUSIC) and contains(combined, SOCIAL)


def discover(session, source):
    url = source['url']
    if urlparse(url).scheme != 'https':
        raise ValueError('Source URL must use HTTPS')
    landing_url, landing = get_page(session, url)
    home_host = urlparse(landing_url).netloc.lower()
    max_items = max(1, min(int(source.get('max_items', 20)), 50))
    # Page inspection is intentionally capped to limit traffic and Actions time.
    inspect_limit = max(10, min(int(source.get('inspect_limit', 25)), 40))
    candidates, seen = [], set()
    for href, title in landing.links:
        full = urldefrag(urljoin(landing_url, href))[0]
        parsed = urlparse(full)
        if parsed.scheme != 'https' or not parsed.netloc or full in seen:
            continue
        seen.add(full)
        if parsed.netloc.lower() != home_host and not source.get('allow_external', False):
            continue
        if not is_candidate(title, full):
            continue
        candidates.append((full, title))
    # Check promising links first, rather than the site's menu order.
    def priority(item):
        full, title = item
        value = norm(title + ' ' + urlparse(full).path)
        return (int(contains(value, MUSIC)) + int(contains(value, SOCIAL)),
                int(urlparse(full).path.lower().endswith('.pdf')))
    candidates.sort(key=priority, reverse=True)
    count = 0
    for full, title in candidates[:inspect_limit]:
        if count >= max_items:
            break
        pdf = urlparse(full).path.lower().endswith('.pdf')
        context = ''
        page_title = title
        if not pdf and urlparse(full).netloc.lower() == home_host:
            try:
                _, page = get_page(session, full)
                context = tidy(' '.join(page.body_text))
                extracted = tidy(' '.join(page.title_text))
                if extracted and len(extracted) >= 12:
                    page_title = extracted[:400]
            except (requests.RequestException, ValueError, UnicodeError):
                pass
        if not relevant(page_title, full, source, context):
            continue
        summary = context[:500] if context else (
            'Document PDF public repéré sur ' if pdf else 'Publication repérée sur '
        ) + source['source']
        yield {
            'url': full[:2000],
            'title': page_title[:400],
            'summary': summary,
            'source': source['source'][:200],
            'orchestra': identify_orchestra(
    page_title + ' ' + context[:1200],
    source.get('orchestra') or SECTOR
),

            'category': topic(page_title + ' ' + context[:1000]),
            'published_at': None,
            'is_auto': True,
            'review_status': 'unreviewed',
        }
        count += 1


def read_sources(path=None):
    path = Path(path or Path(__file__).with_name('web_sources.json'))
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('web_sources.json must contain a list')
    return [item for item in data if isinstance(item, dict) and item.get('enabled', False)]


def run(store, session=None):
    session = session or requests.Session()
    session.headers.update(HEADERS)
    count, errors = 0, []
    for source in read_sources():
        try:
            n = 0
            for article in discover(session, source):
                store(article)
                count += 1
                n += 1
            print('WEB', source['source'], n, 'publications proposées')
        except (requests.RequestException, ValueError, KeyError, UnicodeError) as exc:
            errors.append(f"{source.get('source', 'unknown')}: {exc}")
            print('WEB WARNING', errors[-1])
        time.sleep(0.3)
    print(f'Web discovery: {count} entries proposed, {len(errors)} source warnings')
    return count

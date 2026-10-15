"""Public HTML page and PDF-link discovery for Observatoire SUD ONPL.

Only visits explicitly configured HTTPS pages. Does not follow links recursively,
access private content, or download PDFs. Runs alongside the V2 RSS collector.
"""
import html
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests

SECTOR = 'Secteur orchestral français'
ORCHESTRA_WORDS = [
    'orchestre', 'orchestral', 'symphonique', 'philharmonique', 'musicien',
    'spectacle vivant', 'culture', 'artistique', 'musique', 'opéra', 'opera',
]
SOCIAL_WORDS = [
    'budget', 'financement', 'subvention', 'dotation', 'rapport', 'audit',
    'emploi', 'recrutement', 'concours', 'poste', 'effectif', 'licenciement',
    'syndicat', 'syndical', 'grève', 'greve', 'mobilisation', 'préavis',
    'conditions de travail', 'rémunération', 'salaire', 'convention collective',
    'délibération', 'deliberation', 'politique culturelle', 'finances',
    'réorganisation', 'restructuration', 'suppression', 'direction',
    'appel à candidature', 'communiqué', 'communique', 'bilan', 'aide publique',
]
TOPICS = [
    ('Budget et subventions', ['budget', 'subvention', 'financement', 'dotation', 'finances']),
    ('Emploi et recrutement', ['recrutement', 'emploi', 'concours', 'effectif', 'licenciement', 'poste']),
    ('Mobilisation et grève', ['syndical', 'syndicat', 'grève', 'greve', 'mobilisation', 'préavis']),
    ('Conditions de travail', ['salaire', 'rémunération', 'conditions de travail', 'convention collective']),
    ('Gouvernance', ['direction', 'réorganisation', 'restructuration', 'délibération', 'audit']),
]


def tidy(s):
    return re.sub(r'\s+', ' ', html.unescape(str(s or ''))).strip()[:1200]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            attrs = dict(attrs)
            self.current = attrs.get('href')
            self.text = []

    def handle_data(self, data):
        if self.current is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == 'a' and self.current is not None:
            self.links.append((self.current, tidy(' '.join(self.text))))
            self.current = None
            self.text = []


def topic(s):
    lower = s.casefold()
    for label, words in TOPICS:
        if any(w in lower for w in words):
            return label
    return 'Autres'


def relevant(title, url, source):
    value = (title + ' ' + urlparse(url).path.replace('-', ' ').replace('_', ' ')).casefold()
    # For orchestra-specific sources, relevant social/cultural publications qualify.
    # For sector-wide sources, require both a musical/cultural term and a social term.
    social = any(word in value for word in SOCIAL_WORDS)
    musical = any(word in value for word in ORCHESTRA_WORDS)
    if source.get('orchestra') and source['orchestra'] != SECTOR:
        return social or musical
    return social and musical


def discover(session, source):
    url = source['url']
    if urlparse(url).scheme != 'https':
        raise ValueError('Source URL must use HTTPS')
    response = session.get(url, timeout=20, headers={'Accept': 'text/html,application/xhtml+xml'})
    response.raise_for_status()
    content_type = response.headers.get('Content-Type', '').lower()
    if 'html' not in content_type:
        raise ValueError('Not an HTML page')
    if len(response.content) > 3_000_000:
        raise ValueError('HTML page exceeds size limit')
    parser = LinkParser()
    parser.feed(response.text)
    accepted = 0
    seen = set()
    for href, title in parser.links:
        if accepted >= int(source.get('max_items', 20)):
            break
        full = urldefrag(urljoin(response.url, href))[0]
        parsed = urlparse(full)
        if parsed.scheme != 'https' or not parsed.netloc or full in seen:
            continue
        seen.add(full)
        if parsed.netloc.lower() != urlparse(response.url).netloc.lower() and not source.get('allow_external', False):
            continue
        if not title or len(title) < 12 or not relevant(title, full, source):
            continue
        is_pdf = parsed.path.lower().endswith('.pdf')
        article = {
            'url': full[:2000],
            'title': tidy(title)[:400],
            'summary': ('Document PDF public découvert sur ' if is_pdf else 'Publication repérée sur ') + source['source'],
            'source': source['source'][:200],
            'orchestra': source.get('orchestra') or SECTOR,
            'category': topic(title + ' ' + full),
            # No date inferred from a page's current date; use database found_at.
            'published_at': None,
            'is_auto': True,
            'review_status': 'unreviewed',
        }
        accepted += 1
        yield article


def read_sources(path=None):
    path = Path(path or Path(__file__).with_name('web_sources.json'))
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('web_sources.json must contain a list')
    return [x for x in data if isinstance(x, dict) and x.get('enabled', False)]


def run(store, session=None):
    session = session or requests.Session()
    session.headers.update({'User-Agent': 'Observatoire-SUD-ONPL/3.0 (+public-web-monitoring)'})
    count, errors = 0, []
    for source in read_sources():
        try:
            for article in discover(session, source):
                store(article)
                count += 1
            print('WEB', source['source'], 'processed')
        except (requests.RequestException, ValueError, KeyError, UnicodeError) as exc:
            # A single blocked/changed source must not stop the collector.
            errors.append(f"{source.get('source', 'unknown')}: {exc}")
            print('WEB WARNING', errors[-1])
        time.sleep(0.3)
    print(f'Web discovery: {count} entries proposed, {len(errors)} source warnings')
    return count

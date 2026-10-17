"""Bounded public-document discovery from XML sitemaps; no paid API.

Only public HTTPS URLs from configured, same-host sitemaps are considered.
Does not bypass paywalls, search Google, or promise complete coverage.
"""
import gzip
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urljoin
import json
import requests

SECTOR = 'Secteur orchestral français'
MUSIC = ('orchestre', 'opera', 'musicien', 'symphoni', 'philharmoni', 'spectacle vivant', 'musique')
ISSUES = ('subvention', 'budget', 'financ', 'deficit', 'emploi', 'recrut', 'poste', 'effectif', 'greve', 'syndic', 'remuner', 'salaire', 'audit', 'rapport', 'deliberation', 'convention', 'suppression', 'restructur', 'dotation', 'economie', 'compte administratif')
TOPICS = [
 ('Budget et subventions', ('subvention', 'budget', 'financ', 'deficit', 'dotation', 'economie')),
 ('Emploi et recrutement', ('emploi', 'recrut', 'poste', 'effectif', 'suppression')),
 ('Mobilisation et grève', ('greve', 'syndic', 'mobilis', 'preavis')),
 ('Conditions de travail', ('remuner', 'salaire', 'convention collective', 'conditions de travail')),
 ('Gouvernance', ('direction', 'audit', 'deliberation', 'restructur', 'rapport')),
]

def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c))

def identify_orchestra(text, default):
    text = fold(text)

    if (
        re.search(r'\bonpl\b', text)
        or 'orchestre national des pays de la loire' in text
        or 'orchestre national des pays-de-la-loire' in text
    ):
        return 'ONPL'

    return default

def label(text):
    t = fold(text)
    for category, keys in TOPICS:
        if any(k in t for k in keys):
            return category
    return 'Autres'

def allowed(url, host):
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname == host and not p.username and not p.password

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ''
        self.in_title = False
        self.description = ''
        self.date = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title': self.in_title = True
        if tag == 'meta':
            key = (a.get('property') or a.get('name') or '').lower()
            if key in ('description', 'og:description') and not self.description:
                self.description = a.get('content', '')
            if key in ('article:published_time', 'datepublished', 'date'):
                self.date = a.get('content') or self.date
    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
    def handle_data(self, data):
        if self.in_title: self.title += data

def get_bytes(session, url, max_bytes=2_000_000):
    with session.get(url, timeout=18, stream=True, allow_redirects=False) as r:
        r.raise_for_status()
        chunks = []
        size = 0
        for chunk in r.iter_content(65536):
            size += len(chunk)
            if size > max_bytes: raise ValueError('response too large')
            chunks.append(chunk)
        return b''.join(chunks), r.headers.get('content-type', '')

def sitemap_urls(session, url, host, remaining, visited):
    if not allowed(url, host) or url in visited or len(visited) >= 35: return
    visited.add(url)
    try:
        raw, _ = get_bytes(session, url)
        if url.endswith('.gz'): raw = gzip.decompress(raw)
        root = ET.fromstring(raw)
    except (requests.RequestException, ValueError, ET.ParseError, OSError) as e:
        print('SITEMAP WARNING', url, str(e)[:100]); return
    tag = root.tag.rsplit('}', 1)[-1]
    if tag == 'sitemapindex':
        for loc in root.findall('.//{*}sitemap/{*}loc'):
            if remaining[0] <= 0: break
            yield from sitemap_urls(session, (loc.text or '').strip(), host, remaining, visited)
    elif tag == 'urlset':
        for item in root.findall('.//{*}url'):
            if remaining[0] <= 0: break
            loc = item.find('{*}loc')
            if loc is None or not loc.text: continue
            link = loc.text.strip()
            if not allowed(link, host): continue
            remaining[0] -= 1
            yield link

def discover(store, session=None, path=None):
    config = Path(path or Path(__file__).with_name('document_sources.json'))
    sources = json.loads(config.read_text(encoding='utf-8')) if config.exists() else []
    session = session or requests.Session()
    session.headers.update({'User-Agent': 'Observatoire-SUD-ONPL/5.0 (public sitemap monitoring)'})
    found = 0
    for source in sources:
        if not source.get('enabled', False): continue
        sitemap = source['sitemap']
        host = urlparse(sitemap).hostname
        if not host or not allowed(sitemap, host): continue
        limit = min(int(source.get('max_urls', 200)), 1000)
        checked = 0
        for link in sitemap_urls(session, sitemap, host, [limit], set()):
            # Fast URL-level prefilter, then bounded HTML metadata check.
            hint = fold(link.replace('-', ' ').replace('_', ' '))
            if not (any(k in hint for k in MUSIC) or any(k in hint for k in ISSUES)):
                continue
            if checked >= min(int(source.get('max_pages', 25)), 60): break
            checked += 1
            if link.lower().split('?')[0].endswith('.pdf'):
                title = link.rsplit('/', 1)[-1].replace('-', ' ').replace('_', ' ')
                summary = 'Document PDF public (contenu non extrait)'
                date = None
            else:
                try:
                    raw, content_type = get_bytes(session, link, 700_000)
                    if 'html' not in content_type.lower(): continue
                    parser = MetaParser()
                    parser.feed(raw.decode('utf-8', errors='replace'))
                    title = parser.title.strip()[:400]
                    summary = parser.description.strip()[:1000]
                    date = parser.date
                except (requests.RequestException, ValueError, UnicodeError) as e:
                    print('PAGE WARNING', link, str(e)[:90]); continue
            combined = fold(title + ' ' + summary + ' ' + link)
            # Sector-wide documents must be about music AND a policy/employment issue.
            # For orchestra-specific sources the configured source establishes context.
            issue = any(k in combined for k in ISSUES)
            music = any(k in combined for k in MUSIC)
            if not issue or (source.get('orchestra', SECTOR) == SECTOR and not music): continue
            published = None
            if date:
                try:
                    parsed = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    if parsed.tzinfo: published = parsed.isoformat()
                except ValueError: pass
            article = {'url': link[:2000], 'title': title or link.rsplit('/',1)[-1],
                       'summary': summary or 'Publication documentaire publique',
                       'source': source['source'][:200],
                       'orchestra': identify_orchestra(
    title + ' ' + summary,
    source.get('orchestra') or SECTOR
),

                       'category': label(combined), 'published_at': published,
                       'is_auto': True, 'review_status': 'unreviewed'}
            store(article)
            found += 1
            time.sleep(0.2)
        print('DOCUMENTARY', source['source'], 'pages examined', checked)
    print('Documentary discovery proposed:', found)
    return found

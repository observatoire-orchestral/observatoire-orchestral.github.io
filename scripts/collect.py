"""Observatoire SUD ONPL — public web/RSS monitoring, no paid API.

Collects Google News RSS searches (orchestra and sector), plus optional direct RSS/Atom
feeds configured in sources.json. It does not crawl the whole web or bypass paywalls.
"""
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlparse

import feedparser
import requests

URL = os.environ['SUPABASE_URL'].rstrip('/')
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
HEADERS = {
    'apikey': KEY,
    'Authorization': 'Bearer ' + KEY,
    'Content-Type': 'application/json',
    'Prefer': 'resolution=ignore-duplicates,return=minimal',
}
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Observatoire-SUD-ONPL/2.0 (public RSS monitoring)'})

ORCHESTRAS = {
    'ONPL': '("ONPL" OR "Orchestre National des Pays de la Loire")',
    'Orchestre de Paris': '"Orchestre de Paris"',
    'Orchestre national de Lyon': '"Orchestre national de Lyon"',
    'Orchestre national de Lille': '"Orchestre national de Lille"',
    'Orchestre national de Bordeaux Aquitaine': '("Opéra de Bordeaux" OR "Opéra National de Bordeaux" OR "Orchestre National Bordeaux Aquitaine" OR "ONBA")',
    'Orchestre national du Capitole de Toulouse': '"Orchestre national du Capitole"',
    'Orchestre philharmonique de Strasbourg': '"Orchestre philharmonique de Strasbourg"',
    'Orchestre national de Metz': '"Orchestre national de Metz"',
    'Orchestre national de Bretagne': '"Orchestre national de Bretagne"',
    'Orchestre national de Montpellier': '"Orchestre national Montpellier"',
    'Orchestre de l’Opéra de Nice': '"Opéra de Nice" orchestre',
    'Orchestre national d’Île-de-France': '"Orchestre national d’Île-de-France"',
    'Orchestre de l’Opéra de Marseille': '"Opéra de Marseille" orchestre',
    'Orchestre national Avignon-Provence': '"Orchestre national Avignon-Provence"',
    'Orchestre national de Cannes': '"Orchestre national de Cannes"',
}

ORCHESTRA_TERMS = '(budget OR subvention OR grève OR syndicat OR recrutement OR suppression OR emploi OR musicien OR déficit OR restructuration OR communiqué OR rapport)'
SECTOR = 'Secteur orchestral français'
SECTOR_QUERIES = [
    
    # Critiques musicales — presse spécialisée
    'site:bachtrack.com "Orchestre de Paris"',
    'site:bachtrack.com "orchestre national" France',
    'site:resmusica.com "orchestre" concert',
    'site:resmusica.com "orchestre national"',
    'site:forumopera.com "orchestre" critique',
    'site:forumopera.com "Opéra de Nice"',
    'site:concertclassic.com "orchestre" critique',
    'site:concertclassic.com "orchestre national"',
    'site:sudouest.fr "Opéra de Bordeaux" (subvention OR budget OR financement OR suppression)',
    '"orchestres permanents" (budget OR financement OR emploi OR syndicat)',
    '"musiciens d’orchestre" (conditions de travail OR salaire OR emploi OR grève)',
    '"orchestres symphoniques" (subventions OR financement OR crise OR budget)',
    '"spectacle vivant" "orchestre" (financement OR emploi OR réforme)',
    '"ministère de la Culture" orchestres (budget OR financement OR rapport)',
    '"collectivités territoriales" orchestres (subvention OR budget)',
    '"convention collective" musiciens orchestre',
    '"SNAM-CGT" orchestre',
    '"CGT Spectacle" orchestre',
    '"SUD Culture" orchestre',
    '"Cour des comptes" orchestre rapport',
    '"DRAC" orchestre subvention',
]
TOPICS = [
    ('Budget et subventions', ['budget', 'subvention', 'déficit', 'financement', 'coupe budgétaire', 'dotation']),
    ('Emploi et recrutement', ['recrut', 'poste', 'emploi', 'licenci', 'effectif', 'suppression', 'concours']),
    ('Mobilisation et grève', ['grève', 'manifest', 'mobilis', 'préavis', 'syndica', 'pétition']),
    ('Conditions de travail', ['salaire', 'conditions de travail', 'temps de travail', 'rémunération', 'convention collective']),
    ('Gouvernance', ['direction', 'directeur général', 'gouvernance', 'réorganisation', 'restructur', 'nomination']),
]


def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(value or '')))).strip()[:1200]


def category(text):
    lower = text.casefold()
    for name, words in TOPICS:
        if any(word in lower for word in words):
            return name
    return 'Autres'


def published(entry):
    # feedparser struct_time is UTC. calendar.timegm avoids local-time conversion.
    import calendar
    stamp = entry.get('published_parsed') or entry.get('updated_parsed')
    if stamp:
        return datetime.fromtimestamp(calendar.timegm(stamp), timezone.utc).isoformat()
    raw = entry.get('published') or entry.get('updated')
    if raw:
        try:
            return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            pass
    return None

def normalize(entry, orchestra, fallback_source):
    title = clean(entry.get('title'))
    link = (entry.get('link') or '').strip()

    if not title or urlparse(link).scheme not in ('http', 'https'):
        return None

    summary = clean(entry.get('summary') or entry.get('description'))
    source_info = entry.get('source') or {}
    source = clean(
        source_info.get('title')
        if hasattr(source_info, 'get') else ''
    ) or fallback_source

    # Recognise specialist music-review publications
    review_sources = (
        'bachtrack',
        'resmusica',
        'forumopera',
        'forum opéra',
        'concertclassic',
    )

    source_text = source.casefold()
    domain = urlparse(link).netloc.casefold()

    is_review_source = any(
        name in source_text or name.replace(' ', '') in domain
        for name in review_sources
    )

    return {
        'url': link,
        'title': title,
        'summary': summary,
        'source': source[:200],
        'orchestra': orchestra,
        'category': (
            'Critique musicale'
            if is_review_source
            else category(title + ' ' + summary)
        ),
        'published_at': published(entry),
        'is_auto': True,
        'review_status': 'validated',
    }



def read_feed(feed_url, orchestra, fallback_source, max_items=15):
    response = SESSION.get(feed_url, timeout=25)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise RuntimeError('Invalid RSS/Atom response')
    for entry in parsed.entries[:max_items]:
        article = normalize(entry, orchestra, fallback_source)
        if article:
            yield article



def google_news(query, orchestra):
    feed_url = ('https://news.google.com/rss/search?q='
                + quote(query + ' when:365d') + '&hl=fr&gl=FR&ceid=FR:fr')
    yield from read_feed(feed_url, orchestra, 'Google Actualités', max_items=100)


def extra_feeds():
    path = Path(__file__).with_name('sources.json')
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('sources.json must contain a JSON list')
    feeds = []
    for item in data:
        if not isinstance(item, dict):
            continue
        feed_url = item.get('url', '')
        if urlparse(feed_url).scheme != 'https':
            raise ValueError('RSS feed URL must use HTTPS')
        feeds.append((feed_url, item.get('orchestra') or SECTOR,
                      item.get('source') or urlparse(feed_url).netloc))
    return feeds



def store(article):
    response = SESSION.post(
        URL + '/rest/v1/articles?on_conflict=url',
        json=article,
        headers={
            **HEADERS,
            'Accept': 'application/json',
        },
        timeout=25,
    )
    if not response.ok:
        raise RuntimeError(
            f'{response.status_code}: {response.text[:350]}'
        )


def main():
    from web_sources import run as run_web_discovery
    proposed = 0
    errors = []
    searches = [(name, query + ' ' + ORCHESTRA_TERMS)
                for name, query in ORCHESTRAS.items()]
    searches.extend((SECTOR, query) for query in SECTOR_QUERIES)
    for orchestra, query in searches:
        try:
            for article in google_news(query, orchestra):
                store(article)
                proposed += 1
        except Exception as exc:
            errors.append(f'{orchestra} / {query[:55]}: {exc}')
            print('ERROR', errors[-1], file=sys.stderr)
        time.sleep(0.5)

    try:
        feeds = extra_feeds()
    except Exception as exc:
        errors.append(f'sources.json: {exc}')
        feeds = []
    for feed_url, orchestra, source in feeds:
        try:
            for article in read_feed(feed_url, orchestra, source, max_items=40):
                store(article)
                proposed += 1
        except Exception as exc:
            errors.append(f'RSS {feed_url}: {exc}')
            print('ERROR', errors[-1], file=sys.stderr)
        time.sleep(0.5)

    try:
        proposed += run_web_discovery(store, SESSION)
    except Exception as exc:
        print(f'WEB WARNING: {exc}', file=sys.stderr)

    try:
        from documentary import discover as run_documentary
        proposed += run_documentary(store, SESSION)
    except Exception as exc:
        print(f'DOCUMENTARY WARNING: {exc}', file=sys.stderr)

    print(f'Collecte terminée : {proposed} entrées proposées (doublons ignorés), {len(errors)} erreurs')
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()

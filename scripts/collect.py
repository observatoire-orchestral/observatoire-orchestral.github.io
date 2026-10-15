"""Collecte RSS via Google News, sans clé IA payante. Exécution GitHub Actions."""
import os
import re
import time
import html
import sys
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

import requests
import feedparser

URL = os.environ['SUPABASE_URL'].rstrip('/')
KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
HEADERS = {
    'apikey': KEY,
    'Authorization': 'Bearer ' + KEY,
    'Content-Type': 'application/json',
    'Prefer': 'resolution=ignore-duplicates,return=minimal',
}

ORCHESTRAS = {
    'ONPL': '"Orchestre National des Pays de la Loire"',
    'Orchestre de Paris': '"Orchestre de Paris"',
    'Orchestre national de Lyon': '"Orchestre national de Lyon"',
    'Orchestre national de Lille': '"Orchestre national de Lille"',
    'Orchestre national de Bordeaux Aquitaine': '"Orchestre national Bordeaux Aquitaine"',
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

TERMS = '(budget OR subvention OR grève OR syndicat OR recrutement OR suppression OR emploi OR musicien OR déficit OR restructuration)'
TOPICS = [
    ('Budget et subventions', ['budget', 'subvention', 'déficit', 'financement', 'économie', 'coupe budgétaire']),
    ('Emploi et recrutement', ['recrut', 'poste', 'emploi', 'licenci', 'effectif', 'suppression']),
    ('Mobilisation et grève', ['grève', 'manifest', 'mobilis', 'préavis', 'syndica']),
    ('Conditions de travail', ['salaire', 'conditions de travail', 'temps de travail', 'rémunération']),
    ('Gouvernance', ['direction', 'directeur général', 'gouvernance', 'réorganisation', 'restructur']),
]


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()[:1200]


def topic(s):
    s = s.lower()
    for name, words in TOPICS:
        if any(word in s for word in words):
            return name
    return 'Autres'


def fetch(name, query):
    feed = 'https://news.google.com/rss/search?q=' + quote(query + ' when:30d') + '&hl=fr&gl=FR&ceid=FR:fr'
    response = requests.get(feed, timeout=25, headers={'User-Agent': 'SUDCT44-Observatoire/1.0 (RSS monitoring)'})
    response.raise_for_status()
    parsed = feedparser.parse(response.content)

    for entry in parsed.entries[:15]:
        title = clean(entry.get('title', ''))
        link = entry.get('link', '')
        if not title or urlparse(link).scheme not in ('http', 'https'):
            continue

        summary = clean(entry.get('summary', ''))
        published = None
        if entry.get('published_parsed'):
            published = datetime.fromtimestamp(
                __import__('calendar').timegm(entry.published_parsed), timezone.utc
            ).isoformat()
        source = entry.get('source', {}).get('title', 'Google Actualités')

        yield {
            'url': link,
            'title': title,
            'summary': summary,
            'source': clean(source)[:200],
            'orchestra': name,
            'category': topic(title + ' ' + summary),
            'published_at': published,
            'is_auto': True,
            'review_status': 'unreviewed',
        }


def main():
    count = 0
    errors = []
    for name, query in ORCHESTRAS.items():
        try:
            for article in fetch(name, query + ' ' + TERMS):
                response = requests.post(
                    URL + '/rest/v1/articles?on_conflict=url',
                    json=article,
                    headers=HEADERS,
                    timeout=25,
                )
                if not response.ok:
                    raise RuntimeError(f'{response.status_code}: {response.text[:300]}')
                count += 1
        except Exception as exc:
            errors.append(f'{name}: {exc}')
            print('ERROR', errors[-1], file=sys.stderr)
        time.sleep(0.5)
    print(f'Collecte terminée : {count} entrées proposées (doublons ignorés), {len(errors)} erreurs')
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()

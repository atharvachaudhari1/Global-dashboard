import feedparser
from datetime import datetime
from typing import List, Dict

RSS_SOURCES = [
    {"name": "India RSS", "url": "https://www.thehindu.com/news/national/ rss-feed.xml"},
    {"name": "BBC World RSS", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "BBC India RSS", "url": "https://www.bbc.co.uk/sport/world/rss.xml"},
]

def _to_iso(dt) -> str:
    if not dt:
        return datetime.utcnow().isoformat() + "Z"
    if isinstance(dt, datetime):
        return dt.isoformat()
    try:
        return datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %Z").isoformat()
    except Exception:
        return datetime.utcnow().isoformat() + "Z"

def parse_rss_sources() -> List[Dict[str, object]]:
    articles: List[Dict[str, object]] = []
    for src in RSS_SOURCES:
        feed = feedparser.parse(src["url"])
        for entry in feed.entries[:10]:
            title = getattr(entry, 'title', '')
            description = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
            link = getattr(entry, 'link', '#')
            published = getattr(entry, 'published', None) or getattr(entry, 'updated', None)
            country = 'global'
            article = {
                'title': title,
                'description': description,
                'source': src["name"],
                'country': country,
                'pubDate': _to_iso(published),
                'link': link,
                'apiSource': 'RSS'
            }
            articles.append(article)
    return articles

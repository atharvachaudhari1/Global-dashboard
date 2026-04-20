from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import hashlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import feedparser
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
COUNTRIES_PATH = BASE_DIR / "data" / "countries.json"
CONFIG_PATH = BASE_DIR / "config.js"
ENV_PATH = BASE_DIR / ".env"
SAMPLE_NEWS_PATH = BASE_DIR / "data" / "sample_news.json"
DB_PATH = BASE_DIR / "news_archive.db"
SQLITE_MAX_ROWS = max(1000, int(os.getenv("SQLITE_MAX_ROWS", "50000")))
SQLITE_PRUNE_BATCH = max(100, int(os.getenv("SQLITE_PRUNE_BATCH", "1000")))

RSS_FEEDS = [
    ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC Politics", "http://feeds.bbci.co.uk/news/politics/rss.xml"),
    ("Reuters World", "https://www.reutersagency.com/feed/?best-topics=world&post_type=best"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Guardian World", "https://www.theguardian.com/world/rss"),
    ("UN News", "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
    ("DW World", "https://rss.dw.com/xml/rss-en-all"),
    ("Google Peace", "https://news.google.com/rss/search?q=peace+OR+ceasefire+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Conflict", "https://news.google.com/rss/search?q=war+OR+conflict+OR+airstrike+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Diplomacy", "https://news.google.com/rss/search?q=diplomacy+OR+treaty+OR+summit+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Humanitarian", "https://news.google.com/rss/search?q=humanitarian+aid+OR+refugees+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google MENA", "https://news.google.com/rss/search?q=middle+east+conflict+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Europe Security", "https://news.google.com/rss/search?q=europe+security+OR+ukraine+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Asia Security", "https://news.google.com/rss/search?q=asia+security+OR+south+china+sea+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Africa Conflict", "https://news.google.com/rss/search?q=africa+conflict+OR+coup+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Latin America", "https://news.google.com/rss/search?q=latin+america+protest+OR+violence+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Border Tensions", "https://news.google.com/rss/search?q=border+tensions+OR+military+standoff+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Peace Talks", "https://news.google.com/rss/search?q=peace+talks+OR+mediation+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Sanctions", "https://news.google.com/rss/search?q=sanctions+OR+embargo+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Refugee Crisis", "https://news.google.com/rss/search?q=refugee+crisis+OR+displacement+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Terror Security", "https://news.google.com/rss/search?q=terror+threat+OR+counterterrorism+when:30d&hl=en-US&gl=US&ceid=US:en"),
    ("Google Nuclear Tensions", "https://news.google.com/rss/search?q=nuclear+tensions+OR+missile+test+when:30d&hl=en-US&gl=US&ceid=US:en"),
]

GDELT_QUERIES = [
    "peace OR conflict OR war OR protest OR diplomacy OR ceasefire OR violence OR tension",
    "war OR airstrike OR invasion OR shelling OR missile OR troops OR insurgency",
    "ceasefire OR diplomacy OR summit OR treaty OR negotiation OR humanitarian aid",
    "protest OR unrest OR riot OR coup OR sanctions OR crisis",
]
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

CONFLICT_KEYWORDS = {
    "war", "attack", "bomb", "explosion", "killed", "dead", "death", "missile", "airstrike",
    "shooting", "violence", "riot", "clash", "conflict", "fighting", "troops", "invasion",
    "coup", "protest", "unrest", "crisis", "hostage", "terror", "terrorist", "genocide",
    "massacre", "casualties", "wounded", "destroyed", "refugee", "siege", "blockade",
    "sanctions", "nuclear", "chemical weapon", "ethnic cleansing", "displacement", "insurgency",
    "militant",
}

PEACE_KEYWORDS = {
    "peace", "ceasefire", "agreement", "treaty", "diplomacy", "talks", "negotiation", "cooperation",
    "aid", "relief", "reconstruction", "democracy", "election", "vote", "freedom", "human rights",
    "development", "trade", "partnership", "alliance", "reconciliation", "dialogue", "humanitarian",
    "donation", "recovery", "stability", "truce", "resolution", "accord", "summit", "bilateral",
    "multilateral",
}

COUNTRY_MAP = {
    "ukraine": "ua", "russia": "ru", "israel": "il", "gaza": "ps", "palestine": "ps", "iran": "ir",
    "iraq": "iq", "syria": "sy", "yemen": "ye", "afghanistan": "af", "china": "cn", "india": "in",
    "pakistan": "pk", "myanmar": "mm", "sudan": "sd", "ethiopia": "et", "nigeria": "ng",
    "libya": "ly", "somalia": "so", "lebanon": "lb", "usa": "us", "united states": "us",
    "america": "us", "uk": "gb", "britain": "gb", "france": "fr", "germany": "de",
    "australia": "au", "canada": "ca", "japan": "jp",
}

QUERY_STOPWORDS = {
    "what", "where", "when", "which", "with", "this", "that", "from", "into", "about", "news",
    "today", "right", "now", "there", "their", "they", "them", "would", "should", "could", "please",
    "summary", "latest", "current", "situation", "status", "global", "country", "region", "safety",
    "safe", "travel", "going", "know", "tell", "according", "position", "update", "updates", "is",
    "it", "to", "in", "of", "for", "and", "or", "on", "a", "an", "the",
}

HYBRID_CACHE: dict[str, dict[str, Any]] = {}
CACHE_TTL_SECONDS = 180
DB_LOCK = threading.Lock()


def load_dotenv() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def extract_api_key_from_config() -> str | None:
    if not CONFIG_PATH.exists():
        return None
    text = CONFIG_PATH.read_text(encoding="utf-8")
    matches = re.findall(r'newsdata\s*:\s*\{.*?key:\s*"([^"]+)"', text, flags=re.IGNORECASE | re.DOTALL)
    if matches:
        key = matches[0].strip()
        if key and "YOUR_" not in key:
            return key
    legacy = re.findall(r'NEWSDATA_API_KEY:\s*"([^"]+)"', text)
    if legacy:
        key = legacy[0].strip()
        if key and "YOUR_" not in key:
            return key
    return None


def get_primary_news_api_key() -> str | None:
    env_key = os.getenv("NEWSDATA_API_KEY", "").strip()
    if env_key and "YOUR_" not in env_key:
        return env_key
    return extract_api_key_from_config()


def load_countries() -> list[dict]:
    if not COUNTRIES_PATH.exists():
        return []
    with COUNTRIES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def init_sqlite() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                source TEXT,
                country TEXT,
                publishedAt TEXT,
                category TEXT,
                peaceScore REAL,
                url TEXT,
                link TEXT,
                pubDate TEXT,
                score REAL,
                apiSource TEXT,
                cls TEXT,
                ingestedAt TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_publishedAt ON articles(publishedAt DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_country ON articles(country)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)")


def build_article_id(title: str, url: str) -> str:
    raw = f"{(title or '').strip().lower()}|{(url or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upsert_articles_sqlite(articles: list[dict]) -> int:
    if not articles:
        return 0
    now_iso = datetime.now(timezone.utc).isoformat()
    rows: list[tuple] = []
    for article in articles:
        title = article.get("title", "")
        url = article.get("url") or article.get("link") or "#"
        article_id = article.get("id") or build_article_id(title, url)
        rows.append(
            (
                article_id,
                title,
                article.get("description", ""),
                article.get("source", ""),
                article.get("country", "global"),
                article.get("publishedAt") or article.get("pubDate") or now_iso,
                article.get("category", "NEUTRAL"),
                float(article.get("peaceScore", article.get("score", 5.0)) or 5.0),
                url,
                article.get("link", url),
                article.get("pubDate") or article.get("publishedAt") or now_iso,
                float(article.get("score", article.get("peaceScore", 5.0)) or 5.0),
                article.get("apiSource", ""),
                article.get("cls", str(article.get("category", "neutral")).lower()),
                now_iso,
            )
        )

    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.executemany(
                """
                INSERT INTO articles (
                    id, title, description, source, country, publishedAt, category, peaceScore,
                    url, link, pubDate, score, apiSource, cls, ingestedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    description=excluded.description,
                    source=excluded.source,
                    country=excluded.country,
                    publishedAt=excluded.publishedAt,
                    category=excluded.category,
                    peaceScore=excluded.peaceScore,
                    url=excluded.url,
                    link=excluded.link,
                    pubDate=excluded.pubDate,
                    score=excluded.score,
                    apiSource=excluded.apiSource,
                    cls=excluded.cls,
                    ingestedAt=excluded.ingestedAt
                """,
                rows,
            )
            conn.commit()
    return len(rows)


def prune_old_sqlite_articles() -> None:
    retention_days = max(1, int(os.getenv("SQLITE_RETENTION_DAYS", "90")))
    cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM articles WHERE ingestedAt < ?", (cutoff_iso,))
            conn.commit()


def enforce_sqlite_capacity() -> int:
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            total_row = conn.execute("SELECT COUNT(*) FROM articles").fetchone()
            total = int(total_row[0] if total_row else 0)
            if total <= SQLITE_MAX_ROWS:
                return 0

            deleted = conn.execute(
                """
                DELETE FROM articles
                WHERE id IN (
                    SELECT id
                    FROM articles
                    ORDER BY publishedAt ASC, ingestedAt ASC
                    LIMIT ?
                )
                """,
                (SQLITE_PRUNE_BATCH,),
            ).rowcount
            conn.commit()
            return int(deleted or 0)


def query_articles_sqlite(*, country: str, category: str, limit: int, page: int) -> tuple[list[dict], int]:
    where_parts: list[str] = []
    params: list[Any] = []

    if country and country != "global":
        where_parts.append("country = ?")
        params.append(country)
    if category in {"PEACE", "NEUTRAL", "CONFLICT"}:
        where_parts.append("category = ?")
        params.append(category)

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    offset = (page - 1) * limit

    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            total_row = conn.execute(
                f"SELECT COUNT(*) AS total FROM articles {where_clause}",
                params,
            ).fetchone()
            rows = conn.execute(
                f"""
                SELECT
                    title, source, description, url, publishedAt, country, category, peaceScore,
                    link, pubDate, score, apiSource, cls
                FROM articles
                {where_clause}
                ORDER BY publishedAt DESC, ingestedAt DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

    return [dict(row) for row in rows], int(total_row["total"] if total_row else 0)


def extract_country_from_query(question: str) -> str:
    q = (question or "").lower()
    if not q.strip():
        return "global"

    direct_codes = {
        "us": "us", "usa": "us", "u.s.": "us", "u.s.a": "us",
        "uk": "gb", "u.k.": "gb",
    }
    for token, code in direct_codes.items():
        if re.search(rf"\b{re.escape(token)}\b", q):
            return code

    for token, code in COUNTRY_MAP.items():
        if token in q:
            return code
    return "global"


def is_safety_question(question: str) -> bool:
    q = (question or "").lower()
    safety_terms = ("safe", "safety", "travel", "danger", "risky", "risk", "visit", "go to")
    return any(term in q for term in safety_terms)


def extract_query_keywords(question: str, limit: int = 8) -> list[str]:
    tokens = re.findall(r"[a-zA-Z]{3,}", (question or "").lower())
    keywords: list[str] = []
    for tok in tokens:
        if tok in QUERY_STOPWORDS:
            continue
        if tok not in keywords:
            keywords.append(tok)
        if len(keywords) >= limit:
            break
    return keywords


def query_chat_context_sqlite(*, question: str, country: str, limit: int = 120) -> list[dict]:
    keywords = extract_query_keywords(question)
    where_parts: list[str] = []
    params: list[Any] = []

    if country and country != "global":
        where_parts.append("country = ?")
        params.append(country)

    if keywords:
        keyword_clauses: list[str] = []
        for kw in keywords:
            keyword_clauses.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
            like = f"%{kw}%"
            params.extend([like, like])
        where_parts.append(f"({' OR '.join(keyword_clauses)})")

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT
                    title, source, description, url, link, publishedAt, pubDate, country, category,
                    peaceScore, score, apiSource, cls
                FROM articles
                {where_clause}
                ORDER BY publishedAt DESC, ingestedAt DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()

            # If query is too narrow, fallback to recent country/global context.
            if len(rows) < 12:
                fallback_clause = "WHERE country = ?" if country and country != "global" else ""
                fallback_params: list[Any] = [country] if fallback_clause else []
                rows = conn.execute(
                    f"""
                    SELECT
                        title, source, description, url, link, publishedAt, pubDate, country, category,
                        peaceScore, score, apiSource, cls
                    FROM articles
                    {fallback_clause}
                    ORDER BY publishedAt DESC, ingestedAt DESC
                    LIMIT ?
                    """,
                    [*fallback_params, limit],
                ).fetchall()

    return [dict(row) for row in rows]


def build_safety_assessment(*, country: str, articles: list[dict]) -> dict[str, Any]:
    if not articles:
        return {
            "country": country,
            "level": "INSUFFICIENT_DATA",
            "summary": "Not enough recent data to estimate safety reliably.",
            "avgScore": None,
            "conflictRatio": None,
            "articleCount": 0,
        }

    scores = [float(a.get("score") or a.get("peaceScore") or 5.0) for a in articles]
    avg_score = round(sum(scores) / max(1, len(scores)), 2)
    conflict_count = sum(1 for a in articles if (a.get("category") or "").upper() == "CONFLICT")
    conflict_ratio = round(conflict_count / max(1, len(articles)), 2)

    if avg_score >= 6.5 and conflict_ratio < 0.3:
        level = "LOW_RISK"
        summary = "News trend is relatively stable with lower conflict signals."
    elif avg_score >= 4.5 and conflict_ratio < 0.5:
        level = "MEDIUM_RISK"
        summary = "Mixed signals. Travel may be possible but requires caution and local checks."
    else:
        high_risk_condition = conflict_ratio >= 0.55 or avg_score < 4.2
        if high_risk_condition:
            level = "HIGH_RISK"
            summary = "Elevated conflict signals in recent coverage. Avoid non-essential travel."
        else:
            level = "MEDIUM_RISK"
            summary = "Signals are mixed with occasional spikes. Use caution and monitor local alerts."

    return {
        "country": country,
        "level": level,
        "summary": summary,
        "avgScore": avg_score,
        "conflictRatio": conflict_ratio,
        "articleCount": len(articles),
    }


def compose_chat_response(question: str) -> dict[str, Any]:
    normalized_question = (question or "").strip()
    if not normalized_question:
        return {
            "answer": "Please ask a question about current news or travel safety.",
            "summary": [],
            "assessment": None,
            "sources": [],
        }

    country = extract_country_from_query(normalized_question)
    context_rows = query_chat_context_sqlite(question=normalized_question, country=country, limit=120)

    if not context_rows:
        return {
            "answer": "I could not find relevant articles yet. Try refreshing the dashboard first.",
            "summary": [],
            "assessment": {
                "country": country,
                "level": "INSUFFICIENT_DATA",
                "summary": "No context articles available in archive.",
                "avgScore": None,
                "conflictRatio": None,
                "articleCount": 0,
            },
            "sources": [],
        }

    assessment = build_safety_assessment(country=country, articles=context_rows)

    category_counter = Counter((a.get("category") or "NEUTRAL").upper() for a in context_rows)
    top_categories = ", ".join(f"{k}: {v}" for k, v in category_counter.most_common(3))

    source_counter = Counter((a.get("source") or "Unknown") for a in context_rows)
    top_sources = [name for name, _ in source_counter.most_common(5)]
    source_line = ", ".join(top_sources) if top_sources else "multiple sources"

    answer: str
    if is_safety_question(normalized_question):
        answer = (
            f"Safety outlook for {country.upper()}: {assessment['level']}. "
            f"{assessment['summary']} Based on {assessment['articleCount']} recent articles "
            f"with average peace score {assessment['avgScore']}."
        )
    else:
        answer = (
            f"Based on {len(context_rows)} recent archived articles, the current trend is: "
            f"{assessment['summary']} Category mix -> {top_categories}."
        )

    top_headlines = context_rows[:3]
    summary = [
        f"Category breakdown: {top_categories}.",
        f"Most-cited outlets in this answer: {source_line}.",
        f"Recent headline signals: {' | '.join((h.get('title') or '').strip() for h in top_headlines if h.get('title'))}.",
    ]

    sources = []
    seen_keys: set[str] = set()
    for row in context_rows:
        url = row.get("url") or row.get("link") or "#"
        title = (row.get("title") or "").strip()
        key = f"{title.lower()}|{url.lower()}"
        if not title or key in seen_keys:
            continue
        seen_keys.add(key)
        sources.append(
            {
                "title": title,
                "source": row.get("source") or "Unknown",
                "url": url,
                "publishedAt": row.get("publishedAt") or row.get("pubDate"),
                "country": row.get("country") or "global",
                "category": row.get("category") or "NEUTRAL",
                "score": row.get("score") or row.get("peaceScore") or 5.0,
            }
        )
        if len(sources) >= 8:
            break

    return {
        "answer": answer,
        "summary": summary,
        "assessment": assessment,
        "sources": sources,
    }


def normalize_country(value: str) -> str:
    val = (value or "").strip().lower()
    if not val:
        return "global"
    if len(val) == 2:
        return val
    for token, code in COUNTRY_MAP.items():
        if token in val:
            return code
    return "global"


def detect_country_from_text(text: str) -> str:
    txt = (text or "").lower()
    for token, code in COUNTRY_MAP.items():
        if token in txt:
            return code
    return "global"


def parse_date_to_iso(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        try:
            parsed = datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")
            return parsed.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return datetime.now(timezone.utc).isoformat()


def format_gdelt_date(value: str | None) -> str:
    if not value or len(value) < 8:
        return datetime.now(timezone.utc).isoformat()
    y, m, d = value[:4], value[4:6], value[6:8]
    hh = value[8:10] if len(value) >= 10 else "00"
    mm = value[10:12] if len(value) >= 12 else "00"
    try:
        dt = datetime.strptime(f"{y}-{m}-{d} {hh}:{mm}", "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def calculate_peace_score(title: str, description: str) -> float:
    text = f"{title or ''} {description or ''}".lower()
    score = 5.0
    conflict_hits = sum(1 for kw in CONFLICT_KEYWORDS if kw in text)
    peace_hits = sum(1 for kw in PEACE_KEYWORDS if kw in text)
    score -= min(conflict_hits * 0.4, 4.5)
    score += min(peace_hits * 0.35, 4.0)

    title_lower = (title or "").lower()
    if any(kw in title_lower for kw in CONFLICT_KEYWORDS):
        score -= 0.5
    if any(kw in title_lower for kw in PEACE_KEYWORDS):
        score += 0.5
    score = max(0.1, min(9.9, score))
    return round(score, 1)


def classify_category(peace_score: float) -> str:
    if peace_score >= 6.5:
        return "PEACE"
    if peace_score >= 4.0:
        return "NEUTRAL"
    return "CONFLICT"


def normalize_article(
    *,
    title: str,
    source: str,
    description: str,
    url: str,
    published_at: str | None,
    country: str,
    source_name: str,
) -> dict:
    normalized_country = normalize_country(country) if country else detect_country_from_text(title)
    iso_date = parse_date_to_iso(published_at)
    peace_score = calculate_peace_score(title, description)
    category = classify_category(peace_score)
    return {
        "title": title or "",
        "source": source or source_name,
        "description": description or "",
        "url": url or "#",
        "publishedAt": iso_date,
        "country": normalized_country,
        "category": category,
        "peaceScore": peace_score,
        "link": url or "#",
        "pubDate": iso_date,
        "score": peace_score,
        "apiSource": source_name,
        "cls": category.lower(),
    }


def fetch_primary_api_news(*, country: str, size: int) -> list[dict]:
    api_key = get_primary_news_api_key()
    if not api_key:
        raise RuntimeError("Primary API key missing")
    base_params = {"apikey": api_key, "language": "en", "size": min(size, 20)}
    if country and country != "global":
        base_params["country"] = country
    variants = [{**base_params, "category": "top"}, base_params, {**base_params, "q": "peace OR conflict OR war OR diplomacy"}]

    data = None
    last_error: Exception | None = None
    for params in variants:
        try:
            response = requests.get("https://newsdata.io/api/1/news", params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    if data is None:
        raise RuntimeError(str(last_error) if last_error else "Primary API failed")

    rows = data.get("results", []) or []
    normalized = []
    for row in rows:
        raw_country = ""
        if isinstance(row.get("country"), list) and row["country"]:
            raw_country = str(row["country"][0])
        elif isinstance(row.get("country"), str):
            raw_country = row["country"]
        normalized.append(
            normalize_article(
                title=row.get("title", ""),
                source=row.get("source_id", "NewsData"),
                description=row.get("description", ""),
                url=row.get("link", "#"),
                published_at=row.get("pubDate"),
                country=raw_country,
                source_name="PrimaryAPI",
            )
        )
    return normalized


def fetch_gdelt_news(*, country: str) -> list[dict]:
    normalized: list[dict] = []
    for query in GDELT_QUERIES:
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 250,
            "sourcelang": "english",
            "timespan": "1month",
            "sort": "datedesc",
        }
        response = requests.get(GDELT_URL, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()
        rows = data.get("articles", []) or []
        for row in rows:
            article = normalize_article(
                title=row.get("title", ""),
                source=row.get("domain", "GDELT"),
                description=row.get("theme", "") or "",
                url=row.get("url", "#"),
                published_at=format_gdelt_date(row.get("seendate")),
                country=detect_country_from_text(row.get("title", "")),
                source_name="GDELT",
            )
            if country and country != "global" and article["country"] != country:
                continue
            normalized.append(article)
    return deduplicate_articles(normalized)


def fetch_rss_news(*, country: str) -> list[dict]:
    normalized: list[dict] = []

    def _parse_feed(feed_name: str, feed_url: str) -> list[dict]:
        parsed = feedparser.parse(feed_url)
        local_rows: list[dict] = []
        for entry in parsed.entries[:500]:
            article = normalize_article(
                title=getattr(entry, "title", ""),
                source=feed_name,
                description=getattr(entry, "summary", ""),
                url=getattr(entry, "link", "#"),
                published_at=getattr(entry, "published", None) or getattr(entry, "updated", None),
                country=detect_country_from_text(getattr(entry, "title", "")),
                source_name="RSS",
            )
            if country and country != "global" and article["country"] != country:
                continue
            local_rows.append(article)
        return local_rows

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_parse_feed, feed_name, feed_url) for feed_name, feed_url in RSS_FEEDS]
        for future in as_completed(futures):
            try:
                normalized.extend(future.result())
            except Exception:
                continue

    return normalized


def load_sample_fallback_articles() -> list[dict]:
    if not SAMPLE_NEWS_PATH.exists():
        return []
    with SAMPLE_NEWS_PATH.open("r", encoding="utf-8") as handle:
        raw_items = json.load(handle)
    return [
        normalize_article(
            title=item.get("headline", "Global peace update"),
            source=item.get("source", "fallback"),
            description="",
            url="#",
            published_at=item.get("pubDate"),
            country=item.get("region", "global"),
            source_name="Fallback",
        )
        for item in raw_items
    ]


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for article in articles:
        key = f"{article.get('title','').strip().lower()}|{article.get('url','').strip().lower()}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(article)
    return deduped


def sort_articles_desc(articles: list[dict]) -> list[dict]:
    return sorted(articles, key=lambda a: a.get("publishedAt", ""), reverse=True)


def aggregate_hybrid_news(*, country: str, size: int) -> tuple[list[dict], dict]:
    cache_key = f"{country or 'global'}:{size}"
    cached = HYBRID_CACHE.get(cache_key)
    if cached and time() - cached["ts"] < CACHE_TTL_SECONDS:
        return cached["data"], {"cached": True, "sources": cached["sources"], "errors": cached["errors"]}

    collected: list[dict] = []
    source_counts: dict[str, int] = {}
    errors: dict[str, str] = {}

    try:
        primary = fetch_primary_api_news(country=country, size=max(20, min(size, 200)))
        collected.extend(primary)
        source_counts["primary_api"] = len(primary)
    except Exception as exc:  # noqa: BLE001
        errors["primary_api"] = str(exc)

    try:
        gdelt = fetch_gdelt_news(country=country)
        collected.extend(gdelt)
        source_counts["gdelt"] = len(gdelt)
    except Exception as exc:  # noqa: BLE001
        errors["gdelt"] = str(exc)

    try:
        rss = fetch_rss_news(country=country)
        collected.extend(rss)
        source_counts["rss"] = len(rss)
    except Exception as exc:  # noqa: BLE001
        errors["rss"] = str(exc)

    if not collected:
        collected = load_sample_fallback_articles()
        source_counts["fallback"] = len(collected)

    merged = sort_articles_desc(deduplicate_articles(collected))[:size]
    HYBRID_CACHE[cache_key] = {"ts": time(), "data": merged, "sources": source_counts, "errors": errors}
    return merged, {"cached": False, "sources": source_counts, "errors": errors}


load_dotenv()
init_sqlite()
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)


@app.get("/api/countries")
def get_countries():
    return jsonify(load_countries())


@app.get("/api/news")
def get_news():
    country = normalize_country((request.args.get("country") or "").strip()) if request.args.get("country") else "global"
    limit = int(request.args.get("limit", request.args.get("size", "120")))
    limit = max(1, min(limit, SQLITE_MAX_ROWS))
    page = int(request.args.get("page", "1"))
    page = max(1, page)
    category = (request.args.get("category") or "").strip().upper()

    fetch_size = 3000 if country == "global" else min(3000, max(500, limit * page, limit))
    ingested = 0
    deleted_oldest = 0
    meta: dict[str, Any] = {"cached": False, "sources": {}, "errors": {}}
    try:
        fetched_articles, meta = aggregate_hybrid_news(country=country, size=fetch_size)
        ingested = upsert_articles_sqlite(fetched_articles)
        prune_old_sqlite_articles()
        deleted_oldest = enforce_sqlite_capacity()
    except Exception as exc:  # noqa: BLE001
        meta["errors"] = {**meta.get("errors", {}), "sqlite_ingest": str(exc)}

    paged, total_available = query_articles_sqlite(
        country=country,
        category=category,
        limit=limit,
        page=page,
    )

    return jsonify(
        {
            "results": paged,
            "meta": {
                "mode": "sqlite_archive",
                "count": len(paged),
                "totalAvailable": total_available,
                "country": country,
                "category": category or "all",
                "page": page,
                "limit": limit,
                "cached": meta["cached"],
                "ingestedThisFetch": ingested,
                "deletedOldestThisFetch": deleted_oldest,
                "maxArchiveSize": SQLITE_MAX_ROWS,
                "sourceCounts": meta["sources"],
                "errors": meta["errors"],
            },
        }
    )


@app.get("/api/news/hybrid")
def get_news_hybrid():
    return get_news()


@app.post("/api/chat")
def chat_with_news():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question") or "").strip()
    response = compose_chat_response(question)
    return jsonify(response)


@app.get("/api/health")
def health():
    sqlite_ready = DB_PATH.exists()
    return jsonify({"ok": True, "hybrid_pipeline": True, "sqlite_archive": sqlite_ready})


@app.get("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:path>")
def serve_static(path: str):
    file_path = BASE_DIR / path
    if file_path.exists() and file_path.is_file():
        return send_from_directory(BASE_DIR, path)
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5050"))
    app.run(host=host, port=port, debug=True)

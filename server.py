from __future__ import annotations

import json
import os
import re
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

RSS_FEEDS = [
    ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Reuters World", "https://www.reutersagency.com/feed/?best-topics=world&post_type=best"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
]

GDELT_QUERY = "peace OR conflict OR war OR protest OR diplomacy OR ceasefire OR violence OR tension"
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

# Key: f"{country or 'global'}:{size}" -> {"ts": epoch, "data": list}
HYBRID_CACHE: dict[str, dict[str, Any]] = {}
CACHE_TTL_SECONDS = 180


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
        # Required unified schema
        "title": title or "",
        "source": source or source_name,
        "description": description or "",
        "url": url or "#",
        "publishedAt": iso_date,
        "country": normalized_country,
        "category": category,
        "peaceScore": peace_score,
        # Backward compatibility fields used by existing frontend
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

    # Free plan is typically stable around ~20 records per call.
    base_params = {"apikey": api_key, "language": "en", "size": min(size, 20)}
    if country and country != "global":
        base_params["country"] = country

    # NewsData varies by account/plan; try multiple compatible variants.
    param_variants = [
        {**base_params, "category": "top"},
        base_params,
        {**base_params, "q": "peace OR conflict OR war OR diplomacy"},
    ]

    last_error: Exception | None = None
    data = None
    for params in param_variants:
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
    result = []
    for row in rows:
        raw_country = ""
        if isinstance(row.get("country"), list) and row["country"]:
            raw_country = str(row["country"][0])
        elif isinstance(row.get("country"), str):
            raw_country = row["country"]
        result.append(
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
    return result


def fetch_gdelt_news(*, country: str) -> list[dict]:
    params = {
        "query": GDELT_QUERY,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": 50,
        "sourcelang": "english",
    }
    response = requests.get(GDELT_URL, params=params, timeout=25)
    response.raise_for_status()
    data = response.json()
    rows = data.get("articles", []) or []
    result = []
    for row in rows:
        normalized = normalize_article(
            title=row.get("title", ""),
            source=row.get("domain", "GDELT"),
            description=row.get("theme", "") or "",
            url=row.get("url", "#"),
            published_at=format_gdelt_date(row.get("seendate")),
            country=detect_country_from_text(row.get("title", "")),
            source_name="GDELT",
        )
        if country and country != "global" and normalized["country"] != country:
            continue
        result.append(normalized)
    return result


def fetch_rss_news(*, country: str) -> list[dict]:
    result: list[dict] = []
    for feed_name, feed_url in RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        entries = parsed.entries[:50]
        for entry in entries:
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            link = getattr(entry, "link", "#")
            published = getattr(entry, "published", None) or getattr(entry, "updated", None)
            normalized = normalize_article(
                title=title,
                source=feed_name,
                description=summary,
                url=link,
                published_at=published,
                country=detect_country_from_text(title),
                source_name="RSS",
            )
            if country and country != "global" and normalized["country"] != country:
                continue
            result.append(normalized)
    return result


def load_sample_fallback_articles() -> list[dict]:
    if not SAMPLE_NEWS_PATH.exists():
        return []
    with SAMPLE_NEWS_PATH.open("r", encoding="utf-8") as handle:
        raw_items = json.load(handle)
    fallback: list[dict] = []
    for item in raw_items:
        fallback.append(
            normalize_article(
                title=item.get("headline", "Global peace update"),
                source=item.get("source", "fallback"),
                description="",
                url="#",
                published_at=item.get("pubDate"),
                country=item.get("region", "global"),
                source_name="Fallback",
            )
        )
    return fallback


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for article in articles:
        key = f"{article.get('title', '').strip().lower()}|{article.get('url', '').strip().lower()}"
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

    # 1) Existing clean API source (primary)
    try:
        primary = fetch_primary_api_news(country=country, size=max(20, min(size, 50)))
        collected.extend(primary)
        source_counts["primary_api"] = len(primary)
    except Exception as exc:  # noqa: BLE001
        errors["primary_api"] = str(exc)

    # 2) GDELT bulk
    try:
        gdelt = fetch_gdelt_news(country=country)
        collected.extend(gdelt)
        source_counts["gdelt"] = len(gdelt)
    except Exception as exc:  # noqa: BLE001
        errors["gdelt"] = str(exc)

    # 3) RSS feeds
    try:
        rss = fetch_rss_news(country=country)
        collected.extend(rss)
        source_counts["rss"] = len(rss)
    except Exception as exc:  # noqa: BLE001
        errors["rss"] = str(exc)

    if not collected:
        collected = load_sample_fallback_articles()
        source_counts["fallback"] = len(collected)

    merged = deduplicate_articles(collected)
    merged = sort_articles_desc(merged)[:size]

    HYBRID_CACHE[cache_key] = {"ts": time(), "data": merged, "sources": source_counts, "errors": errors}
    return merged, {"cached": False, "sources": source_counts, "errors": errors}


load_dotenv()
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)


@app.get("/api/countries")
def get_countries():
    return jsonify(load_countries())


@app.get("/api/news")
def get_news():
    country = normalize_country((request.args.get("country") or "").strip()) if request.args.get("country") else "global"
    size = int(request.args.get("size", "120"))
    size = max(1, min(size, 500))

    articles, meta = aggregate_hybrid_news(country=country, size=size)
    return jsonify(
        {
            "results": articles,
            "meta": {
                "mode": "hybrid",
                "count": len(articles),
                "country": country,
                "cached": meta["cached"],
                "sourceCounts": meta["sources"],
                "errors": meta["errors"],
            },
        }
    )


@app.get("/api/news/hybrid")
def get_news_hybrid():
    return get_news()


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "hybrid_pipeline": True})


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

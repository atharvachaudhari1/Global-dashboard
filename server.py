from __future__ import annotations

import json
import os
from pathlib import Path
from time import time

import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
COUNTRIES_PATH = BASE_DIR / "data" / "countries.json"
CONFIG_PATH = BASE_DIR / "config.js"
SAMPLE_NEWS_PATH = BASE_DIR / "data" / "sample_news.json"


IN_MEMORY_NEWS_CACHE: dict[str, list[dict]] = {"global": []}
RATE_LIMITED_UNTIL = 0.0
RATE_LIMITED_REASON = ""


def extract_api_key_from_config() -> str | None:
    if not CONFIG_PATH.exists():
        return None
    text = CONFIG_PATH.read_text(encoding="utf-8")
    marker = 'NEWSDATA_API_KEY: "'
    start = text.find(marker)
    if start == -1:
        return None
    start += len(marker)
    end = text.find('"', start)
    if end == -1:
        return None
    return text[start:end].strip() or None


def load_countries() -> list[dict]:
    if not COUNTRIES_PATH.exists():
        return []
    with COUNTRIES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_sample_fallback_articles() -> list[dict]:
    # Uses project fallback file and adapts shape to news-like response.
    if not SAMPLE_NEWS_PATH.exists():
        return []
    with SAMPLE_NEWS_PATH.open("r", encoding="utf-8") as handle:
        raw_items = json.load(handle)

    converted: list[dict] = []
    for item in raw_items:
        converted.append(
            {
                "title": item.get("headline", "Global peace update"),
                "description": "",
                "source_id": item.get("source", "fallback"),
                "country": ["global"],
                "pubDate": item.get("pubDate") or "2026-01-01T00:00:00Z",
                "link": "#",
            }
        )
    return converted


def build_fallback_news(country: str, size: int) -> list[dict]:
    if country and IN_MEMORY_NEWS_CACHE.get(country):
        return IN_MEMORY_NEWS_CACHE[country][:size]
    if IN_MEMORY_NEWS_CACHE.get("global"):
        return IN_MEMORY_NEWS_CACHE["global"][:size]
    return load_sample_fallback_articles()[:size]


app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)


@app.get("/api/countries")
def get_countries():
    return jsonify(load_countries())


@app.get("/api/news")
def get_news():
    global RATE_LIMITED_UNTIL, RATE_LIMITED_REASON

    api_key = extract_api_key_from_config()
    if not api_key:
        fallback_size = int(request.args.get("size", "20"))
        return jsonify(
            {
                "results": build_fallback_news("", fallback_size),
                "meta": {
                    "fallback": True,
                    "reason": "API key missing in config.js",
                },
            }
        )

    country = (request.args.get("country") or "").strip().lower()
    size = int(request.args.get("size", "20"))

    if RATE_LIMITED_UNTIL > time():
        return jsonify(
            {
                "results": build_fallback_news(country, size),
                "meta": {
                    "fallback": True,
                    "reason": RATE_LIMITED_REASON or "Rate limited by provider.",
                },
            }
        )

    params = {
        "apikey": api_key,
        "language": "en",
        "category": "top",
        "size": size,
    }
    if country:
        params["country"] = country

    try:
        response = requests.get("https://newsdata.io/api/1/news", params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", []) or []
        if country:
            IN_MEMORY_NEWS_CACHE[country] = results
        else:
            IN_MEMORY_NEWS_CACHE["global"] = results
        return jsonify({"results": results, "meta": {"fallback": False}})
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code == 429:
            RATE_LIMITED_UNTIL = time() + 30 * 60
            RATE_LIMITED_REASON = "News provider request quota reached. Serving cached/fallback data."

        fallback_reason = RATE_LIMITED_REASON if status_code == 429 else str(exc)
        return jsonify(
            {
                "results": build_fallback_news(country, size),
                "meta": {
                    "fallback": True,
                    "reason": fallback_reason,
                },
            }
        )


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


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

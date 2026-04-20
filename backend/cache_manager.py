from __future__ import annotations

import threading
import time
from typing import Any


class NewsCache:
    """Thread-safe in-memory article cache with TTL-based expiry."""

    def __init__(self, ttl_seconds: int = 900) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._items: dict[str, dict[str, Any]] = {}

    def upsert(self, article: dict[str, Any]) -> None:
        article_id = str(article.get("id") or "")
        if not article_id:
            return

        entry = dict(article)
        # Track insertion/update time for TTL eviction.
        entry["_cached_at"] = time.time()

        with self._lock:
            self._items[article_id] = entry

    def get_all(
        self,
        *,
        country: str = "global",
        category: str | None = None,
        limit: int = 120,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        now = time.time()
        country_norm = (country or "global").strip().lower()
        category_norm = (category or "").strip().lower()

        with self._lock:
            items = []
            for article in self._items.values():
                cached_at = float(article.get("_cached_at", 0))
                if now - cached_at > self.ttl_seconds:
                    continue

                article_country = str(article.get("country", "global")).strip().lower()
                if country_norm != "global" and article_country != country_norm:
                    continue

                if category_norm:
                    article_category = str(article.get("category", "")).strip().lower()
                    if article_category != category_norm:
                        continue

                clean = dict(article)
                clean.pop("_cached_at", None)
                items.append(clean)

        items.sort(key=lambda a: float(a.get("timestamp", 0)), reverse=True)
        if limit is None:
            return items
        offset = max(0, (page - 1) * limit)
        end = offset + limit
        return items[offset:end]

    def clear_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired_keys = [
                key
                for key, article in self._items.items()
                if now - float(article.get("_cached_at", 0)) > self.ttl_seconds
            ]
            for key in expired_keys:
                self._items.pop(key, None)

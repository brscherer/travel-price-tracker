from __future__ import annotations

import hashlib
import logging

import feedparser
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .models import PromoItem

log = logging.getLogger(__name__)

_USER_AGENT = "travel-price-tracker/0.1 (+personal deal tracker; non-commercial)"


def parse_feed(raw: bytes, source_name: str) -> list[PromoItem]:
    parsed = feedparser.parse(raw)
    items: list[PromoItem] = []
    for entry in parsed.entries:
        item_id = entry.get("id") or entry.get("link") or hashlib.sha1(entry.get("title", "").encode()).hexdigest()
        items.append(
            PromoItem(
                source=source_name,
                item_id=item_id,
                title=entry.get("title", ""),
                link=entry.get("link", ""),
                summary=entry.get("summary", ""),
                published_at=entry.get("published"),
            )
        )
    return items


class RssProvider:
    """RSS feed reader for Brazilian miles/deal blogs. Fetches over HTTP
    (with retries) and hands the raw bytes to feedparser -- keeps the
    network layer swappable/mockable independent of feed parsing.
    """

    name = "rss"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _fetch_raw(self, url: str) -> bytes:
        resp = requests.get(url, timeout=15, headers={"User-Agent": _USER_AGENT})
        resp.raise_for_status()
        return resp.content

    def fetch(self, url: str, source_name: str) -> list[PromoItem]:
        try:
            raw = self._fetch_raw(url)
        except requests.RequestException:
            log.warning("RSS fetch failed for %s (%s) -- skipping this feed for this run", source_name, url)
            return []
        return parse_feed(raw, source_name)

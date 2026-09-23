from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PromoItem:
    """A single promo/blog-post/channel-message candidate, from any source
    (RSS feed or Telegram channel) -- normalized so the same filter/dedup/
    alert pipeline can handle both.
    """

    source: str
    item_id: str
    title: str
    link: str
    summary: str
    published_at: str | None

from __future__ import annotations

import logging

from ..promos.models import PromoItem

log = logging.getLogger(__name__)


def fetch_recent_messages(
    session_name: str,
    api_id: str,
    api_hash: str,
    channels: list[str],
    keywords: list[str],
    limit: int = 50,
) -> list[PromoItem]:
    """Pull recent messages from public Telegram channels via a saved
    Telethon session (created once via `login.py`), pre-filtered by
    keyword. Public channels only -- no scraping anything behind a login.
    """
    if not api_id or not api_hash:
        log.info("Telegram channel monitoring enabled but TELEGRAM_API_ID/TELEGRAM_API_HASH not set, skipping")
        return []

    try:
        from telethon.sync import TelegramClient
    except ImportError:
        log.warning("telethon not installed -- run `pip install -e '.[telegram]'` to enable channel monitoring")
        return []

    items: list[PromoItem] = []
    try:
        with TelegramClient(session_name, int(api_id), api_hash) as client:
            for channel in channels:
                try:
                    for message in client.iter_messages(channel, limit=limit):
                        text = message.text or ""
                        if not text or not any(kw.lower() in text.lower() for kw in keywords):
                            continue
                        items.append(
                            PromoItem(
                                source=f"telegram:{channel}",
                                item_id=str(message.id),
                                title=text[:120],
                                link=f"https://t.me/{channel}/{message.id}",
                                summary=text,
                                published_at=message.date.isoformat() if message.date else None,
                            )
                        )
                except Exception:
                    log.exception("Failed to read Telegram channel %s -- skipping", channel)
    except Exception:
        log.exception(
            "Failed to open Telethon session '%s' -- run `python -m travel_tracker.telegram_channels.login` first",
            session_name,
        )
        return []

    return items

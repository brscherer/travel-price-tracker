from __future__ import annotations

import logging

from .alerts.telegram import TelegramAlerter
from .config import AppConfig, Secrets, load_config, load_secrets
from .db.models import connect
from .promos.pipeline import process_promo_item
from .promos.rss import RssProvider

log = logging.getLogger(__name__)


def run_promo_scan(config: AppConfig | None = None, secrets: Secrets | None = None) -> None:
    """RSS deal-blog feeds (+ optional Telegram channel monitoring) for
    POA/miles-program-relevant promos, transfer bonuses, and miles sales.
    """
    config = config or load_config()
    secrets = secrets or load_secrets()

    if not config.promos.enabled:
        log.info("promo scan disabled in config, skipping")
        return

    conn = connect(secrets.database_path)
    alerter = TelegramAlerter(secrets.telegram_bot_token, secrets.telegram_chat_id) if config.alerts.telegram_enabled else None
    rss = RssProvider()

    summary_lines: list[str] = []

    for feed in config.promos.rss_feeds:
        items = rss.fetch(feed.url, feed.name)
        log.info("feed=%s items_found=%d", feed.name, len(items))
        for item in items:
            line = process_promo_item(conn, item, config.promos, alerter)
            if line:
                summary_lines.append(line)

    tg_cfg = config.promos.telegram_channels
    if tg_cfg.enabled and tg_cfg.channels:
        from .telegram_channels.monitor import fetch_recent_messages

        channel_items = fetch_recent_messages(
            tg_cfg.session_name,
            secrets.telegram_api_id,
            secrets.telegram_api_hash,
            tg_cfg.channels,
            tg_cfg.keywords or config.promos.keywords,
        )
        log.info("telegram channels scanned=%d messages_matched=%d", len(tg_cfg.channels), len(channel_items))
        for item in channel_items:
            line = process_promo_item(conn, item, config.promos, alerter)
            if line:
                summary_lines.append(line)

    if alerter and summary_lines:
        alerter.send_daily_summary(summary_lines)

    conn.close()

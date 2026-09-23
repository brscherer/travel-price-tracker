from __future__ import annotations

import logging

from .alerts.telegram import TelegramAlerter
from .config import AppConfig, Secrets, load_config, load_secrets
from .db.models import connect
from .pipeline import process_fare
from .providers.serpapi import SerpApiProvider
from .providers.travelpayouts import TravelpayoutsProvider

log = logging.getLogger(__name__)


def run_wide_scan(config: AppConfig | None = None, secrets: Secrets | None = None) -> None:
    """'POA to anywhere' scan -- catches unusual drops on routes that
    aren't on the watchlist. Shares the same detection/alert pipeline as
    the watchlist scan, just fed from `TravelpayoutsProvider.wide_scan`
    instead of per-route searches.
    """
    config = config or load_config()
    secrets = secrets or load_secrets()

    if not config.wide_scan.enabled:
        log.info("wide scan disabled in config, skipping")
        return

    conn = connect(secrets.database_path)
    provider = TravelpayoutsProvider(secrets.travelpayouts_token, secrets.travelpayouts_marker)
    alerter = TelegramAlerter(secrets.telegram_bot_token, secrets.telegram_chat_id) if config.alerts.telegram_enabled else None
    serpapi = SerpApiProvider(secrets.serpapi_key) if config.serpapi.enabled and secrets.serpapi_key else None

    fares = provider.wide_scan(config.wide_scan.origin, cabin=config.wide_scan.cabin)
    log.info("wide scan origin=%s destinations_found=%d", config.wide_scan.origin, len(fares))

    summary_lines: list[str] = []
    for fare in fares:
        line = process_fare(conn, fare, config, alerter, serpapi, max_price_brl=None)
        if line:
            summary_lines.append(line)

    if alerter and summary_lines:
        alerter.send_daily_summary(summary_lines)

    conn.close()

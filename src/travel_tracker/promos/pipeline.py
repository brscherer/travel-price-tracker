from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

from ..alerts.telegram import TelegramAlerter
from ..config import PromosConfig
from ..db.models import promo_already_alerted, record_promo_alert
from .filters import extract_transfer_bonus_pct, is_miles_sale, matches_keywords
from .models import PromoItem

log = logging.getLogger(__name__)


def process_promo_item(
    conn: sqlite3.Connection,
    item: PromoItem,
    promos_config: PromosConfig,
    alerter: TelegramAlerter | None,
) -> str | None:
    """Classify a promo/channel-message item, dedup against what's already
    been alerted, and send an alert if it clears one of the promo rules.
    Same item (by source + item_id) never alerts twice. Returns a one-line
    summary string when an alert fired, else None.
    """
    if promo_already_alerted(conn, item.source, item.item_id):
        return None

    text = f"{item.title} {item.summary}"
    bonus_pct = extract_transfer_bonus_pct(text)

    if bonus_pct is not None and bonus_pct >= promos_config.transfer_bonus_min_pct:
        label, alert_type, note = "Transfer bonus", "transfer_bonus", f"{bonus_pct}% bonus mentioned"
    elif is_miles_sale(text):
        label, alert_type, note = "Miles sale", "miles_sale", None
    elif matches_keywords(text, promos_config.keywords):
        label, alert_type, note = "Promo", "promo", None
    else:
        return None

    sent_at = datetime.now(timezone.utc).isoformat()
    if alerter:
        alerter.send_promo_alert(label, item.title, item.link, item.source, note)
    record_promo_alert(conn, item.source, item.item_id, alert_type, sent_at, title=item.title, link=item.link)

    return f"[{label}] {item.title} ({item.source})"

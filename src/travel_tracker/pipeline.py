from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

from .alerts.dedup import should_alert
from .alerts.telegram import TelegramAlerter
from .config import AppConfig
from .db.models import (
    FareSnapshotRecord,
    get_last_alert_price,
    get_or_create_route,
    get_price_history_brl,
    insert_snapshot,
    record_alert,
)
from .deals.detector import DealType, evaluate_price
from .deals.recheck import confirm_or_downgrade
from .providers.base import FareResult
from .providers.serpapi import SerpApiProvider

log = logging.getLogger(__name__)


def process_fare(
    conn: sqlite3.Connection,
    fare: FareResult,
    config: AppConfig,
    alerter: TelegramAlerter | None,
    serpapi: SerpApiProvider | None,
    max_price_brl: float | None = None,
) -> str | None:
    """Store a fare snapshot, classify it, live-recheck possible error
    fares, dedup against the last alert, and send an alert if warranted.
    Shared by the watchlist scan and the wide "anywhere" scan. Returns a
    one-line summary string when an alert fired, else None.
    """
    route_id = get_or_create_route(conn, fare.origin, fare.destination, fare.cabin)
    history = get_price_history_brl(conn, route_id, config.deal_detection.rolling_window_days)
    fetched_at = datetime.now(timezone.utc).isoformat()

    insert_snapshot(
        conn,
        FareSnapshotRecord(
            route_id=route_id,
            depart_date=fare.depart_date,
            return_date=fare.return_date,
            price=fare.price,
            currency=fare.currency,
            price_brl=fare.price_brl,
            cabin=fare.cabin,
            source=fare.source,
            booking_link=fare.booking_link,
            fetched_at=fetched_at,
        ),
    )

    evaluation = evaluate_price(
        fare.price_brl,
        history,
        config.deal_detection.min_snapshots_for_median,
        config.deal_detection.hot_deal_discount_pct,
        config.deal_detection.error_fare_discount_pct,
        max_price_brl=max_price_brl,
    )
    if evaluation.deal_type == DealType.NONE:
        return None

    last_alert_price = get_last_alert_price(conn, route_id, fare.depart_date, fare.return_date)
    if last_alert_price is not None and fare.price_brl >= last_alert_price:
        # Cached price is no better than what we already alerted (or already
        # live-checked and cleared) at -- skip before spending a live
        # re-check call on it.
        return None

    alert_price_brl = fare.price_brl

    if evaluation.deal_type == DealType.ERROR_FARE and serpapi and evaluation.median_brl is not None:
        live_price = serpapi.check_price(fare.origin, fare.destination, fare.depart_date, fare.return_date, fare.cabin)
        evaluation = confirm_or_downgrade(
            live_price,
            fare.price_brl,
            evaluation.median_brl,
            config.deal_detection.hot_deal_discount_pct,
            config.deal_detection.error_fare_discount_pct,
        )
        if evaluation.deal_type == DealType.NONE:
            log.info(
                "Live re-check cleared cached error fare %s-%s %s (cached R$ %.2f, live R$ %s)",
                fare.origin,
                fare.destination,
                fare.depart_date,
                fare.price_brl,
                live_price,
            )
            # Record against the cached price so a re-scan that turns up the
            # same stale cached price again is skipped by the guard above,
            # instead of burning another SerpApi call on a known-fake price.
            record_alert(
                conn, route_id, fare.depart_date, fare.return_date, fare.price_brl, "error_fare_cleared", fetched_at
            )
            return None
        if live_price is not None:
            alert_price_brl = live_price

    if not should_alert(alert_price_brl, last_alert_price):
        return None

    if alerter:
        alerter.send_deal_alert(
            deal_type=evaluation.deal_type,
            origin=fare.origin,
            destination=fare.destination,
            depart_date=fare.depart_date,
            return_date=fare.return_date,
            price_brl=alert_price_brl,
            discount_pct=evaluation.discount_pct,
            source=fare.source,
            booking_link=fare.booking_link,
        )
    record_alert(
        conn,
        route_id,
        fare.depart_date,
        fare.return_date,
        alert_price_brl,
        evaluation.deal_type.value,
        fetched_at,
    )

    discount_note = (
        f"{evaluation.discount_pct:.0f}% below median" if evaluation.discount_pct is not None else "within target price"
    )
    return f"{fare.origin}->{fare.destination} {fare.depart_date}: R$ {alert_price_brl:,.2f} ({discount_note})"

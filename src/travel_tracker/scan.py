from __future__ import annotations

import logging
from datetime import datetime, timezone

from .alerts.dedup import should_alert
from .alerts.telegram import TelegramAlerter
from .config import AppConfig, Secrets, load_config, load_secrets
from .db.models import (
    FareSnapshotRecord,
    connect,
    get_last_alert_price,
    get_or_create_route,
    get_price_history_brl,
    insert_snapshot,
    record_alert,
)
from .deals.detector import DealType, evaluate_price
from .providers.travelpayouts import TravelpayoutsProvider

log = logging.getLogger(__name__)


def run_scan(config: AppConfig | None = None, secrets: Secrets | None = None) -> None:
    config = config or load_config()
    secrets = secrets or load_secrets()

    conn = connect(secrets.database_path)
    provider = TravelpayoutsProvider(secrets.travelpayouts_token, secrets.travelpayouts_marker)
    alerter = TelegramAlerter(secrets.telegram_bot_token, secrets.telegram_chat_id) if config.alerts.telegram_enabled else None

    summary_lines: list[str] = []

    for entry in config.watchlist:
        route_id = get_or_create_route(conn, entry.origin, entry.destination, entry.cabin)
        fares = provider.search(
            origin=entry.origin,
            destination=entry.destination,
            date_from=entry.date_window.start,
            date_to=entry.date_window.end,
            trip_length_days=tuple(entry.trip_length_days),
            cabin=entry.cabin,
        )
        log.info("route=%s-%s fares_found=%d", entry.origin, entry.destination, len(fares))

        for fare in fares:
            fetched_at = datetime.now(timezone.utc).isoformat()

            history = get_price_history_brl(conn, route_id, config.deal_detection.rolling_window_days)

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
            )

            if evaluation.deal_type == DealType.NONE:
                continue

            last_alert_price = get_last_alert_price(conn, route_id, fare.depart_date, fare.return_date)
            if not should_alert(fare.price_brl, last_alert_price):
                continue

            if alerter:
                alerter.send_deal_alert(
                    deal_type=evaluation.deal_type,
                    origin=fare.origin,
                    destination=fare.destination,
                    depart_date=fare.depart_date,
                    return_date=fare.return_date,
                    price_brl=fare.price_brl,
                    discount_pct=evaluation.discount_pct or 0.0,
                    source=fare.source,
                    booking_link=fare.booking_link,
                )
            record_alert(
                conn,
                route_id,
                fare.depart_date,
                fare.return_date,
                fare.price_brl,
                evaluation.deal_type.value,
                fetched_at,
            )
            summary_lines.append(
                f"{fare.origin}->{fare.destination} {fare.depart_date}: R$ {fare.price_brl:,.2f} "
                f"({evaluation.discount_pct:.0f}% below median)"
            )

    if alerter and config.alerts.daily_summary and summary_lines:
        alerter.send_daily_summary(summary_lines)

    conn.close()

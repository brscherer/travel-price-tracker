from datetime import datetime, timedelta, timezone

from travel_tracker.db.models import (
    FareSnapshotRecord,
    connect,
    get_last_alert_price,
    get_or_create_route,
    get_price_history_brl,
    insert_snapshot,
    record_alert,
)


def make_snapshot(route_id, price_brl, fetched_at):
    return FareSnapshotRecord(
        route_id=route_id,
        depart_date="2026-12-01",
        return_date="2026-12-10",
        price=price_brl,
        currency="BRL",
        price_brl=price_brl,
        cabin="economy",
        source="test",
        booking_link=None,
        fetched_at=fetched_at,
    )


def test_get_or_create_route_is_idempotent():
    conn = connect(":memory:")
    id1 = get_or_create_route(conn, "POA", "LIS", "economy")
    id2 = get_or_create_route(conn, "POA", "LIS", "economy")
    assert id1 == id2


def test_price_history_respects_rolling_window():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    now = datetime.now(timezone.utc)

    insert_snapshot(conn, make_snapshot(route_id, 1000.0, (now - timedelta(days=90)).isoformat()))
    insert_snapshot(conn, make_snapshot(route_id, 900.0, (now - timedelta(days=5)).isoformat()))

    history = get_price_history_brl(conn, route_id, rolling_window_days=60, now=now)
    assert history == [900.0]


def test_last_alert_price_roundtrip():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")

    assert get_last_alert_price(conn, route_id, "2026-12-01", "2026-12-10") is None

    record_alert(
        conn, route_id, "2026-12-01", "2026-12-10", 750.0, "hot_deal", datetime.now(timezone.utc).isoformat()
    )

    assert get_last_alert_price(conn, route_id, "2026-12-01", "2026-12-10") == 750.0

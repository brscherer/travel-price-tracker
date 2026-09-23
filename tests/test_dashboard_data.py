from datetime import datetime, timedelta, timezone

from travel_tracker.dashboard import data as dashboard_data
from travel_tracker.db.models import (
    FareSnapshotRecord,
    connect,
    get_or_create_route,
    insert_snapshot,
    record_alert,
    record_promo_alert,
)


def test_load_routes_lists_created_routes():
    conn = connect(":memory:")
    get_or_create_route(conn, "POA", "LIS", "economy")
    get_or_create_route(conn, "POA", "GRU", "economy")

    df = dashboard_data.load_routes(conn)

    assert len(df) == 2
    assert set(df["destination"]) == {"LIS", "GRU"}


def test_load_price_history_respects_days_window():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    now = datetime.now(timezone.utc)

    insert_snapshot(
        conn,
        FareSnapshotRecord(
            route_id=route_id,
            depart_date="2026-12-01",
            return_date="2026-12-10",
            price=1000.0,
            currency="BRL",
            price_brl=1000.0,
            cabin="economy",
            source="test",
            booking_link=None,
            fetched_at=(now - timedelta(days=90)).isoformat(),
        ),
    )
    insert_snapshot(
        conn,
        FareSnapshotRecord(
            route_id=route_id,
            depart_date="2026-12-01",
            return_date="2026-12-10",
            price=800.0,
            currency="BRL",
            price_brl=800.0,
            cabin="economy",
            source="test",
            booking_link=None,
            fetched_at=(now - timedelta(days=5)).isoformat(),
        ),
    )

    df = dashboard_data.load_price_history(conn, route_id, days=60)

    assert len(df) == 1
    assert df.iloc[0]["price_brl"] == 800.0


def test_load_price_history_empty_route_returns_empty_frame():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")

    df = dashboard_data.load_price_history(conn, route_id, days=60)

    assert df.empty


def test_load_recent_deals_within_window():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    now = datetime.now(timezone.utc)

    record_alert(conn, route_id, "2026-12-01", "2026-12-10", 700.0, "hot_deal", (now - timedelta(hours=2)).isoformat())
    record_alert(conn, route_id, "2026-11-01", "2026-11-10", 700.0, "hot_deal", (now - timedelta(hours=48)).isoformat())

    df = dashboard_data.load_recent_deals(conn, hours=24)

    assert len(df) == 1
    assert df.iloc[0]["depart_date"] == "2026-12-01"


def test_load_recent_promos_within_window():
    conn = connect(":memory:")
    now = datetime.now(timezone.utc)

    record_promo_alert(
        conn, "feed_a", "item-1", "promo", (now - timedelta(hours=3)).isoformat(), title="Recent promo", link=""
    )
    record_promo_alert(
        conn, "feed_a", "item-2", "promo", (now - timedelta(hours=72)).isoformat(), title="Old promo", link=""
    )

    df = dashboard_data.load_recent_promos(conn, hours=48)

    assert len(df) == 1
    assert df.iloc[0]["title"] == "Recent promo"


def test_load_recent_promos_null_title_and_link_come_back_as_empty_string():
    # Rows recorded before title/link existed (pre-migration) have NULL
    # there -- pandas would otherwise surface that as NaN, a truthy float
    # that breaks `title or fallback`-style display logic.
    conn = connect(":memory:")
    now = datetime.now(timezone.utc)
    conn.execute(
        "INSERT INTO promo_alerts_sent (source, item_id, alert_type, sent_at) VALUES (?, ?, ?, ?)",
        ("feed_a", "item-legacy", "promo", now.isoformat()),
    )
    conn.commit()

    df = dashboard_data.load_recent_promos(conn, hours=48)

    assert len(df) == 1
    assert df.iloc[0]["title"] == ""
    assert df.iloc[0]["link"] == ""

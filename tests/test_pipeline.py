from datetime import datetime, timedelta, timezone

from travel_tracker.config import AppConfig, DealDetectionConfig
from travel_tracker.db.models import FareSnapshotRecord, connect, get_or_create_route, insert_snapshot
from travel_tracker.pipeline import process_fare
from travel_tracker.providers.base import FareResult


class FakeAlerter:
    def __init__(self):
        self.deal_alerts = []

    def send_deal_alert(self, **kwargs):
        self.deal_alerts.append(kwargs)


class FakeSerpApi:
    def __init__(self, live_price):
        self.live_price = live_price
        self.calls = 0

    def check_price(self, *args, **kwargs):
        self.calls += 1
        return self.live_price


def make_config(**deal_detection_overrides):
    detection = DealDetectionConfig(
        min_snapshots_for_median=3,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
        **deal_detection_overrides,
    )
    return AppConfig(watchlist=[], deal_detection=detection)


def make_fare(price_brl=300.0):
    return FareResult(
        origin="POA",
        destination="LIS",
        depart_date="2026-12-01",
        return_date="2026-12-10",
        price=price_brl,
        currency="BRL",
        price_brl=price_brl,
        cabin="economy",
        source="test",
        booking_link=None,
    )


def seed_history(conn, route_id, prices):
    now = datetime.now(timezone.utc)
    for i, p in enumerate(prices):
        insert_snapshot(
            conn,
            FareSnapshotRecord(
                route_id=route_id,
                depart_date="2026-12-01",
                return_date="2026-12-10",
                price=p,
                currency="BRL",
                price_brl=p,
                cabin="economy",
                source="test",
                booking_link=None,
                fetched_at=(now - timedelta(days=i + 1)).isoformat(),
            ),
        )


def test_hot_deal_alerts_without_live_recheck():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    seed_history(conn, route_id, [1000.0] * 5)

    config = make_config()
    alerter = FakeAlerter()
    serpapi = FakeSerpApi(live_price=700.0)

    summary = process_fare(conn, make_fare(700.0), config, alerter, serpapi)

    assert summary is not None
    assert len(alerter.deal_alerts) == 1
    assert serpapi.calls == 0  # hot deal doesn't need a live recheck


def test_error_fare_confirmed_by_live_recheck():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    seed_history(conn, route_id, [1000.0] * 5)

    config = make_config()
    alerter = FakeAlerter()
    serpapi = FakeSerpApi(live_price=320.0)  # still ~68% below median

    summary = process_fare(conn, make_fare(300.0), config, alerter, serpapi)

    assert summary is not None
    assert serpapi.calls == 1
    assert alerter.deal_alerts[0]["deal_type"].value == "error_fare"
    assert alerter.deal_alerts[0]["price_brl"] == 320.0  # alert carries the live price


def test_error_fare_downgraded_by_live_recheck():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    seed_history(conn, route_id, [1000.0] * 5)

    config = make_config()
    alerter = FakeAlerter()
    serpapi = FakeSerpApi(live_price=950.0)  # real price is barely below median

    summary = process_fare(conn, make_fare(300.0), config, alerter, serpapi)

    assert summary is None
    assert len(alerter.deal_alerts) == 0
    assert serpapi.calls == 1


def test_cleared_error_fare_not_rechecked_again_at_same_cached_price():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    seed_history(conn, route_id, [1000.0] * 5)

    config = make_config()
    alerter = FakeAlerter()
    serpapi = FakeSerpApi(live_price=950.0)

    first = process_fare(conn, make_fare(300.0), config, alerter, serpapi)
    assert first is None
    assert serpapi.calls == 1

    second = process_fare(conn, make_fare(300.0), config, alerter, serpapi)
    assert second is None
    assert serpapi.calls == 1  # already know this cached price is fake


def test_error_fare_alerts_directly_when_no_serpapi_configured():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    seed_history(conn, route_id, [1000.0] * 5)

    config = make_config()
    alerter = FakeAlerter()

    summary = process_fare(conn, make_fare(300.0), config, alerter, serpapi=None)

    assert summary is not None
    assert alerter.deal_alerts[0]["deal_type"].value == "error_fare"
    assert alerter.deal_alerts[0]["price_brl"] == 300.0


def test_repeat_alert_at_same_price_is_deduped():
    conn = connect(":memory:")
    route_id = get_or_create_route(conn, "POA", "LIS", "economy")
    seed_history(conn, route_id, [1000.0] * 5)

    config = make_config()
    alerter = FakeAlerter()

    first = process_fare(conn, make_fare(700.0), config, alerter, serpapi=None)
    second = process_fare(conn, make_fare(700.0), config, alerter, serpapi=None)

    assert first is not None
    assert second is None
    assert len(alerter.deal_alerts) == 1

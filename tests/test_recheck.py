from travel_tracker.deals.detector import DealType
from travel_tracker.deals.recheck import confirm_or_downgrade


def test_confirms_error_fare_when_live_price_still_extreme():
    result = confirm_or_downgrade(
        live_price_brl=320.0,
        cached_price_brl=300.0,
        median_brl=1000.0,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.ERROR_FARE


def test_downgrades_to_hot_deal_when_live_price_is_higher():
    result = confirm_or_downgrade(
        live_price_brl=740.0,
        cached_price_brl=300.0,
        median_brl=1000.0,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.HOT_DEAL


def test_clears_when_live_price_is_not_a_deal_at_all():
    result = confirm_or_downgrade(
        live_price_brl=950.0,
        cached_price_brl=300.0,
        median_brl=1000.0,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.NONE


def test_falls_back_to_cached_price_when_live_check_fails():
    result = confirm_or_downgrade(
        live_price_brl=None,
        cached_price_brl=300.0,
        median_brl=1000.0,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.ERROR_FARE

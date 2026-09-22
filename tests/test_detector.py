from travel_tracker.deals.detector import DealType, evaluate_price


def test_not_enough_history_never_alerts():
    result = evaluate_price(
        price_brl=100.0,
        history_brl=[1000.0, 1000.0],
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.NONE
    assert result.median_brl is None


def test_price_above_threshold_is_not_a_deal():
    history = [1000.0] * 10
    result = evaluate_price(
        price_brl=900.0,  # 10% below median
        history_brl=history,
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.NONE
    assert result.median_brl == 1000.0


def test_hot_deal_threshold():
    history = [1000.0] * 10
    result = evaluate_price(
        price_brl=740.0,  # 26% below median
        history_brl=history,
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.HOT_DEAL
    assert round(result.discount_pct, 1) == 26.0


def test_error_fare_threshold():
    history = [1000.0] * 10
    result = evaluate_price(
        price_brl=400.0,  # 60% below median
        history_brl=history,
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.ERROR_FARE


def test_exact_boundary_counts_as_deal():
    history = [1000.0] * 10
    result = evaluate_price(
        price_brl=750.0,  # exactly 25% below median
        history_brl=history,
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.deal_type == DealType.HOT_DEAL


def test_median_uses_full_history_not_just_recent():
    history = [500.0, 1500.0]  # median = 1000
    result = evaluate_price(
        price_brl=1000.0,
        history_brl=history,
        min_snapshots_for_median=2,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
    )
    assert result.median_brl == 1000.0
    assert result.deal_type == DealType.NONE

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


def test_target_price_fires_without_enough_history():
    result = evaluate_price(
        price_brl=4000.0,
        history_brl=[],  # no median possible yet
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
        max_price_brl=4500.0,
    )
    assert result.deal_type == DealType.TARGET_PRICE
    assert result.median_brl is None
    assert result.discount_pct is None


def test_target_price_does_not_fire_above_cap():
    result = evaluate_price(
        price_brl=5000.0,
        history_brl=[],
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
        max_price_brl=4500.0,
    )
    assert result.deal_type == DealType.NONE


def test_median_deal_wins_over_target_price_when_more_severe():
    history = [1000.0] * 10
    result = evaluate_price(
        price_brl=400.0,  # 60% below median -> error fare, also under cap
        history_brl=history,
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
        max_price_brl=4500.0,
    )
    assert result.deal_type == DealType.ERROR_FARE


def test_target_price_wins_when_price_not_below_median_threshold():
    history = [1000.0] * 10
    result = evaluate_price(
        price_brl=900.0,  # only 10% below median -> not a median-based deal
        history_brl=history,
        min_snapshots_for_median=10,
        hot_deal_discount_pct=25,
        error_fare_discount_pct=50,
        max_price_brl=950.0,  # but under the absolute cap
    )
    assert result.deal_type == DealType.TARGET_PRICE
    assert result.median_brl == 1000.0

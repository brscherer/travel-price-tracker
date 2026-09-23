from __future__ import annotations

from .detector import DealEvaluation, DealType


def confirm_or_downgrade(
    live_price_brl: float | None,
    cached_price_brl: float,
    median_brl: float,
    hot_deal_discount_pct: float,
    error_fare_discount_pct: float,
) -> DealEvaluation:
    """Re-classify a cached ERROR_FARE hit against a live price check.

    Google Flights (via SerpApi) sometimes returns nothing for a given
    itinerary -- when that happens `live_price_brl` is None and this falls
    back to the cached price rather than silently dropping a possible real
    error fare just because the live check itself failed.
    """
    price_to_use = live_price_brl if live_price_brl is not None else cached_price_brl

    if median_brl <= 0:
        return DealEvaluation(DealType.NONE, median_brl, None)

    discount_pct = (median_brl - price_to_use) / median_brl * 100
    if discount_pct >= error_fare_discount_pct:
        deal_type = DealType.ERROR_FARE
    elif discount_pct >= hot_deal_discount_pct:
        deal_type = DealType.HOT_DEAL
    else:
        deal_type = DealType.NONE

    return DealEvaluation(deal_type, median_brl, discount_pct)

from __future__ import annotations

import statistics
from dataclasses import dataclass
from enum import Enum


class DealType(str, Enum):
    NONE = "none"
    TARGET_PRICE = "target_price"
    HOT_DEAL = "hot_deal"
    ERROR_FARE = "error_fare"


_SEVERITY = {
    DealType.NONE: 0,
    DealType.TARGET_PRICE: 1,
    DealType.HOT_DEAL: 2,
    DealType.ERROR_FARE: 3,
}


@dataclass
class DealEvaluation:
    deal_type: DealType
    median_brl: float | None
    discount_pct: float | None


def evaluate_price(
    price_brl: float,
    history_brl: list[float],
    min_snapshots_for_median: int,
    hot_deal_discount_pct: float,
    error_fare_discount_pct: float,
    max_price_brl: float | None = None,
) -> DealEvaluation:
    """Classify a fare against its route's rolling price history, and
    independently against a hard price ceiling.

    Median-relative detection needs at least `min_snapshots_for_median`
    prior snapshots before it will call anything a deal -- otherwise a
    route's first couple of price points would trivially look like a huge
    drop against themselves. `max_price_brl` is an absolute trigger that
    fires regardless of history depth, so a route that's simply always
    worth booking below some price still alerts on day one.

    When both fire, the more severe classification wins (error_fare >
    hot_deal > target_price).
    """
    deal_type = DealType.NONE
    median: float | None = None
    discount_pct: float | None = None

    if len(history_brl) >= min_snapshots_for_median:
        median = statistics.median(history_brl)
        if median > 0:
            discount_pct = (median - price_brl) / median * 100
            if discount_pct >= error_fare_discount_pct:
                deal_type = DealType.ERROR_FARE
            elif discount_pct >= hot_deal_discount_pct:
                deal_type = DealType.HOT_DEAL

    if max_price_brl is not None and price_brl <= max_price_brl:
        if _SEVERITY[DealType.TARGET_PRICE] > _SEVERITY[deal_type]:
            deal_type = DealType.TARGET_PRICE

    return DealEvaluation(deal_type, median, discount_pct)

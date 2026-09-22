from __future__ import annotations

import statistics
from dataclasses import dataclass
from enum import Enum


class DealType(str, Enum):
    NONE = "none"
    HOT_DEAL = "hot_deal"
    ERROR_FARE = "error_fare"


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
) -> DealEvaluation:
    """Classify a fare against its route's rolling price history.

    Needs at least `min_snapshots_for_median` prior snapshots before it will
    call anything a deal -- otherwise a route's first couple of price points
    would trivially look like a huge drop against themselves.
    """
    if len(history_brl) < min_snapshots_for_median:
        return DealEvaluation(DealType.NONE, None, None)

    median = statistics.median(history_brl)
    if median <= 0:
        return DealEvaluation(DealType.NONE, median, None)

    discount_pct = (median - price_brl) / median * 100

    if discount_pct >= error_fare_discount_pct:
        deal_type = DealType.ERROR_FARE
    elif discount_pct >= hot_deal_discount_pct:
        deal_type = DealType.HOT_DEAL
    else:
        deal_type = DealType.NONE

    return DealEvaluation(deal_type, median, discount_pct)

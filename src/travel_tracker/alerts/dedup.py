from __future__ import annotations


def should_alert(price_brl: float, last_alert_price_brl: float | None) -> bool:
    """Only alert if this is the first alert for the itinerary, or the price
    has dropped further since the last alert. Prevents repeat pings for a
    price that's just holding steady at a already-alerted level.
    """
    if last_alert_price_brl is None:
        return True
    return price_brl < last_alert_price_brl

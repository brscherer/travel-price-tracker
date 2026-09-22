from travel_tracker.alerts.dedup import should_alert


def test_first_alert_always_fires():
    assert should_alert(price_brl=1000.0, last_alert_price_brl=None) is True


def test_same_price_does_not_realert():
    assert should_alert(price_brl=1000.0, last_alert_price_brl=1000.0) is False


def test_higher_price_does_not_realert():
    assert should_alert(price_brl=1100.0, last_alert_price_brl=1000.0) is False


def test_lower_price_realerts():
    assert should_alert(price_brl=900.0, last_alert_price_brl=1000.0) is True

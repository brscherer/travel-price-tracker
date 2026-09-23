from travel_tracker.config import PromosConfig
from travel_tracker.db.models import connect
from travel_tracker.promos.models import PromoItem
from travel_tracker.promos.pipeline import process_promo_item


class FakeAlerter:
    def __init__(self):
        self.promo_alerts = []

    def send_promo_alert(self, label, title, link, source, note=None):
        self.promo_alerts.append((label, title, link, source, note))


def make_config(**overrides):
    base = dict(keywords=["Porto Alegre", "POA"], transfer_bonus_min_pct=80.0)
    base.update(overrides)
    return PromosConfig(**base)


def make_item(item_id="item-1", title="Passagem POA em promoção", summary="Detalhes da promoção"):
    return PromoItem(
        source="test_feed",
        item_id=item_id,
        title=title,
        link="https://example.com/" + item_id,
        summary=summary,
        published_at=None,
    )


def test_keyword_match_alerts_as_promo():
    conn = connect(":memory:")
    config = make_config()
    alerter = FakeAlerter()

    summary = process_promo_item(conn, make_item(), config, alerter)

    assert summary is not None
    assert len(alerter.promo_alerts) == 1
    assert alerter.promo_alerts[0][0] == "Promo"


def test_transfer_bonus_alerts_and_beats_keyword_match():
    conn = connect(":memory:")
    config = make_config()
    alerter = FakeAlerter()
    item = make_item(title="Porto Alegre bônus", summary="Bônus de 100% Livelo para Smiles")

    summary = process_promo_item(conn, item, config, alerter)

    assert summary is not None
    assert alerter.promo_alerts[0][0] == "Transfer bonus"


def test_transfer_bonus_below_threshold_falls_back_to_keyword_check():
    conn = connect(":memory:")
    config = make_config(transfer_bonus_min_pct=80.0)
    alerter = FakeAlerter()
    item = make_item(title="Porto Alegre bônus", summary="Bônus de 50% Livelo para Smiles")

    summary = process_promo_item(conn, item, config, alerter)

    assert summary is not None
    assert alerter.promo_alerts[0][0] == "Promo"  # bonus too small, but keyword still matches


def test_miles_sale_alerts():
    conn = connect(":memory:")
    config = make_config(keywords=[])  # no keyword relevance, only the sale rule should fire
    alerter = FakeAlerter()
    item = make_item(title="Compra de milhas Smiles", summary="Desconto especial hoje")

    summary = process_promo_item(conn, item, config, alerter)

    assert summary is not None
    assert alerter.promo_alerts[0][0] == "Miles sale"


def test_no_match_does_not_alert():
    conn = connect(":memory:")
    config = make_config(keywords=["Porto Alegre"])
    alerter = FakeAlerter()
    item = make_item(title="Passagem para Rio de Janeiro", summary="Sem relação com POA")

    summary = process_promo_item(conn, item, config, alerter)

    assert summary is None
    assert len(alerter.promo_alerts) == 0


def test_same_item_never_alerts_twice():
    conn = connect(":memory:")
    config = make_config()
    alerter = FakeAlerter()
    item = make_item()

    first = process_promo_item(conn, item, config, alerter)
    second = process_promo_item(conn, item, config, alerter)

    assert first is not None
    assert second is None
    assert len(alerter.promo_alerts) == 1

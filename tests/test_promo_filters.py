from travel_tracker.promos.filters import extract_transfer_bonus_pct, is_miles_sale, matches_keywords


def test_matches_keywords_case_insensitive():
    assert matches_keywords("Promoção para Porto Alegre!", ["porto alegre"]) is True


def test_matches_keywords_no_hit():
    assert matches_keywords("Promoção para Rio de Janeiro", ["Porto Alegre", "POA"]) is False


def test_matches_keywords_ignores_blank_entries():
    assert matches_keywords("anything", ["", None]) is False


def test_extract_transfer_bonus_requires_bonus_word():
    assert extract_transfer_bonus_pct("Desconto de 80% nas passagens") is None


def test_extract_transfer_bonus_finds_percentage():
    assert extract_transfer_bonus_pct("Bônus de 100% Livelo para Smiles") == 100


def test_extract_transfer_bonus_picks_highest_when_range_given():
    assert extract_transfer_bonus_pct("Bônus de 80% a 120% na transferência") == 120


def test_extract_transfer_bonus_no_percentage_present():
    assert extract_transfer_bonus_pct("Bônus imperdível chegando em breve") is None


def test_is_miles_sale_detects_portuguese_keyword():
    assert is_miles_sale("Compra de milhas Smiles com desconto") is True


def test_is_miles_sale_no_match():
    assert is_miles_sale("Passagem promocional para Lisboa") is False

from __future__ import annotations

import re

_BONUS_RE = re.compile(r"(\d{2,3})\s*%")

_MILES_SALE_KEYWORDS = (
    "compra de milhas",
    "compre milhas",
    "comprar milhas",
    "miles sale",
    "buy miles",
)


def matches_keywords(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in keywords if kw)


def extract_transfer_bonus_pct(text: str) -> int | None:
    """Best-effort extraction of a transfer-bonus percentage from Portuguese
    promo text. This is a heuristic, not a guarantee -- it looks for a
    percentage figure only when the word "bonus"/"bônus" also appears
    anywhere in the text, and returns the highest percentage found (posts
    sometimes list a range, e.g. "de 80% a 100%").
    """
    lowered = text.lower()
    if "bônus" not in lowered and "bonus" not in lowered:
        return None
    matches = _BONUS_RE.findall(text)
    if not matches:
        return None
    return max(int(m) for m in matches)


def is_miles_sale(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in _MILES_SALE_KEYWORDS)

from __future__ import annotations

import logging
from datetime import date, datetime

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import FareResult, Provider

log = logging.getLogger(__name__)

_BASE_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


class TravelpayoutsProvider(Provider):
    """Cached cheap-fare search via the Travelpayouts Data API.

    Docs: https://support.travelpayouts.com/hc/en-us/articles/203956163
    Not a live-pricing source -- results are cached by Travelpayouts and can
    lag actual airline prices, which is why flagged deals get a live re-check
    against SerpApi in a later phase.
    """

    name = "travelpayouts"

    def __init__(self, token: str, marker: str):
        self.token = token
        self.marker = marker

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _fetch(self, params: dict) -> dict:
        resp = requests.get(_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def search(
        self,
        origin: str,
        destination: str,
        date_from: str,
        date_to: str,
        trip_length_days: tuple[int, int],
        cabin: str,
    ) -> list[FareResult]:
        params = {
            "origin": origin,
            "destination": destination,
            "currency": "brl",
            "one_way": "false",
            "sorting": "price",
            "direct": "false",
            "limit": 200,
            "token": self.token,
            "marker": self.marker,
        }
        try:
            payload = self._fetch(params)
        except requests.RequestException:
            log.exception("Travelpayouts request failed for %s-%s", origin, destination)
            return []

        if not payload.get("success", False):
            log.warning("Travelpayouts returned success=false for %s-%s: %s", origin, destination, payload)
            return []

        window_start = date.fromisoformat(date_from)
        window_end = date.fromisoformat(date_to)
        min_len, max_len = trip_length_days

        results: list[FareResult] = []
        for item in payload.get("data", []):
            depart_at = item.get("departure_at")
            return_at = item.get("return_at")
            if not depart_at:
                continue
            depart_date = datetime.fromisoformat(depart_at).date()
            if not (window_start <= depart_date <= window_end):
                continue
            if return_at:
                return_date = datetime.fromisoformat(return_at).date()
                trip_len = (return_date - depart_date).days
                if not (min_len <= trip_len <= max_len):
                    continue
            else:
                return_date = None

            price = float(item["price"])
            results.append(
                FareResult(
                    origin=origin,
                    destination=destination,
                    depart_date=depart_date.isoformat(),
                    return_date=return_date.isoformat() if return_date else None,
                    price=price,
                    currency="BRL",
                    price_brl=price,
                    cabin=cabin,
                    source=self.name,
                    booking_link=self._booking_link(item),
                )
            )
        return results

    @staticmethod
    def _booking_link(item: dict) -> str | None:
        link = item.get("link")
        if not link:
            return None
        return f"https://www.aviasales.com{link}" if link.startswith("/") else link

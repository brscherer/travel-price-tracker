from __future__ import annotations

import logging
from datetime import date, datetime

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import FareResult, Provider

log = logging.getLogger(__name__)

_SEARCH_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
_ANYWHERE_URL = "https://api.travelpayouts.com/v1/city-directions"


class TravelpayoutsProvider(Provider):
    """Cached cheap-fare search via the Travelpayouts Data API.

    Docs: https://support.travelpayouts.com/hc/en-us/articles/203956163
    Not a live-pricing source -- results are cached by Travelpayouts and can
    lag actual airline prices, which is why flagged possible error fares get
    a live re-check against SerpApi before alerting.
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
    def _get(self, url: str, params: dict) -> dict:
        resp = requests.get(url, params=params, timeout=15)
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
            payload = self._get(_SEARCH_URL, params)
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

    def wide_scan(self, origin: str, cabin: str = "economy") -> list[FareResult]:
        """'POA to anywhere' scan: cheapest cached fare per destination from
        `origin`, across every destination Travelpayouts has cached data for.
        One API call covers ~hundreds of destinations, which is what makes
        this cheap enough to run alongside the per-route watchlist scan.
        """
        params = {"origin": origin, "currency": "brl", "token": self.token}
        try:
            payload = self._get(_ANYWHERE_URL, params)
        except requests.RequestException:
            log.exception("Travelpayouts wide scan request failed for origin=%s", origin)
            return []

        if not payload.get("success", False):
            log.warning("Travelpayouts wide scan returned success=false for origin=%s: %s", origin, payload)
            return []

        data = payload.get("data", {})
        entries = data.values() if isinstance(data, dict) else data

        results: list[FareResult] = []
        for item in entries:
            destination = item.get("destination")
            depart_at = item.get("departure_at")
            if not destination or not depart_at:
                continue
            depart_date = datetime.fromisoformat(depart_at).date()
            return_at = item.get("return_at")
            return_date = datetime.fromisoformat(return_at).date() if return_at else None

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
                    source="travelpayouts_wide",
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

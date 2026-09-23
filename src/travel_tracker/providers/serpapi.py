from __future__ import annotations

import logging

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

_URL = "https://serpapi.com/search"

_TRAVEL_CLASS = {
    "economy": "1",
    "premium_economy": "2",
    "business": "3",
    "first": "4",
}


class SerpApiProvider:
    """Live Google Flights price check via SerpApi, used only to confirm or
    clear a possible error fare flagged from cached Travelpayouts data --
    not a general search source (paid API, kept to a handful of calls).
    """

    name = "serpapi"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _fetch(self, params: dict) -> dict:
        resp = requests.get(_URL, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def check_price(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: str | None,
        cabin: str = "economy",
    ) -> float | None:
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": depart_date,
            "currency": "BRL",
            "hl": "en",
            "travel_class": _TRAVEL_CLASS.get(cabin, "1"),
            "api_key": self.api_key,
        }
        if return_date:
            params["return_date"] = return_date
        else:
            params["type"] = "2"  # one-way

        try:
            payload = self._fetch(params)
        except requests.RequestException:
            log.exception("SerpApi request failed for %s-%s %s", origin, destination, depart_date)
            return None

        if "error" in payload:
            log.warning("SerpApi error for %s-%s %s: %s", origin, destination, depart_date, payload["error"])
            return None

        flights = (payload.get("best_flights") or []) + (payload.get("other_flights") or [])
        prices = [f["price"] for f in flights if isinstance(f.get("price"), (int, float))]
        if not prices:
            log.info("SerpApi returned no priced flights for %s-%s %s", origin, destination, depart_date)
            return None
        return float(min(prices))

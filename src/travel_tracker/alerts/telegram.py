from __future__ import annotations

import logging

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..deals.detector import DealType

log = logging.getLogger(__name__)

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

_PRIORITY_EMOJI = {
    DealType.HOT_DEAL: "\U0001f525",  # fire
    DealType.ERROR_FARE: "\U0001f6a8",  # rotating light
}


class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def send(self, text: str) -> None:
        url = _API_URL.format(token=self.bot_token)
        resp = requests.post(
            url,
            json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
        resp.raise_for_status()

    def send_deal_alert(
        self,
        deal_type: DealType,
        origin: str,
        destination: str,
        depart_date: str,
        return_date: str | None,
        price_brl: float,
        discount_pct: float,
        source: str,
        booking_link: str | None,
    ) -> None:
        emoji = _PRIORITY_EMOJI.get(deal_type, "")
        label = "ERROR FARE?" if deal_type == DealType.ERROR_FARE else "Hot deal"
        dates = f"{depart_date} -> {return_date}" if return_date else depart_date
        lines = [
            f"{emoji} <b>{label}</b>: {origin} -> {destination}",
            f"Dates: {dates}",
            f"Price: R$ {price_brl:,.2f} ({discount_pct:.0f}% below median)",
            f"Source: {source}",
        ]
        if booking_link:
            lines.append(booking_link)
        self.send("\n".join(lines))

    def send_daily_summary(self, lines: list[str]) -> None:
        if not lines:
            self.send("Daily summary: no deals today.")
            return
        self.send("Daily summary:\n" + "\n".join(lines))

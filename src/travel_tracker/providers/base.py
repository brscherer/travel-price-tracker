from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FareResult:
    """A single normalized fare quote from a provider."""

    origin: str
    destination: str
    depart_date: str  # YYYY-MM-DD
    return_date: str | None
    price: float
    currency: str
    price_brl: float
    cabin: str
    source: str
    booking_link: str | None


class Provider(ABC):
    """Common interface every fare data source must implement."""

    name: str

    @abstractmethod
    def search(
        self,
        origin: str,
        destination: str,
        date_from: str,
        date_to: str,
        trip_length_days: tuple[int, int],
        cabin: str,
    ) -> list[FareResult]:
        """Return normalized fare results for the given route and date window."""
        raise NotImplementedError

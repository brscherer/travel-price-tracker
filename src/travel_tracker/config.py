from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class DateWindow(BaseModel):
    start: str
    end: str


class WatchlistEntry(BaseModel):
    origin: str
    destination: str
    date_window: DateWindow
    trip_length_days: list[int] = Field(min_length=2, max_length=2)
    cabin: str = "economy"
    max_price_brl: float


class DealDetectionConfig(BaseModel):
    min_snapshots_for_median: int = 10
    rolling_window_days: int = 60
    hot_deal_discount_pct: float = 25.0
    error_fare_discount_pct: float = 50.0


class ScanConfig(BaseModel):
    cadence_hours: int = 6


class AlertsConfig(BaseModel):
    telegram_enabled: bool = True
    daily_summary: bool = True
    daily_summary_time: str = "08:00"


class AppConfig(BaseModel):
    timezone: str = "America/Sao_Paulo"
    currency: str = "BRL"
    watchlist: list[WatchlistEntry]
    deal_detection: DealDetectionConfig = DealDetectionConfig()
    scan: ScanConfig = ScanConfig()
    miles_programs: list[dict] = []
    alerts: AlertsConfig = AlertsConfig()


class Secrets(BaseModel):
    travelpayouts_token: str
    travelpayouts_marker: str
    telegram_bot_token: str
    telegram_chat_id: str
    database_path: str = "data/tracker.db"


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig.model_validate(raw)


def load_secrets() -> Secrets:
    return Secrets(
        travelpayouts_token=os.environ.get("TRAVELPAYOUTS_TOKEN", ""),
        travelpayouts_marker=os.environ.get("TRAVELPAYOUTS_MARKER", ""),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        database_path=os.environ.get("DATABASE_PATH") or "data/tracker.db",
    )

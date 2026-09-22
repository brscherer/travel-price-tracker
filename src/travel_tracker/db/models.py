from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def get_or_create_route(conn: sqlite3.Connection, origin: str, destination: str, cabin: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO routes (origin, destination, cabin) VALUES (?, ?, ?)",
        (origin, destination, cabin),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM routes WHERE origin = ? AND destination = ? AND cabin = ?",
        (origin, destination, cabin),
    ).fetchone()
    return row["id"]


@dataclass
class FareSnapshotRecord:
    route_id: int
    depart_date: str
    return_date: str | None
    price: float
    currency: str
    price_brl: float
    cabin: str
    source: str
    booking_link: str | None
    fetched_at: str


def insert_snapshot(conn: sqlite3.Connection, snap: FareSnapshotRecord) -> int:
    cur = conn.execute(
        """
        INSERT INTO fare_snapshots
            (route_id, depart_date, return_date, price, currency, price_brl,
             cabin, source, booking_link, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snap.route_id,
            snap.depart_date,
            snap.return_date,
            snap.price,
            snap.currency,
            snap.price_brl,
            snap.cabin,
            snap.source,
            snap.booking_link,
            snap.fetched_at,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_price_history_brl(
    conn: sqlite3.Connection, route_id: int, rolling_window_days: int, now: datetime | None = None
) -> list[float]:
    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=rolling_window_days)).isoformat()
    rows = conn.execute(
        "SELECT price_brl FROM fare_snapshots WHERE route_id = ? AND fetched_at >= ?",
        (route_id, cutoff),
    ).fetchall()
    return [r["price_brl"] for r in rows]


def get_last_alert_price(
    conn: sqlite3.Connection, route_id: int, depart_date: str, return_date: str | None
) -> float | None:
    row = conn.execute(
        """
        SELECT price_brl FROM alerts_sent
        WHERE route_id = ? AND depart_date = ? AND (return_date IS ? OR return_date = ?)
        ORDER BY sent_at DESC LIMIT 1
        """,
        (route_id, depart_date, return_date, return_date),
    ).fetchone()
    return row["price_brl"] if row else None


def record_alert(
    conn: sqlite3.Connection,
    route_id: int,
    depart_date: str,
    return_date: str | None,
    price_brl: float,
    alert_type: str,
    sent_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO alerts_sent (route_id, depart_date, return_date, price_brl, alert_type, sent_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (route_id, depart_date, return_date, price_brl, alert_type, sent_at),
    )
    conn.commit()

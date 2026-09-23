from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: Streamlit can rerun a script on a different
    # thread than the one that created a cached (st.cache_resource)
    # connection. Access here is still sequential (one script run at a
    # time per session), never truly concurrent, so this is safe.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent column additions for tables that already existed before
    the column was introduced -- `CREATE TABLE IF NOT EXISTS` in schema.sql
    doesn't touch a table that's already there.
    """
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(promo_alerts_sent)")}
    if "title" not in existing_cols:
        conn.execute("ALTER TABLE promo_alerts_sent ADD COLUMN title TEXT")
    if "link" not in existing_cols:
        conn.execute("ALTER TABLE promo_alerts_sent ADD COLUMN link TEXT")
    conn.commit()


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


def promo_already_alerted(conn: sqlite3.Connection, source: str, item_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM promo_alerts_sent WHERE source = ? AND item_id = ?",
        (source, item_id),
    ).fetchone()
    return row is not None


def record_promo_alert(
    conn: sqlite3.Connection,
    source: str,
    item_id: str,
    alert_type: str,
    sent_at: str,
    title: str = "",
    link: str = "",
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO promo_alerts_sent (source, item_id, alert_type, sent_at, title, link)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source, item_id, alert_type, sent_at, title, link),
    )
    conn.commit()

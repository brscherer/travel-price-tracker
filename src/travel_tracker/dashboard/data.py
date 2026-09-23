from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pandas as pd

# Pure, connection-in/DataFrame-out query functions -- kept separate from
# app.py so they're testable without a Streamlit runtime.


def load_routes(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT id, origin, destination, cabin FROM routes ORDER BY origin, destination", conn)


def load_price_history(conn: sqlite3.Connection, route_id: int, days: int = 90) -> pd.DataFrame:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    df = pd.read_sql_query(
        """
        SELECT fetched_at, price_brl, depart_date, return_date, source
        FROM fare_snapshots
        WHERE route_id = ? AND fetched_at >= ?
        ORDER BY fetched_at
        """,
        conn,
        params=(route_id, cutoff),
    )
    if df.empty:
        return df
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])
    df["date"] = df["fetched_at"].dt.date
    return df


def load_recent_deals(conn: sqlite3.Connection, hours: int = 24) -> pd.DataFrame:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return pd.read_sql_query(
        """
        SELECT a.sent_at, r.origin, r.destination, r.cabin, a.depart_date, a.return_date,
               a.price_brl, a.alert_type
        FROM alerts_sent a
        JOIN routes r ON r.id = a.route_id
        WHERE a.sent_at >= ?
        ORDER BY a.sent_at DESC
        """,
        conn,
        params=(cutoff,),
    )


def load_recent_promos(conn: sqlite3.Connection, hours: int = 48) -> pd.DataFrame:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return pd.read_sql_query(
        """
        SELECT sent_at, source, alert_type, COALESCE(title, '') AS title, COALESCE(link, '') AS link
        FROM promo_alerts_sent
        WHERE sent_at >= ?
        ORDER BY sent_at DESC
        """,
        conn,
        params=(cutoff,),
    )

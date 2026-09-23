CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    cabin TEXT NOT NULL DEFAULT 'economy',
    UNIQUE(origin, destination, cabin)
);

CREATE TABLE IF NOT EXISTS fare_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL REFERENCES routes(id),
    depart_date TEXT NOT NULL,
    return_date TEXT,
    price REAL NOT NULL,
    currency TEXT NOT NULL,
    price_brl REAL NOT NULL,
    cabin TEXT NOT NULL,
    source TEXT NOT NULL,
    booking_link TEXT,
    fetched_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_route_date
    ON fare_snapshots(route_id, depart_date);

CREATE TABLE IF NOT EXISTS alerts_sent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL REFERENCES routes(id),
    depart_date TEXT NOT NULL,
    return_date TEXT,
    price_brl REAL NOT NULL,
    alert_type TEXT NOT NULL,
    sent_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_route_date
    ON alerts_sent(route_id, depart_date, return_date);

CREATE TABLE IF NOT EXISTS promo_alerts_sent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    item_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    title TEXT,
    link TEXT,
    UNIQUE(source, item_id)
);

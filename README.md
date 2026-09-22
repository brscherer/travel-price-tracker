# travel-price-tracker

Personal flight-deal tracker for departures from Porto Alegre (POA). Phase 1:
watchlist cash-fare tracking via Travelpayouts, rolling-median deal
detection, Telegram alerts, SQLite storage.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# fill in TRAVELPAYOUTS_TOKEN, TRAVELPAYOUTS_MARKER, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

Accounts needed:

- **Travelpayouts** (travelpayouts.com) -- free signup, gives an API token
  and an affiliate marker. Used for cached cheap-fare search
  (`aviasales/v3/prices_for_dates`).
- **Telegram bot** -- create one via [@BotFather](https://t.me/BotFather),
  copy the bot token. Message the bot once, then hit
  `https://api.telegram.org/bot<TOKEN>/getUpdates` to read off your chat id.

Edit `config.yaml` to change the watchlist, date windows, cabin, and
deal-detection thresholds.

## Run a scan

```bash
python -m travel_tracker scan
```

Reads `config.yaml`, fetches fares for each watchlist route, stores a
snapshot per fare in SQLite (`data/tracker.db` by default), compares each
price against that route's rolling median, and sends a Telegram alert for
any hot deal (>=25% below median, configurable) or possible error fare
(>=50% below median). Same price never alerts twice -- only a further drop
re-alerts. A summary message goes out at the end of a scan if any deals
fired.

## Tests

```bash
pytest
```

Covers deal-detection thresholds (`tests/test_detector.py`), alert dedup
(`tests/test_dedup.py`), and the SQLite helpers (`tests/test_db.py`).

## Scheduling

### Option A: cron (local machine)

```cron
0 */6 * * * cd /path/to/travel-price-tracker && /path/to/venv/bin/python -m travel_tracker scan >> scan.log 2>&1
```

### Option B: GitHub Actions

`.github/workflows/scan.yml` runs every 6 hours via `workflow_dispatch` +
`schedule`. Add these repo secrets (Settings -> Secrets and variables ->
Actions): `TRAVELPAYOUTS_TOKEN`, `TRAVELPAYOUTS_MARKER`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. The SQLite file is persisted
between runs via `actions/cache` (keyed off `data/tracker.db`) rather than
committed to the repo -- simplest option for a personal project, though the
cache can be evicted after ~7 days of no runs, which would reset price
history. Swap in Postgres/Supabase later if that matters.

## Notes / limitations (Phase 1)

- Travelpayouts fares are cached, not live -- can lag real airline prices.
  Live re-check via SerpApi for flagged deals is Phase 2.
- Daily summary currently fires at the end of any scan that found deals,
  not on a fixed daily schedule -- a dedicated once-a-day job is a small
  follow-up once Phase 2/3 land.
- Award/miles tracking (Smiles, LATAM Pass, Azul Fidelidade, Livelo/Esfera
  transfer bonuses) and RSS/Telegram-channel promo scanning are Phase 3.
- Dashboard is Phase 4.

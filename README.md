# travel-price-tracker

Personal flight-deal tracker for departures from Porto Alegre (POA).

- **Phase 1**: watchlist cash-fare tracking via Travelpayouts, rolling-median
  deal detection, Telegram alerts, SQLite storage.
- **Phase 2**: "POA to anywhere" wide scan, plus a live re-check via SerpApi
  before alerting on a possible error fare.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# fill in TRAVELPAYOUTS_TOKEN, TRAVELPAYOUTS_MARKER, TELEGRAM_BOT_TOKEN,
# TELEGRAM_CHAT_ID, and (optional) SERPAPI_KEY
```

Accounts needed:

- **Travelpayouts** (travelpayouts.com) -- free signup, gives an API token
  and an affiliate marker. Used for cached cheap-fare search
  (`aviasales/v3/prices_for_dates`) and the wide "anywhere" scan
  (`v1/city-directions`).
- **Telegram bot** -- create one via [@BotFather](https://t.me/BotFather),
  copy the bot token. Message the bot once, then hit
  `https://api.telegram.org/bot<TOKEN>/getUpdates` to read off your chat id.
- **SerpApi** (serpapi.com) -- optional. Only called to live-recheck a fare
  already classified as a possible error fare (>=50% below median), so a
  personal-project free/low tier is enough. Without a key, error fares still
  alert straight off cached Travelpayouts data (Phase 1 behavior).

Edit `config.yaml` to change the watchlist, date windows, cabin, and
deal-detection thresholds.

## Run a scan

```bash
python -m travel_tracker scan       # watchlist routes
python -m travel_tracker wide-scan  # POA -> anywhere
```

`scan` reads the watchlist in `config.yaml`, fetches fares per route, stores
a snapshot per fare in SQLite (`data/tracker.db` by default), and classifies
each price. `wide-scan` does the same but pulls the cheapest cached fare to
every destination Travelpayouts has data for from POA in a single API call,
to catch drops on routes you're not explicitly watching.

Both share the same detection pipeline (`pipeline.process_fare`):

- **Hot deal**: price >=25% below the route's rolling median (needs 10+
  prior snapshots; configurable).
- **Possible error fare**: >=50% below median. If `SERPAPI_KEY` is set, this
  triggers an immediate live Google Flights price check before alerting --
  if the live price no longer clears the threshold, the alert is downgraded
  or dropped instead of sending a false positive.
- **Target price**: price at or below a watchlist entry's `max_price_brl`,
  fires even before there's enough history for a median (watchlist only --
  wide scan has no per-route cap).
- Same price (cached or live) never alerts twice; only a further drop
  re-alerts. A cleared error fare is remembered too, so a stale cached price
  that already failed a live re-check isn't rechecked again on every run.

A summary message goes out at the end of a scan if any deals fired.

## Tests

```bash
pytest
```

- `test_detector.py` -- median/target-price classification thresholds
- `test_recheck.py` -- live re-check confirm/downgrade/clear logic
- `test_pipeline.py` -- end-to-end snapshot/classify/recheck/dedup/alert flow
- `test_dedup.py`, `test_db.py` -- alert dedup and SQLite helpers

## Scheduling

### Option A: cron (local machine)

```cron
0 */6 * * * cd /path/to/travel-price-tracker && /path/to/venv/bin/python -m travel_tracker scan >> scan.log 2>&1
30 6 * * *  cd /path/to/travel-price-tracker && /path/to/venv/bin/python -m travel_tracker wide-scan >> wide_scan.log 2>&1
```

### Option B: GitHub Actions

`.github/workflows/scan.yml` runs the watchlist scan every 6 hours;
`.github/workflows/wide_scan.yml` runs the wide scan once a day (heavier,
less time-sensitive). Both trigger on `workflow_dispatch` too. Add these
repo secrets (Settings -> Secrets and variables -> Actions):
`TRAVELPAYOUTS_TOKEN`, `TRAVELPAYOUTS_MARKER`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`, `SERPAPI_KEY` (optional). The SQLite file is persisted
between runs via `actions/cache` (keyed off `data/tracker.db`) rather than
committed to the repo -- simplest option for a personal project, though the
cache can be evicted after ~7 days of no runs, which would reset price
history. Swap in Postgres/Supabase later if that matters.

## Notes / limitations

- Travelpayouts fares are cached, not live -- can lag real airline prices.
  That's why error fares get a live SerpApi re-check when a key is set.
- Daily summary currently fires at the end of any scan that found deals,
  not on a fixed daily schedule -- a dedicated once-a-day job is a small
  follow-up.
- Award/miles tracking (Smiles, LATAM Pass, Azul Fidelidade, Livelo/Esfera
  transfer bonuses) and RSS/Telegram-channel promo scanning are Phase 3.
- Dashboard is Phase 4.

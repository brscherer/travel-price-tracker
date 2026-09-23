# travel-price-tracker

Personal flight-deal tracker for departures from Porto Alegre (POA).

- **Phase 1**: watchlist cash-fare tracking via Travelpayouts, rolling-median
  deal detection, Telegram alerts, SQLite storage.
- **Phase 2**: "POA to anywhere" wide scan, plus a live re-check via SerpApi
  before alerting on a possible error fare.
- **Phase 3**: promo feeds (RSS + optional Telegram channel monitoring),
  transfer-bonus and miles-sale detection. Award/miles availability tracking
  (seats.aero) is deferred -- see below.
- **Phase 4**: local Streamlit dashboard -- price charts per route, today's
  deals, active promos.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# fill in TRAVELPAYOUTS_TOKEN, TRAVELPAYOUTS_MARKER, TELEGRAM_BOT_TOKEN,
# TELEGRAM_CHAT_ID, and (optional) SERPAPI_KEY, TELEGRAM_API_ID/HASH
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
- **Telethon API credentials** (my.telegram.org) -- optional, only needed
  for public Telegram channel monitoring. See "Telegram channel monitoring"
  below.

Edit `config.yaml` to change the watchlist, date windows, cabin,
deal-detection thresholds, and promo feeds/keywords.

## Run a scan

```bash
python -m travel_tracker scan        # watchlist routes
python -m travel_tracker wide-scan   # POA -> anywhere
python -m travel_tracker promo-scan  # RSS + Telegram channel promos
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

`promo-scan` reads each feed in `promos.rss_feeds`, plus any Telegram
channels configured under `promos.telegram_channels` (see below), and
classifies every item via `promos.pipeline.process_promo_item`:

- **Transfer bonus**: item mentions "bônus"/"bonus" alongside a percentage
  >= `promos.transfer_bonus_min_pct` (default 80). Text-mining heuristic on
  Portuguese blog copy, not a guarantee -- it can miss unusual phrasing.
- **Miles sale**: item mentions buying miles directly (keyword-based).
- **Promo**: item matches any of `promos.keywords` (route/city terms or
  miles-program names) but doesn't clear the above two.
- Same item (by feed + link/guid, or channel + message id) never alerts
  twice, ever -- promos don't have a "further drop" concept the way fares do.

A summary message goes out at the end of each scan type if anything fired.

### Telegram channel monitoring (optional)

Off by default. To enable:

1. Get `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` from
   [my.telegram.org](https://my.telegram.org) -> "API development tools" ->
   create an app. Put them in `.env`.
2. Install the extra: `pip install -e ".[telegram]"`.
3. One-time interactive login (needs your phone + the code Telegram sends
   you -- run this yourself, not from cron/CI):
   ```bash
   python -m travel_tracker.telegram_channels.login
   ```
   This writes a `travel_tracker.session` file -- keep it private, it's
   equivalent to being logged into your Telegram account. Never commit it
   (already gitignored).
4. In `config.yaml`, set `promos.telegram_channels.enabled: true` and list
   public channel usernames under `channels` (no `@`, e.g. `passagensimperdiveis`).
   Only public channels -- no scraping anything behind a login.

Channel monitoring needs that local session file, so it's local-cron-only
for now; it isn't wired into the GitHub Actions workflows (would need a
`StringSession` stored as a secret instead -- a follow-up if useful).

## Dashboard

```bash
pip install -e ".[dashboard]"
python -m travel_tracker dashboard
```

Opens a local Streamlit app (`http://localhost:8501`) reading the same
SQLite database the scans write to -- no separate data layer. Three tabs:

- **Today's deals** -- `alerts_sent` from the last 24h (hot deals, error
  fares, target-price hits), joined with route info.
- **Price charts** -- pick any route that's ever been scanned (watchlist or
  wide-scan-discovered), a line chart of daily minimum cached price over a
  configurable window, plus the raw snapshot table underneath.
- **Active promos** -- `promo_alerts_sent` from the last 48h (transfer
  bonuses, miles sales, general promos), with title/link when available.

Runs read-only against the DB; nothing here writes data. Equivalent to
`streamlit run src/travel_tracker/dashboard/app.py` if you'd rather invoke
Streamlit directly. A `.claude/launch.json` entry is included for previewing
it via Claude Code's browser tooling.

## Tests

```bash
pytest
```

- `test_detector.py` -- median/target-price classification thresholds
- `test_recheck.py` -- live re-check confirm/downgrade/clear logic
- `test_pipeline.py` -- end-to-end fare snapshot/classify/recheck/dedup/alert flow
- `test_promo_filters.py` -- transfer-bonus/miles-sale/keyword text matching
- `test_rss_parse.py` -- RSS feed parsing
- `test_promo_pipeline.py` -- promo classify/dedup/alert flow
- `test_dashboard_data.py` -- dashboard query functions (routes, price
  history, recent deals/promos, including the NULL-vs-empty-string case for
  pre-Phase-4 promo rows)
- `test_dedup.py`, `test_db.py` -- alert dedup and SQLite helpers

## Scheduling

### Option A: cron (local machine)

```cron
0 */6 * * *  cd /path/to/travel-price-tracker && /path/to/venv/bin/python -m travel_tracker scan >> scan.log 2>&1
30 6 * * *   cd /path/to/travel-price-tracker && /path/to/venv/bin/python -m travel_tracker wide-scan >> wide_scan.log 2>&1
15 */2 * * * cd /path/to/travel-price-tracker && /path/to/venv/bin/python -m travel_tracker promo-scan >> promo_scan.log 2>&1
```

### Option B: GitHub Actions

`.github/workflows/scan.yml` (every 6h), `wide_scan.yml` (daily), and
`promo_scan.yml` (every 2h) each trigger on `workflow_dispatch` too. Add
these repo secrets (Settings -> Secrets and variables -> Actions):
`TRAVELPAYOUTS_TOKEN`, `TRAVELPAYOUTS_MARKER`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`, `SERPAPI_KEY` (optional). `promo_scan.yml` only needs
the Telegram secrets -- Telegram channel monitoring doesn't run in Actions
(see above). The SQLite file is persisted between runs via `actions/cache`
(keyed off `data/tracker.db`) rather than committed to the repo -- simplest
option for a personal project, though the cache can be evicted after ~7 days
of no runs, which would reset price/promo history. Swap in Postgres/Supabase
later if that matters.

## Notes / limitations

- Travelpayouts fares are cached, not live -- can lag real airline prices.
  That's why error fares get a live SerpApi re-check when a key is set.
- Daily summary currently fires at the end of any scan that found deals,
  not on a fixed daily schedule -- a dedicated once-a-day job is a small
  follow-up.
- Passagens Imperdíveis' RSS feed (`passagensimperdiveis.com.br/feed/`) is
  blocked by Cloudflare bot-protection as of 2026-09, even from a normal
  browser. Left configured since that may change; `promo-scan` logs a
  warning and skips it rather than failing the whole run.
- **Award/miles availability tracking (seats.aero) is deferred.** Their
  partner API needs a seats.aero Pro subscription (~R$50/mo) to get an API
  key -- not a free tier like the other sources here. The `Provider`
  interface (`providers/base.py`) makes this a self-contained addition
  whenever that's decided; `miles_programs` in `config.yaml` is a placeholder
  until then.
- The dashboard is read-only and local (`localhost:8501` by default, not
  exposed publicly) -- no auth, since it's a personal single-user tool. Don't
  bind it to a public interface without adding some.

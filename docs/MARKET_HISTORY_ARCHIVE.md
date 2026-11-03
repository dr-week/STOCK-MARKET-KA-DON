# Local Market History

## What exists

- Validated provider candles are persisted in the separate local SQLite database `stock-signal-bot/backend/app/data/market_history.db`.
- Yahoo scan candles are archived for the existing 5-minute and 15-minute scan intervals. Groww history can be requested explicitly for 5m, 15m, 1h, and 1d charts.
- When a chart symbol or supported interval is selected, the backend fetches bounded public Yahoo chart history and archives it; if that provider is unavailable, existing cached candles are returned with a warning. “Fetch broker history” makes a separate explicit Groww request; Groww candles are saved locally and returned to the chart.
- The chart symbol search accepts a validated NSE ticker outside the configured scan universe and requests one-stock analysis. A symbol is not considered available unless its provider data is returned and validated.
- The chart does not synthesize candles. Missing history produces an explicit empty/error state.
- The archive stores price/volume candles and provider provenance only. It is separate from paper trades and Groww account snapshots. Its database and SQLite sidecars are excluded from Git.
- The archive and Groww history routes are loopback-only. Groww credentials and access tokens remain in backend memory and are not written into the candle database.

## Source, cost, and limits

### Sources checked

| Source | What the official documentation verifies | Access and caveats |
|---|---|---|
| [Groww Trading API / historical candles](https://groww.in/trade-api/docs/python-sdk/backtesting) | Equity, index, and F&O candle history from 2020; documented intervals and bounded request windows | Groww's [SDK introduction](https://groww.in/trade-api/docs/python-sdk) requires an active Trading API subscription. SDK availability is not a free-data grant. |
| [Zerodha Kite Connect](https://kite.trade/docs/connect/v3/historical/) | Historical OHLCV intervals include minute, 3-minute, 5-minute, hourly, and daily candles | The [official pricing page](https://zerodha.com/products/api/) lists historical candles and real-time WebSocket data under Connect at ₹500/month; its Personal (Free) tier does not list those data features. Requires an authenticated API account. |
| [Yahoo Finance chart endpoint](https://query1.finance.yahoo.com/) | SMKD retrieves chart candles for selected NSE tickers | This is an unofficial public endpoint, not an exchange-authorized API. It can change or rate-limit; SMKD has not verified redistribution or retention rights. Do not treat it as an official real-time feed or rely on it as the sole source for a trading decision. |
| NSE/BSE exchange reports and data products | Exchange reports such as daily bhavcopy/EOD records are distinct from minute-level intraday history | No free, unrestricted official intraday API or reuse license was verified for this implementation. Exchange reports and paid data products do not establish that minute candles are free or redistributable. |

The public Yahoo adapter currently requests these bounded ranges:

| Interval | Requested range |
|---|---:|
| 1m | 30 days |
| 5m, 15m | 60 days |
| 1h | 2 years |
| 1d | Maximum available from the endpoint |

The 3m interval is not available from this adapter; it uses only candles already in the local archive, such as history fetched from Groww. A failed public fetch uses validated cached data with a warning, or returns an error if no cache exists. No candles are generated to fill missing history.

Groww's [official historical-candles documentation](https://groww.in/trade-api/docs/python-sdk/backtesting) describes equity, index, and F&O candle history from 2020. Its per-request maximums are:

| Interval | Maximum request range |
|---|---:|
| 1m, 2m, 3m, 5m | 30 days |
| 10m, 15m, 30m | 90 days |
| 1h, 4h, 1d, 1w, 1mo | 180 days |

This implementation supports 5m, 15m, 1h, and 1d, and requests no more than the applicable provider range at a time. The chart's end-date field allows moving back through history in separate bounded requests; it does not automatically download multiple years. Groww API authorization is required; confirm current data-use and retention terms directly with Groww before relying on it. Availability in an SDK does not grant market-data rights.

**Bottom line:** no free, unlimited, official Indian intraday feed was verified. Groww requires a subscription; Zerodha's historical feed is in a paid tier. Yahoo history may be accessible without an API key, but it is unofficial and its reuse rights are unverified, so it must not be described as a licensed free feed.

The current app is a local-first SMKD backend with SQLite archives; it is **not** a cloud-native, zero-local-database deployment. Moving private account state or market history to a cloud database requires a separate security, retention, cost, and deployment design.

## Data integrity

- Stored rows are keyed by symbol, interval, timestamp, and provider. Re-fetching the same provider candle updates that row rather than duplicating it.
- Timestamps are normalized to Unix seconds. Groww timestamps without a timezone offset are interpreted as Asia/Kolkata, as disclosed by the API response.
- Incomplete current candles are excluded. Rows are rejected for invalid timestamps, non-finite/non-positive OHLC prices, negative volume, or inconsistent OHLC bounds.
- Local chart history is ordered by timestamp and carries the selected provider for provenance. A database write failure is surfaced to the caller; it is not reported as a successful archive.
- No historical download has been run against the user's Groww account. Tests use synthetic fixtures only.

## Current gaps

- Groww requests currently fetch one bounded window (up to 30/90/180 days, depending on interval) ending on the date selected in the chart. The API documentation says data exists from 2020, but automated multi-year chunking, rate-limit policy, and progress/resume are not implemented.
- History requests require an active, authorized in-memory Groww session. The user must connect explicitly; no credentials are requested or stored by the chart.
- There is no verified NSE/BSE import path, multi-provider reconciliation, exchange-calendar validation, completeness audit, or automated archive backup/export.
- A local archive is not proof of real-time freshness, completeness, provider licensing, or trading profitability.

## Next steps

1. Confirm Groww subscription and historical-data retention terms, and any restrictions on local storage.
2. Add bounded date-range selection and resumable chunk backfill only after provider rate limits are documented.
3. Verify an official NSE/BSE end-of-day source and its terms before adding it; keep EOD and intraday coverage clearly distinguished.
4. Add archive integrity checks (source gaps, duplicate timestamps, session calendar, and OHLCV validation) and an explicit local backup/restore flow.

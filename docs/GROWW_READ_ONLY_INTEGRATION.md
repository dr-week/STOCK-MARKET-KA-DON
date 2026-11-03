# Groww read-only account integration

## Code boundaries

```text
backend/app/integrations/groww/
  service.py       Groww SDK session, normalization, read-only account fetch
  history_provider.py
                  Bounded historical candle fetch and OHLCV validation
backend/app/api/routes_groww.py
                  Loopback-only account and history routes
backend/app/departments/market_data/history_store.py
                  Validated local SQLite OHLCV archive
frontend/src/api/groww.ts
                  Typed local API client and response validation
frontend/src/ui/features/groww-account.ts
                  Account-only presentation
frontend/src/ui/features/groww-controller.ts
                  Connect, refresh, disconnect, and chart navigation
frontend/src/ui/chart/executions.ts
                  Exact-time execution markers for the custom candle chart
```

The existing paper journal remains a separate feature and database. Groww account data must never be copied into the paper ledger or mixed with simulated trades.

## What works

- Uses Groww's published `growwapi` SDK, not private app endpoints or browser scraping.
- Fetches delivery holdings, cash and F&O positions, recent orders, and exchange execution records including `trade_date_time`, price, quantity, side, and trade ID.
- Shows broker order creation time separately from actual execution time. Times with a provider timezone are displayed in IST; timezone-less times are not converted or guessed.
- BUY and SELL execution markers are anchored to the corresponding five-minute candle only when the timezone-aware fill timestamp falls inside the loaded candle window; marker labels preserve the exact execution time in IST. The Groww activity view remains the source of truth when an execution is outside the visible chart history.
- Groww data is loaded on demand, not streamed. The order view is limited to the first 25 orders per segment and execution lookups to 20 executed orders; the UI discloses these limits.
- No order placement, modification, cancellation, or broker automation is exposed.
- Historical candles are fetched only on explicit request through Groww's documented backtesting API. The chart supports 5m, 15m, 1h, and 1d intervals, with a selectable history end date; each request is bounded by the published 30-, 90-, or 180-day maximum and the result is stored in the separate local market-history database.
- History timestamps without an offset are interpreted as Asia/Kolkata, incomplete candles are omitted, and invalid OHLCV rows fail validation. This adapter does not store or expose account credentials, positions, orders, or executions in the candle archive.

## Local-data and credential boundary

- Groww API credentials are sent from the UI to the loopback backend and used to obtain an access token. Neither credentials nor the token are written to files, SQLite, browser storage, logs, or API responses.
- The backend keeps the token in memory only. Disconnecting or restarting the backend clears it. Users must reconnect after restart or token expiry.
- Holdings, positions, orders, and executions are fetched into process/UI memory on refresh and are not persisted by this integration.
- Groww routes reject non-loopback clients. CORS is restricted to local development/preview origins. The backend itself should continue binding only to `127.0.0.1`.
- The existing paper SQLite database is local runtime data and is now excluded from Git. Never commit personal account data, API keys, access tokens, or database files.
- Groww requires a Trading API subscription. Groww's API-key/secret authentication may require daily approval in the Groww Cloud API Keys page. This feature has not been connected to a real account without the user's credentials and approval.

## Trade start and end: interpretation rules

- An execution is an exchange fill, not necessarily a complete trade. A BUY can open/add to a long position or close/reduce a short; a SELL can reduce/close a long or open/add to a short. Do not label every BUY as an entry or every SELL as an exit.
- Use Groww's current net position quantity to establish what is still open. Use the individual fills and their timestamps to inspect where/when units were traded. Broker-provided average prices are not substitutes for per-fill entry prices.
- A reliable round-trip timeline needs the complete execution history and a documented matching rule (instrument/contract, product, account, and FIFO or broker's realized-P&L method). The current first-page fetch is intentionally not presented as complete historical coverage.
- Stops, targets, mark-to-market, intraday alerts, and a personalized sell decision are not inferred from holdings or fills. Users must define their own risk plan; the app must not fabricate a sell time, future opportunity, or earning estimate.

## Remaining work / current gaps

1. Paginate and locally archive full execution history with explicit import bounds, deduplication, and an export/backup path that stays outside Git.
2. Verify live quote/mark-to-market fields and exchange/timezone behavior against Groww's API contract before calculating unrealized P&L or suggesting alerts.
3. Add optional, user-entered stop/target/risk notes and local price alerts. Clearly separate these from broker orders and AI/scan hypotheses.
4. Improve chart controls in independent modules: selectable indicator parameters, additional validated studies, and user-adjustable pane layout. Historical chart intervals now use the local archive or an explicit bounded Groww history fetch. Automated multi-year chunking and progress/resume remain unimplemented.
5. Add a reconciliation view for partial fills, same-symbol multi-leg activity, corporate actions, and broker position changes before claiming a complete trade start/end lifecycle.

No expected-profit number is produced by this feature. Historical gross P&L is not a forecast and does not guarantee future returns.
For market-data source limits, local archive behavior, and unverified exchange archive access, see [Local market history](./MARKET_HISTORY_ARCHIVE.md).

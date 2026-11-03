# Cloud-Native Data and Runtime Plan

**Status:** Target architecture and verified source assessment. This is not a claim that the app is deployed in the cloud. The checked-out backend still creates three local SQLite databases.

## Decision

- **Primary managed database:** Supabase Postgres. The current data is relational (candles, scan runs, signal records, paper positions, feedback); this is a better fit than MongoDB for constraints, de-duplication, audit joins, and transactional trade-state changes.
- **Realtime:** Start with HTTPS requests for history and a single authenticated backend WebSocket only after a provider grants an authorized live stream. Use managed Redis only if ingestion/fan-out needs multiple workers; Redis is transient queue/cache/pub-sub, not the durable trade ledger.
- **Market-data adapter:** Keep Groww as the currently documented historical source for this account, with an explicit user-authorized request. Do not select Twelve Data, Alpha Vantage, Finnhub, or another feed for NSE until that provider confirms NSE symbols, intervals, freshness, quotas, cloud/display rights, and the actual paid/free entitlement in writing.
- **Broker account privacy:** Do not send Groww API keys, access tokens, holdings, orders, or personal fills to a cloud backend by default. Keep the existing Groww feature read-only and memory-only, and exclude broker-account sync from cloud deployments until the user deliberately opts in to a separately secured design. Cloud storage for trade/account data is a privacy change, not a transport refactor.
- **Execution:** This app remains analysis and paper-trading only. No live order route, execution state machine, or promise of millisecond fills is included.

## Target request and event flow

```text
Browser (static UI; Supabase Auth session)
  ├─ HTTPS /api/market-history/{symbol}?interval&start&end
  ├─ HTTPS /api/scan and paper-trade endpoints
  └─ WSS /api/stream (only when an entitled live source exists)
          │
          ▼
Cloud API (authenticated FastAPI service; provider credentials in cloud secret manager)
  ├─ market-data adapters → normalization + instrument/time validation
  ├─ deterministic analysis → explicit provider/freshness/data-quality metadata
  ├─ news adapters → de-duplicate, tag, sentiment with model/version provenance
  ├─ paper-only state machine → idempotent audit events; no broker order calls
  └─ bounded background workers → historical fetch / news refresh / scheduled tasks
          ├─ Supabase Postgres: candles, news metadata, scans, paper journal, audit
          └─ Optional managed Redis: job queue, short-lived cache, multi-worker fan-out
```

The browser never receives provider secrets and never connects directly to a market-data vendor or database service-role key. Supabase service-role/secret keys bypass row-level security and must remain server-only. Authenticate every cloud API route; apply authorization per user and RLS to user-owned paper/settings records. Do not keep the current loopback-only guard as the cloud authentication strategy, and do not remove it until cloud auth is implemented and tested.

Use REST for historical chart requests and only complete, validated candles. A persistent worker can hold a provider WebSocket if the selected provider documents that capability and hosting supports long-lived connections. Aggregate ticks into 1m/3m/5m bars in the ingestion service; persist bars, not every raw tick, unless license, cost, retention, and audit needs justify raw tick storage. Push snapshots/deltas to browsers through the authenticated app WebSocket. A database-change subscription is not a substitute for a low-latency market feed.

## Verified provider facts and limits

| Source | Verified from provider documentation | Decision |
|---|---|---|
| Groww Trading API | Historical OHLCV supports 1m, 2m, 3m, 5m, 10m, 15m, 30m, 1h, 4h, daily, weekly, monthly; per-request history caps are 30 days for 1–5m, 90 days for 10–30m, and 180 days for 1h and longer. The live-data guide documents REST `get_quote` and `get_ohlc`. | Current historical adapter supports 1m/3m/5m/15m/1h/1d in bounded requests. A persistent live WebSocket was not found in the referenced public live-data guide; do not assume one is available. Requires authorized Groww API credentials/subscription. |
| Twelve Data | Current personal Basic listing shows $0, 8 API credits/minute (800/day), and 8 trial WebSocket credits; it lists real-time US equities/ETFs, forex, and crypto. The page does not establish that the Basic plan supplies NSE real-time/intraday access. Paid plans are shown from $79/month, but plan and exchange entitlements still need account-level confirmation. | Not a verified free NSE source. Do not put an API key in the browser or promise Indian-market coverage from the free plan. |
| Alpha Vantage | Official pages state a standard free usage limit of 25 API requests/day and mark intraday historical/realtime endpoints as premium. The intraday examples and real-time entitlement described are US-market oriented. | Not selected for an NSE intraday feed without separate documented NSE coverage and entitlement. |
| Finnhub / Marketaux / RSS | Potential news integrations; coverage, freshness, request quotas, sentiment semantics, redistribution/display rights, and cloud use must be confirmed against the exact plan and source. | Keep behind separate news-provider adapters; no scrape of paywalled or access-controlled sites. RSS availability is not a grant to republish article text. |

These are documentation snapshots, not a guarantee of current prices or a legal opinion. Verify the vendor's current terms and symbol-specific entitlements before enabling provider traffic.

## Cloud database inventory

The current checkout has these file-backed stores, which must all move before the strict “zero local database files” goal is met:

1. `app/data/market_history.db` — validated provider candles.
2. `app/data/paper_trades.db` — paper positions plus signal-feedback outcomes.
3. `app/data/signals_tree.db` — scan runs, signal nodes, and backtest evaluations.

Target Postgres ownership:

- `market_candles`: provider, exchange, instrument identifier, interval, UTC epoch/time, OHLCV, source observation time; unique provider/instrument/interval/time key.
- `paper_positions` and `paper_trade_events`: user ID, entry/exit values, state, timestamps, plan, idempotency key, append-only transition audit.
- `scan_runs`, `signal_nodes`, `backtest_evaluations`: existing research/history without conflating deterministic heuristics with calibrated predictions.
- `news_articles` and `news_entity_tags`: canonical URL/provider ID, publication and ingestion timestamps, source, tickers, normalized tags, deduplication key; store only content the license permits retaining.
- `provider_jobs`: bounded backfill cursor, status, quota/last-success metadata, and safe retry information. Never put API keys or broker tokens in job rows.

Use migrations and schema constraints. Partition/retention policy for candles must be chosen from verified provider retention terms and actual usage. Keep user-owned paper data behind authenticated user identity and RLS; keep service-only market ingestion tables inaccessible to browser publishable keys unless read access is explicitly authorized.

## Free tier and reliability reality

Supabase currently documents a Free tier with 500 MB database size, 5 GB egress, two active projects, and pausing after one week of inactivity; its pricing page says automatic database backups are not included on Free. The page lists Pro from $25/month with 8 GB disk per project and seven-day backups. Provider data/API access is a separate cost and license. A free-tier prototype can be inexpensive, but uninterrupted production operation, provider entitlements, reliable backup/restore, and real-time Indian market data are not guaranteed free.

Redis is not required for the first cloud version. Add a managed Redis plan only when measured ingestion scale requires queueing or cross-instance fan-out; Redis free tiers also have eviction, capacity, and uptime limitations and must not be the only copy of trade state.

## Migration and rollout gates

1. **Provision cloud environment:** create Supabase project in an appropriate region, Auth settings, production and staging environments, RLS policies, migration runner, secret manager values, backup/restore plan, and a cost/quota alert. No project, credentials, or deployment target is available in the current workspace.
2. **Implement repository seam:** replace the SQLite-specific history, paper/feedback, and scan-tree repositories with Postgres repositories; retain SQLite only for isolated temporary test fixtures. Cloud mode must fail closed if cloud configuration is missing; it must never silently create local operational databases.
3. **Migrate with reconciliation:** take a protected backup of each existing DB; import to staging; compare table counts, IDs, timestamps, numeric totals, uniqueness, open/closed position state, and query results; then validate the live API against staging.
4. **Secure API before public deployment:** add Supabase Auth JWT verification, user scoping, RLS, rate limits, HTTPS-only origins, safe errors/observability, and tests for unauthorized/cross-user access. The existing loopback-only Groww route guard is not sufficient for a public service.
5. **Deploy API and worker:** run FastAPI plus a separately supervised worker in a region/host that supports stable outbound provider connections. Use scheduled tasks for REST-only history/news, bounded retries/backoff, and explicit data-freshness states. Do not treat retries as permission to exceed vendor quotas.
6. **Enable live streaming only after source approval:** document symbol coverage, market-data rights, WS support, expected/observed latency, disconnect/replay handling, duplicate/out-of-order tick rules, heartbeat, rate limits, and cost. Measure end-to-end p50/p95/p99 latency; do not call it HFT or “split-second execution.”
7. **Cut over without losing local data:** keep local DBs untouched until cloud reconciliation and backup restore are proven and the user approves the final migration. After cutover, run in cloud-only mode and verify no operational `sqlite3.connect` path is invoked. Delete local DB files only as a separate, explicitly authorized cleanup step after a restorable cloud copy is verified.

## Implemented first slice

- Added 1-minute and 3-minute historical chart interval choices using Groww's documented bounded REST history API; these are OHLCV bars, not tick history or streaming.
- The repo still stores its three application databases locally. Cloud persistence/auth, news providers, continuously streamed data, Redis, and deployment are not implemented. See [Local market history](./MARKET_HISTORY_ARCHIVE.md) for the existing archive behavior.

## Official references

- [Groww historical candles and per-request caps](https://groww.in/trade-api/docs/python-sdk/backtesting)
- [Groww live data: quote and OHLC API](https://groww.in/trade-api/docs/python-sdk/live-data)
- [Twelve Data current personal pricing and usage limits](https://twelvedata.com/pricing)
- [Twelve Data exchange directory](https://twelvedata.com/exchanges)
- [Alpha Vantage API documentation](https://www.alphavantage.co/documentation/)
- [Alpha Vantage premium limits](https://www.alphavantage.co/premium/)
- [Alpha Vantage realtime data policy](https://www.alphavantage.co/realtime_data_policy/)
- [Supabase current pricing](https://supabase.com/pricing)
- [Supabase Postgres overview](https://supabase.com/docs/guides/database/overview)
- [Supabase secure-data guidance](https://supabase.com/docs/guides/database/secure-data)
- [Supabase Postgres change subscriptions](https://supabase.com/docs/guides/realtime/postgres-changes)

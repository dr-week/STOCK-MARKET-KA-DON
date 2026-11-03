# SMKD Product and Technical Roadmap

**Review date:** 2026-11-02  
**Scope:** Current repository implementation and near-term engineering priorities. Market outputs are experimental; no performance or profitability claim is made.

## 1. Product purpose

SMKD should be an **intraday analysis and research assistant for NSE equities**: identify candidate activity from market data, explain the rules and source data behind each observation, show risk levels, and let the team evaluate those rules with honest backtests and forward paper trading.

It should not promise to predict prices or improve win rates until measured evidence supports that claim. The immediate product objective is **trustworthy, explainable, testable analysis**, not adding more indicators or calling a rules engine “AI.”

## 2. Verified current behavior

### Request and decision path

1. The dashboard in `fast-framework/packages/stock-bot-ui/src/main.ts` starts in a loading state and requests `GET /api/scan`.
2. `stock-signal-bot/backend/app/main.py` mounts the API router on one FastAPI process.
3. `api/routes_scan.py` obtains market intelligence, then scans the configured universe concurrently.
4. Per symbol, `process_unified_stock` obtains candles, computes technicals, fetches fundamentals/news, computes a confluence/risk decision, then computes SystemOne output.
5. A scan snapshot is written to SQLite; the API returns results and failed-symbol names.
6. The UI validates and normalizes the response. Request failures show an error and retry control; the active scan path does not substitute sample rows.

### Current features versus claims

| Capability | Verified implementation | Not established |
|---|---|---|
| Market data | Yahoo Finance chart endpoint; aligned OHLCV rows; incomplete 5m/15m and daily bars excluded; source/fetch timestamps and replay/provider provenance returned | Exchange-direct or guaranteed real-time quotes, freshness SLA, multi-provider confirmation |
| Indicators | Deterministic calculations from OHLCV, including VWAP, EMA, RSI, ATR, ADX, RVOL, and structure | Independent evidence from each indicator; many inputs share one source series |
| Primary signal | Hand-written confluence rules, entry/stop/target levels, and sizing | Validated probability of success or an audited execution fill |
| SystemOne | Hand-authored scoring adjustments and score labels | Model training, online learning, empirical calibration, or proven price forecasting |
| News/fundamentals | Keyword-based headline sentiment; static company metric table and defaults | Live audited fundamental data or a financial-language model |
| Primary chart | In-repo SVG chart from validated 1m/3m/5m/15m/1h/1d OHLCV; toggleable EMA 9/21, RSI 14, and volume; proposed entry/stop/target overlays; Groww fill markers; local horizontal annotations; scroll zoom and drag-to-pan | No TradingView or third-party chart library is used. Chart indicators are visualizations, not new signal inputs. Movable/editable drawings, more studies, multi-year resumable backfill, and a verified exchange-direct source are not implemented. |
| News UI | Deduplicated Google News RSS titles from scan results, symbol associations, publication times, and keyword sentiment labels | Source coverage, latency, licensing, and sentiment correctness are not guaranteed; paid/API provider choice remains open. |
| Backtest | Five-minute Yahoo bars, 1–30 requested days, next-bar-open entry, simple cost parameter | Long-history point-in-time validation, complete brokerage costs, latency/order-book fills, walk-forward validation |
| Paper trading | Persistent SQLite ledger connected to UI for confirmed manual paper entry/exit, open/history views, whole-share and side/level validation, and gross risk/reward preview | Broker fills, live mark-to-market, fees/slippage, partial exits, full event audit, or automated feedback loop |
| Groww account | Loopback-only, read-only SDK connection; in-memory credentials/token; refresh-on-demand holdings, CASH/FNO positions, recent orders and execution timestamps; BUY/SELL fill markers on the custom chart when fills overlap its candle window | Real-account connection still requires the user's Groww Trading API subscription and approval; no live quotes/mark-to-market, complete paginated history, alerts, or inferred round-trip matching |

See [Architecture](./ARCHITECTURE.md), [AI decision scoring](./AI_DECISION_ENGINE.md), and [backtesting details](./BACKTESTING_FEEDBACK_LOOP.md) for implementation-level notes.
Groww data scope, local-only guarantees, execution interpretation, and gaps are documented in [Groww read-only integration](./GROWW_READ_ONLY_INTEGRATION.md).

## 3. Highest-priority findings

### P0 — Make the displayed data trustworthy

- The legacy `market_data.timestamp` is local fetch time, not proof of exchange-time freshness. `data_quality` now reports the provider timestamp when supplied, otherwise the latest complete five-minute candle start, plus local fetch time; neither proves a freshness SLA.
- OHLCV rows are now validated together, preserving candle/timestamp alignment; incomplete 5m/15m bars and the in-progress daily bar are excluded from provider mode.
- Nifty defaults to a fixed price/change if the fetch fails; India VIX is fixed; sector strengths have a hardcoded fallback; fundamentals use a static table or generic defaults.
- Technical analysis now returns explicit insufficient-history status, omits fabricated indicator values and empty-history sparklines, blocks signal candidates, and skips SystemOne scoring until 21 complete five-minute bars exist.
- The active UI no longer shows example rows after request failures; it displays loading, error, empty, partial, source-time, and analysis-readiness states.
- The main chart uses an in-repository SVG renderer for validated archived 1m/3m/5m/15m/1h/1d OHLCV with candlesticks, toggleable volume/EMA 9/21/RSI 14, proposed entry/stop/target levels, Groww fill markers, and local horizontal annotations. Scroll zoom and drag-to-pan are supported. History is fetched from Groww only after an explicit user action; absent intervals are not fabricated. No TradingView chart, widget, or charting library is used.
- The local market-history archive is separate from the paper ledger and broker account snapshots. Its DB and sidecars are ignored by Git. See [Local market history](./MARKET_HISTORY_ARCHIVE.md) for provider range limits, source licensing caveats, and the unimplemented multi-year backfill.
- The News desk consumes scan headlines, and the details panel exposes SystemOne rules with an explicit uncalibrated label. The UI does not present `probable_move_pct` as a forecast.
- The scan route catches per-symbol exceptions and records only the failed symbol. Provider errors need structured, observable reasons rather than silent degradation.

**Required behavior:** every result identifies provider, instrument, interval, source timestamp, fetch timestamp, provider/replay mode, completeness, and status (`available`, `delayed`, `stale`, `replay`, `insufficient`, or `unavailable`). The current implementation now carries partial provenance and candle-quality counts, but stale/delayed classification, structured provider errors, and removal of fixed Nifty/sector context and static fundamentals remain. If required data is invalid or indicator history is insufficient, do not compute or display a tradable candidate. Never substitute demo or fixed data into a live-looking result.

### P1 — Correct AI and signal semantics

- SystemOne is fixed deterministic scoring. Its `win_probability` is a piecewise score mapping, not a historically calibrated probability.
- The EV assumes a fixed `RR=2.5`; its mapping is not side-aware, so strong bearish scores cannot be read as calibrated short-trade win probabilities.
- `probable_move_pct = (ai_score - 0.5) * 8` is a display transformation, not a forecast.
- `routes_scan.py` passes price-versus-VWAP percentage into a parameter named `change_pct`; the input meaning is inconsistent with its name.
- The scan supplies Nifty regime labels (`BULLISH`/`BEARISH`/`SIDEWAYS`) while SystemOne checks for `TRENDING`/`RANGE`; those regime adjustments do not match the current API values.
- The primary `signal_risk` output and SystemOne verdict are computed independently. UI presentation should not imply that one confirms the other unless a tested rule defines that relationship.
- Technical/news inputs are correlated or heuristic; adding factors alone does not establish greater precision.

**Required behavior:** until calibrated, label scores as experimental heuristics; remove probability/forecast phrasing or make the unvalidated assumption explicit. Define separate long and short outcome labels and never infer real confidence from confluence score alone.

### P1 — Fix the frontend/backend contract

- The UI API client now uses a configurable base URL and runtime-validated types.
- The initial view and scan-failure handler no longer display static example trades; explicit loading/error/empty states are present.
- The scan handler sorts by `signal_decision.confluence_score`, and the UI displays returned rows in that order. That is a rule-score sort, not a ranking by validated expected return or measured stock activity.
- The paper journal now calls the existing paper API and uses `stock-signal-bot/backend/app/data/paper_trades.db`; entry/exit is user-recorded paper-only and does not submit broker orders. P&L is gross and no live mark-to-market is shown.

**Required behavior:** validate API response models, use a configurable API base, share explicit TypeScript types, and render loading/empty/error/stale/replay states. Demo fixtures must be reachable only in a visibly labeled development/demo mode. Document and test the sort key; do not describe an unvalidated heuristic ranking as predictive. Add contract tests at the API/UI boundary.

### P2 — Upgrade research quality before tuning signals

The current backtest is a short-window mechanics check, not a precision benchmark. Important gaps include limited provider history, neutral historical Nifty context, a static fundamental filter, no point-in-time universe, simplified costs/fills, and threshold comparisons on the same sample.

Do not optimize thresholds until sufficient authorized history and timestamped features/outcomes exist. Evaluate time-ordered out-of-sample and walk-forward results; include sample counts, net costs, drawdown, expectancy, and calibration. Keep a final untouched holdout and compare against a simple baseline. Do not set a target accuracy or win rate without a defensible use case and dataset.

### P3 — Refactor as a modular monolith

The backend is already divided into API routes, departments, indicators, AI, backtesting, paper trading, feedback, and persistence. The visible problem is not an all-in-one `main.py`; the app entrypoint and top-level route aggregator are small. Avoid a risky rewrite or premature microservices.

Use explicit ownership and names at existing domain seams:

```text
api/                 HTTP validation, response models, status codes
application/         scan/backtest/paper use-case orchestration
market_data/         provider interface, normalization, quality checks
indicators/          deterministic calculations
signals/             confluence rules, risk levels, side-aware outputs
analytics/           scoring, calibration, evaluation (only with evidence)
backtesting/         event timeline, fills, costs, metrics
paper_trading/       simulated order/position lifecycle
persistence/         repositories, migrations, audit snapshots
```

This is a target boundary, not a directive to rename every current folder. Move code only when tests protect its current behavior. Keep provider adapters and replay fixtures separate; avoid sharing mutable global state across scan requests; keep routes thin; do not make a network call inside pure indicator/strategy functions.

## 4. Delivery sequence and acceptance checks

### Execution status

- **Implemented in earlier changes:** split UI startup from dashboard interaction/state (`main.ts` → `ui/app-controller.ts`); add validated TypeScript API contracts and configurable API base; remove live-path sample-row fallback; show loading/error/empty/partial states; render charts only from timestamp-aligned backend closes; remove fabricated chart/news/paper-summary values; validate and display provider/replay provenance and source time; align and validate candle OHLCV rows; exclude incomplete bars; require 21 complete five-minute bars before technical signals or SystemOne scoring.
- **Implemented in this change:** connect the paper journal UI to the persistent SQLite paper ledger; validate entry, side, level ordering, whole-share quantity, exit price, and one-time close; show open positions, closed history, gross risk/reward preview, explicit confirmation, and API error states. Restart the local API/UI processes when stopped; the current chart still has only 5m candles.
- **Still required for Phase 0:** classify stale/delayed feeds against an exchange calendar, remove fixed Nifty/sector context fallbacks and static company fundamentals from live decisions, expose structured per-symbol provider errors, and add backend response models. Yahoo data is still not verified as exchange-direct or real-time.
- **Not started:** historical event/news replay, provider integration, calibrated model evaluation, and broader backend domain extraction.

| Phase | Deliverable | Acceptance checks |
|---|---|---|
| **0. Trust and visibility** | Source/data-quality envelope; remove live-path fixed fallbacks and static UI fallback; structured provider failures | Tests prove stale, missing, malformed, incomplete, and replay data have distinct statuses; no failure path displays example rows as live |
| **1. Typed integration** | Backend response models and frontend types; configurable API base; UI loading/error/empty states | Contract tests cover scan success, partial failure, full failure, unknown symbol, and invalid payload; UI has no `any` on scan response |
| **2. Research baseline** | Point-in-time data store and reproducible backtest run configuration; explicit fees/slippage/fill assumptions | Deterministic replay tests for gaps, stop/target same bar, session close, and costs; saved run includes data and strategy versions |
| **3. Evaluation and calibration** | Side-aware trade outcomes, time-split and walk-forward report, score calibration metrics | Final holdout untouched during tuning; report includes sample size, uncertainty, costs, baseline, long/short metrics, and calibration |
| **4. Domain extraction** | Thin routers and use-case services, provider/strategy/persistence interfaces | One bounded refactor at a time; API compatibility tests and relevant unit tests pass; no duplicate business rules |
| **5. Product expansion** | Alerts, broader universe/breadth, or later broker features chosen from user needs; paper-journal depth such as fees, partial exits, and event audit | Each feature has a licensed data source, failure semantics, operational owner, and acceptance tests; broker execution requires a separate safety/security review |

Phases 0–3 should precede any claim that a model improves precision. Modular extraction can proceed in small, test-backed changes without blocking the data-integrity work.

## 5. Competitive research

Public product documentation provides useful workflow references: TradingView documents paper order management and strategy reports; Kite Connect documents historical candle intervals and instrument tokens; QuantConnect documents out-of-sample research, look-ahead/survivorship risks, and fill/slippage assumptions. These are engineering references, not proof that SMKD should match every feature or that another product predicts better.

See [Competitive research](./COMPETITIVE_ANALYSIS.md) for source links and the comparison table.

## 6. Non-goals until evidence exists

- Do not add a generative LLM to manufacture a price target or explain unavailable data.
- Do not represent a fixed score-to-probability mapping as calibrated AI.
- Do not add broker automation before data, order-state, authorization, risk limits, and audit controls are independently validated.
- Do not split the application into services just to reduce file size.
- Do not claim improved accuracy from additional indicators without a controlled out-of-sample comparison.

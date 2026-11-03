# SMKD Architecture

**Status:** Verified against the checked-out implementation on 2026-11-02. This describes the current code, not a production-readiness claim.

## Product boundary

SMKD is an experimental NSE intraday analysis and research dashboard. It fetches market data, computes indicators, produces rule-based scan signals, and exposes backtest and paper-trading APIs. It does not have evidence of a profitable edge, train a predictive model, or place live broker orders.

## Current runtime

```text
Vite + TypeScript UI
  └─ GET http://127.0.0.1:8000/api/scan
       └─ FastAPI app (`app/main.py`, one process)
            ├─ market_intelligence ── Nifty/sector context and session state
            └─ per-symbol scan (`api/routes_scan.py`)
                 ├─ market_data ── Yahoo Finance chart endpoint
                 ├─ technical_analysis ── indicators and price structure
                 ├─ fundamental_analysis ── static company table + headline sentiment
                 ├─ signal_risk ── confluence score and risk levels
                 └─ SystemOne ── separate deterministic heuristic score
                       └─ SQLite scan snapshot

Separate API paths: backtest, paper trading, Groww read-only account sync, feedback reports, backups, feed health
Market-data persistence: validated OHLCV is stored separately in a local, Git-ignored SQLite archive
```

The backend is a **modular monolith**: route modules and domain services run in one FastAPI process. SQLite databases are local files. The frontend is a Vite application under `fast-framework/packages/stock-bot-ui`.

## Existing module boundaries

| Responsibility | Current location |
|---|---|
| App setup and router mounting | `stock-signal-bot/backend/app/main.py`, `api/routes.py` |
| Scan and stock analysis orchestration | `api/routes_scan.py` |
| Market data requests and short in-memory cache | `departments/market_data/service.py` |
| Pure indicator and structure calculations | `indicators/`, `departments/technical_analysis/` |
| News and static company fundamentals | `news/`, `departments/fundamental_analysis/` |
| Index/sector/session context | `departments/market_intelligence/`, `market/` |
| Signal levels and sizing | `departments/signal_risk/`, `indicators/calculations.py` |
| Heuristic score displayed alongside the signal | `ai/system_one.py` |
| Historical simulation | `backtesting/backtest_engine.py` |
| Paper ledger and outcome reports | `paper_trading/`, `feedback/` |
| Groww account data (read-only, in-memory session) | `integrations/groww/service.py`, `api/routes_groww.py` |
| Historical provider candles and local archive | `integrations/groww/history_provider.py`, `departments/market_data/history_store.py`, `api/routes_market_history.py` |
| Scan history and backups | `db/` |
| UI API client and rendering | `fast-framework/packages/stock-bot-ui/src/` |

## Important current boundaries and gaps

- The scan path calls the Yahoo Finance chart endpoint; fetch time is currently used as the market-data timestamp. This does not establish exchange-time freshness or real-time delivery.
- Nifty and sector context can use fixed fallback values; company fundamentals come from a static table or generic defaults. These values must not be presented as verified live observations.
- Indicator defaults can be returned when candle history is insufficient. A response therefore needs an explicit data-quality state before it can safely be treated as a valid signal.
- The UI starts with example rows and restores them if the scan request fails. It needs distinct loading, live-data, empty, stale, replay, and error states.
- The paper and feedback APIs exist, but the current dashboard startup path does not call the paper endpoints. No automatic model-training/calibration loop is established by these routes.
- The Groww integration reads account data through Groww's published SDK, restricts requests to loopback clients, and keeps its token in process memory. It does not persist the account snapshot or provide any broker order-write API.
- Historical market candles are distinct from Groww account data and paper trades. Only validated OHLCV rows are persisted in the separate ignored `market_history.db`; the chart uses the archive or explicitly requested bounded Groww history.
- Backtesting uses the production technical and signal-risk services, but does not evaluate the SystemOne score as a trained forecasting model.

See [Product and technical roadmap](./PRODUCT_TECHNICAL_ROADMAP.md) for prioritized fixes and acceptance criteria, [AI decision engine](./AI_DECISION_ENGINE.md) for score semantics, and [Backtesting and paper trading](./BACKTESTING_FEEDBACK_LOOP.md) for simulation limits.

## Architecture direction

Keep a **modular monolith** for now. Split responsibilities behind clear Python interfaces and typed API contracts, but do not introduce microservices until there is a measured scaling or operational need. The next safe seams are:

1. Separate request orchestration from API route handlers.
2. Define a market-data provider interface and a normalized candle contract.
3. Keep indicators and scoring as deterministic domain functions.
4. Isolate backtest execution, fill/cost assumptions, and result reporting.
5. Give persistence explicit repositories and schema migrations.
6. Make the frontend consume typed response contracts and report provider/data status.

Move one boundary at a time, retaining compatibility at the API boundary and adding regression tests before moving behavior.

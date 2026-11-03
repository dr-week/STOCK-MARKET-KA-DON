# SMKD — Codebase Map

File-by-file responsibility table. Every Python and TypeScript source file grouped by architectural layer.

---

## Backend — AI Engine

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/ai/system_one.py` | System-1 fast scorer: blends VWAP, EMA, RSI, ADX, volume, sector, and multi-TF alignment into a composite AI score and trade verdict |

---

## Backend — API Layer

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/api/routes_scan.py` | `/api/scan` and `/api/stock/{symbol}` endpoints; orchestrates all 5 departments and AI engine per symbol |
| `stock-signal-bot/backend/app/api/routes_feedback.py` | `/api/feedback` endpoints for signal outcome recording |
| `stock-signal-bot/backend/app/api/routes_paper.py` | `/api/paper` endpoints for paper-trading positions and P&L |
| `stock-signal-bot/backend/app/api/routes_system.py` | `/api/health`, `/api/backup`, and system-status endpoints |
| `stock-signal-bot/backend/app/api/routes.py` | FastAPI router aggregator — mounts all sub-routers |

---

## Backend — Department Pipeline

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/departments/market_data/service.py` | **Dept 1** — Fetches live 5m, 15m, and daily OHLCV candles from Yahoo Finance; 10-second in-memory cache |
| `stock-signal-bot/backend/app/departments/market_data/collector.py` | Scheduled tick collector / background aggregator |
| `stock-signal-bot/backend/app/departments/market_data/feed_integrity.py` | Detects stale, gapped, or spiked candle data |
| `stock-signal-bot/backend/app/departments/market_data/replay_harness.py` | Replay provider: substitutes fixture JSON for live data in test/replay mode |
| `stock-signal-bot/backend/app/departments/technical_analysis/service.py` | **Dept 2** — Calculates RSI, EMA, VWAP, ATR, ADX, RVOL, Fibonacci, market structure, and m15/H1 trend direction |
| `stock-signal-bot/backend/app/departments/fundamental_analysis/service.py` | **Dept 3** — Fetches news headlines and computes sentiment for a stock |
| `stock-signal-bot/backend/app/departments/market_intelligence/service.py` | **Dept 4** — Nifty 50 trend, live sector heatmap (NSE ETFs via Yahoo Finance), session state |
| `stock-signal-bot/backend/app/departments/signal_risk/service.py` | **Dept 5** — Synthesises Buy/Sell/Watch signal, confluence score, entry/stop/target levels, and position sizing |

---

## Backend — Indicators

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/indicators/technicals.py` | Pure math: RSI, EMA, VWAP, ATR, ADX+DI, RVOL implementations |
| `stock-signal-bot/backend/app/indicators/structure.py` | Market-structure analysis, supply/demand zones, key-candle detection |
| `stock-signal-bot/backend/app/indicators/calculations.py` | Intraday level computation (entry, stop, target) and risk-sizing formulas |

---

## Backend — Market Infrastructure

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/market/fetcher.py` | `fetch_nse_chart()` — generic Yahoo Finance chart fetcher used across departments |
| `stock-signal-bot/backend/app/market/sessions.py` | NSE session state machine (Opening Trap / Prime / Square-Off / Post-Market) |

---

## Backend — Strategies

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/strategies/intraday.py` | Intraday signal generation rules (breakout, VWAP reversion, etc.) |
| `stock-signal-bot/backend/app/strategies/delivery.py` | Overnight/delivery signal rules |

---

## Backend — Paper Trading

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/paper_trading/engine.py` | Simulated order book, fill logic, mark-to-market P&L |
| `stock-signal-bot/backend/app/paper_trading/__init__.py` | Package init |

---

## Backend — Feedback & Calibration

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/feedback/recorder.py` | Records signal outcomes to SQLite for win-rate calibration |
| `stock-signal-bot/backend/app/feedback/__init__.py` | Package init |

---

## Backend — Backtesting

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/backtesting/backtest_engine.py` | Historical replay engine: simulates 5-30 day candle walks with stop/target logic |

---

## Backend — News

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/news/sentiment.py` | Headline sentiment analyser (rule-based keyword scoring) |

---

## Backend — Database

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/db/database.py` | SQLite init, schema migrations, `record_analysis_tree()` |
| `stock-signal-bot/backend/app/db/backup.py` | Automated DB backup with rotation |

---

## Backend — Core

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/core/config.py` | Tracked universe list, account capital, app-wide constants |
| `stock-signal-bot/backend/app/main.py` | FastAPI app factory; CORS, router mounting |

---

## Backend — Tests

| File | Responsibility |
|------|----------------|
| `stock-signal-bot/backend/app/tests/test_system_one_model.py` | Unit tests for the AI scorer |
| `stock-signal-bot/backend/app/tests/test_calculations_edge_cases.py` | Edge-case tests for risk-sizing and intraday level calculations |
| `stock-signal-bot/backend/app/tests/test_backtest_engine.py` | Backtest simulation correctness and API integration |
| `stock-signal-bot/backend/app/tests/test_market_data_freshness.py` | Indicator determinism and feed-freshness tests |
| `stock-signal-bot/backend/app/tests/test_market_data_integrity.py` | Scan resilience and 503 failover tests |
| `stock-signal-bot/backend/app/tests/test_provider_replay.py` | Replay harness fixture tests |
| `stock-signal-bot/backend/app/tests/test_live_provider_integration.py` | Live network integration tests (skipped offline) |
| `stock-signal-bot/backend/app/tests/test_trading_correctness.py` | Risk sizing, short-sell directionality, DB backup |

---

## Frontend — Source (`fast-framework/packages/stock-bot-ui/src/`)

| File | Responsibility |
|------|----------------|
| `main.ts` | App entry point: bootstraps UI, orchestrates `renderApp`, wires DOM events |
| `api/client.ts` | API fetch helpers: `fetchScan()`, `fetchStock()`, `API_BASE` |
| `ui/normalizer.ts` | `normalizeTrade()` — maps raw scan payload to flat trade-row shape; `formatMoney()` |
| `ui/chart.ts` | `renderChart()`, custom SVG chart lifecycle, chart gestures, and local annotations; SVG rendering helpers are in `ui/chart/` |
| `ui/dashboard.ts` | `renderDashboard()` — full HTML template renderer |
| `ui/features/market-overview.ts` | Market overview panel renderer |
| `ui/features/online-icons.ts` | Live-status icon components |
| `ui/data/trades.ts` | Static/default trade row data |
| `data/dashboard.ts` | Dashboard data helpers |
| `state/store.ts` | Lightweight UI state store |

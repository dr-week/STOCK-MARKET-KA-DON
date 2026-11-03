# Backtesting, Paper Trading, and Feedback

## Current implementation

### Historical backtest

`GET /api/backtest/{symbol}` runs `backtesting/backtest_engine.py` against five-minute Yahoo Finance chart data. The API accepts `days` from 1–30, `holding_bars` from 1–60 (default 15), `cost_bps_per_side` from 0–100 (default 5), and an optional threshold comparison.

The simulator:

- Reuses production technical-analysis and signal-risk services; it does **not** evaluate SystemOne's heuristic score as a predictive model.
- Requires 30 warm-up bars, resets indicators at each session, enters at the next bar's open, and closes within that session.
- Checks stop and target against subsequent OHLC bars; if both are crossed in one bar it assumes the stop was hit first.
- Subtracts a flat configured cost per side. It does not fully model exchange/broker taxes, spread, market impact, order queueing, latency, or realistic order-type fills.
- Uses neutral Nifty context and a static fundamental quality filter for historical decisions.
- Can compare thresholds 6–9 on the same requested sample. This is exploratory in-sample comparison, not walk-forward optimization; it does not persist a selected threshold.

Provider coverage and history are limited. A passing test of the simulator's mechanics is not evidence that the strategy is profitable or generalizes.

### Paper ledger

The `/api/paper/*` routes use the persistent SQLite file `backend/app/data/paper_trades.db` and its `paper_positions` table. The dashboard paper view records a paper plan/entry, lists open and closed positions, and lets the user record an exit. The backend validates finite positive prices, integer share quantities, and side-consistent stop/target levels. Closing stores the exit price/time and computes gross P&L atomically once; this is not a broker simulator or live execution integration. Fees, slippage, current market marks, partial exits, and an append-only event audit are not modeled.

`GET /api/paper/pnl` reports lifetime statistics for automatic (`AUTO`) and
manual journal entries separately. Attempted counts include open and closed
positions actually recorded, not scan candidates skipped before opening;
win/loss/breakeven counts and win rate use closed trades only. Gross return is
realized gross P&L divided by closed-trade entry notional (entry price
× quantity); it excludes open trades and fees/costs. The Paper Trading view
shows these journal figures separately from historical backtest results.

Automatic paper trading starts with the backend and scans on weekdays during
NSE session hours about once per minute; the dashboard does not need to be open.
This only records simulated BUY/SELL positions in SQLite. No broker order,
Groww account, or real money is used. Position entry/exit prices are provider
snapshots and threshold simulations, not exchange fills. New entries still
require fresh provider data and pass the existing risk and market-session
rules. The backend must remain running; no NSE holiday calendar is integrated.

The backend exposes a historical backtest on demand for a chosen symbol and
1–30 day sample. The current SMKD Paper Trading UI does not call this endpoint
yet; integrating it requires a change in the separate `fast-framework` checkout.
The response contains simulated outcomes, win rate, average net per-trade
percentage, net compounded return, profit factor, and maximum drawdown. It uses
the historical simulator described above and does not reuse or blend paper-ledger
results.

### Feedback

`/api/feedback/accuracy` and `/api/feedback/calibration` expose reports from the feedback recorder. Their existence does not mean SystemOne is trained or its weights are automatically recalibrated. Preserve outcome provenance and sample counts before using such reports to change a score.

The backend's always-on paper runner scans independently of the dashboard.
Eligible fresh provider signals can open paper positions, and later scans
simulate stop/target exits. Each closed automatic position records its outcome
and point-in-time features.
The separate `/api/feedback/learning` status reports the readiness of the local
research trainer. See the [automatic paper-outcome candidate](./AI_TRAINING_PIPELINE.md#automatic-paper-outcome-candidate).

The trainer runs in a single background CPU worker after an outcome, but only
fits a provider-isolated candidate after 100 eligible win/loss outcomes (at least
20 of each class) spanning 30 sessions. It stores a chronological holdout result
and never affects the production signal or entry path. Paper fills are threshold
simulations using scan snapshots, not exchange fills; fees, spread, slippage, and
intrabar candle ordering are not fully modeled.

## Validation roadmap

Before using backtest results to tune a production signal:

1. Use authorized, sufficiently deep historical data with exchange timestamps, market-session calendars, and point-in-time universe membership.
2. Validate candle ordering, timezone, gaps, corporate actions, and instrument identity; exclude incomplete bars from decisions.
3. Make execution assumptions explicit: next eligible fill, gaps through stops, intrabar stop/target ordering, spread, fees/taxes, slippage, and latency.
4. Separate development, walk-forward validation, and untouched final test periods. Freeze parameters before the final test.
5. Report trade count, net expectancy in R, profit factor, drawdown, exposure, long/short breakdown, period/regime breakdown, and calibration with confidence/sample information.
6. Compare simulated orders with forward paper-trading observations, including missed/partial fills and measured slippage.

Do not set a target win rate or optimize on the test set. Preserve losing and skipped trades, report uncertainty, and never represent a short sample as proof of a durable edge.

## Modular test runner

The offline-first runner keeps AI rules, backtest mechanics, feedback/paper flow, market-data fixtures, and developer-controller tests selectable by suite:

```powershell
npm run test:stock-ai
.\scripts\dev\test-stock-ai.ps1 -Suite ai
.\scripts\dev\test-stock-ai.ps1 -Suite training
.\scripts\dev\test-stock-ai.ps1 -Suite feedback
.\scripts\dev\test-stock-ai.ps1 -Suite paper
.\scripts\dev\test-stock-ai.ps1 -TestPath stock-signal-bot\backend\app\tests\test_backtest_engine.py -Keyword gap
```

Provider integration tests are excluded unless `-LiveProvider` is supplied explicitly. Use `-PythonPath` to select a different interpreter.

## Open-source research

- [Freqtrade strategy customization](https://www.freqtrade.io/en/stable/strategy-customization/), [Hyperopt](https://www.freqtrade.io/en/stable/hyperopt/), and [lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/) are useful references for separating strategy rules, historical parameter experiments, and bias checks. Parameter search is not proof of out-of-sample performance.
- [Microsoft Qlib](https://github.com/microsoft/qlib) is a broad quantitative-research platform with point-in-time data and model workflows. It is not a small drop-in replacement for this application's short-horizon deterministic rules.

The current SystemOne rules and paper-outcome recorder are reusable as a transparent baseline. Keep changes to weights offline until time-ordered evaluation and paper-trade evidence support them.

## Related API and test

- API handler: `stock-signal-bot/backend/app/api/routes_system.py`
- Simulator: `stock-signal-bot/backend/app/backtesting/backtest_engine.py`
- Paper endpoints: `stock-signal-bot/backend/app/api/routes_paper.py`
- Backtest tests: `stock-signal-bot/backend/app/tests/test_backtest_engine.py`

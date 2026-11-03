# Indian Stock-Market Signal Dashboard

This project is a **rules-based decision-support dashboard** for a configured set of NSE stocks. It calculates technical confluence, displays candidate entry/stop/target levels, and links to Groww. It does **not** know the future, place orders, or have a demonstrated ability to predict profitable trades.

> **Important:** Treat every signal as unverified analysis, not a recommendation or a promise of return. Do not trade real money based only on this app. The current implementation has synthetic fallback values and does not reliably identify stale or delayed prices; see [What is and is not trustworthy](#what-is-and-is-not-trustworthy) before using it.

## What actually supplies a decision?

### Providers and data feeds

- **One market-data provider:** Yahoo Finance's chart endpoint (`query1.finance.yahoo.com`). For each stock, the backend requests 5-minute candles and daily candles; it also requests 5-minute candles for the Nifty 50 index. These are multiple requests/series, **not independent confirming providers**. Daily closes are returned for display but are not part of the active intraday score.
- **News:** Google News RSS is queried for up to four headlines per stock and headlines are tagged using keyword matching. News sentiment is displayed, but **is not included in the BUY/SELL score**.
- **No live Groww or direct NSE execution/data feed** is used by the active stock-signal path. Groww links only open the external stock page.
- Setting `SMKD_DATA_MODE=replay` selects local fixtures for market-data requests. Otherwise the market-data service attempts Yahoo Finance. Yahoo's chart endpoint does not guarantee exchange-direct, real-time delivery; availability and delay can vary.

### The active intraday scoring model

The API's `/scan` and `/stock/{symbol}` routes pass the Yahoo stock data through technical analysis and a deterministic score. The signal has **seven scored rule groups, with 10 possible points**:

1. Market structure: **2** points.
2. Supply/demand zone or key-candle confirmation: **2**.
3. Price relative to VWAP: **2**.
4. EMA 9/EMA 21 alignment: **1**.
5. Relative volume (RVOL): **1**.
6. Momentum: RSI, ADX and directional indicators together: **1**.
7. Nifty 50 direction: **1**.

BUY/SELL candidates require at least **7 points** and a risk/reward check; otherwise the result is a watching/scanning state. ATR-derived levels and position sizing are risk calculations, not evidence that a target will be reached. The fundamental quality check can cap a bullish score, but fundamentals and news do not otherwise contribute points.

The dashboard also shows RSI, EMA, VWAP, ATR, Wilder-smoothed ADX/DI, RVOL, price structure, supply/demand zones and Fibonacci levels. A 14-period ADX is withheld until at least 28 completed candles are available. This is not the same as having many independent sources: these are calculations from largely the **same 5-minute OHLCV feed**, so they are correlated inputs.

### Groww cost and movement screen

For BUY/SELL candidates, the dashboard displays a quantity based on the configured per-trade risk budget, estimated round-trip Groww NSE equity charges, the modeled net result at Target 1, and the estimated loss at the stop. It also shows the fee-only minimum quantity whose modeled Target 1 proceeds exceed estimated charges. That minimum is **not** a recommended position size; never increase risk to reach it.

The estimate follows the [Groww pricing schedule](https://groww.in/pricing): equity brokerage at 0.1% per executed order, capped at ₹20 and subject to a ₹5 minimum; intraday STT on the sell leg; stamp duty on the buy leg; NSE exchange, SEBI and IPFT charges; and 18% GST on applicable charges. Rates can change, and the estimate excludes slippage, order execution variance, and any unlisted charges.

ADX is a measure of **trend strength**, not volatility or direction. ADX ≥ 20 is only a heuristic screen. ATR supplies a recent price-range scale; the UI compares it with estimated round-trip charges and requires the modeled target net to be positive before saying the cost/trend checks pass. Passing these screens does not establish an edge or guarantee a profitable trade.

## Is it live? Is it any good, or bluff?

**Honest assessment: it is real code implementing a simple heuristic, but it is not a validated prediction system.** Calling it wholly fake would be inaccurate; calling it a proven or reliable predictor would also be inaccurate.

- In the default mode, the service makes HTTP requests to Yahoo Finance and caches each stock's result in memory for 10 seconds. That is not a streaming feed, and the app does not verify provider timestamps or exclude an in-progress candle before scoring. The timestamp returned for stock data is the local fetch time, not the exchange's candle timestamp. A recent fetch time therefore does not prove that the underlying quote is current.
- Some outputs can look real when they are not. If the Nifty request fails, market intelligence substitutes a fixed Nifty price and change; India VIX and sector-strength values are hard-coded. Fundamental metrics come from a static in-code table (or generic defaults for unknown symbols). If technical history is too short, the technical-analysis service supplies neutral/default indicator values and a flat sparkline. These values are not real-time observations and must not be presented as such.
- The displayed `confidence` is mechanically derived from the confluence score (for example, score 7 becomes 70%). It is **not** a probability of success and has not been calibrated against historical outcomes.
- The backtest now reuses the production technical-analysis and signal/risk decision services, enters at the next bar's open, and reports estimated transaction costs, net returns and drawdown. It uses a neutral Nifty trend because point-in-time historical Nifty context is not yet aligned to each stock bar; this remains a limitation. Costs are a configurable estimate, not exact brokerage/tax/slippage modeling, and the Yahoo intraday sample is limited. Threshold comparison is research-only: it does not automatically change or persist live settings, and results need separate out-of-sample validation.
- Automated tests cover selected calculations, replay fixtures, risk-level directionality and failure handling. They do not prove profitability, robustness across market regimes, or feed freshness in production. The live-provider integration test is opt-in and may be inconclusive when upstream access is unavailable.

**Bottom line:** use this as an experimental scanner/learning aid only. Before considering real-money use, remove or explicitly label synthetic fallbacks, expose provider and exchange timestamps plus stale/delayed status, validate completed candles, and test the strategy over a sufficiently long, out-of-sample, cost-inclusive dataset with paper trading. The current backtest is a first research tool, not proof of an edge. No performance claim is made here.

For the research threshold comparison, the backend accepts `optimize=true` on `/api/backtest/{symbol}`. It compares thresholds 6–9 on the requested sample only; it deliberately does not choose a production value or change the live strategy. A short-window comparison can overfit and should not be used to configure real trades.

## Architecture

- Backend: FastAPI in `stock-signal-bot/backend`; routes call market data, technical analysis, fundamental/news display, market intelligence and the signal/risk engine.
- Frontend: Vite application in `fast-framework/packages/stock-bot-ui` using the Zuari framework packages.
- Replay fixtures: `stock-signal-bot/backend/app/tests/fixtures/market_data`.
- Configured stock universe and risk parameters: `stock-signal-bot/backend/app/core/config.py`.

## Run locally

From the repository root, start the backend in one PowerShell terminal:

```powershell
cd stock-signal-bot/backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Then start the frontend from the repository root in another terminal:

```powershell
cd fast-framework/packages/stock-bot-ui
pnpm run dev
```

Open the Vite URL shown in the terminal. The backend API documentation is at `http://127.0.0.1:8000/docs`.

To use deterministic local market-data fixtures for backend development, set the mode in the backend PowerShell terminal before starting the server:

```powershell
$env:SMKD_DATA_MODE = "replay"
```

Replay fixtures are for tests/development and are not live prices.

## Tests

From `stock-signal-bot/backend`, run the existing unittest suite with:

```powershell
python -m unittest discover -s app/tests
```

The live-provider integration tests are opt-in. To enable them in PowerShell, set the variable before running the suite:

```powershell
$env:SMKD_LIVE_PROVIDER_TESTS = "1"
```

They require upstream network access and do not constitute a performance test.

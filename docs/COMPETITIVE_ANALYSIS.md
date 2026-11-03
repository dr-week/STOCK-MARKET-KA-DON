# Competitive Research and Product Gaps

**Reviewed:** 2026-11-02. This is a functional comparison against public product documentation, not a claim that SMKD matches professional platforms or that their signals are profitable.

## What to learn from adjacent products

| Product/reference | Publicly documented capability | Practical lesson for SMKD |
|---|---|---|
| TradingView Paper Trading | Simulated orders and positions; order ticket, chart trading, and depth-of-market interface | A paper workflow should track order lifecycle and execution assumptions, not only store manually entered positions. |
| TradingView Strategy Tester | Historical strategy testing, metrics, trade list, and forward testing as data updates | Show reproducible run settings and trade-level evidence, not only a single aggregate score. |
| TradingView charting product | Broad chart interaction, drawing tools, indicators, and layout customization | Use as a product capability reference only. SMKD implements its chart renderer in-repo and must not embed TradingView or its charting library. |
| KLineChart | Open-source canvas chart with built-in indicator and drawing APIs | An alternative library for future evaluation; SMKD currently uses its own SVG implementation and should adopt a library only after an explicit product decision. |
| Zerodha Kite Connect historical API | Timestamped OHLCV candles at several intervals, keyed by instrument token | Model provider identity, instrument mapping, interval, authorization, coverage, and timestamps explicitly behind a provider interface. This is a possible integration reference, not a recommendation to switch vendors. |
| QuantConnect research guidance | Hypothesis-driven tests, walk-forward/out-of-sample evaluation, and warnings about look-ahead and survivorship bias | Treat backtest selection and point-in-time data as first-class research controls. |
| QuantConnect execution modeling | Fill and slippage assumptions affect simulated results; slippage depends on latency and market conditions | A flat basis-point deduction is only a rough cost estimate; label it and test sensitivity. |

## SMKD baseline versus useful next capabilities

| Area | Verified today | Gap / recommended direction |
|---|---|---|
| Intraday analysis | Five-minute Yahoo chart data; aligned OHLCV validation; incomplete-bar filtering; indicator warm-up gate | Verify provider freshness, corporate-action handling, session gaps, and source reliability before treating results as current. |
| Higher-timeframe context | 15-minute candles and daily-close EMA proxy are used by SystemOne | Rename the daily proxy accurately; validate that the data is sufficient and point-in-time. |
| AI/analytics | Deterministic hand-written weights and threshold labels | No trained model or measured predictive precision. Keep outputs clearly marked experimental until calibrated on held-out outcomes. |
| Breadth / sector | A small set of sector indices; fixed sector fallback exists | Add breadth only with a documented, authorized source and explicit missing/stale state. Do not substitute static values for live context. |
| Market depth | No order-book feed in the scan path | Defer until a licensed provider exposes usable depth; aggregated candle volume is not order flow. |
| Backtest | Five-minute, 1–30-day provider window, next-open entry, simple flat costs | Add deep point-in-time history, explicit execution models, walk-forward evaluation, and trade-level audit output before model tuning. |
| Paper trading | SQLite API for manual paper positions | Integrate the UI only after validating position lifecycle, current marks, fees, and realized/unrealized P&L. |
| Frontend integration | UI fetches `/api/scan`; validates typed scan and source-quality fields; shows loading/error/empty/partial states without sample fallbacks | Add API-level contract tests and stale/delayed-feed UX after freshness semantics are defined. |
| Execution | Groww deep link in scan payload | No broker order placement is implemented in this flow. Keep execution out of scope until separate authorization, risk, and audit controls exist. |

## Chart, news, and AI integration status

- The primary chart uses SMKD's own SVG renderer for validated OHLCV candles, toggleable volume/EMA 9/21/RSI 14, proposed entry/stop/target levels, Groww execution markers, and user horizontal marks saved per symbol in local browser storage. It includes scroll zoom and drag-to-pan. Indicator implementations match the backend's current EMA seed and rolling-average RSI formulas; RSI is absent until 14 price changes are available. This is visualization, not a change to the strategy signal.
- The chart code and renderer are in the repository; the frontend does not depend on TradingView or a third-party charting library. Other indicators and advanced drawing operations remain unimplemented.
- Public GitHub repositories can supply chart code and examples, but they are not a market-data source or evidence of rights to reuse candle datasets. Select market-data providers separately based on coverage, freshness, terms, and display/redistribution rights.
- The News desk surfaces the scan's existing Google News RSS headlines. Sentiment is still keyword tagging of titles, not NLP/FinBERT; an empty response does not imply there was no news. No additional feed vendor was connected because NSE coverage, freshness, redistribution rights, quotas, and credentials are not yet established.
- SystemOne details are surfaced as experimental rule output only. Its score and action are not a calibrated forecast, and this UI deliberately does not display its computed `probable_move_pct` as a prediction.

## Useful project and practitioner communities

These are places to inspect library issues/examples or discuss implementation. They are not market-data providers, and code from them should be reviewed for license, maintenance, data rights, and security before reuse.

- [KLineChart GitHub repository and discussions](https://github.com/klinecharts/KLineChart) — alternative chart library with indicator support and an active project discussion area.
- [QuantConnect Forum](https://www.quantconnect.com/forum/) — quantitative research, strategy testing, and execution-model discussions.
- [Quantitative Finance Stack Exchange](https://quant.stackexchange.com/) — focused questions on quantitative methods; validate answers against primary sources and reproducible calculations.

## Sources

- TradingView, [Paper Trading](https://www.tradingview.com/support/solutions/43000516466-paper-trading/).
- TradingView, [Backtesting and forward testing](https://www.tradingview.com/support/solutions/43000562362-strategy-tester/).
- Zerodha Kite Connect, [Historical candle data API](https://kite.trade/docs/connect/v3/historical/).
- KLineChart, [GitHub repository](https://github.com/klinecharts/KLineChart) and [documentation](https://www.klinecharts.com/).
- QuantConnect, [Research guide](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide).
- QuantConnect, [Trade-fill models](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/trade-fills/key-concepts) and [slippage modeling](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/slippage/key-concepts).

Pages checked on 2026-11-02. Product capabilities and provider terms can change; confirm current licensing, API access, latency, and data rights before integration.

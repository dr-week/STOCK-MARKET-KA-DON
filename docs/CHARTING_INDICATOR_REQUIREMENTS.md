# Charting and Indicator Requirements

**Status:** Requirements plus current implementation checkpoint. The roadmap remains the project-wide status source.

## Library and product boundary

SMKD's primary chart is rendered in-app by SMKD's own SVG renderer from validated market data. It does not use a TradingView widget, TradingView Lightweight Charts, or another third-party chart engine. TradingView is a competing product and workflow reference only. Do not copy proprietary UI assets, code, or paid indicators.

## Implementation plan and status

1. **Custom chart baseline — implemented:** an in-repo SVG renderer draws validated candle history with price/time axes, price scale, volume, EMA 9/21, RSI 14, proposed levels, Groww fill marks, and locally saved horizontal annotations. The renderer is independent of TradingView and external charting libraries.
2. **Useful first controls — implemented:** EMA 9, EMA 21, RSI 14, and per-candle volume can be toggled. The current proposed entry, stop, and target 1 are drawn only for a valid directional BUY/SELL candidate. Horizontal user marks are placed by clicking the chart and saved per symbol in this browser's local storage; they are annotations, not orders.
3. **Data-backed intervals — first slice implemented:** 1m, 3m, 5m, 15m, 1H, and 1D controls read validated local archived candles; the user can explicitly fetch a provider-bounded Groww range ending on a selected date. Multi-year automated backfill, resumption, and provider-independent coverage remain pending.
4. **Richer drawing and journal linkage — pending:** add trend lines/rays, edit/delete/select annotations, templates, and paper-position-linked levels only with explicit interaction design, persistence semantics, and tests. Do not promise drag-to-edit until supported and tested.
5. **Additional studies — pending:** add SMA, session-reset VWAP, ATR, and later MACD/Bollinger Bands through shared, tested calculation functions. Do not duplicate backend signal math or imply study output improves signal precision.
6. **Authorized data coverage — pending:** Groww's documented historical-candle API is the first supported backfill source; verify current subscription and data-use terms before relying on it. NSE/BSE archive availability and terms remain unverified. Do not source production candles from GitHub repositories, scraped files, or unverified free snapshots.

GitHub is useful for chart libraries, plugins, examples, and calculation implementations. A public code repository is not an authoritative or licensed market-data feed. Keep provider credentials server-side; validate every received instrument, timestamp, interval, and OHLCV record before charting.

## Chart data contract

- Render only backend-provided, validated OHLCV candles. Never synthesize candles to fill gaps or extend the visible history.
- Keep timestamps ordered, timezone-aware, and associated with the correct NSE instrument and interval. Exclude incomplete bars from calculations unless explicitly shown as an in-progress bar.
- Display instrument, exchange, interval, provider, data mode, and source/fetch time where the backend makes them available. Distinguish provider data, replay, stale/delayed data, insufficient history, and unavailable data.
- Treat missing history, malformed candles, unsupported symbols, or provider failures as explicit chart states. Do not silently substitute another symbol or timeframe.
- Render a timeframe only from validated candles for that interval. The current controls offer 1m, 3m, 5m, 15m, 1h, and 1d; missing intervals show an explicit no-data state. Daily close-only series are not candlesticks.
- The chart view must resize with its container, remain usable at narrow widths, and provide keyboard-accessible controls and a textual status/readout.

## Initial studies

Implement studies as deterministic calculations over the same validated candle series. Each study must declare its input interval, parameter values, warm-up requirement, and display name. Show a warm-up/insufficient-history state instead of emitting a default value.

| Study | Purpose | Requirement |
|---|---|---|
| Volume | Participation context | Show per-candle volume; do not call it order flow or market depth. |
| EMA and SMA | Trend context | Configurable period; calculation convention documented and tested against the backend if shared. |
| VWAP | Session price reference | Require valid intraday volume and a defined session reset; no carry-over between sessions. |
| RSI | Momentum context | Define lookback and initialization method; expose overbought/oversold guides as references, not signals. |
| ATR | Volatility context | Define lookback and units; do not imply that ATR itself defines a safe stop. |
| MACD / Bollinger Bands | Optional later studies | Add only after chart controls, calculations, tests, and visual performance are established. |

Do not display all studies by default. Allow users to toggle supported studies and keep defaults limited to candles, volume, and a small set of useful overlays. Indicator values are descriptive calculations, not independent evidence of a profitable signal.

## 5-minute price-action patterns — first heuristic slice

The backend describes selected shapes on the latest completed 5-minute candles: doji, context-qualified hammer/shooting-star, context-qualified bullish/bearish engulfing, and conservative bull/bear flag-like pullbacks. These rules emit a name, direction, short explanation, confirmation level, and invalidation level; they do not emit a probability, BUY/SHORT instruction, or expected return. A flag-like pullback is explicitly marked as forming and needs a later completed close through its boundary; volume expansion is a useful check, not currently a detection guarantee.

The definitions are intentionally simplified, deterministic heuristics. A hammer/shooting-star shape requires trend context; engulfing compares real bodies and also requires prior trend context. A doji is neutral. The flag detector is a short-window intraday approximation and must not be presented as a classic, validated multi-week flag. Missing/malformed OHLCV is not converted into a pattern. UI copy must explain that detected shapes can fail and must be considered with data freshness, trend, volume, levels, and risk controls.

No evidence currently establishes that these rules improve returns. Before any signal weighting or automated entry, evaluate them on validated historical data with completed candles only, realistic costs/slippage, out-of-sample periods, and benchmark comparisons. Keep paper/live execution separate from descriptive pattern output.

## Trade-plan overlays

- Draw entry, stop, and only the targets that the active, validated analysis contract supplies.
- Label each level, its source (rule-derived or user-entered), and whether it is proposed or an actual paper fill.
- Keep target 1 and target 2 separate. A third target is unavailable until a strategy rule defines it and tests its direction, edge cases, and backtest semantics.
- Never convert an experimental AI score or a percentage transformation of that score into a chart price level.
- If the data is insufficient or signal is `WAIT`, the chart may still show valid price history, but must not imply a ready-to-trade setup.

## Implementation boundaries

- **Market-data API/service:** owns provider access, instrument mapping, timestamp/timezone normalization, validation, and interval coverage.
- **Technical-analysis domain:** owns reusable study calculations and warm-up/data-quality results; UI chart utilities must not become a second source of signal calculations.
- **Chart UI module:** owns chart lifecycle, series rendering, study toggles, and overlays; it must not fetch providers or calculate trade recommendations.
- **UI controller:** owns selected symbol, interval, and enabled-study state and passes explicit data to the chart.
- **Tests:** cover calculation boundaries, warm-up lengths, invalid/unaligned candles, timeframe switching, chart disposal/re-render, and absence of overlays when levels are unavailable.

Keep SVG rendering and interaction logic in the chart module, separate from provider and analysis logic. Avoid duplicating provider, indicator, or signal business logic in components.

## Acceptance criteria

- A symbol's candles render only when their identity, timestamps, OHLCV values, and interval pass validation.
- Switching symbol or interval never leaves the previous series or trade levels visible.
- Each study's values match its documented formula and are absent until its warm-up completes.
- The UI does not claim exchange-real-time freshness when the provider does not establish it.
- Chart rendering and study selection do not alter the backend signal or backtest calculations.
- Chart rendering works without third-party charting libraries or external chart widgets.

## References

- [Zerodha Kite Connect historical candles](https://kite.trade/docs/connect/v3/historical/) — example of an API that provides timestamped interval candles; access, rights, and terms must be evaluated before adoption.
- [StockCharts Candlestick Pattern Dictionary](https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-pattern-dictionary.md) — educational definitions for doji, hammer, shooting star, and engulfing patterns; not evidence of profitability.
- [StockCharts Flag and Pennant Patterns](https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/flag-pennant.md) — describes prior impulse, consolidation, breakout, and volume context; the application's intraday flag-like heuristic is narrower and unvalidated.
- [TradingView paper trading and chart trading capabilities](https://www.tradingview.com/support/solutions/43000516466-paper-trading/) — workflow reference only; not a design/code source for copying.
- Current candle shape and quality limitations: [Data specification](./DATA_SPECIFICATION.md).

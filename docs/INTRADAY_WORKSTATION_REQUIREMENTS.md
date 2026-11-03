# Intraday Workstation Requirements

**Status:** Product requirements and acceptance criteria; not a claim that every item is implemented.

## Product purpose

SMKD is an NSE intraday analysis and research workstation. It should help a user inspect market activity, understand why a rule-based signal appeared, plan and record a paper trade, and review outcomes. It must not promise a profitable edge or present experimental scores as probabilities.

The current implementation and its known data limitations remain documented in the [product roadmap](./PRODUCT_TECHNICAL_ROADMAP.md). This document specifies the user-facing workflow; it does not duplicate provider research, AI formulas, or API schemas.

## Information hierarchy

The selected-symbol workspace should prioritize:

1. **Instrument and data state:** exchange/symbol, selected interval, provider, source time when available, local fetch time, and available/stale/delayed/insufficient/unavailable state.
2. **Price action:** validated candlesticks and volume, with only the indicators and overlays the user has enabled.
3. **Trade plan:** current signal state, planned entry, stop, available targets, reward/risk derived from those levels, and sizing assumptions.
4. **Context:** market/session state, selected technical readings, and relevant company or market headlines with source and publication time.
5. **Explanation:** rule reasons and explicitly experimental analytics, separated from observed data and calculated indicator values.

Do not repeat the same score, entry, stop, target, or signal in multiple cards. Prefer one compact summary with links or controls to inspect detail. Do not fill empty space with decorative gauges or unsupported indicators; use it for the trade plan, source freshness, or relevant catalysts.

## Layout and interaction

- Keep the symbol list and selected-symbol workspace distinct. Selecting a symbol must update chart, analysis, news, and trade-plan context together.
- Use the chart as the primary visual surface. Put the compact trade-plan panel alongside it on wide screens; on narrow screens, stack or tab the details without hiding the data-quality state.
- Keep timeframe and indicator controls adjacent to the chart. A control may only be enabled when its data and calculation are supported.
- Keep paper-trade entry and open-position management in a dedicated journal view or focused panel, not duplicated in every scanner row.
- Show loading, empty, partial, stale, insufficient-history, and error states explicitly. Preserve a clear retry path for recoverable fetch failures.
- Keyboard operation, visible focus, readable contrast, and text alternatives for chart status are required. Do not communicate signal direction by color alone.

## Signal and level semantics

- Distinguish observed provider values, calculated technical values, rule-derived levels, and user-entered values in both labels and API/UI types.
- A `WAIT` or insufficient-data state must not expose a submit-ready trade plan.
- Display only levels returned by a validated rule or explicitly configured strategy. Current analysis returns target 1 and target 2; target 3 is **not defined**. Do not invent or extrapolate a third target.
- Show reward/risk only when entry, stop, and target are finite, positive, directionally consistent, and based on the same plan. State whether the prices are proposed levels or user-confirmed fills.
- Risk sizing must disclose the account value and risk budget used, be calculated from the entry-to-stop distance, and remain a planning aid. Do not assume a risk percentage or imply that a quantity is suitable for the user.
- No price, candle, indicator, news item, or signal may be filled with a demo/default value on live-data failure. See [data contracts and gaps](./DATA_SPECIFICATION.md).

## News and AI presentation

- News must show source, linked article when available, publication time, and ticker association. Missing headlines mean coverage is unavailable, not that no catalyst exists.
- Keyword sentiment and SystemOne scores must remain visibly labeled as experimental heuristics. Never call them calibrated AI, a forecast, or a recommendation.
- Keep rule explanations traceable to the inputs and rules used. Do not allow generated text to create a price target or hide missing/stale input data.
- Provider selection, licensing, freshness, and the current AI limitations are tracked in [competitive research](./COMPETITIVE_ANALYSIS.md) and [AI decision scoring](./AI_DECISION_ENGINE.md).

## Delivery order

1. Consolidate repeated signal/price metrics and use the right-side workspace for source state, a concise trade plan, and relevant context.
2. Integrate the existing paper API as a clearly labeled manual paper journal; never route this UI to a broker.
3. Improve the local chart with data-backed timeframe and indicator controls, reusing validated market data and shared calculations.
4. Add richer news or model-based analysis only after provider rights, freshness, source coverage, and evaluation are established.

## Acceptance criteria

- A user can tell which symbol and interval are shown, when the data was sourced/fetched, and whether it is usable.
- No live-looking example/fallback values appear when scan or candle data is missing.
- Selecting a symbol synchronizes its chart, levels, news, and analysis without stale content from the previously selected symbol.
- A visible trade plan never displays a fabricated target 3 or an unsupported risk/reward value.
- The UI labels rules, provider facts, calculations, and manual journal values distinctly.
- At common desktop and narrow viewport widths, the primary chart and trade workflow remain reachable without duplicating the same metrics.

## Related requirements

- Paper-trade lifecycle and stored fields: [Paper-trade workflow](./PAPER_TRADE_WORKFLOW.md).
- Chart library, supported studies, and data states: [Charting and indicator requirements](./CHARTING_INDICATOR_REQUIREMENTS.md).
- Existing backend/frontend boundaries: [Architecture](./ARCHITECTURE.md).

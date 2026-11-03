# API Specification

## Endpoints

### 1. `GET /api/session`
Returns current IST market status and active trading permission.
```json
{
  "phase": "PRIME_MOMENTUM_1",
  "can_trade_intraday": true,
  "ist_time": "10:30:15"
}
```

### 2. `GET /api/scan?filter_type=all`
Scans universe and returns ranked opportunities.
- Query params: `filter_type` (`all`, `intraday_buy`, `intraday_sell`, `delivery_buy`)
- `technicals.price_action_patterns` lists heuristic patterns detected on completed 5-minute candles, with direction, explanation, confirmation level, and invalidation level. This field is descriptive only and does not change the BUY/SHORT/WAIT decision.
- `technicals.adx` and directional-index values remain unavailable until 28 completed 5-minute candles; `technicals.data_quality` reports the available bars, warm-up requirement, and pending indicators.
- `ai_decision.win_probability` is an uncalibrated heuristic estimate, not a historically validated success rate or guarantee.
- Indicator values and pattern levels are unavailable when their required candle inputs are insufficient. Patterns are uncalibrated and must not be interpreted as a price forecast or guaranteed trade.

### 3. `GET /api/stock/{symbol}`
Detailed breakdown with technical indicators, levels, reasons, and news.

### 4. `GET /api/backtest/{symbol}`
Research-only historical simulation of the production technical and signal/risk rules using five-minute Yahoo Finance candles.
- Query params: `days` (1–30, default 5), `holding_bars` (1–60, default 15), `cost_bps_per_side` (0–100, default 5), `optimize` (boolean, default false).
- Response includes trade count, net-positive percentage, estimated net returns, drawdown, and a recent trade sample.
- With `optimize=true`, returns a threshold comparison for confluence cutoffs 6–9. It does not update production configuration. The comparison can overfit its sample; validate independently before considering any strategy change.
- Historical Nifty context is held neutral, costs are estimates, and results do not guarantee live execution or future performance.

## Groww URL Scheme
```
https://groww.in/stocks/{company-slug}
```
Directly launches stock chart & order placement modal on Groww.

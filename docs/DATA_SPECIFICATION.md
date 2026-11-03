# Current API Data Shape and Contract Gaps

**Status:** Observed implementation, not a validated or versioned API contract. Values shown below are types/placeholders, not market data.

## Endpoints

| Method and path | Current response |
|---|---|
| `GET /api/scan` | `{ intelligence, count, results, failed_symbols, is_partial }`; results are sorted by descending primary confluence score |
| `GET /api/overview` | Market/session intelligence |
| `GET /api/stock/{symbol}` | One stock analysis object; 503 when market data cannot be fetched |
| `GET /api/backtest/{symbol}` | Historical simulation summary and recent trades; provider/validation errors may be returned in the JSON body |
| `/api/paper/*` | Manual paper order, close, positions, history, and P&L routes |
| `/api/feedback/*` | Accuracy and calibration report routes |

## Stock result fields currently returned

```text
symbol, name, sector, current_price, change_pct, day_high, day_low, groww_url
market_data:
  volume_today, timestamp
  data_quality:
    provider, instrument_id, interval, mode, status, fetched_at, source_timestamp,
    last_complete_candle_timestamp, invalid_5m_candles, excluded_incomplete_5m_candles
  candles_5m: opens[], highs[], lows[], closes[], volumes[], timestamps[]
  candles_15m: opens[], highs[], lows[], closes[], volumes[], timestamps[]
  candles_daily: closes[]
technicals: indicator, market-structure, supply/demand, and trend fields
fundamentals: static company metrics, quality_filter_passed, news, news_summary
signal_decision: signal, confluence_score, confidence, entry, targets, stop_loss,
  risk_sizing (unavailable when history is insufficient), reasons
ai_decision: ai_score, ai_verdict, recommended_action, win_probability,
  expected_value, signal_quality, probable_move_pct, probable_move_label,
  system_one_rules, summary
intraday: a flattened duplicate of selected signal, technical, risk, and AI fields
news[]
```

`ai_decision` is `null` when the technical warm-up gate reports insufficient history. In that case the signal is `WAIT`, the confluence score is zero, risk sizing is unavailable, and indicator values are not synthesized.

`/api/scan` currently sorts by `signal_decision.confluence_score`, not by a validated probability or expected return. A high confluence score is not an empirically established “best stock” ranking.

## Known contract and data-integrity problems

- The backend has no versioned Pydantic response model for this result. The frontend now validates a minimal scan/stock contract and source-quality metadata.
- `market_data.timestamp` remains the local fetch time in Unix seconds. `data_quality` adds provider/replay mode, provider source time when supplied (otherwise the latest complete five-minute candle start), and candle-quality counts; this is not proof of a real-time feed.
- Candle OHLCV values are now validated row-wise, preserving timestamp alignment; incomplete 5m/15m and daily bars are excluded in provider mode. This does not yet classify stale/delayed data against an exchange calendar.
- `candles_daily` exposes closes only, unlike the intraday arrays.
- Technical analysis now reports insufficient history and omits indicator defaults and fabricated sparkline values until 21 complete five-minute bars are available. Fixed market-context fallbacks and static company fundamentals can still appear in the same response.
- `ai_decision.win_probability`, `expected_value`, and `probable_move_pct` are heuristic outputs, not calibrated forecasts. See [AI decision scoring](./AI_DECISION_ENGINE.md).
- Some API failures are represented as a `failed_symbols` entry, while complete failure returns HTTP 503; provider-specific causes are not consistently surfaced.

## Contract to implement

The first provider-quality fields are now returned and validated. Complete the market-data envelope before expanding consumers; it should distinguish:

```text
provider, instrument_id, interval
source_timestamp, received_timestamp
mode: provider | delayed | replay | unknown
quality: available | stale | incomplete | invalid | insufficient | unavailable
reason
```

The candle contract should use a list of timestamped OHLCV records (rather than parallel arrays), with explicit timezone and ordering. Validate finite positive prices, `low <= open/close <= high`, nonnegative volume, interval/session consistency, duplicate timestamps, and candle completeness before calculations. A failed or stale feed must not be replaced by fixed or example prices.

Use explicit response schemas for scan, stock detail, errors, and backtest runs. Keep backward compatibility intentionally versioned; make unavailable values nullable with a status/reason rather than silently substituting zero, neutral metrics, or a plausible-looking default. Provider-specific errors, exchange-calendar freshness states, candle records (instead of parallel arrays), and schema versioning remain pending. See the [product roadmap](./PRODUCT_TECHNICAL_ROADMAP.md) for acceptance criteria.

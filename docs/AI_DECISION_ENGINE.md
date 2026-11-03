# AI and Decision Scoring

## What is implemented

`stock-signal-bot/backend/app/ai/system_one.py` contains a deterministic, hand-written scoring class (`SystemOneDecisionModel`). It is not a trained machine-learning model, LLM, price-pattern model, or online-learning system. It has no model-training pipeline or empirically fitted weights.

For each stock, `api/routes_scan.py` first calls the separate `signal_risk` service to produce the primary BUY/SELL/WATCH decision and risk levels. It then calls SystemOne and returns its score/verdict as a second, supplementary analysis block. The SystemOne verdict does not replace the primary signal.

## Inputs and score

SystemOne starts from `0.50`, applies fixed adjustments, clamps the result to `[0.05, 0.95]`, and emits the fired rules. Inputs include VWAP distance, EMA spread, RSI, news sentiment, ADX/trend strength, relative volume, support/resistance, price structure, market regime, session phase, 15-minute and hourly trend signals, and sector strength.

Current adjustments include:

| Input | Current rule |
|---|---|
| Price vs. VWAP | Above/below 0.15%: `+0.15` / `-0.15` |
| EMA 9/21 spread | Above/below 0.1%: `+0.12` / `-0.12` |
| RSI | 55–68: `+0.12`; above 74: `-0.18`; 30–45: `-0.10`; below 25: `+0.08` |
| News sentiment | BULLISH/BEARISH: `+0.08` / `-0.08` |
| ADX | At least 25: `+0.08` plus a trend-strength adjustment; below 18: `-0.06` |
| Relative volume | At least 1.4: `+0.10`; at most 0.8: `-0.06`; an additional confirmation flag can add `+0.06` |
| Structure / market | Structure: `+/-0.07`; trending/range regime: `+/-0.04` |
| Timeframes / sector | Aligned 15m and daily proxy: `+0.08`; conflict: `-0.10`; sector: `+/-0.06` |

These are heuristic weights, not evidence that the features independently predict outcomes. Many inputs derive from the same OHLCV series and are correlated.

## Output semantics: experimental, not calibrated

| Output | Implementation | Correct interpretation |
|---|---|---|
| `ai_score` | Fixed weighted rules | A heuristic score, not a probability |
| `ai_verdict` | Score thresholds | A rule label; not a validated recommendation |
| `win_probability` | Piecewise formula based only on score | An unvalidated estimate; it is not fitted to completed trades |
| `expected_value` | `p * assumed_RR - (1 - p)`, with caller-supplied `RR=2.5` | A hypothetical value that inherits the unvalidated probability and reward/risk assumptions |
| `signal_quality` | Thresholds on that EV | Not evidence of profitable trade quality |
| `probable_move_pct` | `(ai_score - 0.5) * 8` | A display transformation, not a price forecast |

There is a directional mismatch: low scores can produce a strong **sell** verdict, while the probability mapping and EV formula treat lower scores as lower win probability for a generic trade. As a result, sell-side probabilities/EV are not a meaningful short-trade calibration. The input named `change_pct` is also populated with price-versus-VWAP percentage in `routes_scan.py`, not the stock's daily change.

There is also a regime-contract mismatch: the scan passes Nifty labels such as `BULLISH`, `BEARISH`, or `SIDEWAYS`, but the scorer's regime adjustments check for `TRENDING` and `RANGE`. Those adjustments therefore do not represent the current Nifty labels.

The opening-trap score reset occurs before later score adjustments; it is not a hard SystemOne output block. The primary `signal_risk` service separately returns `WAIT` during its opening trap phase.

## Evidence required before calling this predictive AI

1. Preserve point-in-time input features, provider timestamps, model/rule version, signal side, entry/exit policy, and realized outcome.
2. Use a time-ordered, point-in-time dataset; keep training, tuning, and final evaluation periods separate.
3. Report sample size and calibration (for example reliability bins and Brier score) in addition to net return, expectancy, drawdown, and costs.
4. Evaluate long and short outcomes separately. Do not equate heuristic score, confluence, or win rate with a calibrated probability.
5. Compare against simple baselines and require repeatable out-of-sample and paper-trading results before changing live display semantics.

The formulas above document existing behavior so it can be tested and replaced deliberately; they are not endorsed as a strategy.

## Optional offline forecasting experiment

`backend/app/research/benchmark_cli.py` evaluates the open-weight Chronos-Bolt Small model against a last-close baseline using one provider-specific series from the local candle archive. It uses the final 20% of observations as a rolling holdout, requires at least two non-overlapping forecast windows, and reports price MAE. It does not train a model, call a hosted AI API, update SystemOne, or affect live signals.

From `stock-signal-bot/backend`, install the optional `chronos-forecasting` and PyTorch packages in a separate research environment, then run:

```powershell
python -m app.research.benchmark_cli --symbol RELIANCE --provider yahoo_finance_public_unofficial --interval 5m
```

The provider ID must exactly match the archive. Model weights are downloaded on first use; this requires network access. The current archive is short and uneven across symbols, and some existing history came from an unofficial provider. Treat results as a software experiment only, not as evidence of a live trading edge or permission to redistribute source data. Do not send brokerage credentials or account/order data to hosted model APIs.

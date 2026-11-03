# Free market data and AI research register

**Reviewed:** 2026-11-03  
**Scope:** Publicly documented sources and model projects relevant to this repository. This is a research snapshot, not legal advice or a guarantee of current availability. Verify provider terms, quotas, symbols, latency, and redistribution rights before implementation.

## Decisions

- There is no verified, unrestricted, no-cost, licensed NSE real-time feed established for unattended production use. Treat "free tier" as quota-limited and subject to change; do not call it exchange-direct live data.
- Keep production signals deterministic and provider failures explicit. Never replace unavailable live data with fixtures or synthetic values.
- Do not send market/account/order inputs to hosted AI services by default. Hosted free tiers can change limits and data-use terms; no model is approved as a production trading predictor.
- Evaluate pretrained time-series models offline against a chronological holdout and a persistence baseline before considering further work. A benchmark result is not a strategy backtest.
- Dataset availability is not permission to use data commercially or redistribute it. Record source, collection date, license, and provenance for each dataset before training.

## Sources and evidence

| Topic | Primary source | What it establishes | Caveat / repository action |
|---|---|---|---|
| Yahoo Finance data | [Yahoo terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) | Yahoo content is governed by Yahoo terms. | Not an exchange-authorized production feed; review terms and source timestamps. Existing adapter is best-effort, not a real-time guarantee. |
| NSE products | [NSE market data](https://www.nseindia.com/market-data) | NSE documents its market-data products and access pathways. | Confirm product entitlement, use, symbols, latency, and redistribution terms directly with NSE before relying on data. |
| Alpha Vantage | [Plans and support](https://www.alphavantage.co/premium/) | Service publishes its plan/pricing and API terms. | A no-cost key is rate-limited; verify current endpoint coverage and terms before use. |
| Twelve Data | [Pricing](https://twelvedata.com/pricing) | Service publishes plan and quota details. | Free access is limited and may not include the needed exchange, interval, or commercial rights. |
| GDELT | [GDELT data](https://www.gdeltproject.org/data.html) | Public news/event metadata and data access are documented. | News/event metadata is not a price/candle source; validate coverage, freshness, and reuse conditions. |
| Chronos | [Chronos repository](https://github.com/amazon-science/chronos-forecasting) | Open time-series forecasting code and model artifacts are published. | Model quality on broad benchmarks does not establish NSE predictive value. Keep inference in offline research until locally validated. |
| Public datasets | [Kaggle datasets](https://www.kaggle.com/datasets) | User-uploaded datasets can be discovered. | A platform listing or uploader label alone does not establish exchange provenance, completeness, or a usable license. |

## Local implementation status

- **SystemOne:** deterministic, hand-coded scoring. Its probability/expected-value-like outputs are not calibrated by a validated training pipeline; see [AI decision engine](../AI_DECISION_ENGINE.md).
- **Chronos benchmark:** offline-only chronological holdout against last-close persistence. Optional inference dependencies/weights are not bundled. See the same [AI decision engine](../AI_DECISION_ENGINE.md).
- **Supervised training:** research-only readiness checks and artifact handling; training must refuse insufficient or conflicting history. See [AI training pipeline](../AI_TRAINING_PIPELINE.md).
- **Data quality:** existing local history is uneven and too sparse to claim reliable broad-symbol training coverage. Provider aliases must remain isolated; conflicting duplicate candles are not to be silently merged.

## Recheck checklist

Before adding a provider, model, or dataset, record:

1. Official source URL and date checked.
2. Exact instrument/interval coverage, timezone, publication delay, quotas, and failure behavior.
3. Commercial use, retention, redistribution, and model/data licenses.
4. Validation evidence using chronological splits and a simple baseline.
5. Local code path, tests, and whether credentials or private inputs leave the machine.

Recheck provider pricing/terms immediately before implementation and at least quarterly for any active integration.

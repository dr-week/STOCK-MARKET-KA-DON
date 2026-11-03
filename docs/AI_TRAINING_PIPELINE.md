# Experimental AI training pipeline

## Recommendation

Keep the current SystemOne rule scorer as the production baseline. Train a separate,
offline candidate and promote nothing automatically. At the latest local readiness
check (2026-11-03), the selected Yahoo provider series contained 17,340 five-minute
candles, 8,971 generated samples, and 59 distinct sessions against the 60-session
minimum. The check correctly returned `NOT_READY`; the feedback database contained
one older labeled outcome, without the feature snapshot required by the paper
trainer. Its current eligible count is therefore zero. These counts are a local
snapshot, not a coverage or quality claim. There is not enough independent evidence
to judge a learned signal.

The new runner makes one model per exact provider identifier; it does not blend
providers. The two Yahoo labels in the archive are not treated as aliases because
overlapping rows can disagree. Both are still the same underlying, unofficial Yahoo
source, so they do not count as independent data providers. Groww is an optional
authenticated source, not an anonymous free feed. Do not fetch, retain, or train on
another provider's data until its NSE coverage, usage rights, and storage/training
terms are confirmed.

## Run a research candidate

From `stock-signal-bot/backend`:

```powershell
python -m app.ai.training.cli --provider yahoo_finance_public_unofficial
python -m app.ai.training.cli --provider groww_trade_api --model-out .runtime\groww-candidate.joblib
```

By default, training requires at least 60 distinct sessions. Override
`--min-sessions` only for an explicitly exploratory run. The model predicts whether
the future close over `--horizon-bars` beats a symmetric `--cost-bps` threshold
(default: 15 five-minute bars and 10 round-trip basis points). It uses past returns,
candle range, and relative volume, then reports a chronological 80/20 holdout with
the training labels purged at the split. Test predictions overlap and are not a
portfolio backtest. Artifacts are research-only and are never loaded by production
signal routes.

This small scikit-learn logistic model intentionally runs on CPU; for the current
2,249-sample experiment, adding CUDA/PyTorch or uploading data to a hosted GPU
would add complexity without a meaningful speed benefit. The same CLI is portable
to a user-controlled Colab notebook for occasional experiments, but it does not
create a persistent cloud training service. Colab free resources are not guaranteed
and VMs are temporary; never upload broker credentials or API secrets.

## Data sources and open-source references

- The existing Yahoo chart-history adapter is explicitly unofficial. It is not an
  exchange-certified real-time feed.
- The existing Groww historical adapter requires a connected Groww API account.
- [Alpha Vantage](https://www.alphavantage.co/premium/) documents a standard free
  limit of 25 API requests per day; that is not enough to bulk refresh this universe
  frequently. Verify NSE symbol coverage and usage rights before adding it.
- [Freqtrade data download](https://www.freqtrade.io/en/stable/data-download/) and
  [lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/)
  are useful references for reproducible history and leakage checks.
- [Microsoft Qlib](https://github.com/microsoft/qlib) is a larger quantitative
  research system; its point-in-time and evaluation patterns are useful, but it is
  not a lightweight runtime dependency for this app.
- [Google Colab FAQ](https://research.google.com/colaboratory/faq.html) states that
  free resources are variable and VMs are deleted after idle time or at a maximum
  lifetime.

No live provider was called. One in-memory diagnostic was fit from the existing
Yahoo archive with the default gates explicitly lowered to 50 sessions; no model
artifact was saved or connected to production. Run `npm run test:stock-ai` for
isolated tests.

For a separate agent that can retain project memory or propose code changes, see
[local self-improving agent research](./research/LOCAL_SELF_IMPROVING_AGENTS.md).
That workflow is distinct from market-model training; an agent must not promote a
stock model or alter production rules automatically.

## Automatic paper-outcome candidate

The paper automation stores a point-in-time feature snapshot, provider ID, source
timestamp, and rule version when it opens an automatic paper trade. When that
trade closes, a background CPU job checks the outcomes for that exact provider and
trains a binary win/loss logistic-regression candidate only after there are at
least 100 eligible outcomes, 20 wins and 20 losses, across 30 sessions. The split
is chronological, and training rows whose outcome was not known by the split are
purged. Older outcomes without snapshots are excluded.

Candidate artifacts are written locally under `app/data/research/`. Readiness is
available from `GET /api/feedback/learning`. Candidates are **never loaded by
production signal or paper-entry code**. Candidate scores are not proof of an
edge: outcomes are simulated gross of costs, the sample can be biased, and the
feature set is small. Rule/model changes require separate review and further
validation. The current local feedback database has one older outcome without
features, so the eligible count is zero and this path reports `NOT_READY`.

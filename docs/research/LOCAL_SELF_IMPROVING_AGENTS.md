# Local self-improving agents for SMKD

**Reviewed:** 2026-11-03  
**Purpose:** Evaluate whether SMKD can learn from use and improve itself on the developer's laptop without continuous cloud costs or large resource use. This is a design/research note, not an installed agent or a claim that a model can reliably improve trading performance.

## Short answer

Yes, a bounded local improvement loop is feasible. Do not run an unrestricted coding agent inside the live application or let it change production signals automatically. Separate four different capabilities:

1. **Memory/skills:** retain approved project knowledge and reusable procedures. This changes what an agent recalls, not model weights or stock predictions.
2. **Software improvement:** inspect errors, tests, and explicitly approved feedback; propose a patch in an isolated branch/worktree; run tests; ask a person to review and merge.
3. **Stock-model research:** create an offline candidate from point-in-time market features/outcomes; compare with baselines on later data; never promote automatically.
4. **Runtime adaptation:** adjust a live rule or UI based on recent observations. Do not enable this; small biased feedback samples can silently degrade behavior.

The app can trigger lightweight analysis when opened, after a paper outcome, or when idle. It should not continuously run an LLM or rewrite its own source while being used.

## Hardware observed

The current Windows host reported:

- ASUS TUF Gaming F16 `FX607VUR_FX677VU`
- 16 GB system RAM (16,788,983,808 bytes reported)
- NVIDIA GeForce RTX 4050 Laptop GPU, 6,141 MiB reported video memory

These are a snapshot of the machine currently running this workspace; verify power mode, free memory, GPU utilization, and other running apps before any model test. The 6 GB VRAM budget is limited. Small quantized local models may be practical for short summaries/classification or code completion; larger agentic coding models, long contexts, parallel agents, and fine-tuning can compete with the browser, IDE, and app for memory and responsiveness. Quantization, context length, runtime, and GPU offload materially change actual use.

**Practical resource policy:** begin with no resident LLM. If later tested, use one local model process, short contexts, no concurrent agents, an explicit idle trigger, a configurable timeout, and an immediate stop/disable switch. Benchmark memory, latency, temperatures, and app responsiveness before enabling it during a trading session.

## Existing SMKD pieces

- SystemOne is deterministic rule scoring, not an online-learning model: [AI decision engine](../AI_DECISION_ENGINE.md).
- The app records signal outcomes and exposes accuracy/calibration reports. Those reports do not modify model weights: [feedback workflow](../BACKTESTING_FEEDBACK_LOOP.md).
- A separate scikit-learn training CLI builds research-only candidates from provider-isolated candles and a chronological split. Artifacts are not loaded by production routes: [training pipeline](../AI_TRAINING_PIPELINE.md).
- **Latest local check (2026-11-03):** candle-training readiness returned `NOT_READY` for `yahoo_finance_public_unofficial`: 17,340 five-minute candles, 8,971 generated samples, 59 sessions versus the 60-session gate. The feedback database has one older labeled outcome, but it lacks the feature snapshot required by the paper trainer; eligible outcomes currently total zero. These are local snapshots, not assurances of data quality or independent source coverage. Re-run the readiness/count checks before any training run.
- **Paper-outcome trainer:** the backend stores input features and provider identity for automatic paper entries, then starts a single background training attempt after a closed outcome. It requires 100 eligible outcomes, at least 20 wins and 20 losses, and 30 sessions. The current `/api/feedback/learning` status is `NOT_READY`; even once ready, it only saves a research candidate and never changes production signals. Details: [AI training pipeline](../AI_TRAINING_PIPELINE.md#automatic-paper-outcome-candidate).

The feedback recorder is therefore a foundation, not a complete closed learning loop. It needs reliable feature snapshots tied to each signal, outcomes with execution/cost provenance, sufficient chronological coverage, explicit model/rule versions, and a reviewed candidate-promotion process.

## Options reviewed

| Project | Useful capability | Fit for this project | Cost/resource and caution |
|---|---|---|---|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) ([official docs](https://hermes-agent.nousresearch.com/docs/)) | Persistent curated memory, reusable skills, skill creation/improvement, tool use, and scheduled workflows are advertised by its maintainers. The project provides Windows installation paths and an MIT license. | Best match to the idea of an assistant remembering SMKD procedures and producing repeatable engineering tasks. Treat the learning-loop claims as project-described features, not independent evidence of correctness. A new agent would still need a configured model provider and carefully limited repository access. | Agent software being open source does not make model inference, cloud providers, or hosted tools free. Confirm a local model endpoint and Windows support for the chosen configuration before assuming fully offline operation. Review its security/approval settings before granting shell or file-write access. |
| [OpenHands Agent Canvas](https://github.com/OpenHands/OpenHands) ([backend docs](https://docs.openhands.dev/openhands/usage/agent-canvas/backends)) | Self-hosted control surface for coding agents and scheduled/triggered engineering automations; supports local or isolated/container/remote backends and integrations with multiple agents. | A possible future orchestration layer for queued code-maintenance jobs, not an online stock learner. Stronger isolation and always-on workflows are possible, but they add deployment and maintenance. | It orchestrates agents; it does not provide free model inference. A persistent backend, Docker sandbox, model, or cloud runtime can consume resources or incur cost. |
| [Continue](https://docs.continue.dev/customize/deep-dives/autocomplete) + [Ollama](https://ollama.com/) | IDE assistance can use a local Ollama model; Continue documents small code-completion model configurations. Ollama runs models behind a local API. | Lowest-friction way to test local code suggestions while keeping source prompts on the machine, subject to local configuration. Useful for developer assistance, not for silently changing the app or training a stock model. | Small completion models are not equivalent to a strong autonomous coding agent. A model server still consumes RAM/VRAM while resident; shut it down when not needed. |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | Research/engineering agent workflow that takes software issues and attempts repository changes. | Useful reference for one task at a time: issue, patch, test, review. It does not provide SMKD-specific ongoing memory or evidence that it can safely self-maintain this app unattended. | Agent task loops need a model and execution environment; repeated unattended runs can create noisy or risky changes. |
| [Unsloth](https://github.com/unslothai/unsloth) | Tooling for running and fine-tuning open models, including LoRA/QLoRA workflows. | Not a first step. Fine-tuning a language model is distinct from learning from stock outcomes and does not add trustworthy market signal skill by itself. | Training consumes more compute and data than a memory/skills workflow. The 6 GB GPU is not a reason to fine-tune; current signal labels and clean history are more important constraints. |

## Recommended design for SMKD

Keep the running market-analysis app deterministic and responsive. Add any agent as a separate, opt-in local service with a queue and strict permissions:

```text
signal/paper outcome or explicit "analyze improvements" action
  -> local, bounded metrics and test report (no broker credentials)
  -> agent reads an allowlisted docs/code/test context
  -> candidate finding or patch in a disposable branch/worktree
  -> existing tests + UI checks + data-integrity checks
  -> human review/approval
  -> normal merge/release; production model/rules remain unchanged until separately validated
```

For code/UI quality, useful inputs are reproducible bug reports, failed tests, user-approved UX feedback, accessibility checks, and visual-regression results. The agent should return small proposals with evidence and tests, not continuously rewrite the interface based on guesses.

For stock outcomes, first improve the existing recorder: store immutable point-in-time feature snapshots, provider and candle timestamps, signal direction, rule version, planned and realized fills, costs, and outcome reason. Then evaluate offline candidates against a simple baseline with chronological holdouts and separate long/short metrics. Require minimum sample and session thresholds, calibration/error metrics, and forward paper results. A model must never self-promote or place orders.

## Rollout gates

1. **No-model baseline:** measure current feedback-data completeness, failures, test coverage, app idle CPU/RAM/GPU, and cold-start time.
2. **Local read-only assistant:** optionally invoke one local model after explicit request; provide a small sanitized context and ask only for a ranked finding/report. Verify prompts stay local.
3. **Patch proposal mode:** allow a task-scoped worktree and permitted tests only. No commit, merge, live file writes, credential access, network actions, or deployment without explicit human approval.
4. **Research candidate mode:** train/evaluate the separate market model offline after data-readiness gates pass. Keep candidates isolated from production.
5. **Promotion:** a maintainer reviews evidence, diff, tests, model/data license, and resource impact. Promotion is an explicit release action with rollback.

Do not install an always-on agent, start cloud workers, add a new model provider, or grant repository write/shell permissions until resource, privacy, licensing, and approval boundaries are agreed and tested.

## Sources checked

- [Hermes Agent README and license](https://github.com/NousResearch/hermes-agent), [official documentation](https://hermes-agent.nousresearch.com/docs/), [memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory), [skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), and [security](https://hermes-agent.nousresearch.com/docs/user-guide/security).
- [OpenHands repository](https://github.com/OpenHands/OpenHands) and [Agent Canvas backend documentation](https://docs.openhands.dev/openhands/usage/agent-canvas/backends).
- [SWE-agent repository](https://github.com/SWE-agent/SWE-agent).
- [Continue local Ollama autocomplete guide](https://docs.continue.dev/customize/deep-dives/autocomplete), [Ollama](https://ollama.com/), and [Ollama model library](https://ollama.com/library).
- [Unsloth repository](https://github.com/unslothai/unsloth).

Provider capability, model availability, licenses, and project security posture change over time. Re-verify upstream docs and the exact model's license before deployment.

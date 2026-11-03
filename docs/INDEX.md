# SMKD Documentation

## Start here

- [Product and technical roadmap](./PRODUCT_TECHNICAL_ROADMAP.md) — verified purpose, current gaps, architecture direction, and prioritized delivery plan.
- [Intraday workstation requirements](./INTRADAY_WORKSTATION_REQUIREMENTS.md) — dashboard hierarchy, interaction, signal semantics, and acceptance criteria.
- [Charting and indicator requirements](./CHARTING_INDICATOR_REQUIREMENTS.md) — open chart approach, data integrity, studies, and chart boundaries.
- [Paper-trade workflow](./PAPER_TRADE_WORKFLOW.md) — paper-only trade registration, lifecycle, validation, and API gaps.
- [Groww read-only integration](./GROWW_READ_ONLY_INTEGRATION.md) — local credential/data boundary, account sync, execution timestamps, and chart markers.
- [Local market history](./MARKET_HISTORY_ARCHIVE.md) — candle sources, bounded historical fetch, local storage, source limits, and unresolved licensing/access checks.
- [Cloud-native architecture](./CLOUD_NATIVE_ARCHITECTURE.md) — target cloud data flow, verified provider limits, security boundaries, and migration gates.
- [Architecture](./ARCHITECTURE.md) — current runtime and module boundaries.
- [AI decision engine](./AI_DECISION_ENGINE.md) — actual SystemOne inputs, formulas, and limitations.
- [Backtesting and paper trading](./BACKTESTING_FEEDBACK_LOOP.md) — implementation and validation requirements.
- [Competitive research](./COMPETITIVE_ANALYSIS.md) — source-backed feature comparison and lessons.
- [Research register: free data and AI](./research/FREE_DATA_AND_AI.md) — sourced provider/model notes, access caveats, and adoption decisions.
- [Local self-improving agents](./research/LOCAL_SELF_IMPROVING_AGENTS.md) — Hermes and alternatives, observed laptop resources, and a safe agent/feedback design.
- [Documentation workflow](./dev/DOCUMENTATION_WORKFLOW.md) — search existing research and check code-to-doc impact.

## Reference

- [Data specification](./DATA_SPECIFICATION.md) — existing API payload examples; validate against the current implementation before treating examples as a contract.
- [Android setup](./ANDROID_SETUP.md)
- [Developer start guide](./dev/START_HERE.md)
- [Codebase map](./dev/CODEBASE_MAP.md)

The product roadmap is the current status source of truth. Older audit and feature documents may describe planned work; check implementation and tests before relying on them.

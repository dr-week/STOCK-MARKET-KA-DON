# SMKD developer docs

SMKD is an experimental NSE intraday analysis dashboard. It uses a FastAPI backend and a Vite/TypeScript frontend. The backend's SystemOne component is deterministic rule scoring, not a trained prediction model. Signals and backtests are unvalidated research outputs, not financial advice or a demonstrated trading edge.

## Start with

- [Product and technical roadmap](docs/PRODUCT_TECHNICAL_ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [AI decision scoring](docs/AI_DECISION_ENGINE.md)
- [Backtesting and paper trading](docs/BACKTESTING_FEEDBACK_LOOP.md)
- [Competitive research](docs/COMPETITIVE_ANALYSIS.md)
- [Full documentation index](docs/INDEX.md)

## Main runtime entry points

| Component | Entry point |
|---|---|
| FastAPI app | `stock-signal-bot/backend/app/main.py` |
| Scan routes and orchestration | `stock-signal-bot/backend/app/api/routes_scan.py` |
| Market data | `stock-signal-bot/backend/app/departments/market_data/service.py` |
| Primary confluence/risk decision | `stock-signal-bot/backend/app/departments/signal_risk/service.py` |
| SystemOne heuristic score | `stock-signal-bot/backend/app/ai/system_one.py` |
| Backtest | `stock-signal-bot/backend/app/backtesting/backtest_engine.py` |
| Frontend startup and scan request | `fast-framework/packages/stock-bot-ui/src/main.ts` |

## Local commands

From the repository root:

```powershell
pnpm run dev:backend
pnpm run dev:ui
```

For the frontend backend URL, copy `fast-framework/packages/stock-bot-ui/.env.example` to `.env.local` and set `VITE_API_BASE_URL` as needed. Frontend contract tests can be run with:

```powershell
node --experimental-strip-types --test fast-framework/packages/stock-bot-ui/src/api/contracts.test.mjs
```

Backend API docs: `http://127.0.0.1:8000/docs`. Backend test instructions are in [the developer start guide](docs/dev/START_HERE.md).

## Find and update documentation

Search existing docs before repeating research:

```powershell
python scripts/dev/docs_tools/find.py --query "NSE live data license"
```

Check which docs a code change may affect:

```powershell
python scripts/dev/docs_tools/check.py
```

The checker reports affected docs; it does not invent or rewrite prose. CI requires mapped docs to be included in a pull request. See [the documentation workflow](docs/dev/DOCUMENTATION_WORKFLOW.md) and [the research register](docs/research/FREE_DATA_AND_AI.md).

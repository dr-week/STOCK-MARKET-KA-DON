# Large-module inventory

Measured source files only (`.py`, `.ts`, `.tsx`, `.js`, `.mjs`), excluding vendor, build, and cache folders.

## Priority list

| Lines | Module | Main responsibilities | Priority |
|---:|---|---|---|
| 143 | `fast-framework/packages/stock-bot-ui/src/api/contracts.ts` | Public API contract types and parser facade | completed |
| 269 | `fast-framework/packages/stock-bot-ui/src/ui/app-controller.ts` | UI state, API loading, chart actions, navigation, paper, Groww, and event wiring | 1 |
| 276 | `fast-framework/packages/stock-bot-ui/src/ui/chart.ts` | Chart data preparation, rendering orchestration, drawings, and executions | 2 |
| 336 | `stock-signal-bot/backend/app/paper_trading/engine.py` | Paper order validation, fills, positions, and ledger persistence | 3 |
| 213 | `stock-signal-bot/backend/app/backtesting/backtest_engine.py` | Backtest orchestration and result assembly | 3 |
| 286 | `stock-signal-bot/backend/app/departments/market_data/service.py` | Provider fetch, normalization, freshness, and archive coordination | 5 |
| 269 | `stock-signal-bot/backend/app/api/routes_scan.py` | Scan orchestration and response mapping | 4 |
| 261 | `stock-signal-bot/backend/app/feedback/recorder.py` | Feedback validation, persistence, and aggregation | 5 |
| 256 | `stock-signal-bot/backend/app/paper_trading/automation.py` | Automated paper-trade scan evaluation and execution | 6 |
| 242 | `stock-signal-bot/backend/app/integrations/groww/service.py` | Groww integration requests and response normalization | 7 |
| 208 | `stock-signal-bot/backend/app/indicators/structure.py` | Market-structure detection and level calculations | 10 |
| 207 | `stock-signal-bot/backend/app/strategies/intraday.py` | Intraday strategy orchestration and signal construction | 11 |
| 201 | `fast-framework/packages/stock-bot-ui/src/ui/normalizer.ts` | API trade normalization for UI consumption | 12 |

## Step 1: contract parser — completed

Split `contracts.ts` by validated domain, preserving the public exports:

1. `contracts/primitives.ts`: finite numbers, records, arrays, and shared scalar validation.
2. `contracts/market-data.ts`: candles, data quality, zones, and technicals.
3. `contracts/trade-decision.ts`: signal decisions and risk-sizing payloads.
4. `contracts/news.ts`: article and sentiment validation.
5. `contracts/scan-response.ts`: top-level scan and stock response composition.
6. Keep `contracts.ts` as a compatibility facade while callers migrate.

Completed sub-steps: shared primitive validators now live in `api/contracts/primitives.ts`, OHLCV candle validation now lives in `api/contracts/market-data.ts`, news validation now lives in `api/contracts/news.ts`, provider quality validation now lives in `api/contracts/market-quality.ts`, technical indicator validation now lives in `api/contracts/technicals.ts`, AI decision validation now lives in `api/contracts/ai-decision.ts`, trade and risk-sizing validation now lives in `api/contracts/trade-decision.ts`, and scan/stock composition now lives in `api/contracts/scan-response.ts`. The 602-line facade is now 143 lines and contains no duplicate legacy parser implementation.

Acceptance criteria:

- Existing API field names remain unchanged.
- Complete, partial, malformed, and unavailable payload behavior remains explicit.
- Existing contract tests pass without weakening validation.
- No feature renderer imports parser internals.

## Step 2: application controller — next task

After the contract split is stable, extract stateful workflows:

- `controllers/scan-controller.ts`: scan loading and retry.
- `controllers/chart-controller.ts`: symbol, timeframe, history, and studies.
- `controllers/paper-controller.ts`: paper ledger actions.
- `controllers/groww-controller.ts`: Groww account actions.
- `ui/app-controller.ts`: composition and event binding only.

Measured boundary for the next pass: `startDashboard` currently owns six named workflows plus one approximately 260-line render-and-event-binding block. The first safe extraction is the paper workflow (paper automation, risk preview, order submission, and close-position handlers), because it has a distinct API surface and state object. The chart workflow is the second extraction (history loading, symbol selection, timeframe/studies, drawings, and chart rendering). Scan loading and Groww controls remain composition-level until those two boundaries are tested.

## Safety rule

Line count identifies review candidates; it does not justify arbitrary splitting. Each extraction must have a separate responsibility, dependency boundary, and focused test. Do not split tests, generated data, or compatibility facades solely because they are long.

## Automated developer process

## Modularization development rule

Use this rule for every future feature and refactor:

1. Measure first with `npm run audit:modules` and record the current line count.
2. Identify one responsibility boundary: provider access, normalization, validation, persistence, calculation, orchestration, or presentation.
3. Create a named module in the folder that owns that responsibility.
4. Preserve the public contract through a small facade or orchestration layer.
5. Compile or run focused tests before moving to the next boundary.
6. Update this inventory with before/after line counts and the next task.

The audit is an automated detection tool, not an automatic rewrite tool. A file over 200 lines is a review candidate; it is not split without a clear dependency and test boundary. Test files and compatibility facades are not split solely because of line count.

## Live-data rule

The dashboard must refresh provider-backed scan data on a bounded timer even when paper automation is disabled. Every refresh must reload the selected chart timeframe so completed candles, prices, indicators, and news can advance together. A provider snapshot must be labeled as a snapshot; the UI must not imply streaming when the provider is delayed or polling-based.

Run the audit from the repository root:

```powershell
npm run audit:modules
npm run audit:modules -- -Threshold 400 -Top 10
```

The script scans approved source roots, excludes generated/vendor/cache folders, ranks files by physical line count, and prints the review rule with every report. It is an audit aid, not an automatic refactoring tool; a developer must confirm the responsibility boundary before splitting a module.

CI runs the same audit on every push and pull request through the `module-size-audit` job in `.github/workflows/ci.yml`. The job reports candidates but does not fail the build solely because a file is large; architectural review decides whether a split is justified.

# SMKD modularization plan

## Goal

Keep market-data acquisition, calculations, decision rules, API contracts, and presentation independent enough that a change in one area does not silently change another. Each module should have one reason to change, a small public interface, and focused tests.

## Existing boundaries

### Backend

- `app/indicators/groww_costs.py`: Groww charge assumptions and fee-clearing quantity.
- `app/indicators/trade_sizing.py`: price levels and risk-budget sizing.
- `app/indicators/profitability.py`: ADX/ATR/cost eligibility gate.
- `app/departments/market_data/`: provider data, normalization, freshness, and integrity.
- `app/departments/technical_analysis/`: indicators and pattern analysis.
- `app/departments/signal_risk/`: confluence and trade-plan synthesis.
- `app/api/routes_scan.py`: orchestration and response assembly only.

`app/indicators/calculations.py` remains a compatibility facade for old imports. New code should import the specific module it needs.

### Frontend

- `ui/features/trade-economics.ts`: Groww costs, quantities, and profitability presentation.
- `ui/features/groww-account.ts`: account activity presentation.
- `ui/features/paper-trading.ts`: paper-trading presentation.
- `ui/api/contracts.ts`: runtime validation at the API boundary.
- `ui/normalizer.ts`: conversion from API analysis to display rows.
- `ui/dashboard.ts`: composition and navigation; it should not own domain calculations.

## Step-by-step sequence

1. **Completed — economics separation.** Split Groww charges, risk sizing, and profitability rules on the backend; extracted the Groww economics panel on the frontend.
2. **Completed — compatibility and boundary safety.** Kept legacy imports working and made incomplete broker payloads unavailable instead of allowing one malformed field to hide the whole scan.
3. **Phase 2 in progress — chart/detail extraction.** Trade-row, market-news, chart-history formatting, chart status, selected-trade selection, chart toolbar, five-minute plan, indicator readouts, pattern cards, and trade thesis are feature modules. The chart canvas and surrounding detail composition remain as the next boundary.
4. **Next — scan orchestration.** Move response assembly from `routes_scan.py` into a response-mapper module. Keep the route responsible for HTTP parameters and partial-failure handling.
5. **Next — contracts and tests.** Group backend calculation tests by module and add contract fixtures for complete, partial, stale, and unavailable data.
6. **Final — dependency cleanup.** Update imports to target modules directly, then remove only compatibility code with a migration note and a passing full suite.

## Rules for each extraction

- Move one responsibility at a time.
- Preserve public behavior and API field names.
- Add or move a focused test before removing the old implementation.
- Do not use fallback or synthetic market data to hide missing provider data.
- Run targeted tests after every step and inspect the diff before the next step.

## Dependency direction

```text
API contracts → normalizers → feature renderers → dashboard composition
market data → indicators → risk/signal services → API response assembly
```

Feature renderers may depend on types, escaping, and formatting helpers. They must not fetch data, calculate indicators, or mutate application state. Calculation modules must not import UI code. Route modules may orchestrate services, but they must not contain broker-fee formulas or HTML templates.

## Completion criteria for the current phase

- Dashboard feature responsibilities are in named modules.
- `dashboard.ts` composes features and owns only page-level layout/navigation.
- Backend trade economics has separate cost, sizing, and profitability modules.
- Compatibility exports remain until all callers are migrated.
- Focused tests pass after each extraction.

Do not split a module merely because it has many lines. Split when a responsibility has a separate input/output contract, test boundary, or change reason. This is the stop condition that prevents fragmentation.

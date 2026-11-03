# Paper-Trade Workflow Requirements

**Status:** Workflow requirements and first integration checkpoint. See the [roadmap](./PRODUCT_TECHNICAL_ROADMAP.md) for overall status.

## Scope and safety

This feature is a **paper journal only**. It records user-entered simulated trades and must never submit, modify, or close a live broker order. The current backend routes are `/api/paper/order`, `/api/paper/close/{position_id}`, `/api/paper/positions`, `/api/paper/history`, and `/api/paper/pnl`.

The paper view now uses the SQLite `paper_positions` ledger at `stock-signal-bot/backend/app/data/paper_trades.db`. It stores symbol, side, entry, stop, one target, whole-share quantity, confluence score, status, exit, gross P&L, and open/close timestamps. The UI confirms paper entry and exit, previews planned gross risk/reward, and preserves API errors and form input. It does not store fees, slippage, proposed versus filled prices separately, exit reason, multiple targets, or a complete event/audit history. P&L is gross price difference times quantity, not net realized return.

`GET /api/paper/pnl` reports lifetime results separately for `AUTO` and `MANUAL`
entries, independent of the recent-history display limit. Attempted trades count
automatic positions actually opened (open plus closed); scan candidates skipped
before a position opens are not persisted in the lifetime total. Closed trades
are classified as wins (gross P&L > 0),
losses (< 0), or breakeven (= 0); win rate is wins divided by all closed trades,
including breakeven in the denominator. Gross return is total realized gross P&L
divided by the sum of entry price × quantity for closed trades. Open trades are
excluded from both closed outcomes and this return. Percentage is unavailable
until at least one trade is closed. These are journal statistics, not net
portfolio returns or proof of a trading edge.

The aggregates are available through `/api/paper/pnl`, but the current
`fast-framework` Paper UI has not yet been updated to render these new fields.
Individual open and closed positions remain available through
`/api/paper/positions` and `/api/paper/history`.

Automatic paper trading is always on while the backend runs; no opt-in is
required, and the backend refuses disable requests. The existing external
`fast-framework` UI may still show its legacy toggle until that checkout is
updated. A backend worker scans the configured universe about once a minute
on weekdays during NSE session hours, even with the dashboard closed. Starting
the backend is
required; this is not a cloud service and does not run while the machine/backend
is stopped. The dashboard can request scans too; a backend scan skips if a
dashboard scan just ran to reduce duplicate provider traffic.

An automatic "BUY" or "SELL" creates a **virtual ledger position only** in
SQLite. It does not submit a broker order, use a Groww account, reserve real
cash, or spend real money. Quantity is risk-sized using the configured virtual
capital (currently ₹18,000 reference capital, 0.5% risk per trade) and stop
distance. This reference is used for risk sizing; the app does not model cash
reservation or a withdrawable virtual balance. A SELL is a simulated short
position only. The ledger records symbol, side, quantity, entry,
stop, target, status, timestamps, exit, and simulated gross P&L. Entry uses the
provider's current-price snapshot; stop/target exits are threshold simulations,
not exchange fills. Data must pass provider/freshness checks, and new entries
must pass the existing signal, risk/reward, session, and daily-loss gates.
Yahoo data may be delayed or unavailable; this is not a guaranteed real-time
feed. No NSE holiday calendar is integrated, so a weekday holiday can still
cause scan attempts, but stale data is rejected for entry.

The optional [Groww read-only account view](./GROWW_READ_ONLY_INTEGRATION.md) is deliberately separate from this paper journal. Broker executions must never be copied into simulated entries or treated as paper fills.

## User workflow

### Register a paper trade

1. Start from the selected symbol's current analysis, or open the journal directly.
2. Prefill proposed side, entry, stop, and target 1 only when a valid signal plan is available. Label these as **suggested plan**, not an execution.
3. Require the user to confirm or edit the paper fill entry, side, quantity, stop, and target before submitting.
4. Show the planned monetary risk (`abs(entry - stop) × quantity`) and target reward before confirmation. Do not silently choose a risk budget or quantity.
5. Clearly mark the action as **Record paper trade**. Show an explicit success/error result and refresh the open-position list only after a successful API response.
6. If signal/data state is `WAIT`, stale, unavailable, or insufficient, disable prefill from the signal. A user may still record a manually defined journal entry if the product supports that mode, but it must be marked manual and must not appear as a generated signal.

### Manage and close an open position

- Show open positions with symbol, side, user-recorded entry, stop, target, quantity, open time, and current mark only when a valid current price is available.
- Do not display a zero or stale price as a live mark. Until live marking is connected, show unrealized P&L as unavailable rather than a fabricated value.
- Provide an explicit **Record paper exit** action with exit price and exit time. Require confirmation before closing; show calculated gross P&L and state that fees/slippage are excluded by the current API.
- Preserve closed positions in history. Do not delete losing, canceled, or manually entered records to improve summary metrics.
- Distinguish user-entered exit price from an automatically observed fill. The current API supports only manual close prices.

## Data and validation requirements

- Side must be `BUY` or `SELL`; symbol must be a known supported instrument or an explicitly marked manual symbol.
- Entry, stop, target, exit, quantity, and all derived values must be finite and valid. For the supported NSE equity workflow, quantity must be a positive whole share count. If another instrument class is added, define its lot-size contract first.
- Validate the price ordering relative to side: long stop below entry and target above entry; short stop above entry and target below entry. If the user intentionally records a nonstandard plan, require a clear manual-plan path rather than silently accepting inconsistent risk math.
- Reject submission when required fields are invalid and show the field-level reason. The backend must enforce validation too; frontend checks are not a security or integrity boundary.
- Store timestamps in UTC and render them in the user's selected/display timezone with the timezone stated.
- Never send AI probabilities or heuristic score values as a trade fill, realized outcome, or guaranteed confidence. A confluence score may be stored as trace context only and must retain its experimental label.

## Performance limitations and future accounting work

The backend exposes an on-demand historical backtest for a selected symbol. Its
response includes the simulator's trade count and outcomes, win rate, average
net per-trade percentage, net compounded return, profit factor, and maximum
drawdown. The current SMKD Paper Trading UI does not call this endpoint yet;
the interface change belongs in the separate `fast-framework` checkout. This
is a separate historical sample, not the paper ledger or a forecast; Yahoo
5-minute history and modeled costs are limited.

Do not present these figures as complete net trade analytics. The current table
should be extended through a deliberate schema migration before making that
claim. Add distinct fields for:

- proposed plan versus user-confirmed entry/exit fill;
- target selection and exit reason (manual, stop, target, session close, other);
- entry/exit timestamps and actor/source;
- fees, taxes, and slippage assumptions or explicit `not modeled` status;
- strategy/rule version and scan/data snapshot reference;
- append-only lifecycle events for opened, edited, and closed actions.

Keep paper data separate from live brokerage state. Add idempotency/duplicate-submit handling and validate position state transitions (open to closed once). Existing P&L/history endpoints need documented semantics and response models before they become a source of calibration.

Do not add target 2/3 trade legs until partial closes and position accounting are modeled explicitly. Current analysis provides two target levels but the existing paper API stores one target only; the journal should show that constraint instead of implying a multi-target execution model.

## UI/API ownership

- **Frontend API client:** owns typed request/response parsing and HTTP errors.
- **Paper journal view:** owns form state, confirmation, validation feedback, and position/history rendering.
- **Controller:** owns loading/saving states, calls the client, and refreshes the journal after success.
- **Backend paper routes:** validate inputs and return explicit errors; do not silently coerce invalid requests.
- **Paper-trading engine/repository:** owns persisted lifecycle and P&L semantics; UI code must not duplicate authoritative calculations.

Do not put paper-trade fetches in the chart renderer or scan normalizer. Keep the dedicated journal panel separate from scanner rows to avoid repeated controls and mixed responsibilities.

## Acceptance criteria

- A user can record and manually close a paper position from the UI; no broker endpoint or broker credential is called.
- API errors preserve the form and are visible; success is shown only after a confirmed backend response.
- Positions and history survive page reload because the backend ledger is authoritative.
- Invalid values, side/level mismatches, duplicate close attempts, and missing prices are covered by backend tests.
- Gross P&L is labeled as gross, and unavailable current marks/fees/slippage are not displayed as zero-cost live results.
- Every record can be traced to a manual entry or a specific signal/data snapshot without treating the signal as a prediction.

## Related documentation

- Existing implementation and simulator limits: [Backtesting, paper trading, and feedback](./BACKTESTING_FEEDBACK_LOOP.md).
- Product layout and signal-level semantics: [Intraday workstation requirements](./INTRADAY_WORKSTATION_REQUIREMENTS.md).
- Current routes and API contract gaps: [Data specification](./DATA_SPECIFICATION.md).

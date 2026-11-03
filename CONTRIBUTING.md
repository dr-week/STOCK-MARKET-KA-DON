# Contributing to Stock Market Ka Don (SMKD)

Thank you for contributing to **SMKD**, the high-performance algorithmic trading intelligence terminal for Indian Equities (NSE).

To maintain code quality, market-data integrity, and reproducible releases, please follow this guide.

---

## 1. Core Principles

- **Market-Data Integrity**: Never fabricate prices, synthetic candles, or indicators in production paths. Production code must handle closed markets, missing feeds, and rate limits with explicit unavailable states (e.g. HTTP 503 / `DataQualityStatus.STALE_FEED`), not synthetic mockups.
- **Scope Isolation**: SMKD repository only. Do not modify the separate `fast-framework` (Zuari) core packages unless specifically directed.
- **Deterministic Testing**: Keep deterministic unit tests passing on every change; live broker/provider integration tests run separately via opt-in flags.

---

## 2. Environment Setup

### Prerequisites
- **Python**: 3.11+ (Python 3.14 compatible)
- **Node.js**: v20+
- **pnpm**: v9+

### Backend Setup
```bash
cd stock-signal-bot/backend
python -m pip install -r requirements-lock.txt
python -m uvicorn app.main:app --reload --port 8000
```
API Documentation will be live at `http://127.0.0.1:8000/docs`.

### Frontend Setup
```bash
# In fast-framework submodule:
pnpm install --frozen-lockfile
pnpm --filter stock-signal-bot-frontend run dev
```
Terminal interface will be accessible at `http://localhost:5173`.

---

## 3. Verification Sequence

Before submitting a Pull Request, run the local verification suite:

### 1. Run Backend Tests & Integrity Checks
```bash
python -m unittest discover -s stock-signal-bot/backend/app/tests
```
For focused paper ledger and always-on runner tests, use
`.\scripts\dev\test-stock-ai.ps1 -Suite paper`.

### 2. Run UI Tests (Vitest)
```bash
pnpm -C fast-framework run test --run packages/stock-bot-ui
```

### 3. Verify Production Frontend Build
```bash
pnpm -C fast-framework --filter stock-signal-bot-frontend run build
```

### 4. Opt-in Live Provider Check (Optional)
To test connectivity against live market providers:
```bash
# In PowerShell:
$env:SMKD_LIVE_PROVIDER_TESTS="1"; python -m unittest stock-signal-bot/backend/app/tests/test_live_provider_integration.py
```

---

## 4. Pull Request Guidelines

1. Ensure the CI workflow (`.github/workflows/ci.yml`) passes cleanly on your branch.
2. If dependencies are updated, verify both `requirements.txt` and `requirements-lock.txt` or `pnpm-lock.yaml` are synchronized.
3. For new features or bug fixes, record notes in [`CHANGELOG.md`](./CHANGELOG.md) under the `[Unreleased]` section.

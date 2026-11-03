# SMKD — Start Here

## Run the backend
```
cd stock-signal-bot/backend && ../.venv/Scripts/uvicorn app.main:app --reload
```

## Run the frontend
```
cd fast-framework/packages/stock-bot-ui && pnpm dev
```

## Run tests
```
.venv/Scripts/python -m pytest stock-signal-bot/backend/app/tests -v
.\scripts\dev\test-stock-ai.ps1 -Suite paper
```

## Key entry points
- **Backend:** `stock-signal-bot/backend/app/main.py`
- **AI Engine:** `stock-signal-bot/backend/app/ai/system_one.py`
- **Frontend:** `fast-framework/packages/stock-bot-ui/src/main.ts`
- **Config:** `stock-signal-bot/backend/app/core/config.py`

## Useful shortcuts
- API docs (when backend is running): http://127.0.0.1:8000/docs
- Frontend dev server: http://localhost:5173
- Scan endpoint: `GET /api/scan`
- Single stock: `GET /api/stock/{SYMBOL}`

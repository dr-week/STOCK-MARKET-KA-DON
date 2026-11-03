import os
from typing import List, Set, Dict, Any

# Source paths mapped to the docs that describe their observable contracts.
DOC_MAP = {
    "stock-signal-bot/backend/app/api": [
        "stock-signal-bot/docs/04_API_SPECIFICATION.md",
        "docs/DATA_SPECIFICATION.md",
        "docs/ARCHITECTURE.md",
    ],
    "stock-signal-bot/backend/app/departments/market_data": [
        "docs/MARKET_HISTORY_ARCHIVE.md",
        "docs/CLOUD_NATIVE_ARCHITECTURE.md",
    ],
    "stock-signal-bot/backend/app/ai": [
        "docs/AI_DECISION_ENGINE.md",
        "docs/AI_TRAINING_PIPELINE.md",
    ],
    "stock-signal-bot/backend/app/research": [
        "docs/AI_DECISION_ENGINE.md",
        "docs/AI_TRAINING_PIPELINE.md",
    ],
    "stock-signal-bot/backend/app/backtesting": [
        "docs/BACKTESTING_FEEDBACK_LOOP.md",
    ],
    "stock-signal-bot/backend/app/feedback": [
        "docs/AI_TRAINING_PIPELINE.md",
        "docs/BACKTESTING_FEEDBACK_LOOP.md",
    ],
    "stock-signal-bot/backend/app/paper_trading": [
        "docs/BACKTESTING_FEEDBACK_LOOP.md",
        "docs/PAPER_TRADE_WORKFLOW.md",
    ],
    "stock-signal-bot/backend/app/paper_trading": [
        "docs/PAPER_TRADE_WORKFLOW.md",
        "docs/BACKTESTING_FEEDBACK_LOOP.md",
    ],
    "stock-signal-bot/backend/app/indicators": [
        "docs/INTRADAY_PROFITABILITY.md",
        "docs/CHARTING_INDICATOR_REQUIREMENTS.md",
    ],
    "stock-signal-bot/backend/app/departments/signal_risk": [
        "docs/PRODUCT_TECHNICAL_ROADMAP.md",
        "docs/AI_DECISION_ENGINE.md",
    ],
    "stock-signal-bot/backend/app/main.py": ["docs/ARCHITECTURE.md"],
    "fast-framework/packages/stock-bot-ui/src": [
        "docs/ARCHITECTURE.md",
        "docs/INTRADAY_WORKSTATION_REQUIREMENTS.md",
    ],
    "scripts/dev": [
        "docs/dev/START_HERE.md",
        "CONTRIBUTING.md",
    ],
    "docs/research": ["docs/INDEX.md"],
    "AGENTS.md": ["docs/dev/START_HERE.md", "CONTRIBUTING.md"],
}


def get_affected_docs(changed_files: List[str]) -> Set[str]:
    affected: Set[str] = set()
    for f in changed_files:
        norm = f.replace("\\", "/")
        for prefix, docs in DOC_MAP.items():
            if norm == prefix or norm.startswith(prefix.rstrip("/") + "/"):
                affected.update(docs)
    return affected


def check_doc_sync_status(task_id: str, changed_files: List[str]) -> Dict[str, Any]:
    affected = get_affected_docs(changed_files)
    if not affected:
        return {"status": "NOT_REQUIRED", "affected_docs": []}
    missing = [d for d in sorted(affected) if not os.path.exists(d)]
    changed = {path.replace("\\", "/") for path in changed_files}
    pending = [path for path in sorted(affected) if path not in changed]
    return {
        "status": "SYNCED" if not missing and not pending else "PENDING_SYNC",
        "affected_docs": sorted(affected),
        "missing_docs": missing,
        "pending_docs": pending,
    }

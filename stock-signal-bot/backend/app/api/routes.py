"""
Consolidated API router for the SMKD signal backend.
Combines modular domain routers while preserving exact backward compatibility.
"""
from fastapi import APIRouter

from app.api.routes_scan import (
    router as scan_router,
    process_unified_stock,
    get_overview,
    scan_all,
    get_single_stock,
)
from app.api.routes_paper import (
    router as paper_router,
    OrderRequest,
    CloseRequest,
    paper_place_order,
    paper_close_position,
    paper_open_positions,
    paper_closed_history,
    paper_pnl_summary,
)
from app.api.routes_feedback import (
    router as feedback_router,
    feedback_accuracy,
    feedback_calibration,
    feedback_learning_status,
)
from app.api.routes_system import (
    router as system_router,
    backtest,
    tree_history,
    trigger_system_backup,
    list_system_backups,
    check_feed_health,
)
from app.api.routes_groww import router as groww_router
from app.api.routes_market_history import router as market_history_router

router = APIRouter()

# Include modular domain routers
router.include_router(scan_router)
router.include_router(paper_router)
router.include_router(feedback_router)
router.include_router(system_router)
router.include_router(groww_router)
router.include_router(market_history_router)

__all__ = [
    "router",
    "process_unified_stock",
    "get_overview",
    "scan_all",
    "get_single_stock",
    "OrderRequest",
    "CloseRequest",
    "paper_place_order",
    "paper_close_position",
    "paper_open_positions",
    "paper_closed_history",
    "paper_pnl_summary",
    "feedback_accuracy",
    "feedback_calibration",
    "feedback_learning_status",
    "backtest",
    "tree_history",
    "trigger_system_backup",
    "list_system_backups",
    "check_feed_health",
]

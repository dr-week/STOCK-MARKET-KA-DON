from fastapi import APIRouter, Query
from app.backtesting.backtest_engine import run_historical_backtest
from app.db.database import get_tree_history
from app.db.backup import backup_service
from app.departments.market_data.collector import collector_service

router = APIRouter()


@router.get("/backtest/{symbol}")
def backtest(
    symbol: str,
    days: int = Query(5, ge=1, le=30),
    holding_bars: int = Query(15, ge=1, le=60),
    cost_bps_per_side: float = Query(5.0, ge=0, le=100),
    optimize: bool = Query(False),
):
    """Historical backtest execution."""
    return run_historical_backtest(
        symbol.upper(),
        days=days,
        holding_bars=holding_bars,
        cost_bps_per_side=cost_bps_per_side,
        optimize=optimize,
    )


@router.get("/tree-history")
def tree_history(limit: int = Query(10, ge=1, le=50)):
    """Fetch recent historical analysis tree snapshots."""
    return get_tree_history(limit)


@router.post("/system/backup")
def trigger_system_backup():
    """Trigger an atomic point-in-time snapshot backup of the database."""
    return backup_service.create_snapshot_backup()


@router.get("/system/backups")
def list_system_backups():
    """List available database backups and point-in-time recovery archives."""
    return {"backups": backup_service.list_backups()}


@router.get("/system/feed-health/{symbol}")
def check_feed_health(symbol: str):
    """Check health and freshness of the market feed for a given symbol."""
    is_healthy, status_code = collector_service.check_feed_health(symbol.upper())
    return {
        "symbol": symbol.upper(),
        "is_healthy": is_healthy,
        "status": status_code,
        "active_provider": collector_service.active_provider,
    }

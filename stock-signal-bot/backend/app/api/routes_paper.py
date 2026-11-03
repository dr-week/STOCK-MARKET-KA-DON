from fastapi import APIRouter, HTTPException, status
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.paper_trading.automation import paper_automation
from app.paper_trading.auto_runner import paper_auto_runner
from app.paper_trading.engine import paper_engine

router = APIRouter()


class OrderRequest(BaseModel):
    """Request body for placing a paper order."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)

    symbol: str
    action: Literal["BUY", "SELL"]
    entry: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    target: float = Field(gt=0)
    qty: float = Field(gt=0, multiple_of=1)
    confluence_score: float = Field(default=0.0, ge=0, le=10)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        if not value:
            raise ValueError("symbol must not be empty")
        return value.upper()

    @model_validator(mode="after")
    def validate_level_direction(self):
        if self.action == "BUY" and not self.stop_loss < self.entry < self.target:
            raise ValueError("BUY trades require stop_loss < entry < target")
        if self.action == "SELL" and not self.target < self.entry < self.stop_loss:
            raise ValueError("SELL trades require target < entry < stop_loss")
        return self


class CloseRequest(BaseModel):
    """Request body for closing a paper position."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    exit_price: float = Field(gt=0)


class PaperAutomationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


@router.post("/paper/order")
def paper_place_order(req: OrderRequest):
    """Place a new paper-trading order and return the created position."""
    try:
        position = paper_engine.place_order(
            symbol=req.symbol,
            action=req.action,
            entry=req.entry,
            stop_loss=req.stop_loss,
            target=req.target,
            qty=req.qty,
            confluence_score=req.confluence_score,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"position": position}


@router.post("/paper/close/{position_id}")
def paper_close_position(position_id: int, req: CloseRequest):
    """Close an open paper position at the given exit price."""
    try:
        position = paper_engine.close_position(position_id, req.exit_price)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    paper_automation.record_outcome(position)
    return {"position": position}


@router.get("/paper/positions")
def paper_open_positions():
    """Return all currently open paper positions."""
    return {"positions": paper_engine.get_open_positions()}


@router.get("/paper/history")
def paper_closed_history(limit: int = 20):
    """Return recent closed paper trades (most recent first)."""
    return {"trades": paper_engine.get_closed_positions(limit=limit)}


@router.get("/paper/pnl")
def paper_pnl_summary():
    """Return aggregate P&L summary across all paper trades."""
    return paper_engine.get_pnl_summary()


@router.get("/paper/automation")
def paper_automation_status():
    return {**paper_automation.settings(), **paper_auto_runner.status()}


@router.put("/paper/automation")
def configure_paper_automation(req: PaperAutomationRequest):
    try:
        return paper_automation.set_enabled(req.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

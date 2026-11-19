from typing import Dict, Any
from app.indicators.calculations import calculate_trade_risk_and_sizing
from app.core.config import MIN_CONFLUENCE_SCORE, ACCOUNT_CAPITAL

class SignalRiskDepartment:
    """
    DEPARTMENT 5: SIGNAL & RISK ENGINE
    Responsibility: Takes unified inputs from Market Data, Technical Analysis,
    Fundamental Analysis, and Market Intelligence, then produces:
    - Final BUY / SELL / WAIT verdict (7-10 confluence score)
    - Precise Entry, Stop Loss, Target 1, Target 2
    - Strict position size (0.5% risk = ₹90 on ₹18,000 capital)
    - Explainable reasons detailing every factor.
    """
    def synthesize_decision(
        self,
        market_data: Dict[str, Any],
        technicals: Dict[str, Any],
        fundamentals: Dict[str, Any],
        intelligence: Dict[str, Any],
        capital: float = ACCOUNT_CAPITAL,
        min_confluence_score: int = MIN_CONFLUENCE_SCORE
    ) -> Dict[str, Any]:
        c_price = market_data["current_price"]
        quality = technicals.get("data_quality") or {}
        if quality.get("status") == "insufficient":
            reason = quality.get("reason", "Insufficient complete candle history; no candidate produced.")
            return {
                "signal": "WAIT",
                "confluence_score": 0,
                "confidence": None,
                "entry": c_price,
                "target_1": c_price,
                "target_2": c_price,
                "stop_loss": c_price,
                "reasons": [reason],
                "risk_sizing": None,
            }

        ema_9 = technicals.get("ema_9", c_price)
        ema_21 = technicals.get("ema_21", c_price)
        atr = technicals.get("atr", 5.0)

        from app.departments.signal_risk.confluence import evaluate_confluence_rules
        conf = evaluate_confluence_rules(c_price, technicals, quality, fundamentals, intelligence)
        bull_score, bear_score = conf.bull_score, conf.bear_score
        max_score = conf.max_score
        bull_reasons, bear_reasons = conf.bull_reasons, conf.bear_reasons
        adx_available = conf.adx_available
        m15_alignment_reason = conf.m15_alignment_reason
        m15_conflicts = conf.m15_conflicts

        # Session Trap Filter (09:15-09:30 AM block)
        if intelligence.get("session", {}).get("phase") == "OPENING_TRAP_ZONE":
            return {
                "signal": "WAIT",
                "confluence_score": 0,
                "confidence": 30,
                "entry": c_price, "target_1": c_price, "target_2": c_price, "stop_loss": c_price,
                "reasons": ["Opening Trap Zone Active (09:15-09:30 AM): Orders blocked to prevent stop-loss hunting."],
                "risk_sizing": calculate_trade_risk_and_sizing(c_price, c_price - 1.0, c_price + 2.0, c_price + 3.0, capital)
            }

        # Final Verdict Decision
        volatility_buffer = max(1.2 * atr, c_price * 0.005)

        if bull_score == bear_score:
            signal_state = "WATCHING" if bull_score >= 4 else "SCANNING"
            total_score = bull_score
            reasons = ["Bullish and bearish confluence are tied; no directional candidate is issued."]
            stop_loss = target_1 = target_2 = c_price
        elif bull_score > bear_score and bull_score >= min_confluence_score:
            signal_state = "BUY CANDIDATE"
            total_score = bull_score
            reasons = bull_reasons
            stop_loss = round(c_price - volatility_buffer, 2)
            target_1 = round(c_price + (volatility_buffer * 2.0), 2)  # Mandatory 1:2 R:R
            target_2 = round(c_price + (volatility_buffer * 3.0), 2)
        elif bear_score > bull_score and bear_score >= min_confluence_score:
            signal_state = "SELL CANDIDATE"
            total_score = bear_score
            reasons = bear_reasons
            stop_loss = round(c_price + volatility_buffer, 2)
            target_1 = round(c_price - (volatility_buffer * 2.0), 2)  # Mandatory 1:2 R:R
            target_2 = round(c_price - (volatility_buffer * 3.0), 2)
        else:
            signal_state = "WATCHING" if bear_score >= 4 or bull_score >= 4 else "SCANNING"
            total_score = max(bull_score, bear_score)
            reasons = [
                f"Confluence score below trigger threshold ({min_confluence_score}/{max_score} required). "
                "Awaiting clean setup alignment."
            ]
            stop_loss = target_1 = target_2 = c_price

        candles_5m = market_data.get("candles_5m", {})
        completed_closes = candles_5m.get("closes", [])
        latest_close = completed_closes[-1] if completed_closes else c_price
        below_both_emas = c_price < min(ema_9, ema_21) or latest_close < min(ema_9, ema_21)
        above_both_emas = c_price > max(ema_9, ema_21) or latest_close > max(ema_9, ema_21)
        if signal_state == "BUY CANDIDATE" and below_both_emas:
            signal_state = "WATCHING"
            stop_loss = target_1 = target_2 = c_price
            reasons.append(
                "BUY trigger withheld: the quote and latest completed 5m close are below EMA 9 and EMA 21; "
                "wait for a confirmed reclaim before considering a long entry."
            )
        elif signal_state == "SELL CANDIDATE" and above_both_emas:
            signal_state = "WATCHING"
            stop_loss = target_1 = target_2 = c_price
            reasons.append(
                "SHORT trigger withheld: the quote and latest completed 5m close are above EMA 9 and EMA 21; "
                "wait for a confirmed rejection before considering a short entry."
            )

        if not adx_available:
            reasons.append(f"ADX is still warming up; its momentum point is withheld from the {max_score} available confluence points.")
        if m15_alignment_reason and m15_alignment_reason not in reasons:
            reasons.append(m15_alignment_reason)
        if m15_conflicts:
            reasons.append("15m trend conflicts with the intraday confluence; no alignment point is awarded.")

        risk_profile = calculate_trade_risk_and_sizing(
            entry_price=c_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            capital=capital
        ) if signal_state in ("BUY CANDIDATE", "SELL CANDIDATE") else None

        return {
            "signal": signal_state,
            "confluence_score": total_score,
            "max_score": max_score,
            "confidence": None if bull_score == bear_score else min(95, max(45, total_score * 10)),
            "entry": c_price,
            "target_1": target_1,
            "target_2": target_2,
            "stop_loss": stop_loss,
            "reasons": reasons,
            "risk_sizing": risk_profile
        }

signal_risk_dep = SignalRiskDepartment()

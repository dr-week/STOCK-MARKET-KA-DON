import sqlite3
import os
import json
import time
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "signals_tree.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Analysis Scan Runs (Root nodes of the analysis tree)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            ist_time TEXT,
            market_phase TEXT,
            total_scanned INTEGER,
            bullish_count INTEGER,
            bearish_count INTEGER
        )
    """)
    
    # 2. Individual Stock Signal Nodes (Branch nodes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_run_id INTEGER,
            symbol TEXT,
            company_name TEXT,
            sector TEXT,
            price REAL,
            change_pct REAL,
            signal TEXT,
            confidence INTEGER,
            ai_score REAL,
            ai_verdict TEXT,
            entry REAL,
            target_1 REAL,
            target_2 REAL,
            stop_loss REAL,
            vwap REAL,
            rsi REAL,
            ema_9 REAL,
            ema_21 REAL,
            atr REAL,
            reasons_json TEXT,
            news_count INTEGER,
            created_at REAL,
            FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id)
        )
    """)
    
    # 3. Backtest Outcomes & Verifications (Leaf performance nodes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            test_date TEXT,
            signal_type TEXT,
            entry_price REAL,
            target_1 REAL,
            target_2 REAL,
            stop_loss REAL,
            outcome TEXT,  -- TARGET_1_HIT, TARGET_2_HIT, STOP_LOSS_HIT, TIME_EXPIRED
            pnl_pct REAL,
            bars_held INTEGER,
            max_favorable_excursion REAL,
            max_adverse_excursion REAL,
            evaluated_at REAL
        )
    """)
    
    conn.commit()
    conn.close()

def record_analysis_tree(market_phase: str, ist_time: str, stocks_data: List[Dict[str, Any]]) -> int:
    """Records a complete scan snapshot and all signal branches in the SQLite tree"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = time.time()
    bullish = sum(1 for s in stocks_data if "BUY" in (s.get("intraday") or {}).get("signal", ""))
    bearish = sum(1 for s in stocks_data if "SELL" in (s.get("intraday") or {}).get("signal", ""))
    
    cursor.execute("""
        INSERT INTO scan_runs (timestamp, ist_time, market_phase, total_scanned, bullish_count, bearish_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now, ist_time, market_phase, len(stocks_data), bullish, bearish))
    
    scan_id = cursor.lastrowid
    
    for s in stocks_data:
        intra = s.get("intraday") or {}
        ai = s.get("ai_decision") or {}
        cursor.execute("""
            INSERT INTO signal_nodes (
                scan_run_id, symbol, company_name, sector, price, change_pct,
                signal, confidence, ai_score, ai_verdict, entry, target_1, target_2, stop_loss,
                vwap, rsi, ema_9, ema_21, atr, reasons_json, news_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scan_id, s["symbol"], s["name"], s["sector"], s["current_price"], s["change_pct"],
            intra.get("signal", "HOLD"), intra.get("confidence", 50),
            ai.get("ai_score", 0.5), ai.get("ai_verdict", "NEUTRAL"),
            intra.get("entry", 0), intra.get("target_1", 0), intra.get("target_2", 0), intra.get("stop_loss", 0),
            intra.get("vwap", 0), intra.get("rsi", 50), intra.get("ema_9", 0), intra.get("ema_21", 0),
            intra.get("atr", 0), json.dumps(intra.get("reasons", [])), len(s.get("news", [])), now
        ))
        
    conn.commit()
    conn.close()
    return scan_id

def get_tree_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches recent analysis tree snapshots"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM scan_runs ORDER BY id DESC LIMIT ?
    """, (limit,))
    
    runs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return runs

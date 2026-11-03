import sqlite3

from .pnl_calculator import unrealized_pnl


def update_for_symbol(connection: sqlite3.Connection, symbol: str, current_price: float) -> int:
    rows = connection.execute(
        "SELECT id, action, entry_price, qty FROM paper_positions WHERE status='OPEN' AND symbol=?",
        (symbol,),
    ).fetchall()
    for row in rows:
        connection.execute(
            "UPDATE paper_positions SET unrealized_pnl=? WHERE id=?",
            (unrealized_pnl(row["action"], row["entry_price"], current_price, row["qty"]), row["id"]),
        )
    connection.commit()
    return len(rows)

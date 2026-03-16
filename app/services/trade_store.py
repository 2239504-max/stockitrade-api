import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path("data/trades.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                fee REAL NOT NULL DEFAULT 0,
                account TEXT,
                memo TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def insert_trade(trade: dict[str, Any]) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO trades (date, ticker, side, quantity, price, fee, account, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade["date"],
                trade["ticker"],
                trade["side"],
                trade["quantity"],
                trade["price"],
                trade.get("fee", 0),
                trade.get("account"),
                trade.get("memo"),
            ),
        )
        return int(cursor.lastrowid)


def list_trades() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, date, ticker, side, quantity, price, fee, account, memo, created_at FROM trades ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_summary() -> dict[str, Any]:
    trades = list_trades()
    positions: dict[str, float] = {}
    cash = 0.0

    for trade in trades:
        qty = float(trade["quantity"])
        price = float(trade["price"])
        fee = float(trade["fee"])
        ticker = trade["ticker"]
        side = str(trade["side"]).lower()

        if side == "buy":
            positions[ticker] = positions.get(ticker, 0.0) + qty
            cash -= qty * price + fee
        elif side == "sell":
            positions[ticker] = positions.get(ticker, 0.0) - qty
            cash += qty * price - fee

    open_positions = {k: v for k, v in positions.items() if abs(v) > 0}

    return {
        "total_trades": len(trades),
        "total_positions": len(open_positions),
        "positions": open_positions,
        "cash": round(cash, 2),
        "market_value": 0,
    }

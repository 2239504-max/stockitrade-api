import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import settings

DB_PATH = Path(settings.db_path)


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
                market TEXT,
                currency TEXT,
                asset_type TEXT,
                upload_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def insert_trade(trade: dict[str, Any]) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO trades (
                date, ticker, side, quantity, price, fee, account, memo,
                market, currency, asset_type, upload_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                trade.get("market"),
                trade.get("currency"),
                trade.get("asset_type"),
                trade.get("upload_id"),
            ),
        )
        return int(cursor.lastrowid)


def list_trades() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id, date, ticker, side, quantity, price, fee, account, memo,
                market, currency, asset_type, upload_id, created_at
            FROM trades
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]

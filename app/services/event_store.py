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


def init_event_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS normalized_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                ticker TEXT,
                ticker_name TEXT,
                quantity REAL,
                price REAL,
                amount REAL,
                fee REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL DEFAULT 0,
                currency TEXT,
                account TEXT,
                memo TEXT,
                raw_trade_name TEXT,
                source_broker TEXT,
                source_row_number INTEGER,
                market TEXT,
                asset_type TEXT,
                mapping_status TEXT,
                file_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def insert_normalized_event(event: dict[str, Any], file_hash: str | None = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO normalized_events (
                date, event_type, ticker, ticker_name, quantity, price, amount,
                fee, tax, currency, account, memo, raw_trade_name,
                source_broker, source_row_number, market, asset_type,
                mapping_status, file_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.get("date"),
                event.get("event_type"),
                event.get("ticker"),
                event.get("ticker_name"),
                event.get("quantity"),
                event.get("price"),
                event.get("amount"),
                event.get("fee", 0),
                event.get("tax", 0),
                event.get("currency"),
                event.get("account"),
                event.get("memo"),
                event.get("raw_trade_name"),
                event.get("source_broker"),
                event.get("source_row_number"),
                event.get("market"),
                event.get("asset_type"),
                event.get("mapping_status"),
                file_hash,
            ),
        )
        return int(cursor.lastrowid)


def insert_normalized_events(events: list[dict[str, Any]], file_hash: str | None = None) -> int:
    inserted = 0
    for event in events:
        insert_normalized_event(event, file_hash=file_hash)
        inserted += 1
    return inserted


def list_normalized_events(limit: int = 1000) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id, date, event_type, ticker, ticker_name, quantity, price, amount,
                fee, tax, currency, account, memo, raw_trade_name,
                source_broker, source_row_number, market, asset_type,
                mapping_status, file_hash, created_at
            FROM normalized_events
            ORDER BY date, id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def count_normalized_events() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM normalized_events"
        ).fetchone()
    return int(row["cnt"])


def delete_events_by_file_hash(file_hash: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM normalized_events
            WHERE file_hash = ?
            """,
            (file_hash,),
        )
        return int(cursor.rowcount)


def count_events_by_file_hash(file_hash: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM normalized_events
            WHERE file_hash = ?
            """,
            (file_hash,),
        ).fetchone()
    return int(row["cnt"])

def list_all_normalized_events() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id, date, event_type, ticker, ticker_name, quantity, price, amount,
                fee, tax, currency, account, memo, raw_trade_name,
                source_broker, source_row_number, market, asset_type,
                mapping_status, file_hash, created_at
            FROM normalized_events
            ORDER BY date, id
            """
        ).fetchall()

    return [dict(row) for row in rows]


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


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {row["name"] for row in rows}
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


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
                trade_no TEXT,
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
        _ensure_column(conn, "normalized_events", "trade_no", "TEXT")


def insert_normalized_event(event: dict[str, Any], file_hash: str | None = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO normalized_events (
                date, event_type, ticker, ticker_name, quantity, price, amount,
                fee, tax, currency, account, memo, raw_trade_name, trade_no,
                source_broker, source_row_number, market, asset_type,
                mapping_status, file_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                event.get("trade_no"),
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


def _build_event_filters(
    date_from: str | None = None,
    date_to: str | None = None,
    ticker: str | None = None,
    event_type: str | None = None,
    currency: str | None = None,
    raw_trade_name: str | None = None,
    file_hash: str | None = None,
) -> tuple[list[str], list[Any]]:
    where_clauses: list[str] = []
    params: list[Any] = []

    if date_from:
        where_clauses.append("date >= ?")
        params.append(date_from)

    if date_to:
        where_clauses.append("date <= ?")
        params.append(date_to)

    if ticker:
        where_clauses.append("ticker = ?")
        params.append(ticker)

    if event_type:
        where_clauses.append("event_type = ?")
        params.append(event_type)

    if currency:
        where_clauses.append("currency = ?")
        params.append(currency)

    if raw_trade_name:
        where_clauses.append("raw_trade_name LIKE ?")
        params.append(f"%{raw_trade_name}%")

    if file_hash:
        where_clauses.append("file_hash = ?")
        params.append(file_hash)

    return where_clauses, params


def list_normalized_events(
    limit: int = 1000,
    offset: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
    ticker: str | None = None,
    event_type: str | None = None,
    currency: str | None = None,
    raw_trade_name: str | None = None,
    file_hash: str | None = None,
) -> list[dict[str, Any]]:
    where_clauses, params = _build_event_filters(
        date_from=date_from,
        date_to=date_to,
        ticker=ticker,
        event_type=event_type,
        currency=currency,
        raw_trade_name=raw_trade_name,
        file_hash=file_hash,
    )

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT
            id, date, event_type, ticker, ticker_name, quantity, price, amount,
            fee, tax, currency, account, memo, raw_trade_name, trade_no,
            source_broker, source_row_number, market, asset_type,
            mapping_status, file_hash, created_at
        FROM normalized_events
        {where_sql}
        ORDER BY date, id
        LIMIT ? OFFSET ?
    """

    with get_connection() as conn:
        rows = conn.execute(sql, (*params, limit, offset)).fetchall()

    return [dict(row) for row in rows]


def count_normalized_events(
    date_from: str | None = None,
    date_to: str | None = None,
    ticker: str | None = None,
    event_type: str | None = None,
    currency: str | None = None,
    raw_trade_name: str | None = None,
    file_hash: str | None = None,
) -> int:
    where_clauses, params = _build_event_filters(
        date_from=date_from,
        date_to=date_to,
        ticker=ticker,
        event_type=event_type,
        currency=currency,
        raw_trade_name=raw_trade_name,
        file_hash=file_hash,
    )

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT COUNT(*) AS cnt
        FROM normalized_events
        {where_sql}
    """

    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()

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


def delete_all_events() -> int:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM normalized_events")
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
                fee, tax, currency, account, memo, raw_trade_name, trade_no,
                source_broker, source_row_number, market, asset_type,
                mapping_status, file_hash, created_at
            FROM normalized_events
            ORDER BY date, id
            """
        ).fetchall()

    return [dict(row) for row in rows]

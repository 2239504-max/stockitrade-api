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
        # 기존 trades 테이블
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

        # 이름 매핑 후보 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS name_mapping_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                candidate_ticker TEXT,
                candidate_name TEXT,
                exchange TEXT,
                market TEXT,
                asset_type TEXT,
                currency TEXT,
                source TEXT,
                score REAL NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 최종 확정 매핑 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS name_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_name TEXT NOT NULL UNIQUE,
                normalized_name TEXT NOT NULL,
                ticker TEXT NOT NULL,
                canonical_name TEXT,
                exchange TEXT,
                market TEXT,
                asset_type TEXT,
                currency TEXT,
                source TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 1.0,
                mapping_status TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 미해결 이름 큐
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS unmapped_names (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_name TEXT NOT NULL UNIQUE,
                normalized_name TEXT NOT NULL,
                first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                seen_count INTEGER NOT NULL DEFAULT 1,
                latest_source_broker TEXT,
                latest_currency TEXT,
                latest_market_hint TEXT
            )
            """
        )


# -----------------------------
# 기존 trades 관련 함수
# -----------------------------
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


# -----------------------------
# name_mappings 관련 함수
# -----------------------------
def find_name_mapping_by_raw_name(raw_name: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM name_mappings
            WHERE raw_name = ?
            LIMIT 1
            """,
            (raw_name,),
        ).fetchone()

    return dict(row) if row else None


def find_name_mapping_by_normalized_name(normalized_name: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM name_mappings
            WHERE normalized_name = ?
            ORDER BY confidence DESC, updated_at DESC
            """,
            (normalized_name,),
        ).fetchall()

    return [dict(row) for row in rows]


def upsert_name_mapping(
    raw_name: str,
    normalized_name: str,
    ticker: str,
    canonical_name: str | None = None,
    exchange: str | None = None,
    market: str | None = None,
    asset_type: str | None = None,
    currency: str | None = None,
    source: str = "manual",
    confidence: float = 1.0,
    mapping_status: str = "confirmed",
    notes: str | None = None,
) -> int:
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM name_mappings
            WHERE raw_name = ?
            LIMIT 1
            """,
            (raw_name,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE name_mappings
                SET normalized_name = ?,
                    ticker = ?,
                    canonical_name = ?,
                    exchange = ?,
                    market = ?,
                    asset_type = ?,
                    currency = ?,
                    source = ?,
                    confidence = ?,
                    mapping_status = ?,
                    notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE raw_name = ?
                """,
                (
                    normalized_name,
                    ticker,
                    canonical_name,
                    exchange,
                    market,
                    asset_type,
                    currency,
                    source,
                    confidence,
                    mapping_status,
                    notes,
                    raw_name,
                ),
            )
            return int(existing["id"])

        cursor = conn.execute(
            """
            INSERT INTO name_mappings (
                raw_name, normalized_name, ticker, canonical_name,
                exchange, market, asset_type, currency,
                source, confidence, mapping_status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_name,
                normalized_name,
                ticker,
                canonical_name,
                exchange,
                market,
                asset_type,
                currency,
                source,
                confidence,
                mapping_status,
                notes,
            ),
        )
        return int(cursor.lastrowid)


# -----------------------------
# 후보(candidate) 관련 함수
# -----------------------------
def clear_name_mapping_candidates(raw_name: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM name_mapping_candidates
            WHERE raw_name = ?
            """,
            (raw_name,),
        )


def save_name_mapping_candidates(
    raw_name: str,
    normalized_name: str,
    candidates: list[dict[str, Any]],
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM name_mapping_candidates
            WHERE raw_name = ?
            """,
            (raw_name,),
        )

        for candidate in candidates:
            conn.execute(
                """
                INSERT INTO name_mapping_candidates (
                    raw_name, normalized_name, candidate_ticker, candidate_name,
                    exchange, market, asset_type, currency, source, score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_name,
                    normalized_name,
                    candidate.get("ticker"),
                    candidate.get("candidate_name") or candidate.get("name"),
                    candidate.get("exchange"),
                    candidate.get("market"),
                    candidate.get("asset_type"),
                    candidate.get("currency"),
                    candidate.get("source"),
                    candidate.get("score", 0),
                ),
            )


def list_name_mapping_candidates(raw_name: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM name_mapping_candidates
            WHERE raw_name = ?
            ORDER BY score DESC, created_at DESC
            """,
            (raw_name,),
        ).fetchall()

    return [dict(row) for row in rows]


# -----------------------------
# 미해결(unmapped) 관련 함수
# -----------------------------
def upsert_unmapped_name(
    raw_name: str,
    normalized_name: str,
    latest_source_broker: str | None = None,
    latest_currency: str | None = None,
    latest_market_hint: str | None = None,
) -> int:
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id, seen_count
            FROM unmapped_names
            WHERE raw_name = ?
            LIMIT 1
            """,
            (raw_name,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE unmapped_names
                SET normalized_name = ?,
                    last_seen_at = CURRENT_TIMESTAMP,
                    seen_count = ?,
                    latest_source_broker = ?,
                    latest_currency = ?,
                    latest_market_hint = ?
                WHERE raw_name = ?
                """,
                (
                    normalized_name,
                    int(existing["seen_count"]) + 1,
                    latest_source_broker,
                    latest_currency,
                    latest_market_hint,
                    raw_name,
                ),
            )
            return int(existing["id"])

        cursor = conn.execute(
            """
            INSERT INTO unmapped_names (
                raw_name, normalized_name,
                latest_source_broker, latest_currency, latest_market_hint
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                raw_name,
                normalized_name,
                latest_source_broker,
                latest_currency,
                latest_market_hint,
            ),
        )
        return int(cursor.lastrowid)


def list_unmapped_names() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM unmapped_names
            ORDER BY seen_count DESC, last_seen_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]

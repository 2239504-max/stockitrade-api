import hashlib
import uuid
from pathlib import Path

from app.core.config import settings
from app.providers.kis.market import get_quote
from app.services.parser_shinhan import parse_shinhan_xlsx
from app.services.trade_store import (
    init_db,
    insert_trade,
    list_trades,
)

from app.services.name_mapping_service import (
    resolve_name,
    calculate_unmapped_name_priorities,
)
from app.services.name_mapping_seed import seed_name_mappings

init_db()
seed_name_mappings()

def _save_upload_file(filename: str, file_bytes: bytes) -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_path = upload_dir / f"{uuid.uuid4()}_{Path(filename).name}"
    saved_path.write_bytes(file_bytes)
    return saved_path


def _hash_bytes(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def ingest_shinhan_file(filename: str, file_bytes: bytes) -> dict:
    if not filename.endswith(".xlsx"):
        raise ValueError("Only .xlsx files are allowed")

    saved_path = _save_upload_file(filename, file_bytes)
    parsed_events, errors, unknown_trade_names = parse_shinhan_xlsx(saved_path)
    enriched_events = _enrich_events_with_ticker(parsed_events)

    mapped_count = sum(1 for e in enriched_events if e.get("ticker"))
    unmapped_name_count = sum(
        1
        for e in enriched_events
        if e.get("ticker_name") and not e.get("ticker")
    )
    unmapped_name_priorities = calculate_unmapped_name_priorities(enriched_events)

    return {
        "message": "shinhan upload parsed",
        "filename": filename,
        "saved_path": str(saved_path),
        "file_hash": _hash_bytes(file_bytes),
        "parsed_count": len(enriched_events),
        "mapped_count": mapped_count,
        "unmapped_name_count": unmapped_name_count,
        "error_count": len(errors),
        "errors": errors,
        "unknown_trade_names": unknown_trade_names,
        "unmapped_name_priorities": unmapped_name_priorities[:30],
        "parsed_preview_head": enriched_events[:20],
        "parsed_preview_tail": enriched_events[-20:],
    }


def create_manual_trade(payload: dict) -> dict:
    trade_id = insert_trade(payload)
    return {
        "message": "manual trade created",
        "trade_id": trade_id,
        "trade": payload,
    }


def build_portfolio_summary() -> dict:
    trades = list_trades()

    lots: dict[str, dict] = {}
    realized_pnl = 0.0
    cash = 0.0

    for trade in trades:
        ticker = trade["ticker"]
        side = str(trade["side"]).lower()
        qty = float(trade["quantity"])
        price = float(trade["price"])
        fee = float(trade["fee"] or 0)

        if ticker not in lots:
            lots[ticker] = {
                "quantity": 0.0,
                "cost_basis": 0.0,
                "market": trade.get("market"),
                "currency": trade.get("currency"),
            }

        bucket = lots[ticker]

        if side == "buy":
            bucket["cost_basis"] += qty * price + fee
            bucket["quantity"] += qty
            cash -= qty * price + fee

        elif side == "sell":
            if bucket["quantity"] <= 0:
                avg_cost = 0.0
            else:
                avg_cost = bucket["cost_basis"] / bucket["quantity"]

            realized_pnl += (price - avg_cost) * qty - fee
            bucket["quantity"] -= qty
            bucket["cost_basis"] -= avg_cost * qty
            cash += qty * price - fee

    positions = []
    market_value = 0.0
    unrealized_pnl = 0.0

    for ticker, bucket in lots.items():
        qty = bucket["quantity"]
        if abs(qty) <= 0:
            continue

        avg_cost = bucket["cost_basis"] / qty if qty else 0.0
        market = bucket.get("market") or "US"

        quote = get_quote(ticker, market=market)
        current_price = float(quote["price"])

        position_market_value = qty * current_price
        position_unrealized = (current_price - avg_cost) * qty

        positions.append({
            "ticker": ticker,
            "quantity": round(qty, 6),
            "avg_cost": round(avg_cost, 4),
            "current_price": round(current_price, 4),
            "market_value": round(position_market_value, 2),
            "unrealized_pnl": round(position_unrealized, 2),
            "realized_pnl": 0.0,
            "market": market,
            "currency": bucket.get("currency") or quote.get("currency"),
        })

        market_value += position_market_value
        unrealized_pnl += position_unrealized

    return {
        "total_trades": len(trades),
        "total_positions": len(positions),
        "cash": round(cash, 2),
        "market_value": round(market_value, 2),
        "total_value": round(cash + market_value, 2),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "positions": positions,
    }

def _enrich_events_with_ticker(parsed_events: list[dict]) -> list[dict]:
    enriched: list[dict] = []

    for event in parsed_events:
        copied = dict(event)

        raw_name = copied.get("ticker_name")
        currency = copied.get("currency")

        if raw_name and not copied.get("ticker"):
            mapping = resolve_name(
                raw_name=raw_name,
                source_broker="shinhan",
                currency=currency,
                market_hint=None,
            )
            if mapping:
                copied["ticker"] = mapping["ticker"]
                copied["market"] = mapping.get("market")
                copied["asset_type"] = mapping.get("asset_type")
                copied["mapping_status"] = mapping.get("mapping_status")
            else:
                copied["mapping_status"] = "unmapped"
        else:
            copied["mapping_status"] = "not_applicable"

        enriched.append(copied)

    return enriched

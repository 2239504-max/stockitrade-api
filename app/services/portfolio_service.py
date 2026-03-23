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

from app.services.event_store import (
    init_event_db,
    insert_normalized_events,
    count_events_by_file_hash,
)

init_db()
init_event_db()
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

    file_hash = _hash_bytes(file_bytes)
    existing_count = count_events_by_file_hash(file_hash)
    if existing_count > 0:
        raise ValueError(f"This file was already uploaded before: {existing_count} events")

    saved_path = _save_upload_file(filename, file_bytes)
    parsed_events, errors, unknown_trade_names = parse_shinhan_xlsx(saved_path)
    enriched_events = _enrich_events_with_ticker(parsed_events)

    inserted_count = insert_normalized_events(enriched_events, file_hash=file_hash)

    mapped_count = sum(1 for e in enriched_events if e.get("ticker"))
    unmapped_name_count = sum(
        1
        for e in enriched_events
        if (
            e.get("ticker_name")
            and not e.get("ticker")
            and e.get("ticker_name") not in {"USD", "KRW", "JPY", "EUR"}
        )
    )
    unmapped_name_priorities = calculate_unmapped_name_priorities(enriched_events)

    return {
        "message": "shinhan upload parsed and stored",
        "filename": filename,
        "saved_path": str(saved_path),
        "file_hash": file_hash,
        "parsed_count": len(enriched_events),
        "inserted_count": inserted_count,
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

def build_portfolio_cash() -> dict:
    events = list_all_normalized_events()

    cash_by_currency: dict[str, dict] = {}

    def ensure_bucket(currency: str) -> dict:
        if currency not in cash_by_currency:
            cash_by_currency[currency] = {
                "currency": currency,
                "net_cash": 0.0,
                "cash_in": 0.0,
                "cash_out": 0.0,
                "buy_out": 0.0,
                "sell_in": 0.0,
                "dividend_in": 0.0,
                "tax_out": 0.0,
                "fx_buy_out": 0.0,
                "fx_sell_in": 0.0,
                "fx_pnl_adjust": 0.0,
            }
        return cash_by_currency[currency]

    for event in events:
        event_type = event.get("event_type")
        currency = event.get("currency") or "KRW"

        amount = float(event.get("amount") or 0)
        fee = float(event.get("fee") or 0)
        tax = float(event.get("tax") or 0)

        bucket = ensure_bucket(currency)

        if event_type == "CASH_IN":
            bucket["cash_in"] += amount
            bucket["net_cash"] += amount

        elif event_type == "CASH_OUT":
            bucket["cash_out"] += amount
            bucket["net_cash"] -= amount

        elif event_type == "BUY":
            cash_delta = amount + fee
            bucket["buy_out"] += cash_delta
            bucket["net_cash"] -= cash_delta

        elif event_type == "SELL":
            cash_delta = amount - fee
            bucket["sell_in"] += cash_delta
            bucket["net_cash"] += cash_delta

        elif event_type == "DIVIDEND":
            dividend_amount = amount
            bucket["dividend_in"] += dividend_amount
            bucket["net_cash"] += dividend_amount

        elif event_type == "TAX":
            tax_amount = amount if amount > 0 else tax
            bucket["tax_out"] += tax_amount
            bucket["net_cash"] -= tax_amount

        elif event_type == "FX_BUY":
            bucket["fx_buy_out"] += amount
            bucket["net_cash"] -= amount

        elif event_type == "FX_SELL":
            bucket["fx_sell_in"] += amount
            bucket["net_cash"] += amount

        elif event_type == "FX_PNL_ADJUST":
            bucket["fx_pnl_adjust"] += amount
            bucket["net_cash"] += amount

        # TRANSFER_IN_KIND 는 현금 이동이 아니라 종목 입고이므로 cash에서는 제외

    cash_list = []
    for bucket in cash_by_currency.values():
        cash_list.append({
            "currency": bucket["currency"],
            "net_cash": round(bucket["net_cash"], 6),
            "cash_in": round(bucket["cash_in"], 6),
            "cash_out": round(bucket["cash_out"], 6),
            "buy_out": round(bucket["buy_out"], 6),
            "sell_in": round(bucket["sell_in"], 6),
            "dividend_in": round(bucket["dividend_in"], 6),
            "tax_out": round(bucket["tax_out"], 6),
            "fx_buy_out": round(bucket["fx_buy_out"], 6),
            "fx_sell_in": round(bucket["fx_sell_in"], 6),
            "fx_pnl_adjust": round(bucket["fx_pnl_adjust"], 6),
        })

    cash_list.sort(key=lambda x: x["currency"])

    return {
        "count": len(cash_list),
        "cash": cash_list,
    }

def build_portfolio_holdings() -> dict:
    events = list_all_normalized_events()

    positions: dict[str, dict] = {}
    realized_pnl_by_currency: dict[str, float] = {}

    for event in events:
        event_type = event.get("event_type")
        ticker = event.get("ticker")

        # holdings 대상 이벤트만 반영
        if event_type not in {"BUY", "SELL", "TRANSFER_IN_KIND"}:
            continue

        # ticker 없는 이벤트는 holdings 계산에서 제외
        if not ticker:
            continue

        quantity = float(event.get("quantity") or 0)
        price = float(event.get("price") or 0)
        amount = float(event.get("amount") or 0)
        fee = float(event.get("fee") or 0)
        currency = event.get("currency") or "UNKNOWN"

        if ticker not in positions:
            positions[ticker] = {
                "ticker": ticker,
                "ticker_name": event.get("ticker_name"),
                "quantity": 0.0,
                "cost_basis": 0.0,
                "avg_cost": 0.0,
                "market": event.get("market"),
                "asset_type": event.get("asset_type"),
                "currency": currency,
                "realized_pnl": 0.0,
                "last_event_date": event.get("date"),
            }

        pos = positions[ticker]

        if event_type in {"BUY", "TRANSFER_IN_KIND"}:
            buy_cost = amount if amount > 0 else (quantity * price)
            buy_cost += fee

            pos["cost_basis"] += buy_cost
            pos["quantity"] += quantity
            pos["avg_cost"] = (
                pos["cost_basis"] / pos["quantity"]
                if pos["quantity"] > 0
                else 0.0
            )

        elif event_type == "SELL":
            if pos["quantity"] <= 0:
                continue

            avg_cost_before_sell = pos["cost_basis"] / pos["quantity"]
            sell_proceeds = amount if amount > 0 else (quantity * price)
            sell_proceeds -= fee

            realized = sell_proceeds - (avg_cost_before_sell * quantity)

            pos["realized_pnl"] += realized
            pos["quantity"] -= quantity
            pos["cost_basis"] -= avg_cost_before_sell * quantity
            pos["avg_cost"] = (
                pos["cost_basis"] / pos["quantity"]
                if pos["quantity"] > 0
                else 0.0
            )

            realized_pnl_by_currency[currency] = (
                realized_pnl_by_currency.get(currency, 0.0) + realized
            )

        pos["last_event_date"] = event.get("date")

    holdings = []
    for pos in positions.values():
        # 완전 청산된 종목은 제외
        if abs(pos["quantity"]) <= 1e-12:
            continue

        holdings.append({
            "ticker": pos["ticker"],
            "ticker_name": pos["ticker_name"],
            "quantity": round(pos["quantity"], 6),
            "avg_cost": round(pos["avg_cost"], 6),
            "cost_basis": round(pos["cost_basis"], 6),
            "market": pos["market"],
            "asset_type": pos["asset_type"],
            "currency": pos["currency"],
            "realized_pnl": round(pos["realized_pnl"], 6),
            "last_event_date": pos["last_event_date"],
        })

    holdings.sort(key=lambda x: (x["currency"] or "", x["ticker"] or ""))

    return {
        "count": len(holdings),
        "holdings": holdings,
        "realized_pnl_by_currency": {
            k: round(v, 6) for k, v in realized_pnl_by_currency.items()
        },
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

import hashlib
import uuid
from collections import defaultdict
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
    list_all_normalized_events,
)

init_db()
init_event_db()
seed_name_mappings()

KNOWN_CURRENCY_CODES = {
    "KRW",
    "USD",
    "JPY",
    "EUR",
    "HKD",
    "CNY",
    "CNH",
    "GBP",
    "AUD",
    "CAD",
    "SGD",
    "CHF",
    "NZD",
}

MARKET_CURRENCY_MAP = {
    "US": "USD",
    "KR": "KRW",
}


def _save_upload_file(filename: str, file_bytes: bytes) -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_path = upload_dir / f"{uuid.uuid4()}_{Path(filename).name}"
    saved_path.write_bytes(file_bytes)
    return saved_path


def _hash_bytes(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _normalize_currency(value) -> str | None:
    if value is None:
        return None

    text = str(value).strip().upper()
    if not text or text == "UNKNOWN":
        return None

    return text


def _coalesce_currency(*values) -> str:
    for value in values:
        normalized = _normalize_currency(value)
        if normalized:
            return normalized
    return "UNKNOWN"


def _infer_currency_from_ticker_name(value) -> str | None:
    if value in (None, ""):
        return None

    text = str(value).strip().upper()
    for code in KNOWN_CURRENCY_CODES:
        if text == code or text.startswith(f"{code} "):
            return code
    return None


def _infer_event_currency(event: dict) -> str:
    market = str(event.get("market") or "").strip().upper()
    market_currency = MARKET_CURRENCY_MAP.get(market)

    return _coalesce_currency(
        event.get("currency"),
        _infer_currency_from_ticker_name(event.get("ticker_name")),
        market_currency,
    )


def _event_sort_key(e: dict) -> tuple:
    return (
        e.get("date") or "",
        int(e.get("source_row_number") or 0),
        int(e.get("id") or 0),
    )


def _build_tax_event_index(events: list[dict]) -> dict[tuple[str, str, float], list[int]]:
    tax_index: dict[tuple[str, str, float], list[int]] = {}

    for event in events:
        if event.get("event_type") != "TAX":
            continue

        currency = _infer_event_currency(event)
        tax_amount = float(event.get("amount") or event.get("tax") or 0)
        if tax_amount <= 0:
            continue

        key = (
            str(event.get("date") or ""),
            currency,
            round(tax_amount, 6),
        )
        tax_index.setdefault(key, []).append(int(event.get("source_row_number") or 0))

    for row_numbers in tax_index.values():
        row_numbers.sort()

    return tax_index


def _has_nearby_standalone_tax(
    event: dict,
    tax_amount: float,
    tax_index: dict[tuple[str, str, float], list[int]],
    row_window: int = 3,
) -> bool:
    if tax_amount <= 0:
        return False

    key = (
        str(event.get("date") or ""),
        _infer_event_currency(event),
        round(tax_amount, 6),
    )
    row_number = int(event.get("source_row_number") or 0)

    for candidate in tax_index.get(key, []):
        if abs(candidate - row_number) <= row_window:
            return True

    return False


def _embedded_sell_tax(event: dict, tax_index: dict[tuple[str, str, float], list[int]]) -> float:
    tax = float(event.get("tax") or 0)
    if tax <= 0:
        return 0.0

    if _has_nearby_standalone_tax(event, tax, tax_index):
        return 0.0

    return tax


def _resolve_plain_cash_event(event: dict) -> tuple[str, float, dict | None]:
    event_currency = _normalize_currency(event.get("currency"))
    ticker_name_currency = _infer_currency_from_ticker_name(event.get("ticker_name"))
    amount = float(event.get("amount") or 0)
    quantity = float(event.get("quantity") or 0)
    price = float(event.get("price") or 0)

    inferred_currency = _coalesce_currency(event_currency, ticker_name_currency)
    inferred_amount = amount
    anomaly = None

    if ticker_name_currency:
        inferred_currency = ticker_name_currency

        if quantity > 0:
            inferred_amount = quantity
        elif event_currency and event_currency != ticker_name_currency and amount > 0 and price > 0:
            inferred_amount = amount / price
        else:
            inferred_amount = amount

    if inferred_currency == "UNKNOWN":
        inferred_currency = "KRW"

        raw_trade_name = str(event.get("raw_trade_name") or "")
        if "외화" in raw_trade_name:
            anomaly = {
                "reason": "cash_event_missing_currency_with_foreign_hint",
                "date": event.get("date"),
                "raw_trade_name": event.get("raw_trade_name"),
                "source_row_number": event.get("source_row_number"),
            }

    return inferred_currency, inferred_amount, anomaly


def _resolve_fx_target(event: dict) -> tuple[str, float]:
    target_currency = _coalesce_currency(
        event.get("currency"),
        _infer_currency_from_ticker_name(event.get("ticker_name")),
    )
    amount = float(event.get("amount") or 0)
    quantity = float(event.get("quantity") or 0)
    price = float(event.get("price") or 0)

    if quantity > 0:
        return target_currency, quantity

    if amount > 0 and price > 0 and target_currency != "KRW":
        return target_currency, amount / price

    return target_currency, 0.0


def _build_same_day_buy_pool(events: list[dict]) -> dict[tuple[str, str], list[dict]]:
    pool: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for e in sorted(events, key=_event_sort_key):
        if e.get("event_type") not in {"BUY", "TRANSFER_IN_KIND"}:
            continue

        ticker = e.get("ticker")
        date = e.get("date")
        if not ticker or not date:
            continue

        qty = float(e.get("quantity") or 0)
        price = float(e.get("price") or 0)
        amount = float(e.get("amount") or 0)
        fee = float(e.get("fee") or 0)

        if qty <= 0:
            continue

        total_cost = amount if amount > 0 else (qty * price)
        total_cost += fee
        unit_cost = total_cost / qty if qty > 0 else 0.0

        pool[(date, ticker)].append({
            "event_id": int(e.get("id") or 0),
            "source_row_number": int(e.get("source_row_number") or 0),
            "remaining_qty": qty,
            "unit_cost": unit_cost,
        })

    return pool


def _consume_same_day_buy_cover(
    buy_pool: list[dict],
    current_row_number: int,
    needed_qty: float,
) -> tuple[float, float, list[dict]]:
    covered_qty = 0.0
    covered_cost = 0.0
    consumed: list[dict] = []

    for item in buy_pool:
        if item["source_row_number"] <= current_row_number:
            continue
        if item["remaining_qty"] <= 0:
            continue
        if needed_qty <= 1e-12:
            break

        take = min(item["remaining_qty"], needed_qty)
        item["remaining_qty"] -= take
        needed_qty -= take

        covered_qty += take
        covered_cost += take * item["unit_cost"]
        consumed.append({
            "event_id": item["event_id"],
            "qty": take,
            "unit_cost": item["unit_cost"],
        })

    return covered_qty, covered_cost, consumed


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
    holdings_result = build_portfolio_holdings()
    cash_result = build_portfolio_cash()

    holdings = holdings_result.get("holdings", [])
    cash = cash_result.get("cash", [])
    realized_pnl_by_currency = holdings_result.get("realized_pnl_by_currency", {})

    position_count_by_currency: dict[str, int] = {}
    holding_cost_basis_by_currency: dict[str, float] = {}
    open_positions_realized_pnl_by_currency: dict[str, float] = {}

    for item in holdings:
        currency = item.get("currency") or "UNKNOWN"
        position_count_by_currency[currency] = position_count_by_currency.get(currency, 0) + 1
        holding_cost_basis_by_currency[currency] = (
            holding_cost_basis_by_currency.get(currency, 0.0)
            + float(item.get("cost_basis") or 0.0)
        )
        open_positions_realized_pnl_by_currency[currency] = (
            open_positions_realized_pnl_by_currency.get(currency, 0.0)
            + float(item.get("realized_pnl") or 0.0)
        )

    return {
        "holdings_count": holdings_result.get("count", 0),
        "cash_count": cash_result.get("count", 0),
        "positions": holdings,
        "cash": cash,
        "realized_pnl_by_currency": {
            k: round(v, 6) for k, v in realized_pnl_by_currency.items()
        },
        "open_positions_realized_pnl_by_currency": {
            k: round(v, 6) for k, v in open_positions_realized_pnl_by_currency.items()
        },
        "position_count_by_currency": position_count_by_currency,
        "holding_cost_basis_by_currency": {
            k: round(v, 6) for k, v in holding_cost_basis_by_currency.items()
        },
        "anomalies": holdings_result.get("anomalies", []) + cash_result.get("anomalies", []),
    }


def build_portfolio_cash() -> dict:
    events = list_all_normalized_events()
    tax_index = _build_tax_event_index(events)

    cash_by_currency: dict[str, dict] = {}
    anomalies: list[dict] = []

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
                "fx_buy_in": 0.0,
                "fx_sell_out": 0.0,
                "fx_sell_in": 0.0,
                "fx_pnl_adjust": 0.0,
            }
        return cash_by_currency[currency]

    def add_cash(currency: str, field: str, delta: float, is_inflow: bool):
        bucket = ensure_bucket(currency)
        bucket[field] += delta
        if is_inflow:
            bucket["net_cash"] += delta
        else:
            bucket["net_cash"] -= delta

    for event in events:
        event_type = event.get("event_type")
        event_currency = _infer_event_currency(event)

        amount = float(event.get("amount") or 0)
        fee = float(event.get("fee") or 0)
        tax = float(event.get("tax") or 0)

        if event_type == "CASH_IN":
            currency, cash_amount, anomaly = _resolve_plain_cash_event(event)
            if anomaly:
                anomalies.append(anomaly)
            if cash_amount > 0:
                add_cash(currency, "cash_in", cash_amount, True)

        elif event_type == "CASH_OUT":
            currency, cash_amount, anomaly = _resolve_plain_cash_event(event)
            if anomaly:
                anomalies.append(anomaly)
            if cash_amount > 0:
                add_cash(currency, "cash_out", cash_amount, False)

        elif event_type == "BUY":
            trade_currency = event_currency
            cash_delta = amount + fee
            if cash_delta > 0:
                add_cash(trade_currency, "buy_out", cash_delta, False)
            elif trade_currency == "UNKNOWN":
                anomalies.append({
                    "reason": "buy_event_missing_currency",
                    "ticker": event.get("ticker"),
                    "date": event.get("date"),
                    "source_row_number": event.get("source_row_number"),
                })

        elif event_type == "SELL":
            trade_currency = event_currency
            embedded_tax = _embedded_sell_tax(event, tax_index)
            cash_delta = amount - fee - embedded_tax
            if cash_delta > 0:
                add_cash(trade_currency, "sell_in", cash_delta, True)
            elif trade_currency == "UNKNOWN":
                anomalies.append({
                    "reason": "sell_event_missing_currency",
                    "ticker": event.get("ticker"),
                    "date": event.get("date"),
                    "source_row_number": event.get("source_row_number"),
                })

        elif event_type == "DIVIDEND":
            dividend_currency = event_currency
            if amount > 0:
                add_cash(dividend_currency, "dividend_in", amount, True)

        elif event_type == "TAX":
            tax_currency = event_currency
            tax_amount = amount if amount > 0 else tax
            if tax_amount > 0:
                add_cash(tax_currency, "tax_out", tax_amount, False)

        elif event_type == "FX_BUY":
            target_currency, foreign_amount = _resolve_fx_target(event)

            if amount > 0:
                add_cash("KRW", "fx_buy_out", amount, False)
            if foreign_amount > 0:
                add_cash(target_currency, "fx_buy_in", foreign_amount, True)
            else:
                anomalies.append({
                    "reason": "fx_buy_missing_foreign_amount",
                    "date": event.get("date"),
                    "raw_trade_name": event.get("raw_trade_name"),
                    "source_row_number": event.get("source_row_number"),
                })

        elif event_type == "FX_SELL":
            source_currency, foreign_amount = _resolve_fx_target(event)

            if foreign_amount > 0:
                add_cash(source_currency, "fx_sell_out", foreign_amount, False)
            else:
                anomalies.append({
                    "reason": "fx_sell_missing_foreign_amount",
                    "date": event.get("date"),
                    "raw_trade_name": event.get("raw_trade_name"),
                    "source_row_number": event.get("source_row_number"),
                })

            if amount > 0:
                add_cash("KRW", "fx_sell_in", amount, True)

        elif event_type == "FX_PNL_ADJUST":
            if amount > 0:
                add_cash("KRW", "fx_pnl_adjust", amount, True)
            elif amount < 0:
                add_cash("KRW", "fx_pnl_adjust", abs(amount), False)

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
            "fx_buy_in": round(bucket["fx_buy_in"], 6),
            "fx_sell_out": round(bucket["fx_sell_out"], 6),
            "fx_sell_in": round(bucket["fx_sell_in"], 6),
            "fx_pnl_adjust": round(bucket["fx_pnl_adjust"], 6),
        })

    cash_list.sort(key=lambda x: x["currency"])

    return {
        "count": len(cash_list),
        "cash": cash_list,
        "anomalies": anomalies,
    }


def build_portfolio_holdings() -> dict:
    events = list_all_normalized_events()
    events = sorted(events, key=_event_sort_key)

    tax_index = _build_tax_event_index(events)
    same_day_buy_pool = _build_same_day_buy_pool(events)

    positions: dict[str, dict] = {}
    realized_pnl_by_currency: dict[str, float] = {}
    anomalies: list[dict] = []
    preconsumed_buy_qty_by_event_id: dict[int, float] = defaultdict(float)

    for event in events:
        event_type = event.get("event_type")
        ticker = event.get("ticker")

        if event_type not in {"BUY", "SELL", "TRANSFER_IN_KIND"}:
            continue

        if not ticker:
            continue

        quantity = float(event.get("quantity") or 0)
        price = float(event.get("price") or 0)
        amount = float(event.get("amount") or 0)
        fee = float(event.get("fee") or 0)
        event_currency = _infer_event_currency(event)

        if ticker not in positions:
            positions[ticker] = {
                "ticker": ticker,
                "ticker_name": event.get("ticker_name"),
                "quantity": 0.0,
                "cost_basis": 0.0,
                "avg_cost": 0.0,
                "market": event.get("market"),
                "asset_type": event.get("asset_type"),
                "currency": None if event_currency == "UNKNOWN" else event_currency,
                "realized_pnl": 0.0,
                "last_event_date": event.get("date"),
            }

        pos = positions[ticker]

        if not pos.get("currency") and event_currency != "UNKNOWN":
            pos["currency"] = event_currency

        if event_type in {"BUY", "TRANSFER_IN_KIND"}:
            event_id = int(event.get("id") or 0)
            already_used = preconsumed_buy_qty_by_event_id.get(event_id, 0.0)
            effective_qty = max(quantity - already_used, 0.0)

            if effective_qty <= 1e-12:
                pos["last_event_date"] = event.get("date")
                continue

            buy_cost = amount if amount > 0 else (quantity * price)
            buy_cost += fee

            if quantity > 0 and effective_qty < quantity:
                buy_cost *= (effective_qty / quantity)

            if event_type == "TRANSFER_IN_KIND" and buy_cost <= 0:
                anomalies.append({
                    "ticker": ticker,
                    "date": event.get("date"),
                    "reason": "transfer_in_kind_missing_cost_basis",
                    "event_quantity": effective_qty,
                    "source_row_number": event.get("source_row_number"),
                })

            pos["cost_basis"] += buy_cost
            pos["quantity"] += effective_qty
            pos["avg_cost"] = (
                pos["cost_basis"] / pos["quantity"]
                if pos["quantity"] > 0
                else 0.0
            )

        elif event_type == "SELL":
            currency = _coalesce_currency(pos.get("currency"), event_currency)

            current_row_number = int(event.get("source_row_number") or 0)
            shortage = max(quantity - pos["quantity"], 0.0)
            group_key = (event.get("date"), ticker)

            if shortage > 1e-12:
                covered_qty, covered_cost, consumed = _consume_same_day_buy_cover(
                    same_day_buy_pool.get(group_key, []),
                    current_row_number,
                    shortage,
                )

                if covered_qty > 0:
                    pos["quantity"] += covered_qty
                    pos["cost_basis"] += covered_cost

                    for item in consumed:
                        preconsumed_buy_qty_by_event_id[item["event_id"]] += item["qty"]

                    anomalies.append({
                        "ticker": ticker,
                        "date": event.get("date"),
                        "reason": "sell_before_buy_same_day_compensated",
                        "event_quantity": quantity,
                        "covered_qty": round(covered_qty, 6),
                        "source_row_number": event.get("source_row_number"),
                    })

            if pos["quantity"] <= 0:
                anomalies.append({
                    "ticker": ticker,
                    "date": event.get("date"),
                    "reason": "sell_with_no_position",
                    "event_quantity": quantity,
                    "position_quantity": pos["quantity"],
                })
                continue

            if quantity > pos["quantity"] + 1e-12:
                anomalies.append({
                    "ticker": ticker,
                    "date": event.get("date"),
                    "reason": "sell_exceeds_position",
                    "event_quantity": quantity,
                    "position_quantity": pos["quantity"],
                })
                continue

            avg_cost_before_sell = pos["cost_basis"] / pos["quantity"]
            embedded_tax = _embedded_sell_tax(event, tax_index)
            sell_proceeds = amount if amount > 0 else (quantity * price)
            sell_proceeds -= fee
            sell_proceeds -= embedded_tax

            realized = sell_proceeds - (avg_cost_before_sell * quantity)

            pos["realized_pnl"] += realized
            pos["quantity"] -= quantity
            pos["cost_basis"] -= avg_cost_before_sell * quantity

            if abs(pos["quantity"]) <= 1e-12:
                pos["quantity"] = 0.0
            if abs(pos["cost_basis"]) <= 1e-9:
                pos["cost_basis"] = 0.0

            if pos["cost_basis"] < 0:
                anomalies.append({
                    "ticker": ticker,
                    "date": event.get("date"),
                    "reason": "negative_cost_basis_after_sell",
                    "cost_basis": pos["cost_basis"],
                })
                pos["cost_basis"] = 0.0

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
            "currency": pos["currency"] or "UNKNOWN",
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
        "anomalies": anomalies,
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

                if not copied.get("currency") and mapping.get("currency"):
                    copied["currency"] = mapping.get("currency")
            else:
                copied["mapping_status"] = "unmapped"

                inferred_currency = _infer_currency_from_ticker_name(raw_name)
                if not copied.get("currency") and inferred_currency:
                    copied["currency"] = inferred_currency
        else:
            copied["mapping_status"] = "not_applicable"

        enriched.append(copied)

    return enriched

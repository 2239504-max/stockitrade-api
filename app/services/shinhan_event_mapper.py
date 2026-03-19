from typing import Any

from app.schemas.events import NormalizedEvent


def classify_trade_name(raw_trade_name: str) -> str:
    name = raw_trade_name.strip()

    exact_map = {
        "이체입금": "CASH_IN",
        "대체입금": "CASH_IN",
        "외화매수": "FX_BUY",
        "외화매도": "FX_SELL",
        "매수": "BUY",
        "매도": "SELL",
        "타사입고": "TRANSFER_IN_KIND",
        "시간외환전정산차금입금": "FX_PNL_ADJUST",
    }
    if name in exact_map:
        return exact_map[name]

    if "주식매수" in name:
        return "BUY"
    if "주식매도" in name:
        return "SELL"
    if "배당" in name:
        return "DIVIDEND"
    if "세금" in name:
        return "TAX"

    return "UNKNOWN"


def map_shinhan_row_to_event(row_number: int, row: dict[str, Any]) -> NormalizedEvent:
    raw_trade_name = str(row.get("trade_name") or "").strip()
    event_type = classify_trade_name(raw_trade_name)

    date = str(row.get("date") or "").strip()
    ticker = None
    ticker_name = _none_if_blank(row.get("ticker_name"))
    quantity = _to_float_or_none(row.get("quantity"))
    price = _to_float_or_none(row.get("price"))
    fee = _to_float_or_zero(row.get("fee"))
    tax = _to_float_or_zero(row.get("tax"))
    currency = _none_if_blank(row.get("currency"))
    account = _none_if_blank(row.get("account"))
    memo = _none_if_blank(row.get("memo"))

    settlement_amount = _to_float_or_none(row.get("settlement_amount"))
    amount = _to_float_or_none(row.get("amount"))

    if settlement_amount is not None:
        final_amount = settlement_amount
    elif amount is not None:
        final_amount = amount
    elif quantity is not None and price is not None:
        final_amount = quantity * price
    else:
        final_amount = None

    return NormalizedEvent(
        event_type=event_type,
        date=date,
        ticker=ticker,
        ticker_name=ticker_name,
        quantity=quantity,
        price=price,
        amount=final_amount,
        fee=fee,
        tax=tax,
        currency=currency,
        account=account,
        memo=memo,
        raw_trade_name=raw_trade_name or None,
        source_row_number=row_number,
    )


def _to_float_or_none(value):
    if value in (None, ""):
        return None
    return float(value)


def _to_float_or_zero(value):
    if value in (None, ""):
        return 0.0
    return float(value)


def _none_if_blank(value):
    if value in (None, ""):
        return None
    return str(value).strip()
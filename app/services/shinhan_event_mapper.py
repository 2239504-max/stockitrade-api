from typing import Any

from app.schemas.events import NormalizedEvent


TRADE_NAME_MAP = {
    "해외주식매수": "BUY",
    "해외주식매도": "SELL",
    "배당금입금": "DIVIDEND",
    "세금출금": "TAX",
    "외화매수": "FX_BUY",
    "외화매도": "FX_SELL",
    "시간외환전정산차금입금": "FX_PNL_ADJUST",
    "타사입고": "TRANSFER_IN_KIND",
}


def classify_trade_name(raw_trade_name: str) -> str:
    name = raw_trade_name.strip()

    exact_map = {
        "이체입금": "CASH_IN",
        "대체입금": "CASH_IN",
        "외화매수": "FX_BUY",
        "외화매도": "FX_SELL",
        "매수": "BUY",
        "매도": "SELL",
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
    event_type = classify_trade_name(raw_trade_name)

    date = str(row.get("date") or "").strip()
    ticker = _none_if_blank(row.get("ticker"))
    quantity = _to_float_or_none(row.get("quantity"))
    price = _to_float_or_none(row.get("price"))
    fee = _to_float_or_zero(row.get("fee"))
    tax = _to_float_or_zero(row.get("tax"))
    currency = _none_if_blank(row.get("currency"))
    account = _none_if_blank(row.get("account"))
    memo = _none_if_blank(row.get("memo"))

    amount = None
    if quantity is not None and price is not None:
        amount = quantity * price

    return NormalizedEvent(
        event_type=event_type,
        date=date,
        ticker=ticker,
        quantity=quantity,
        price=price,
        amount=amount,
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

from typing import Any

from app.schemas.events import NormalizedEvent

KNOWN_CURRENCY_CODES = {
    "KRW", "USD", "JPY", "EUR", "HKD", "CNY", "CNH", "GBP", "AUD", "CAD", "SGD", "CHF", "NZD"
}


def classify_trade_name(raw_trade_name: str) -> str:
    name = raw_trade_name.strip()

    exact_map = {
        "이체입금": "CASH_IN",
        "대체입금": "CASH_IN",
        "이용료입금": "CASH_IN",
        "외화이체입금": "CASH_IN",

        "이체출금": "CASH_OUT",
        "대체출금": "CASH_OUT",

        "외화매수": "FX_BUY",
        "외화매도": "FX_SELL",
        "외화매수(목표환율)": "FX_BUY",
        "시간외외화매도(통합증거금)": "FX_SELL",

        "매수": "BUY",
        "매도": "SELL",
        "타사입고": "TRANSFER_IN_KIND",
        "시간외환전정산차금입금": "FX_PNL_ADJUST",
        "배당금입금": "DIVIDEND",
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
    if "외화매수" in name:
        return "FX_BUY"
    if "외화매도" in name:
        return "FX_SELL"
    if "입금" in name:
        return "CASH_IN"
    if "출금" in name:
        return "CASH_OUT"

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
    currency = _normalize_currency_code(row.get("currency"))
    account = _none_if_blank(row.get("account"))
    memo = _none_if_blank(row.get("memo"))
    trade_no = _normalize_trade_no(row.get("trade_no"))

    if currency is None:
        currency = _infer_currency_from_ticker_name(ticker_name)

    settlement_amount = _to_float_or_none(row.get("settlement_amount"))
    amount = _to_float_or_none(row.get("amount"))

    if settlement_amount not in (None, 0):
        final_amount = settlement_amount
    elif amount not in (None, 0):
        final_amount = amount
    elif quantity is not None and price is not None:
        final_amount = quantity * price
    else:
        final_amount = None

    if event_type in {"DIVIDEND", "CASH_IN", "CASH_OUT", "TAX", "FX_PNL_ADJUST"}:
        if final_amount is None and quantity is not None:
            final_amount = quantity
        quantity = None
        if price is None:
            price = 0.0

    if event_type in {"BUY", "SELL", "TRANSFER_IN_KIND"}:
        if (final_amount in (None, 0)) and quantity is not None and price is not None:
            final_amount = quantity * price

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
        trade_no=trade_no,
        source_row_number=row_number,
    )


def _normalize_number(value: Any) -> str | None:
    if value in (None, ""):
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(",", "")
    text = text.replace(" ", "")
    text = text.replace("\u00a0", "")

    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]

    return text


def _to_float_or_none(value: Any):
    normalized = _normalize_number(value)
    if normalized is None:
        return None
    return float(normalized)


def _to_float_or_zero(value: Any):
    normalized = _normalize_number(value)
    if normalized is None:
        return 0.0
    return float(normalized)


def _none_if_blank(value: Any):
    if value in (None, ""):
        return None
    return str(value).strip()


def _normalize_currency_code(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip().upper()
    if text in KNOWN_CURRENCY_CODES:
        return text
    return None


def _infer_currency_from_ticker_name(value: Any) -> str | None:
    if value in (None, ""):
        return None

    text = str(value).strip().upper()
    for code in KNOWN_CURRENCY_CODES:
        if text == code or text.startswith(f"{code} "):
            return code
    return None


def _normalize_trade_no(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None

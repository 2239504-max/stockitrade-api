from typing import Any

from app.schemas.events import NormalizedEvent

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
    if currency is None:
        currency = _infer_currency_from_ticker_name(ticker_name)

    account = _none_if_blank(row.get("account"))
    memo = _none_if_blank(row.get("memo"))
    trade_no = _none_if_blank(row.get("trade_no"))

    settlement_amount = _to_float_or_none(row.get("settlement_amount"))
    amount = _to_float_or_none(row.get("amount"))

    fx_settlement_amount = _to_float_or_none(row.get("fx_settlement_amount"))
    fx_trade_amount = _to_float_or_none(row.get("fx_trade_amount"))
    fx_cash_balance = _to_float_or_none(row.get("fx_cash_balance"))

    # 기본값
    final_quantity = quantity
    final_price = price
    final_amount = None

    # 1) 증권 거래 / 현물 입고
    if event_type in {"BUY", "SELL", "TRANSFER_IN_KIND"}:
        final_amount = _pick_security_trade_amount(
            settlement_amount=settlement_amount,
            amount=amount,
            quantity=quantity,
            price=price,
        )

    # 2) 일반 현금성 이벤트
    elif event_type in {"CASH_IN", "CASH_OUT", "DIVIDEND", "TAX", "FX_PNL_ADJUST"}:
        final_amount = _pick_cash_like_amount(
            raw_trade_name=raw_trade_name,
            currency=currency,
            settlement_amount=settlement_amount,
            amount=amount,
            quantity=quantity,
            price=price,
            fx_settlement_amount=fx_settlement_amount,
            fx_trade_amount=fx_trade_amount,
            fx_cash_balance=fx_cash_balance,
        )

        final_quantity = None
        if final_price is None:
            final_price = 0.0

    # 3) 환전 이벤트
    elif event_type in {"FX_BUY", "FX_SELL"}:
        foreign_quantity = _pick_fx_foreign_amount(
            currency=currency,
            quantity=quantity,
            price=price,
            amount=amount,
            fx_settlement_amount=fx_settlement_amount,
            fx_trade_amount=fx_trade_amount,
            fx_cash_balance=fx_cash_balance,
        )

        krw_amount = _pick_fx_krw_amount(
            settlement_amount=settlement_amount,
            amount=amount,
            foreign_quantity=foreign_quantity,
            price=price,
        )

        final_quantity = foreign_quantity
        final_amount = krw_amount

    # 4) fallback
    else:
        final_amount = _pick_security_trade_amount(
            settlement_amount=settlement_amount,
            amount=amount,
            quantity=quantity,
            price=price,
        )

    return NormalizedEvent(
        event_type=event_type,
        date=date,
        ticker=ticker,
        ticker_name=ticker_name,
        quantity=final_quantity,
        price=final_price,
        amount=final_amount,
        fee=fee,
        tax=tax,
        currency=currency,
        account=account,
        memo=memo,
        raw_trade_name=raw_trade_name or None,
        trade_no=trade_no,  # schema에 없으면 이 줄만 삭제
        source_row_number=row_number,
    )


def _pick_security_trade_amount(
    settlement_amount: float | None,
    amount: float | None,
    quantity: float | None,
    price: float | None,
) -> float | None:
    if settlement_amount not in (None, 0):
        return settlement_amount
    if amount not in (None, 0):
        return amount
    if quantity is not None and price is not None:
        return quantity * price
    return None


def _pick_cash_like_amount(
    raw_trade_name: str,
    currency: str | None,
    settlement_amount: float | None,
    amount: float | None,
    quantity: float | None,
    price: float | None,
    fx_settlement_amount: float | None,
    fx_trade_amount: float | None,
    fx_cash_balance: float | None,
) -> float | None:
    # 외화 힌트가 있는 현금성 이벤트는 "해당 통화 금액"이 우선
    has_foreign_hint = (
        (currency is not None and currency != "KRW")
        or ("외화" in raw_trade_name)
        or (fx_settlement_amount not in (None, 0))
        or (fx_trade_amount not in (None, 0))
    )

    if has_foreign_hint:
        for candidate in (
            fx_settlement_amount,
            fx_trade_amount,
            quantity,
            amount,
        ):
            if candidate not in (None, 0):
                return candidate

        # 정말 아무것도 없으면 마지막으로 원화환산 역산
        if settlement_amount not in (None, 0) and price not in (None, 0):
            return settlement_amount / price

        return None

    # 일반 원화 현금 이벤트
    for candidate in (
        settlement_amount,
        amount,
        quantity,
    ):
        if candidate not in (None, 0):
            return candidate

    return None


def _pick_fx_foreign_amount(
    currency: str | None,
    quantity: float | None,
    price: float | None,
    amount: float | None,
    fx_settlement_amount: float | None,
    fx_trade_amount: float | None,
    fx_cash_balance: float | None,
) -> float | None:
    # 환전 이벤트에서 quantity는 외화수량이어야 함
    for candidate in (
        fx_settlement_amount,
        fx_trade_amount,
        quantity,
    ):
        if candidate not in (None, 0):
            return candidate

    # amount가 KRW이고 환율이 있으면 역산
    if amount not in (None, 0) and price not in (None, 0) and currency not in (None, "KRW"):
        return amount / price

    return None


def _pick_fx_krw_amount(
    settlement_amount: float | None,
    amount: float | None,
    foreign_quantity: float | None,
    price: float | None,
) -> float | None:
    for candidate in (
        settlement_amount,
        amount,
    ):
        if candidate not in (None, 0):
            return candidate

    if foreign_quantity not in (None, 0) and price not in (None, 0):
        return foreign_quantity * price

    return None


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
    text = str(value).strip()
    return text or None


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

from typing import Any

from app.schemas.events import NormalizedEvent


def classify_trade_name(raw_trade_name: str) -> str:
    name = raw_trade_name.strip()

    exact_map = {
        "이체입금": "CASH_IN",
        "대체입금": "CASH_IN",
        "이용료입금": "CASH_IN",  # 일단 입금성 이벤트로 처리
        "외화매수": "FX_BUY",
        "외화매도": "FX_SELL",
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

    # 기본 금액 우선순위:
    # 1) 정산금액
    # 2) 거래금액
    # 3) 수량*단가
    if settlement_amount is not None:
        final_amount = settlement_amount
    elif amount is not None:
        final_amount = amount
    elif quantity is not None and price is not None:
        final_amount = quantity * price
    else:
        final_amount = None

    # 이벤트별 보정
    # 배당/현금입출금/세금 계열은 quantity/price보다 실제 금액 칼럼이 중요하다.
    if event_type in {"DIVIDEND", "CASH_IN", "CASH_OUT", "TAX", "FX_PNL_ADJUST"}:
        if final_amount is None:
            # 거래금액/정산금액 둘 다 없으면 quantity 쪽 숫자를 금액처럼 쓰는 fallback
            if quantity is not None:
                final_amount = quantity
        # 이런 이벤트는 quantity를 포지션 수량으로 쓰지 않는 편이 안전
        quantity = None
        if price is None:
            price = 0.0

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


def _normalize_number(value: Any) -> str | None:
    if value in (None, ""):
        return None

    text = str(value).strip()
    if not text:
        return None

    # 흔한 표시 제거
    text = text.replace(",", "")
    text = text.replace(" ", "")
    text = text.replace("\u00a0", "")  # non-breaking space

    # 괄호 음수 처리: (1234.5) -> -1234.5
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

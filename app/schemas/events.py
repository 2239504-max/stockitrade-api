from typing import Literal, Optional
from pydantic import BaseModel, Field


EventType = Literal[
    "BUY",
    "SELL",
    "DIVIDEND",
    "TAX",
    "CASH_IN",
    "CASH_OUT",
    "FX_BUY",
    "FX_SELL",
    "FX_PNL_ADJUST",
    "TRANSFER_IN_KIND",
    "UNKNOWN",
]


class RawShinhanRow(BaseModel):
    row_number: int
    raw_data: dict
    normalized_data: dict


class NormalizedEvent(BaseModel):
    event_type: EventType
    date: str
    ticker: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    fee: float = 0.0
    tax: float = 0.0
    currency: Optional[str] = None
    account: Optional[str] = None
    memo: Optional[str] = None
    raw_trade_name: Optional[str] = None
    source_broker: str = "shinhan"
    source_row_number: int

from typing import Literal, Optional, Any
from pydantic import BaseModel


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
    ticker_name: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    fee: float = 0.0
    tax: float = 0.0
    currency: Optional[str] = None
    account: Optional[str] = None
    memo: Optional[str] = None
    raw_trade_name: Optional[str] = None
    trade_no: Optional[str] = None
    source_broker: str = "shinhan"
    source_row_number: int


class EventRecord(BaseModel):
    id: int
    date: str
    event_type: str
    ticker: Optional[str] = None
    ticker_name: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    fee: float
    tax: float
    currency: Optional[str] = None
    account: Optional[str] = None
    memo: Optional[str] = None
    raw_trade_name: Optional[str] = None
    trade_no: Optional[str] = None
    source_broker: Optional[str] = None
    source_row_number: Optional[int] = None
    market: Optional[str] = None
    asset_type: Optional[str] = None
    mapping_status: Optional[str] = None
    file_hash: Optional[str] = None
    created_at: Optional[str] = None


class EventListResponse(BaseModel):
    count: int
    limit: int
    offset: int
    applied_filters: dict[str, Any]
    events: list[EventRecord]


class EventCountResponse(BaseModel):
    count: int


class DeleteAllEventsResponse(BaseModel):
    message: str
    deleted_count: int

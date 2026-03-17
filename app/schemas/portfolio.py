from typing import Literal, Optional
from pydantic import BaseModel, Field


class ManualTradeRequest(BaseModel):
    date: str
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    fee: float = Field(default=0, ge=0)
    account: Optional[str] = None
    memo: Optional[str] = None
    market: Optional[str] = None
    currency: Optional[str] = None
    asset_type: Optional[str] = None


class PositionSummary(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    market: Optional[str] = None
    currency: Optional[str] = None


class PortfolioSummaryResponse(BaseModel):
    total_trades: int
    total_positions: int
    cash: float
    market_value: float
    total_value: float
    realized_pnl: float
    unrealized_pnl: float
    positions: list[PositionSummary]

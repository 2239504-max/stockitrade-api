from typing import Literal, Optional, Any
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


class UploadShinhanResponse(BaseModel):
    message: str
    filename: str
    saved_path: str
    file_hash: str
    force_replace: bool
    deleted_existing_count: int
    parsed_count: int
    inserted_count: int
    mapped_count: int
    unmapped_name_count: int
    error_count: int
    errors: list[dict[str, Any]]
    unknown_trade_names: dict[str, int]
    unmapped_name_priorities: list[dict[str, Any]]
    parsed_preview_head: list[dict[str, Any]]
    parsed_preview_tail: list[dict[str, Any]]


class PortfolioPosition(BaseModel):
    ticker: str
    ticker_name: Optional[str] = None
    quantity: float
    avg_cost: float
    cost_basis: float
    market: Optional[str] = None
    asset_type: Optional[str] = None
    currency: Optional[str] = None
    realized_pnl: float
    last_event_date: Optional[str] = None


class PortfolioCashBucket(BaseModel):
    currency: str
    net_cash: float
    cash_in: float
    cash_out: float
    buy_out: float
    sell_in: float
    dividend_in: float
    tax_out: float
    fx_buy_out: float
    fx_buy_in: float
    fx_sell_out: float
    fx_sell_in: float
    fx_pnl_adjust: float


class PortfolioAdjustmentApplied(BaseModel):
    ticker: Optional[str] = None
    date: Optional[str] = None
    reason: str
    event_quantity: Optional[float] = None
    covered_qty: Optional[float] = None
    source_row_number: Optional[int] = None


class PortfolioAnomaly(BaseModel):
    ticker: Optional[str] = None
    date: Optional[str] = None
    reason: str
    event_quantity: Optional[float] = None
    position_quantity: Optional[float] = None
    cost_basis: Optional[float] = None
    raw_trade_name: Optional[str] = None
    source_row_number: Optional[int] = None


class PortfolioHoldingsResponse(BaseModel):
    count: int
    holdings: list[PortfolioPosition]
    realized_pnl_by_currency: dict[str, float]
    anomalies: list[PortfolioAnomaly]
    adjustments_applied: list[PortfolioAdjustmentApplied]


class PortfolioCashResponse(BaseModel):
    count: int
    cash: list[PortfolioCashBucket]
    anomalies: list[PortfolioAnomaly]
    adjustments_applied: list[PortfolioAdjustmentApplied]


class PortfolioSummaryResponse(BaseModel):
    holdings_count: int
    cash_count: int
    positions: list[PortfolioPosition]
    cash: list[PortfolioCashBucket]
    realized_pnl_by_currency: dict[str, float]
    open_positions_realized_pnl_by_currency: dict[str, float]
    position_count_by_currency: dict[str, int]
    holding_cost_basis_by_currency: dict[str, float]
    anomalies: list[PortfolioAnomaly]
    adjustments_applied: list[PortfolioAdjustmentApplied]

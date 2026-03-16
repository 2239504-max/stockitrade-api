import uuid
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from app.services.parser_shinhan import parse_shinhan_xlsx
from app.services.trade_store import get_summary, init_db, insert_trade

router = APIRouter(prefix="", tags=["portfolio"])
init_db()

UPLOAD_DIR = Path("data/uploads")


class ManualTradeRequest(BaseModel):
    date: str
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    fee: Optional[float] = Field(default=0, ge=0)
    account: Optional[str] = None
    memo: Optional[str] = None


@router.post("/uploads/shinhan")
async def upload_shinhan(
    filename: str,
    file_bytes: bytes = Body(..., media_type="application/octet-stream"),
):
    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOAD_DIR / f"{uuid.uuid4()}_{Path(filename).name}"
    saved_path.write_bytes(file_bytes)

    parsed_trades, errors = parse_shinhan_xlsx(saved_path)

    created_ids = []
    for trade in parsed_trades:
        created_ids.append(insert_trade(trade))

    return {
        "message": "shinhan upload processed",
        "filename": filename,
        "saved_path": str(saved_path),
        "inserted_count": len(created_ids),
        "error_count": len(errors),
        "errors": errors,
    }


@router.post("/trades/manual")
def create_manual_trade(trade: ManualTradeRequest):
    trade_id = insert_trade(trade.model_dump())
    return {
        "message": "manual trade created",
        "trade_id": trade_id,
        "trade": trade.model_dump(),
    }


@router.get("/portfolio/summary")
def get_portfolio_summary():
    return {
        "message": "portfolio summary computed",
        "summary": get_summary(),
    }

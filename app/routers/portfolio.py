from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional


router = APIRouter(prefix="", tags=["portfolio"])


class ManualTradeRequest(BaseModel):
    date: str
    ticker: str
    side: str
    quantity: float
    price: float
    fee: Optional[float] = 0
    account: Optional[str] = None
    memo: Optional[str] = None


@router.post("/uploads/shinhan")
async def upload_shinhan(file: UploadFile = File(...)):
    filename = file.filename or ""

    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")

    return {
        "message": "upload endpoint created",
        "filename": filename,
        "next_step": "connect parser_shinhan.py"
    }


@router.post("/trades/manual")
def create_manual_trade(trade: ManualTradeRequest):
    return {
        "message": "manual trade endpoint created",
        "trade": trade.model_dump()
    }


@router.get("/portfolio/summary")
def get_portfolio_summary():
    return {
        "message": "portfolio summary endpoint created",
        "summary": {
            "total_positions": 0,
            "cash": 0,
            "market_value": 0
        }
    }
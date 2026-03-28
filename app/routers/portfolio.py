from fastapi import APIRouter, Body, HTTPException, Query

from app.schemas.portfolio import ManualTradeRequest
from app.services.portfolio_service import (
    ingest_shinhan_file,
    create_manual_trade,
    build_portfolio_holdings,
    build_portfolio_cash,
    build_portfolio_summary,
)

router = APIRouter(prefix="", tags=["portfolio"])


@router.post("/uploads/shinhan")
async def upload_shinhan(
    filename: str,
    force_replace: bool = Query(False, description="같은 파일 hash가 이미 있으면 기존 events 삭제 후 재적재"),
    file_bytes: bytes = Body(..., media_type="application/octet-stream"),
):
    try:
        return ingest_shinhan_file(
            filename=filename,
            file_bytes=file_bytes,
            force_replace=force_replace,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/trades/manual")
def post_manual_trade(trade: ManualTradeRequest):
    try:
        return create_manual_trade(trade.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/portfolio/summary")
def get_portfolio_summary():
    try:
        return build_portfolio_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/portfolio/cash")
def get_portfolio_cash():
    try:
        return build_portfolio_cash()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/portfolio/holdings")
def get_portfolio_holdings():
    try:
        return build_portfolio_holdings()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

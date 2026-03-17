from fastapi import APIRouter, HTTPException, Query

from app.providers.kis.market import get_quote

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/quote")
def read_quote(
    symbol: str = Query(...),
    market: str = Query("US"),
):
    try:
        return get_quote(symbol=symbol, market=market)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

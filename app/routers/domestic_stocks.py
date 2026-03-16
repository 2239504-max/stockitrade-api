from fastapi import APIRouter

router = APIRouter(prefix="/domestic/stocks", tags=["domestic-stocks"])

@router.get("/quotes/{symbol}")
def get_quote(symbol: str):
    return {
        "assetClass": "domestic_stock",
        "symbol": symbol,
        "name": "삼성전자" if symbol == "005930" else "UNKNOWN",
        "market": "KOSPI",
        "last": 71500,
        "change": 1200,
        "changePct": 1.71
    }

@router.get("/orderbook/{symbol}")
def get_orderbook(symbol: str):
    return {
        "assetClass": "domestic_stock",
        "symbol": symbol,
        "bidLevels": [
            {"price": 71500, "size": 38200},
            {"price": 71400, "size": 51700}
        ],
        "askLevels": [
            {"price": 71600, "size": 42100},
            {"price": 71700, "size": 48800}
        ]
    }

@router.get("/candles/daily")
def get_daily(symbol: str, count: int = 5):
    candles = [
        {"time": "2026-03-05", "open": 69800, "high": 70500, "low": 69400, "close": 70100, "volume": 12000321},
        {"time": "2026-03-06", "open": 70100, "high": 70900, "low": 69900, "close": 70600, "volume": 13422111},
        {"time": "2026-03-07", "open": 70600, "high": 71200, "low": 70300, "close": 70900, "volume": 14099231},
        {"time": "2026-03-10", "open": 70900, "high": 71600, "low": 70500, "close": 71300, "volume": 15111222},
        {"time": "2026-03-11", "open": 70400, "high": 71800, "low": 70100, "close": 71500, "volume": 15320432},
    ]
    return {
        "assetClass": "domestic_stock",
        "symbol": symbol,
        "timeframe": "1d",
        "candles": candles[-count:]
    }

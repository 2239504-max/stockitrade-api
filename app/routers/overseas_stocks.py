from fastapi import APIRouter

router = APIRouter(prefix="/overseas/stocks", tags=["overseas-stocks"])

@router.get("/quotes/{symbol}")
def get_quote(symbol: str):
    return {
        "assetClass": "overseas_stock",
        "symbol": symbol,
        "name": "Apple Inc." if symbol.upper() == "AAPL" else "UNKNOWN",
        "market": "NASDAQ",
        "last": 212.34,
        "change": 1.82,
        "changePct": 0.86
    }

@router.get("/orderbook/{symbol}")
def get_orderbook(symbol: str):
    return {
        "assetClass": "overseas_stock",
        "symbol": symbol,
        "bidLevels": [
            {"price": 212.30, "size": 400},
            {"price": 212.29, "size": 550}
        ],
        "askLevels": [
            {"price": 212.35, "size": 420},
            {"price": 212.36, "size": 610}
        ]
    }

@router.get("/candles/daily")
def get_daily(symbol: str, count: int = 5):
    candles = [
        {"time": "2026-03-05", "open": 208.2, "high": 210.1, "low": 207.9, "close": 209.4, "volume": 54200000},
        {"time": "2026-03-06", "open": 209.5, "high": 211.2, "low": 208.7, "close": 210.8, "volume": 49800000},
        {"time": "2026-03-07", "open": 210.7, "high": 212.0, "low": 209.8, "close": 211.4, "volume": 47300000},
        {"time": "2026-03-10", "open": 211.0, "high": 213.0, "low": 210.6, "close": 211.9, "volume": 52100000},
        {"time": "2026-03-11", "open": 211.7, "high": 213.2, "low": 211.2, "close": 212.34, "volume": 53400000},
    ]
    return {
        "assetClass": "overseas_stock",
        "symbol": symbol.upper(),
        "timeframe": "1d",
        "candles": candles[-count:]
    }

from fastapi import APIRouter

router = APIRouter(prefix="/overseas/derivatives", tags=["overseas-derivatives"])

@router.get("/quotes/{symbol}")
def get_quote(symbol: str):
    return {
        "assetClass": "overseas_derivative",
        "symbol": symbol.upper(),
        "name": "Nasdaq Futures",
        "market": "CME",
        "last": 18452.25,
        "change": 36.75,
        "changePct": 0.20
    }

@router.get("/orderbook/{symbol}")
def get_orderbook(symbol: str):
    return {
        "assetClass": "overseas_derivative",
        "symbol": symbol.upper(),
        "bidLevels": [
            {"price": 18452.00, "size": 35},
            {"price": 18451.75, "size": 28}
        ],
        "askLevels": [
            {"price": 18452.25, "size": 31},
            {"price": 18452.50, "size": 27}
        ]
    }

@router.get("/candles/daily")
def get_daily(symbol: str, count: int = 5):
    candles = [
        {"time": "2026-03-05", "open": 18320.0, "high": 18410.0, "low": 18280.0, "close": 18388.5, "volume": 98000},
        {"time": "2026-03-06", "open": 18390.0, "high": 18435.0, "low": 18310.0, "close": 18402.0, "volume": 102000},
        {"time": "2026-03-07", "open": 18400.5, "high": 18480.0, "low": 18370.0, "close": 18430.5, "volume": 105000},
        {"time": "2026-03-10", "open": 18428.0, "high": 18470.0, "low": 18395.0, "close": 18415.5, "volume": 99000},
        {"time": "2026-03-11", "open": 18410.0, "high": 18465.0, "low": 18388.0, "close": 18452.25, "volume": 101500},
    ]
    return {
        "assetClass": "overseas_derivative",
        "symbol": symbol.upper(),
        "timeframe": "1d",
        "candles": candles[-count:]
    }

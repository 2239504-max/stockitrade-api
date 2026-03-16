from fastapi import APIRouter

router = APIRouter(prefix="/domestic/derivatives", tags=["domestic-derivatives"])

@router.get("/quotes/{symbol}")
def get_quote(symbol: str):
    return {
        "assetClass": "domestic_derivative",
        "symbol": symbol,
        "name": "KOSPI200 Futures",
        "market": "KRX",
        "last": 362.45,
        "change": -1.15,
        "changePct": -0.32
    }

@router.get("/orderbook/{symbol}")
def get_orderbook(symbol: str):
    return {
        "assetClass": "domestic_derivative",
        "symbol": symbol,
        "bidLevels": [
            {"price": 362.40, "size": 128},
            {"price": 362.35, "size": 144}
        ],
        "askLevels": [
            {"price": 362.45, "size": 131},
            {"price": 362.50, "size": 152}
        ]
    }

@router.get("/candles/daily")
def get_daily(symbol: str, count: int = 5):
    candles = [
        {"time": "2026-03-05", "open": 365.2, "high": 366.0, "low": 363.8, "close": 364.1, "volume": 210000},
        {"time": "2026-03-06", "open": 364.0, "high": 365.1, "low": 362.9, "close": 363.4, "volume": 240000},
        {"time": "2026-03-07", "open": 363.6, "high": 364.7, "low": 362.5, "close": 363.0, "volume": 228000},
        {"time": "2026-03-10", "open": 362.9, "high": 363.5, "low": 361.8, "close": 362.8, "volume": 250000},
        {"time": "2026-03-11", "open": 362.7, "high": 363.2, "low": 361.9, "close": 362.45, "volume": 245000},
    ]
    return {
        "assetClass": "domestic_derivative",
        "symbol": symbol,
        "timeframe": "1d",
        "candles": candles[-count:]
    }

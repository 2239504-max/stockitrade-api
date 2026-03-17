import httpx

from app.core.config import settings
from app.providers.kis.auth import get_access_token


def get_quote(symbol: str, market: str = "US") -> dict:
    if not settings.kis_base_url:
        return {
            "symbol": symbol,
            "market": market,
            "price": 0.0,
            "currency": "USD" if market.upper() == "US" else "KRW",
            "source": "kis-mock",
        }

    token = get_access_token()

    # 여기 endpoint/path/header/query는 실제 KIS 사양에 맞게 교체 필요
    url = f"{settings.kis_base_url}/uapi/mock/quote"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": settings.kis_app_key,
        "appsecret": settings.kis_app_secret,
    }
    params = {
        "symbol": symbol,
        "market": market,
    }

    response = httpx.get(url, headers=headers, params=params, timeout=10.0)
    response.raise_for_status()
    data = response.json()

    price = float(data.get("price", 0))
    currency = data.get("currency", "USD" if market.upper() == "US" else "KRW")

    return {
        "symbol": symbol,
        "market": market,
        "price": price,
        "currency": currency,
        "source": "kis",
    }

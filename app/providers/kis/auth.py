import httpx

from app.core.config import settings


def get_access_token() -> str:
    if not settings.kis_app_key or not settings.kis_app_secret or not settings.kis_base_url:
        raise ValueError("KIS credentials or base url are not configured")

    url = f"{settings.kis_base_url}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": settings.kis_app_key,
        "appsecret": settings.kis_app_secret,
    }

    response = httpx.post(url, json=payload, timeout=10.0)
    response.raise_for_status()

    data = response.json()
    token = data.get("access_token")
    if not token:
        raise ValueError("No access_token in KIS response")

    return token

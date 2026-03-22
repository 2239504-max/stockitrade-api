from app.services.trade_store import upsert_name_mapping


COMMON_NAME_MAPPINGS = [
    {
        "raw_name": "USD 애플",
        "normalized_name": "애플",
        "ticker": "AAPL",
        "canonical_name": "Apple Inc.",
        "exchange": "NASDAQ",
        "market": "US",
        "asset_type": "stock",
        "currency": "USD",
    },
    {
        "raw_name": "USD 유나이티드헬스 그룹",
        "normalized_name": "유나이티드헬스 그룹",
        "ticker": "UNH",
        "canonical_name": "UnitedHealth Group Inc.",
        "exchange": "NYSE",
        "market": "US",
        "asset_type": "stock",
        "currency": "USD",
    },
    {
        "raw_name": "USD Direxion 미국 반도체 3X ETF",
        "normalized_name": "Direxion 미국 반도체 3X ETF",
        "ticker": "SOXL",
        "canonical_name": "Direxion Daily Semiconductor Bull 3X Shares",
        "exchange": "NYSEARCA",
        "market": "US",
        "asset_type": "etf",
        "currency": "USD",
    },
    {
        "raw_name": "USD 이더리움 2X ETF",
        "normalized_name": "이더리움 2X ETF",
        "ticker": "ETHU",
        "canonical_name": "2x Ether ETF",
        "exchange": "NYSEARCA",
        "market": "US",
        "asset_type": "etf",
        "currency": "USD",
    },
]


def seed_name_mappings() -> None:
    for item in COMMON_NAME_MAPPINGS:
        upsert_name_mapping(
            raw_name=item["raw_name"],
            normalized_name=item["normalized_name"],
            ticker=item["ticker"],
            canonical_name=item.get("canonical_name"),
            exchange=item.get("exchange"),
            market=item.get("market"),
            asset_type=item.get("asset_type"),
            currency=item.get("currency"),
            source="seed",
            confidence=1.0,
            mapping_status="confirmed",
        )
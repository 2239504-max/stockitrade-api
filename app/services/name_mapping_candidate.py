from app.services.trade_store import upsert_unmapped_name


def save_candidate_mapping(
    raw_name: str,
    normalized_name: str,
    candidate_ticker: str,
    reason: str,
):
    upsert_unmapped_name(
        raw_name=raw_name,
        normalized_name=normalized_name,
        latest_source_broker="shinhan",
        latest_currency="USD",
        latest_market_hint="US",
    )

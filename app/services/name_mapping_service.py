from typing import Any

from app.services.name_normalizer import normalize_security_name
from app.services.trade_store import (
    find_name_mapping_by_raw_name,
    find_name_mapping_by_normalized_name,
    upsert_unmapped_name,
)


def resolve_name(
    raw_name: str,
    source_broker: str | None = None,
    currency: str | None = None,
    market_hint: str | None = None,
) -> dict[str, Any] | None:
    normalized_name = normalize_security_name(raw_name)

    direct = find_name_mapping_by_raw_name(raw_name)
    if direct:
        return direct

    normalized_matches = find_name_mapping_by_normalized_name(normalized_name)
    if len(normalized_matches) == 1:
        return normalized_matches[0]

    upsert_unmapped_name(
        raw_name=raw_name,
        normalized_name=normalized_name,
        latest_source_broker=source_broker,
        latest_currency=currency,
        latest_market_hint=market_hint,
    )
    return None

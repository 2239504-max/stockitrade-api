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


def calculate_unmapped_name_priorities(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    freq: dict[str, dict[str, Any]] = {}

    for e in events:
        name = e.get("ticker_name")
        if not name:
            continue
        if e.get("ticker"):
            continue
        if name in {"USD", "KRW", "JPY", "EUR"}:
            continue

        if name not in freq:
            freq[name] = {
                "ticker_name": name,
                "count": 0,
                "event_types": set(),
                "currencies": set(),
                "priority_score": 0,
            }

        freq[name]["count"] += 1

        event_type = e.get("event_type")
        if event_type:
            freq[name]["event_types"].add(event_type)

            if event_type in {"BUY", "SELL", "TRANSFER_IN_KIND"}:
                freq[name]["priority_score"] += 3
            elif event_type in {"FX_BUY", "FX_SELL"}:
                freq[name]["priority_score"] += 1

        currency = e.get("currency")
        if currency:
            freq[name]["currencies"].add(currency)

    result: list[dict[str, Any]] = []
    for item in freq.values():
        result.append({
            "ticker_name": item["ticker_name"],
            "count": item["count"],
            "event_types": sorted(item["event_types"]),
            "currencies": sorted(item["currencies"]),
            "priority_score": item["priority_score"],
        })

    result.sort(key=lambda x: (-x["priority_score"], -x["count"], x["ticker_name"]))
    return result

from fastapi import APIRouter, HTTPException, Query

from app.schemas.events import (
    EventListResponse,
    EventCountResponse,
    DeleteAllEventsResponse,
)
from app.services.event_store import (
    list_normalized_events,
    count_normalized_events,
    delete_all_events,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
def get_events(
    limit: int = Query(50, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    ticker: str | None = Query(None),
    event_type: str | None = Query(None),
    currency: str | None = Query(None),
    raw_trade_name: str | None = Query(None),
    file_hash: str | None = Query(None),
):
    try:
        events = list_normalized_events(
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
            ticker=ticker,
            event_type=event_type,
            currency=currency,
            raw_trade_name=raw_trade_name,
            file_hash=file_hash,
        )
        return {
            "count": len(events),
            "limit": limit,
            "offset": offset,
            "applied_filters": {
                "date_from": date_from,
                "date_to": date_to,
                "ticker": ticker,
                "event_type": event_type,
                "currency": currency,
                "raw_trade_name": raw_trade_name,
                "file_hash": file_hash,
            },
            "events": events,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/count", response_model=EventCountResponse)
def get_events_count(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    ticker: str | None = Query(None),
    event_type: str | None = Query(None),
    currency: str | None = Query(None),
    raw_trade_name: str | None = Query(None),
    file_hash: str | None = Query(None),
):
    try:
        total = count_normalized_events(
            date_from=date_from,
            date_to=date_to,
            ticker=ticker,
            event_type=event_type,
            currency=currency,
            raw_trade_name=raw_trade_name,
            file_hash=file_hash,
        )
        return {
            "count": total,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/all", response_model=DeleteAllEventsResponse)
def purge_all_events():
    try:
        deleted = delete_all_events()
        return {
            "message": "all normalized events deleted",
            "deleted_count": deleted,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

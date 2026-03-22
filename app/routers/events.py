from fastapi import APIRouter, HTTPException, Query

from app.services.event_store import (
    list_normalized_events,
    count_normalized_events,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def get_events(limit: int = Query(50, ge=1, le=1000)):
    try:
        events = list_normalized_events(limit=limit)
        return {
            "count": len(events),
            "limit": limit,
            "events": events,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/count")
def get_events_count():
    try:
        total = count_normalized_events()
        return {
            "count": total,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

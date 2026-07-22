from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.detection import analyze_event
from app.repositories import (
    get_event,
    import_events,
    list_events,
    list_incidents,
)
from app.schemas import (
    CloudTrailEnvelopeIn,
    DetectionResponse,
    EventImportResult,
    EventRead,
    HealthResponse,
    IncidentRead,
)
from app.rules import ROOT_LOGIN_WITHOUT_MFA_RULE_ID


router = APIRouter()


def get_session(request: Request):
    yield from request.app.state.database.session()


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request) -> HealthResponse:
    return HealthResponse(status="ok", environment=request.app.state.settings.app_env)


@router.post(
    "/api/v1/events/import",
    response_model=EventImportResult,
    status_code=status.HTTP_201_CREATED,
    tags=["events"],
)
def import_cloudtrail_events(
    payload: CloudTrailEnvelopeIn, session: SessionDependency
) -> EventImportResult:
    imported_ids, duplicate_count = import_events(session, payload.records)
    return EventImportResult(
        total=len(payload.records),
        imported=len(imported_ids),
        duplicates=duplicate_count,
        event_ids=imported_ids,
    )


@router.get("/api/v1/events", response_model=list[EventRead], tags=["events"])
def get_events(
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[EventRead]:
    return [
        EventRead.model_validate(item)
        for item in list_events(session, offset=offset, limit=limit)
    ]


@router.get("/api/v1/events/{event_id}", response_model=EventRead, tags=["events"])
def get_event_by_id(event_id: str, session: SessionDependency) -> EventRead:
    event = get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return EventRead.model_validate(event)


@router.post(
    "/api/v1/events/{event_id}/analyze",
    response_model=DetectionResponse,
    tags=["detection"],
)
def analyze_event_by_id(event_id: str, session: SessionDependency) -> DetectionResponse:
    event = get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    finding, incident = analyze_event(session, event)
    if finding is None:
        return DetectionResponse(
            event_id=event_id,
            matched=False,
            rule_id=ROOT_LOGIN_WITHOUT_MFA_RULE_ID,
        )

    return DetectionResponse(
        event_id=event_id,
        matched=True,
        rule_id=finding.rule_id,
        incident_id=incident.incident_id if incident else None,
        severity=finding.severity,
        evidence=finding.evidence,
    )


@router.get(
    "/api/v1/incidents", response_model=list[IncidentRead], tags=["incidents"]
)
def get_incidents(
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[IncidentRead]:
    return [
        IncidentRead.model_validate(item)
        for item in list_incidents(session, offset=offset, limit=limit)
    ]

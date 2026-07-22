from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.agent import (
    AgentConfigurationError,
    AgentStepLimitError,
    run_security_analyst,
)
from app.detection import analyze_event, analyze_event_all
from app.repositories import (
    create_approval_decision,
    create_audit_log,
    get_event,
    get_approval_decision,
    get_incident,
    import_events,
    list_events,
    list_incidents,
    list_audit_logs,
)
from app.schemas import (
    AgentAnalysisResponse,
    AgentAuditItem,
    ApprovalRequest,
    ApprovalResponse,
    CloudTrailEnvelopeIn,
    DetectionResponse,
    EventImportResult,
    EventRead,
    EventAnalysisResponse,
    HealthResponse,
    IncidentRead,
    IncidentReportResponse,
)
from app.rules import ROOT_LOGIN_WITHOUT_MFA_RULE_ID
from app.reporting import build_incident_report


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


@router.post(
    "/api/v1/events/{event_id}/analyze-all",
    response_model=EventAnalysisResponse,
    tags=["detection"],
)
def analyze_event_with_all_rules(
    event_id: str, session: SessionDependency
) -> EventAnalysisResponse:
    event = get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    results = analyze_event_all(session, event)
    findings = [
        DetectionResponse(
            event_id=event_id,
            matched=True,
            rule_id=finding.rule_id,
            incident_id=incident.incident_id,
            severity=finding.severity,
            evidence=finding.evidence,
        )
        for finding, incident in results
    ]
    return EventAnalysisResponse(
        event_id=event_id,
        matched_rules=len(findings),
        findings=findings,
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


@router.get(
    "/api/v1/incidents/{incident_id}/report",
    response_model=IncidentReportResponse,
    tags=["incidents"],
)
def get_incident_report(
    incident_id: str, session: SessionDependency
) -> IncidentReportResponse:
    incident = get_incident(session, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )
    event = get_event(session, incident.event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Incident event is missing",
        )
    return build_incident_report(incident, event)


@router.post(
    "/api/v1/incidents/{incident_id}/agent-analysis",
    response_model=AgentAnalysisResponse,
    tags=["agent"],
)
async def analyze_incident_with_agent(
    incident_id: str, request: Request, session: SessionDependency
) -> AgentAnalysisResponse:
    incident = get_incident(session, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )

    settings = request.app.state.settings
    try:
        analysis, audit = await run_security_analyst(
            session,
            incident=incident,
            model=settings.openai_model,
            max_steps=settings.max_agent_steps,
        )
    except AgentConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    except AgentStepLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI agent request failed",
        ) from error

    return AgentAnalysisResponse(
        incident_id=incident_id,
        model=settings.openai_model,
        analysis=analysis,
        audit=[AgentAuditItem.model_validate(item) for item in audit],
    )


@router.get(
    "/api/v1/incidents/{incident_id}/audit",
    response_model=list[AgentAuditItem],
    tags=["audit"],
)
def get_incident_audit(
    incident_id: str, session: SessionDependency
) -> list[AgentAuditItem]:
    if get_incident(session, incident_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )
    return [
        AgentAuditItem.model_validate(item)
        for item in list_audit_logs(session, incident_id)
    ]


@router.post(
    "/api/v1/incidents/{incident_id}/approval",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["approval"],
)
def decide_incident_approval(
    incident_id: str, payload: ApprovalRequest, session: SessionDependency
) -> ApprovalResponse:
    incident = get_incident(session, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )
    if get_approval_decision(session, incident_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident already has an approval decision",
        )

    approval = create_approval_decision(
        session,
        incident=incident,
        decision=payload.decision,
        decided_by=payload.decided_by,
        rationale=payload.rationale,
    )
    create_audit_log(
        session,
        incident_id=incident_id,
        action_type="human_approval",
        tool_name=None,
        request_payload=payload.model_dump(),
        response_payload={
            "approval_id": approval.approval_id,
            "incident_status": incident.status,
            "remediation_executed": False,
        },
        success=True,
    )
    return ApprovalResponse.model_validate(approval)

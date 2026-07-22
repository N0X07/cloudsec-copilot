from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Incident, SecurityEvent
from app.repositories import get_incident_for_rule
from app.rules import DetectionFinding, detect_root_login_without_mfa


def analyze_event(
    session: Session, event: SecurityEvent
) -> tuple[DetectionFinding | None, Incident | None]:
    finding = detect_root_login_without_mfa(event.raw_event)
    if finding is None:
        return None, None

    existing = get_incident_for_rule(
        session, event_id=event.event_id, rule_id=finding.rule_id
    )
    if existing is not None:
        return finding, existing

    incident = Incident(
        incident_id=f"inc-{finding.rule_id.lower()}-{event.event_id}",
        event_id=event.event_id,
        rule_id=finding.rule_id,
        title=finding.title,
        severity=finding.severity,
        evidence=finding.evidence,
        status="open",
        requires_human_approval=True,
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return finding, incident

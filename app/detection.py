from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Incident, SecurityEvent
from app.repositories import get_incident_for_rule
from app.rules import (
    DetectionFinding,
    detect_root_login_without_mfa,
    run_detection_rules,
)


def _persist_finding(
    session: Session, event: SecurityEvent, finding: DetectionFinding
) -> Incident:
    existing = get_incident_for_rule(
        session, event_id=event.event_id, rule_id=finding.rule_id
    )
    if existing is not None:
        return existing

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
    return incident


def analyze_event(
    session: Session, event: SecurityEvent
) -> tuple[DetectionFinding | None, Incident | None]:
    finding = detect_root_login_without_mfa(event.raw_event)
    if finding is None:
        return None, None

    return finding, _persist_finding(session, event, finding)


def analyze_event_all(
    session: Session, event: SecurityEvent
) -> list[tuple[DetectionFinding, Incident]]:
    return [
        (finding, _persist_finding(session, event, finding))
        for finding in run_detection_rules(event.raw_event)
    ]

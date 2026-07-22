from __future__ import annotations

from app.models import Incident, SecurityEvent
from app.rules import run_detection_rules
from app.schemas import IncidentReportResponse


def build_incident_report(
    incident: Incident, event: SecurityEvent
) -> IncidentReportResponse:
    finding = next(
        (
            item
            for item in run_detection_rules(event.raw_event)
            if item.rule_id == incident.rule_id
        ),
        None,
    )
    attack_techniques = finding.attack_techniques if finding else []
    recommended_actions = finding.recommended_actions if finding else [
        "Escalate to a cloud security analyst for manual investigation."
    ]
    actor = event.actor_arn or event.identity_type
    summary = (
        f"{incident.title} was detected at {event.event_time.isoformat()} "
        f"for actor {actor} from {event.source_ip or 'an unknown source address'}."
    )

    return IncidentReportResponse(
        incident_id=incident.incident_id,
        event_id=event.event_id,
        title=incident.title,
        severity=incident.severity,
        status=incident.status,
        summary=summary,
        observed_at=event.event_time,
        actor_arn=event.actor_arn,
        source_ip=event.source_ip,
        evidence=incident.evidence,
        attack_techniques=attack_techniques,
        recommended_actions=recommended_actions,
        requires_human_approval=incident.requires_human_approval,
        remediation_state=(
            "awaiting_human_approval"
            if incident.requires_human_approval
            else "analysis_only"
        ),
    )

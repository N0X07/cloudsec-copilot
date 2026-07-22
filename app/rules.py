from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ROOT_LOGIN_WITHOUT_MFA_RULE_ID = "AWS-IAM-001"


@dataclass(frozen=True, slots=True)
class DetectionFinding:
    rule_id: str
    title: str
    severity: str
    evidence: list[str]


def detect_root_login_without_mfa(
    raw_event: dict[str, Any],
) -> DetectionFinding | None:
    """Detect a successful AWS root console login where MFA was not used."""
    identity = raw_event.get("userIdentity") or {}
    response = raw_event.get("responseElements") or {}
    additional = raw_event.get("additionalEventData") or {}

    conditions = (
        identity.get("type") == "Root",
        raw_event.get("eventSource") == "signin.amazonaws.com",
        raw_event.get("eventName") == "ConsoleLogin",
        response.get("ConsoleLogin") == "Success",
        additional.get("MFAUsed") == "No",
    )
    if not all(conditions):
        return None

    return DetectionFinding(
        rule_id=ROOT_LOGIN_WITHOUT_MFA_RULE_ID,
        title="Successful root console login without MFA",
        severity="critical",
        evidence=[
            "userIdentity.type=Root",
            "eventSource=signin.amazonaws.com",
            "eventName=ConsoleLogin",
            "responseElements.ConsoleLogin=Success",
            "additionalEventData.MFAUsed=No",
        ],
    )

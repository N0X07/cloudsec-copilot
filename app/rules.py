from __future__ import annotations

from dataclasses import dataclass
import json
from collections.abc import Callable
from typing import Any
from urllib.parse import unquote


ROOT_LOGIN_WITHOUT_MFA_RULE_ID = "AWS-IAM-001"
CLOUDTRAIL_LOGGING_DISABLED_RULE_ID = "AWS-LOG-001"
PUBLIC_S3_POLICY_RULE_ID = "AWS-S3-001"
PUBLIC_MANAGEMENT_PORT_RULE_ID = "AWS-NET-001"
ADMIN_INLINE_POLICY_RULE_ID = "AWS-IAM-002"


@dataclass(frozen=True, slots=True)
class DetectionFinding:
    rule_id: str
    title: str
    severity: str
    evidence: list[str]
    attack_techniques: list[str]
    recommended_actions: list[str]


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
        attack_techniques=["T1078.004 Cloud Accounts"],
        recommended_actions=[
            "Validate the login with the account owner and security team.",
            "Rotate root credentials and enable root-account MFA if unauthorized.",
            "Review adjacent CloudTrail activity from the same source address.",
        ],
    )


def detect_cloudtrail_logging_disabled(
    raw_event: dict[str, Any],
) -> DetectionFinding | None:
    event_name = raw_event.get("eventName")
    if raw_event.get("eventSource") != "cloudtrail.amazonaws.com" or event_name not in {
        "StopLogging",
        "DeleteTrail",
    }:
        return None

    trail_name = (raw_event.get("requestParameters") or {}).get("name", "unknown")
    return DetectionFinding(
        rule_id=CLOUDTRAIL_LOGGING_DISABLED_RULE_ID,
        title="CloudTrail audit logging was disabled or deleted",
        severity="critical",
        evidence=[
            "eventSource=cloudtrail.amazonaws.com",
            f"eventName={event_name}",
            f"requestParameters.name={trail_name}",
        ],
        attack_techniques=["T1562.008 Disable or Modify Cloud Logs"],
        recommended_actions=[
            "Confirm whether the change was authorized.",
            "Restore the affected trail and validate log delivery.",
            "Review activity by the same identity before and after this event.",
        ],
    )


def _policy_document(raw_policy: Any) -> dict[str, Any] | None:
    if isinstance(raw_policy, dict):
        return raw_policy
    if not isinstance(raw_policy, str):
        return None
    try:
        parsed = json.loads(unquote(raw_policy))
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def detect_public_s3_bucket_policy(
    raw_event: dict[str, Any],
) -> DetectionFinding | None:
    if (
        raw_event.get("eventSource") != "s3.amazonaws.com"
        or raw_event.get("eventName") != "PutBucketPolicy"
    ):
        return None

    request = raw_event.get("requestParameters") or {}
    policy = _policy_document(request.get("bucketPolicy") or request.get("policy"))
    if policy is None:
        return None

    statements = _as_list(policy.get("Statement", []))
    for statement in statements:
        if not isinstance(statement, dict) or statement.get("Effect") != "Allow":
            continue
        principal = statement.get("Principal")
        is_public = principal == "*" or (
            isinstance(principal, dict) and principal.get("AWS") == "*"
        )
        actions = [str(action) for action in _as_list(statement.get("Action", []))]
        if is_public and any(action == "s3:*" or action.startswith("s3:") for action in actions):
            bucket = request.get("bucketName", "unknown")
            return DetectionFinding(
                rule_id=PUBLIC_S3_POLICY_RULE_ID,
                title="S3 bucket policy grants public access",
                severity="high",
                evidence=[
                    "eventSource=s3.amazonaws.com",
                    "eventName=PutBucketPolicy",
                    f"requestParameters.bucketName={bucket}",
                    "policy.Statement.Effect=Allow",
                    "policy.Statement.Principal=*",
                ],
                attack_techniques=["T1530 Data from Cloud Storage"],
                recommended_actions=[
                    "Confirm whether public access is an explicit business requirement.",
                    "Enable S3 Block Public Access and replace the public principal.",
                    "Review bucket access logs for unexpected reads.",
                ],
            )
    return None


def detect_public_management_port(
    raw_event: dict[str, Any],
) -> DetectionFinding | None:
    if (
        raw_event.get("eventSource") != "ec2.amazonaws.com"
        or raw_event.get("eventName") != "AuthorizeSecurityGroupIngress"
    ):
        return None

    request = raw_event.get("requestParameters") or {}
    permissions = (request.get("ipPermissions") or {}).get("items", [])
    for permission in permissions:
        protocol = str(permission.get("ipProtocol", ""))
        start = permission.get("fromPort")
        end = permission.get("toPort")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        exposed_ports = [port for port in (22, 3389) if start <= port <= end]
        ranges = (permission.get("ipRanges") or {}).get("items", [])
        cidrs = [item.get("cidrIp") for item in ranges]
        if protocol in {"tcp", "6", "-1"} and exposed_ports and any(
            cidr in {"0.0.0.0/0", "::/0"} for cidr in cidrs
        ):
            group_id = request.get("groupId", "unknown")
            return DetectionFinding(
                rule_id=PUBLIC_MANAGEMENT_PORT_RULE_ID,
                title="Management port opened to the public internet",
                severity="high",
                evidence=[
                    "eventSource=ec2.amazonaws.com",
                    "eventName=AuthorizeSecurityGroupIngress",
                    f"requestParameters.groupId={group_id}",
                    f"publicCidr={next(cidr for cidr in cidrs if cidr in {'0.0.0.0/0', '::/0'})}",
                    f"managementPorts={','.join(map(str, exposed_ports))}",
                ],
                attack_techniques=["T1133 External Remote Services"],
                recommended_actions=[
                    "Restrict the rule to approved corporate or bastion CIDR ranges.",
                    "Use AWS Systems Manager Session Manager where possible.",
                    "Review connection telemetry for the affected security group.",
                ],
            )
    return None


def detect_admin_inline_policy(
    raw_event: dict[str, Any],
) -> DetectionFinding | None:
    if raw_event.get("eventSource") != "iam.amazonaws.com" or raw_event.get(
        "eventName"
    ) not in {"PutUserPolicy", "PutRolePolicy", "PutGroupPolicy"}:
        return None

    request = raw_event.get("requestParameters") or {}
    policy = _policy_document(request.get("policyDocument"))
    if policy is None:
        return None

    for statement in _as_list(policy.get("Statement", [])):
        if not isinstance(statement, dict) or statement.get("Effect") != "Allow":
            continue
        actions = [str(action).lower() for action in _as_list(statement.get("Action", []))]
        resources = [str(resource) for resource in _as_list(statement.get("Resource", []))]
        if "*" in resources and any(action in {"*", "iam:*"} for action in actions):
            target = (
                request.get("userName")
                or request.get("roleName")
                or request.get("groupName")
                or "unknown"
            )
            return DetectionFinding(
                rule_id=ADMIN_INLINE_POLICY_RULE_ID,
                title="Broad administrative inline IAM policy was added",
                severity="critical",
                evidence=[
                    "eventSource=iam.amazonaws.com",
                    f"eventName={raw_event.get('eventName')}",
                    f"targetIdentity={target}",
                    "policy.Statement.Effect=Allow",
                    "policy grants wildcard action on wildcard resource",
                ],
                attack_techniques=["T1098 Account Manipulation"],
                recommended_actions=[
                    "Confirm the policy change through the approved change record.",
                    "Remove the wildcard policy and replace it with least privilege.",
                    "Review actions performed by the affected identity after the change.",
                ],
            )
    return None


RuleFunction = Callable[[dict[str, Any]], DetectionFinding | None]

DETECTION_RULES: tuple[RuleFunction, ...] = (
    detect_root_login_without_mfa,
    detect_cloudtrail_logging_disabled,
    detect_public_s3_bucket_policy,
    detect_public_management_port,
    detect_admin_inline_policy,
)


def run_detection_rules(raw_event: dict[str, Any]) -> list[DetectionFinding]:
    return [finding for rule in DETECTION_RULES if (finding := rule(raw_event))]

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rules import detect_root_login_without_mfa, run_detection_rules


EVENTS_PATH = PROJECT_ROOT / "data" / "cloudtrail_events.json"
LABELS_PATH = PROJECT_ROOT / "data" / "root_login_without_mfa_labels.json"
ADDITIONAL_EVENTS_PATH = PROJECT_ROOT / "data" / "additional_security_events.json"
ADDITIONAL_LABELS_PATH = (
    PROJECT_ROOT / "data" / "additional_security_event_labels.json"
)


def main() -> None:
    events = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))["Records"]
    label_document = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    labels = label_document["labels"]

    event_ids = [event["eventID"] for event in events]
    label_ids = [label["eventID"] for label in labels]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Duplicate event IDs found")
    if set(event_ids) != set(label_ids):
        raise ValueError("Event and label ID sets differ")

    expected = {
        label["eventID"] for label in labels if label["expectedMatch"] is True
    }
    actual = {
        event["eventID"]
        for event in events
        if detect_root_login_without_mfa(event) is not None
    }
    if actual != expected:
        raise ValueError(
            f"Rule/label mismatch: missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )

    additional_events = json.loads(
        ADDITIONAL_EVENTS_PATH.read_text(encoding="utf-8")
    )["Records"]
    additional_labels = json.loads(
        ADDITIONAL_LABELS_PATH.read_text(encoding="utf-8")
    )["labels"]
    additional_event_ids = [event["eventID"] for event in additional_events]
    additional_label_ids = [label["eventID"] for label in additional_labels]
    if len(additional_event_ids) != len(set(additional_event_ids)):
        raise ValueError("Duplicate additional event IDs found")
    if set(additional_event_ids) != set(additional_label_ids):
        raise ValueError("Additional event and label ID sets differ")

    expected_rules = {
        label["eventID"]: label["expectedRuleIds"] for label in additional_labels
    }
    actual_rules = {
        event["eventID"]: [
            finding.rule_id for finding in run_detection_rules(event)
        ]
        for event in additional_events
    }
    if actual_rules != expected_rules:
        raise ValueError(
            f"Additional rule/label mismatch: expected={expected_rules}, "
            f"actual={actual_rules}"
        )

    print(
        json.dumps(
            {
                "events": len(events) + len(additional_events),
                "labels": len(labels) + len(additional_labels),
                "positive_events": len(expected)
                + sum(bool(rule_ids) for rule_ids in expected_rules.values()),
                "negative_events": len(labels)
                - len(expected)
                + sum(not rule_ids for rule_ids in expected_rules.values()),
                "rules": 5,
                "status": "valid",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rules import detect_root_login_without_mfa


EVENTS_PATH = PROJECT_ROOT / "data" / "cloudtrail_events.json"
LABELS_PATH = PROJECT_ROOT / "data" / "root_login_without_mfa_labels.json"


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

    print(
        json.dumps(
            {
                "events": len(events),
                "labels": len(labels),
                "positive": len(expected),
                "negative": len(labels) - len(expected),
                "rule_id": label_document["ruleId"],
                "status": "valid",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

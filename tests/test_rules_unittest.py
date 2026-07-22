from __future__ import annotations

import json
from pathlib import Path
import unittest

from app.rules import (
    ROOT_LOGIN_WITHOUT_MFA_RULE_ID,
    detect_root_login_without_mfa,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RootLoginWithoutMfaRuleTests(unittest.TestCase):
    def test_rule_matches_all_ground_truth_labels(self) -> None:
        events = json.loads(
            (PROJECT_ROOT / "data" / "cloudtrail_events.json").read_text(
                encoding="utf-8"
            )
        )["Records"]
        labels = json.loads(
            (
                PROJECT_ROOT / "data" / "root_login_without_mfa_labels.json"
            ).read_text(encoding="utf-8")
        )["labels"]

        expected_by_id = {
            label["eventID"]: label["expectedMatch"] for label in labels
        }
        actual_by_id = {
            event["eventID"]: detect_root_login_without_mfa(event) is not None
            for event in events
        }

        self.assertEqual(actual_by_id, expected_by_id)
        self.assertEqual(sum(actual_by_id.values()), 2)

    def test_positive_finding_is_auditable(self) -> None:
        events = json.loads(
            (PROJECT_ROOT / "data" / "cloudtrail_events.json").read_text(
                encoding="utf-8"
            )
        )["Records"]
        labels = json.loads(
            (
                PROJECT_ROOT / "data" / "root_login_without_mfa_labels.json"
            ).read_text(encoding="utf-8")
        )["labels"]
        positive_id = next(
            label["eventID"] for label in labels if label["expectedMatch"] is True
        )
        event = next(item for item in events if item["eventID"] == positive_id)

        finding = detect_root_login_without_mfa(event)

        self.assertIsNotNone(finding)
        assert finding is not None
        self.assertEqual(finding.rule_id, ROOT_LOGIN_WITHOUT_MFA_RULE_ID)
        self.assertEqual(finding.severity, "critical")
        self.assertEqual(len(finding.evidence), 5)


if __name__ == "__main__":
    unittest.main()

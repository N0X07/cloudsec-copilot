from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from app.cli import main
from scripts.ops_healthcheck import HealthCheckResult


class CloudsecctlTests(unittest.TestCase):
    def test_health_command_returns_success(self) -> None:
        result = HealthCheckResult(
            ok=True,
            status_code=200,
            elapsed_ms=12,
            message="service healthy",
            payload={"status": "ok", "environment": "test"},
        )
        with patch("app.cli.run_healthcheck", return_value=result):
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["health", "--expected-environment", "test"])

        self.assertEqual(exit_code, 0)
        self.assertIn("OK service healthy", output.getvalue())

    def test_incidents_list_prints_table(self) -> None:
        incidents = [
            {
                "incident_id": "inc-1",
                "severity": "critical",
                "status": "open",
                "rule_id": "root_login_without_mfa",
                "title": "Root login without MFA",
            }
        ]
        with patch("app.cli.fetch_json", return_value=(200, incidents)):
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["incidents", "list"])

        self.assertEqual(exit_code, 0)
        self.assertIn("INCIDENT", output.getvalue())
        self.assertIn("inc-1", output.getvalue())

    def test_validate_infra_returns_failure_on_exception(self) -> None:
        with patch("app.cli.validate_infrastructure", side_effect=ValueError("bad")):
            self.assertEqual(main(["validate-infra"]), 1)

    def test_k8s_check_runs_kustomize(self) -> None:
        completed = Mock(returncode=0, stdout="rendered", stderr="")
        with patch("app.cli.run_command", return_value=completed) as run_command:
            self.assertEqual(main(["k8s-check"]), 0)

        run_command.assert_called_once()
        self.assertEqual(run_command.call_args.args[0], ["kubectl", "kustomize", "k8s/base"])


if __name__ == "__main__":
    unittest.main()

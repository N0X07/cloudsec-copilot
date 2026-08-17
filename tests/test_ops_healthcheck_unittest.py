from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.ops_healthcheck import run_healthcheck


class _FakeResponse:
    status = 200

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class OpsHealthcheckTests(unittest.TestCase):
    def test_accepts_healthy_response(self) -> None:
        with patch(
            "scripts.ops_healthcheck.urlopen",
            return_value=_FakeResponse(b'{"status":"ok","environment":"test"}'),
        ):
            result = run_healthcheck(
                "http://service/health", expected_environment="test"
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.message, "service healthy")

    def test_rejects_environment_mismatch(self) -> None:
        with patch(
            "scripts.ops_healthcheck.urlopen",
            return_value=_FakeResponse(b'{"status":"ok","environment":"demo"}'),
        ):
            result = run_healthcheck(
                "http://service/health", expected_environment="prod"
            )

        self.assertFalse(result.ok)
        self.assertIn("environment mismatch", result.message)

    def test_rejects_unhealthy_payload(self) -> None:
        with patch(
            "scripts.ops_healthcheck.urlopen",
            return_value=_FakeResponse(b'{"status":"degraded","environment":"test"}'),
        ):
            result = run_healthcheck("http://service/health")

        self.assertFalse(result.ok)
        self.assertEqual(result.message, "health payload status is not ok")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_URL = "http://localhost:8000/health"


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    status_code: int | None
    elapsed_ms: int
    message: str
    payload: dict[str, Any] | None = None


def fetch_health(url: str, timeout: float) -> tuple[int, dict[str, Any]]:
    request = Request(url, headers={"User-Agent": "cloudsec-ops-healthcheck/1.0"})
    with urlopen(request, timeout=timeout) as response:
        raw_body = response.read().decode("utf-8")
        payload = json.loads(raw_body)
        return response.status, payload


def run_healthcheck(
    url: str = DEFAULT_URL,
    *,
    timeout: float = 3,
    expected_environment: str | None = None,
) -> HealthCheckResult:
    started = time.perf_counter()
    try:
        status_code, payload = fetch_health(url, timeout)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return HealthCheckResult(
            ok=False,
            status_code=getattr(error, "code", None),
            elapsed_ms=elapsed_ms,
            message=f"health endpoint unavailable: {error}",
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return HealthCheckResult(
            ok=False,
            status_code=None,
            elapsed_ms=elapsed_ms,
            message=f"health endpoint returned invalid JSON: {error}",
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if status_code != 200:
        return HealthCheckResult(
            ok=False,
            status_code=status_code,
            elapsed_ms=elapsed_ms,
            message=f"unexpected HTTP status {status_code}",
            payload=payload,
        )
    if payload.get("status") != "ok":
        return HealthCheckResult(
            ok=False,
            status_code=status_code,
            elapsed_ms=elapsed_ms,
            message="health payload status is not ok",
            payload=payload,
        )
    if expected_environment and payload.get("environment") != expected_environment:
        return HealthCheckResult(
            ok=False,
            status_code=status_code,
            elapsed_ms=elapsed_ms,
            message=(
                "environment mismatch: expected "
                f"{expected_environment!r}, got {payload.get('environment')!r}"
            ),
            payload=payload,
        )

    return HealthCheckResult(
        ok=True,
        status_code=status_code,
        elapsed_ms=elapsed_ms,
        message="service healthy",
        payload=payload,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check the CloudSec Copilot health endpoint for operations triage."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Health endpoint URL.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=3,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--expected-environment",
        help="Optional environment value expected in the health response.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable result instead of a short status line.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_healthcheck(
        args.url,
        timeout=args.timeout,
        expected_environment=args.expected_environment,
    )
    if args.json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        level = "OK" if result.ok else "FAIL"
        print(f"{level} {result.message} ({result.elapsed_ms} ms)")
        if result.payload:
            print(json.dumps(result.payload, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())

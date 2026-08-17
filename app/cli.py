from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.ops_healthcheck import run_healthcheck
from scripts.validate_infrastructure import main as validate_infrastructure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://localhost:8000"


def fetch_json(url: str, *, timeout: float) -> tuple[int, Any]:
    request = Request(url, headers={"User-Agent": "cloudsecctl/0.1"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return response.status, payload


def print_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    widths = [
        max(len(title), *(len(str(row.get(key, ""))) for row in rows))
        for key, title in columns
    ]
    header = "  ".join(title.ljust(width) for width, (_, title) in zip(widths, columns))
    print(header)
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print(
            "  ".join(
                str(row.get(key, "")).ljust(width)
                for width, (key, _) in zip(widths, columns)
            )
        )


def command_health(args: argparse.Namespace) -> int:
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


def command_incidents_list(args: argparse.Namespace) -> int:
    query = urlencode({"offset": args.offset, "limit": args.limit})
    url = f"{args.base_url.rstrip('/')}/api/v1/incidents?{query}"
    try:
        status_code, incidents = fetch_json(url, timeout=args.timeout)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        print(f"FAIL incident API unavailable: {error}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"FAIL incident API returned invalid JSON: {error}", file=sys.stderr)
        return 1

    if status_code != 200:
        print(f"FAIL unexpected HTTP status {status_code}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(incidents, indent=2, sort_keys=True))
        return 0

    if not incidents:
        print("No incidents found.")
        return 0

    rows = [
        {
            "incident_id": incident.get("incident_id", ""),
            "severity": incident.get("severity", ""),
            "status": incident.get("status", ""),
            "rule_id": incident.get("rule_id", ""),
            "title": incident.get("title", ""),
        }
        for incident in incidents
    ]
    print_table(
        rows,
        [
            ("incident_id", "INCIDENT"),
            ("severity", "SEVERITY"),
            ("status", "STATUS"),
            ("rule_id", "RULE"),
            ("title", "TITLE"),
        ],
    )
    return 0


def command_validate_infra(_: argparse.Namespace) -> int:
    try:
        validate_infrastructure()
    except Exception as error:
        print(f"FAIL infrastructure validation failed: {error}", file=sys.stderr)
        return 1
    return 0


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def command_k8s_check(args: argparse.Namespace) -> int:
    checks: list[tuple[str, list[str]]] = [
        ("Render manifests", ["kubectl", "kustomize", args.path]),
    ]
    if args.cluster:
        checks.extend(
            [
                (
                    "Current context",
                    ["kubectl", "config", "current-context"],
                ),
                (
                    "Workloads",
                    ["kubectl", "-n", args.namespace, "get", "pods,svc"],
                ),
            ]
        )

    failures = 0
    for label, command in checks:
        result = run_command(command)
        if result.returncode == 0:
            print(f"OK {label}")
            if args.verbose and result.stdout.strip():
                print(result.stdout.strip())
        else:
            failures += 1
            print(f"FAIL {label}", file=sys.stderr)
            if result.stderr.strip():
                print(result.stderr.strip(), file=sys.stderr)
            elif result.stdout.strip():
                print(result.stdout.strip(), file=sys.stderr)
    return 0 if failures == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cloudsecctl",
        description="Platform operations CLI for CloudSec Copilot.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="Check the API health endpoint.")
    health.add_argument("--url", default=f"{DEFAULT_BASE_URL}/health")
    health.add_argument("--timeout", type=float, default=3)
    health.add_argument("--expected-environment")
    health.add_argument("--json", action="store_true")
    health.set_defaults(func=command_health)

    incidents = subparsers.add_parser("incidents", help="Incident operations.")
    incident_subparsers = incidents.add_subparsers(
        dest="incident_command", required=True
    )
    incidents_list = incident_subparsers.add_parser(
        "list", help="List incidents through the API."
    )
    incidents_list.add_argument("--base-url", default=DEFAULT_BASE_URL)
    incidents_list.add_argument("--offset", type=int, default=0)
    incidents_list.add_argument("--limit", type=int, default=20)
    incidents_list.add_argument("--timeout", type=float, default=5)
    incidents_list.add_argument("--json", action="store_true")
    incidents_list.set_defaults(func=command_incidents_list)

    validate = subparsers.add_parser(
        "validate-infra",
        help="Validate Terraform, Kubernetes, and operations invariants.",
    )
    validate.set_defaults(func=command_validate_infra)

    k8s = subparsers.add_parser(
        "k8s-check", help="Render Kubernetes manifests and optionally inspect a cluster."
    )
    k8s.add_argument("--path", default="k8s/base")
    k8s.add_argument("--namespace", default="cloudsec-copilot")
    k8s.add_argument("--cluster", action="store_true")
    k8s.add_argument("--verbose", action="store_true")
    k8s.set_defaults(func=command_k8s_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

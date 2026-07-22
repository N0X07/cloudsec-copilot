from __future__ import annotations

import json
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_ROOT = PROJECT_ROOT / "infra" / "terraform"


def require(source: str, fragment: str, message: str) -> None:
    if fragment not in source:
        raise ValueError(message)


def forbid(source: str, fragment: str, message: str) -> None:
    if fragment in source:
        raise ValueError(message)


def forbid_pattern(source: str, pattern: str, message: str) -> None:
    if re.search(pattern, source, flags=re.MULTILINE):
        raise ValueError(message)


def main() -> None:
    terraform_files = sorted(TERRAFORM_ROOT.glob("*.tf"))
    if not terraform_files:
        raise ValueError("No Terraform files found")
    source = "\n".join(path.read_text(encoding="utf-8") for path in terraform_files)

    require(source, 'storage_encrypted           = true', "RDS encryption is required")
    require(
        source,
        'manage_master_user_password = true',
        "RDS must manage the database password",
    )
    require(
        source,
        'publicly_accessible    = false',
        "RDS must not be publicly accessible",
    )
    require(
        source,
        'image_tag_mutability = "IMMUTABLE"',
        "ECR tags must be immutable",
    )
    require(source, "scan_on_push = true", "ECR image scanning is required")
    require(
        source,
        'security_groups = [aws_security_group.alb.id]',
        "The API ingress must be scoped to the ALB security group",
    )
    require(
        source,
        'actions = ["secretsmanager:GetSecretValue"]',
        "The execution role must read runtime secrets",
    )
    forbid(
        source,
        'resources = ["*"]',
        "IAM secret access must not use a wildcard resource",
    )
    forbid_pattern(
        source,
        r"^\s*master_user_password\s*=",
        "Database passwords must not be stored in Terraform configuration",
    )

    print(
        json.dumps(
            {
                "terraform_files": len(terraform_files),
                "security_invariants": 9,
                "status": "valid",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_ROOT = PROJECT_ROOT / "infra" / "terraform"
K8S_ROOT = PROJECT_ROOT / "k8s" / "base"
OPS_CHECK = PROJECT_ROOT / "scripts" / "ops_check.sh"
SLO_DOC = PROJECT_ROOT / "docs" / "slo.md"
K8S_DRILL_DOC = PROJECT_ROOT / "docs" / "k8s-failure-drill.md"
DEPLOYMENT_DOC = PROJECT_ROOT / "docs" / "deployment.md"
CONFIGURATION_DOC = PROJECT_ROOT / "docs" / "configuration.md"
OBSERVABILITY_DOC = PROJECT_ROOT / "docs" / "observability.md"
CHANGELOG_DOC = PROJECT_ROOT / "CHANGELOG.md"
README_DOC = PROJECT_ROOT / "README.md"
ASSET_ROOT = PROJECT_ROOT / "docs" / "assets"


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
    require(
        source,
        'retention_in_days = 30',
        "Application logs must have an explicit retention period",
    )
    require(
        source,
        'metric_name         = "HTTPCode_ELB_5XX_Count"',
        "ALB 5XX responses must be covered by a CloudWatch alarm",
    )
    require(
        source,
        'metric_name         = "RunningTaskCount"',
        "ECS running task count must be covered by a CloudWatch alarm",
    )
    require(
        source,
        'treat_missing_data  = "breaching"',
        "The ECS running-task alarm must treat missing data as breaching",
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

    k8s_files = sorted(K8S_ROOT.glob("*.yaml"))
    if not k8s_files:
        raise ValueError("No Kubernetes manifests found")
    k8s_source = "\n".join(path.read_text(encoding="utf-8") for path in k8s_files)
    require(k8s_source, "kind: Deployment", "Kubernetes Deployment is required")
    require(k8s_source, "kind: Service", "Kubernetes Service is required")
    require(k8s_source, "kind: ConfigMap", "Kubernetes ConfigMap is required")
    require(k8s_source, "kind: Secret", "Kubernetes Secret example is required")
    require(k8s_source, "readinessProbe:", "Readiness probe is required")
    require(k8s_source, "livenessProbe:", "Liveness probe is required")
    require(k8s_source, "runAsNonRoot: true", "Pods must run as non-root")
    require(k8s_source, "requests:", "Kubernetes resource requests are required")
    require(k8s_source, "limits:", "Kubernetes resource limits are required")
    require(
        k8s_source,
        "imagePullPolicy: IfNotPresent",
        "Local Kubernetes image loading should not require a registry pull",
    )

    ops_source = OPS_CHECK.read_text(encoding="utf-8")
    require(ops_source, "check_process", "Linux ops check must inspect the process")
    require(ops_source, "check_port", "Linux ops check must inspect the port")
    require(
        ops_source,
        "check_health",
        "Linux ops check must inspect the health endpoint",
    )
    require(ops_source, "check_logs", "Linux ops check must inspect logs when provided")

    slo_source = SLO_DOC.read_text(encoding="utf-8")
    require(slo_source, "Availability target", "SLO doc must define availability")
    require(slo_source, "Latency target", "SLO doc must define latency")
    require(slo_source, "Error budget", "SLO doc must define an error budget")
    require(slo_source, "ALB 5XX", "SLO doc must cover ALB 5XX failures")
    require(slo_source, "K8s pod crashloop", "SLO doc must cover Kubernetes failures")

    drill_source = K8S_DRILL_DOC.read_text(encoding="utf-8")
    require(
        drill_source,
        "ImagePullBackOff",
        "Kubernetes drill doc must cover ImagePullBackOff",
    )
    require(drill_source, "describe pod", "Kubernetes drill doc must use describe")
    require(drill_source, "rollout status", "Kubernetes drill doc must verify rollout")

    deployment_source = DEPLOYMENT_DOC.read_text(encoding="utf-8")
    require(deployment_source, "Rollback", "Deployment doc must describe rollback")
    require(deployment_source, "Docker Compose", "Deployment doc must cover Compose")
    require(deployment_source, "Local Kubernetes", "Deployment doc must cover Kubernetes")
    require(deployment_source, "AWS Terraform", "Deployment doc must cover Terraform")

    configuration_source = CONFIGURATION_DOC.read_text(encoding="utf-8")
    require(configuration_source, "DATABASE_URL", "Configuration doc must cover DB config")
    require(configuration_source, "OPENAI_API_KEY", "Configuration doc must cover secrets")
    require(configuration_source, "ConfigMap", "Configuration doc must cover Kubernetes config")
    require(configuration_source, "Secrets Manager", "Configuration doc must cover AWS secrets")

    observability_source = OBSERVABILITY_DOC.read_text(encoding="utf-8")
    require(observability_source, "Latency", "Observability doc must cover latency")
    require(observability_source, "Traffic", "Observability doc must cover traffic")
    require(observability_source, "Errors", "Observability doc must cover errors")
    require(observability_source, "Saturation", "Observability doc must cover saturation")

    changelog_source = CHANGELOG_DOC.read_text(encoding="utf-8")
    require(changelog_source, "0.3.0", "Changelog must include current platform release")
    require(changelog_source, "cloudsecctl", "Changelog must mention CLI work")

    readme_source = README_DOC.read_text(encoding="utf-8")
    require(readme_source, "```mermaid", "README must include a Mermaid architecture diagram")
    require(readme_source, "docs/observability.md", "README must link observability docs")
    require(readme_source, "docs/assets/architecture.png", "README must show architecture screenshot")
    require(readme_source, "docs/assets/validate-infra.png", "README must show validate-infra screenshot")
    require(readme_source, "docs/assets/pytest.png", "README must show pytest screenshot")
    require(readme_source, "docs/assets/kubectl-pods.png", "README must show Kubernetes screenshot")

    for asset_name in [
        "architecture.png",
        "validate-infra.png",
        "pytest.png",
        "kubectl-pods.png",
    ]:
        asset_path = ASSET_ROOT / asset_name
        if not asset_path.exists() or asset_path.stat().st_size == 0:
            raise ValueError(f"Missing README asset: {asset_name}")

    print(
        json.dumps(
            {
                "terraform_files": len(terraform_files),
                "kubernetes_files": len(k8s_files),
                "security_invariants": 59,
                "status": "valid",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

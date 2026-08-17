# Changelog

All notable changes to CloudSec Copilot are documented here. The project follows
a simple portfolio-friendly changelog style rather than a formal release train.

## 0.3.0 - Platform Engineering polish

- Added `cloudsecctl` CLI with `health`, `incidents list`, `validate-infra`, and
  `k8s-check` commands.
- Added SLO, deployment, configuration, observability, runbook, and Kubernetes
  failure-drill documentation.
- Added local kind validation notes and an ImagePullBackOff failure drill.
- Expanded infrastructure validation to cover Terraform, Kubernetes manifests,
  operations scripts, SLO docs, and failure-drill docs.

## 0.2.0 - DevOps and Kubernetes enhancement

- Added Linux `ops_check.sh` for process, port, resource, log, and health checks.
- Added CloudWatch alarms for ALB 5XX and ECS running task count.
- Added Kubernetes manifests for kind/minikube with ConfigMap, Secret example,
  Deployment, Service, probes, resource limits, and non-root security context.
- Added operations runbook and Kubernetes deployment notes.

## 0.1.0 - Cloud security MVP

- Added CloudTrail-style event ingestion.
- Added deterministic AWS security detection rules.
- Added incident persistence, evidence-backed reports, audit logs, and human
  approval workflow.
- Added optional bounded AI analyst with read-only allow-listed tools.
- Added Dockerfile, Docker Compose, GitHub Actions CI, API tests, dataset
  validation, and AWS Terraform template.

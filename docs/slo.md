# Service Level Objectives

These SLOs describe the portfolio demo environment for CloudSec Copilot. They
are intentionally modest because the project uses disposable infrastructure and
synthetic security events.

## User-facing targets

| Signal | Target | Measurement |
| --- | --- | --- |
| Availability target | 99.5% monthly availability for `/health` | Successful HTTP 200 health checks through ALB or Kubernetes port-forward |
| Latency target | `/health` p95 below 200 ms | `cloudsecctl health --json` elapsed time or synthetic probe output |
| Incident API correctness | Incident list/report endpoints return valid JSON | API tests and CLI smoke checks |
| Deployment readiness | One ready API replica after rollout | `kubectl rollout status` or ECS running task count |

## Error budget

For a 30-day month, 99.5% availability allows about 216 minutes of failed health
checks. This demo treats error budget burn as a signal to pause feature changes
and focus on deployment health, probes, logs, and rollback quality.

Burn examples:

- `/health` fails because the API process exits during startup.
- ALB returns 5XX responses while no healthy targets are available.
- Kubernetes readiness stays false and the service has no ready endpoints.
- RDS connection failures prevent API startup in the AWS deployment path.

## Alert and triage mapping

| Failure scenario | Detection signal | First checks | Recovery action |
| --- | --- | --- | --- |
| ALB 5XX | `alb_5xx_alarm_name` enters `ALARM` | `cloudsecctl health`, ALB target health, CloudWatch logs | Roll forward a fixed image or revert to last known good image tag |
| ECS task down | `ecs_running_tasks_alarm_name` enters `ALARM` | ECS service events, stopped task reason, `/ecs/cloudsec-copilot-demo` logs | Fix runtime config/secrets or force a new deployment |
| DB connection failed | API startup logs show database auth or network errors | RDS status, security groups, DB secret injection, task env | Repair secret/network config and redeploy task |
| K8s pod crashloop | Pod status `CrashLoopBackOff` | `kubectl describe pod`, `kubectl logs --previous`, env/config | Fix image, command, config, or database path and wait for rollout |
| K8s ImagePullBackOff | Pod cannot pull image | Pod events, image tag, kind image list/load step | Build and load `cloudsec-copilot:dev`, then restart rollout |
| Probe failure | Readiness/liveness probe failures in events | `/health`, port mapping, app logs, probe timing | Fix endpoint/config or adjust probe timing after evidence review |

## SLO review checklist

1. Run `cloudsecctl health --expected-environment development` locally.
2. Run `cloudsecctl validate-infra`.
3. Run `cloudsecctl k8s-check --cluster` when the kind cluster is available.
4. Check CloudWatch alarm outputs after Terraform deployment planning.
5. Record any failed scenario in the runbook or failure-drill notes with
   command output and recovery action.

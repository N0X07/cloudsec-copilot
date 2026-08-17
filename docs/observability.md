# Observability

CloudSec Copilot uses the four golden signals as its observability model:
latency, traffic, errors, and saturation. The goal is to keep troubleshooting
simple enough for a portfolio demo while using concepts that transfer to real
SRE work.

## Golden signals

| Signal | Demo measurement | AWS path | Kubernetes path |
| --- | --- | --- | --- |
| Latency | `cloudsecctl health --json` elapsed time | ALB target response time, application logs | Port-forward health latency, probe timing |
| Traffic | API request count in logs | ALB request count, ECS logs | `kubectl logs`, service access |
| Errors | HTTP 5XX, failed CLI checks, exception logs | `HTTPCode_ELB_5XX_Count` alarm, CloudWatch logs | Pod events, probe failures, app logs |
| Saturation | CPU/memory/disk checks | ECS Container Insights, RDS status | Pod resource requests/limits, restart count |

## Health-check signal

`/health` returns:

```json
{
  "status": "ok",
  "environment": "development"
}
```

Use:

```powershell
cloudsecctl health --expected-environment development --json
```

Targets from `docs/slo.md`:

- Availability target: 99.5% monthly success rate for `/health`.
- Latency target: `/health` p95 below 200 ms in local/demo checks.

## CloudWatch signals

Terraform creates:

- Log group: `/ecs/cloudsec-copilot-demo`
- ALB 5XX alarm: `alb_5xx_alarm_name`
- ECS running task count alarm: `ecs_running_tasks_alarm_name`

Useful commands:

```powershell
aws logs tail /ecs/cloudsec-copilot-demo --since 15m --follow
aws cloudwatch describe-alarms --alarm-names ALARM_NAME
aws ecs describe-services --cluster cloudsec-copilot-demo --services cloudsec-copilot-demo
```

## Kubernetes signals

Useful commands:

```powershell
cloudsecctl k8s-check --cluster --verbose
kubectl -n cloudsec-copilot get pods,svc,endpoints
kubectl -n cloudsec-copilot describe pod -l app.kubernetes.io/component=api
kubectl -n cloudsec-copilot logs deploy/cloudsec-copilot-api --tail=100
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
```

Probe configuration:

- Readiness probe: `GET /health`, starts after 5 seconds.
- Liveness probe: `GET /health`, starts after 20 seconds.

## Triage workflow

1. Check user-facing health with `cloudsecctl health`.
2. Check platform state with `cloudsecctl validate-infra` or
   `cloudsecctl k8s-check --cluster`.
3. Inspect recent logs around the failure timestamp.
4. Inspect platform events: ALB target health, ECS service events, or
   `kubectl describe pod`.
5. Decide whether to roll forward, roll back, or fix configuration.

## Gaps and future improvements

- Add structured JSON logging.
- Add request latency middleware and metrics export.
- Add Prometheus/Grafana manifests for the Kubernetes path.
- Add synthetic probes for incident report endpoints.
- Add load-test results for import and incident-list endpoints.

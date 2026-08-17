# CloudSec Copilot Operations Runbook

This runbook is for the disposable portfolio deployment described in
`infra/terraform`. The goal is to restore or explain the demo quickly without
making unapproved changes to cloud resources.

## Quick checks

1. Run the Linux operations check on a host running the API:

   ```sh
   APP_URL=http://localhost:8000/health EXPECTED_ENV=development sh scripts/ops_check.sh
   ```

2. Confirm the public health endpoint:

   ```powershell
   python scripts/ops_healthcheck.py --url http://localhost:8000/health
   python scripts/ops_healthcheck.py --url http://ALB_DNS_NAME/health --expected-environment demo
   ```

3. Check the ALB target group health in AWS:

   ```powershell
   aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN
   ```

4. Check ECS service rollout state:

   ```powershell
   aws ecs describe-services --cluster cloudsec-copilot-demo --services cloudsec-copilot-demo
   ```

5. Check recent application logs:

   ```powershell
   aws logs tail /ecs/cloudsec-copilot-demo --since 15m --follow
   ```

## Alarm response

### ALB 5XX errors

Symptoms:

- The `alb_5xx_alarm_name` CloudWatch alarm is in `ALARM`.
- Users receive intermittent `502` or `503` responses.

Triage:

1. Run `scripts/ops_healthcheck.py` against the ALB URL.
2. Inspect target health. If targets are unhealthy, continue with the ECS task
   section.
3. Tail CloudWatch logs for exceptions around the same timestamp.
4. Confirm the current image tag matches the intended commit SHA.

Likely fixes:

- Roll forward with a fixed container image.
- Force a new ECS deployment if tasks are stuck on stale environment values.
- Revert the image tag in `container_image` to the last known healthy SHA for a
  demo rollback.

### ECS task not running

Symptoms:

- `ecs_running_tasks_alarm_name` is in `ALARM`.
- Desired count is greater than running count.

Triage:

1. Run `aws ecs describe-services` and inspect `events`.
2. Check stopped tasks for exit codes:

   ```powershell
   aws ecs list-tasks --cluster cloudsec-copilot-demo --desired-status STOPPED
   aws ecs describe-tasks --cluster cloudsec-copilot-demo --tasks TASK_ARN
   ```

3. Tail CloudWatch logs for startup errors.
4. Confirm the RDS secret ARN and optional OpenAI secret ARN are readable by the
   execution role.

Likely fixes:

- Repair missing or malformed runtime secrets.
- Confirm the database is available and security groups allow API-to-RDS access.
- Deploy a corrected image if startup imports or schema creation fail.

### RDS connection failure

Symptoms:

- API health checks fail after startup.
- Logs include database connection or authentication errors.

Triage:

1. Confirm the RDS instance is `available`.
2. Confirm the database security group allows inbound `5432` only from the API
   security group.
3. Confirm task environment variables include `DB_HOST`, `DB_PORT`, `DB_NAME`,
   `DB_USER`, and the RDS-managed `DB_PASSWORD` secret.
4. If RDS rotated the password, force a new ECS deployment so tasks receive the
   current secret value.

## Evidence to capture

- Health-check command output.
- Linux `ops_check.sh` output when a host or container shell is available.
- `cloudsecctl validate-infra` and `cloudsecctl k8s-check` output.
- CloudWatch alarm name, state, and timestamp.
- ECS service events and stopped-task reason.
- Relevant log lines from `/ecs/cloudsec-copilot-demo`.
- Terraform image tag and Git commit SHA.

For Kubernetes-specific scenarios such as `ImagePullBackOff`, probe failures,
config mistakes, and service access issues, use `docs/k8s-failure-drill.md` as
the repeatable exercise record.

## Escalation boundary

This MVP never performs automatic remediation. Human approval in the API records
workflow intent only; infrastructure changes still require an explicit operator
action through Terraform or AWS CLI.

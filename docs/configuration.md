# Configuration Management

CloudSec Copilot keeps runtime configuration in environment variables and keeps
secrets out of source control. Local, Docker Compose, Kubernetes, and Terraform
paths use the same core settings.

## Runtime settings

| Variable | Required | Default | Used by | Notes |
| --- | --- | --- | --- | --- |
| `APP_ENV` | No | `development` | API, health checks | Returned by `/health` for environment verification |
| `DATABASE_URL` | No | `sqlite:///./cloudsec.db` | API | Overrides DB component variables |
| `DB_HOST` | No | none | API in AWS path | Enables PostgreSQL URL assembly when `DATABASE_URL` is absent |
| `DB_PORT` | No | `5432` | API in AWS path | Used with `DB_HOST` |
| `DB_NAME` | No | `cloudsec` | API in AWS path | URL encoded before use |
| `DB_USER` | No | `cloudsecadmin` | API in AWS path | URL encoded before use |
| `DB_PASSWORD` | Required with `DB_HOST` | none | API in AWS path | Must come from a secret source |
| `OPENAI_API_KEY` | No | none | Optional agent endpoint | Required only for live agent analysis |
| `OPENAI_MODEL` | No | `gpt-5.6-terra` | Optional agent endpoint | Can be changed per environment |
| `MAX_AGENT_STEPS` | No | `4` | Optional agent endpoint | Hard bounded by application policy |

## Local `.env`

Use `.env.example` as the template. Never commit `.env` files:

```powershell
Copy-Item .env.example .env
```

The app can run without `OPENAI_API_KEY`; deterministic ingestion, detection,
incident reporting, approval, and tests still work.

## Docker Compose

`compose.yaml` sets `DATABASE_URL` to the Compose PostgreSQL service:

```yaml
DATABASE_URL: postgresql+psycopg://cloudsec:cloudsec-local-only@db:5432/cloudsec
```

The Compose database password is development-only. Production secrets must come
from a managed secret store.

## Kubernetes

Kubernetes separates non-secret and secret configuration:

- `k8s/base/configmap.yaml`: `APP_ENV`, `DATABASE_URL`, `OPENAI_MODEL`,
  `MAX_AGENT_STEPS`.
- `k8s/base/secret.example.yaml`: optional `OPENAI_API_KEY` shape.

The ConfigMap contains non-secret runtime values, while the Secret example
documents the expected shape for sensitive values.

Local kind uses SQLite on `/data` through an `emptyDir` volume. This keeps the
Kubernetes demo lightweight and disposable.

Validate manifest configuration:

```powershell
cloudsecctl k8s-check
```

## AWS Terraform

Terraform passes non-secret values through ECS task environment variables and
injects secrets through ECS `secrets`:

- RDS master password is managed by RDS and exposed to the task through Secrets Manager.
- OpenAI API key is optional and must be created outside Terraform; only the ARN
  is passed through `openai_api_key_secret_arn`.
- The execution role can read only the configured secret ARNs.

Important variables:

- `container_image`: immutable ECR image URI.
- `allowed_cidr_blocks`: CIDRs allowed to reach the ALB.
- `certificate_arn`: optional ACM certificate for HTTPS.
- `protect_data`: enables deletion protection and final RDS snapshot.

## Configuration checks

1. Run `cloudsecctl health --expected-environment development` locally.
2. Run `cloudsecctl health --expected-environment kubernetes-local` through
   Kubernetes port-forward.
3. Run `cloudsecctl validate-infra` before committing infrastructure changes.
4. Confirm `.env`, `.tfvars`, PEM files, and key files are ignored by Git.

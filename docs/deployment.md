# Deployment and Rollback

This document describes repeatable deployment paths for CloudSec Copilot. The
project currently has local, Docker Compose, local Kubernetes, and Terraform AWS
paths. AWS resources are not created by default.

## Local API

Use this path for API development and tests:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
cloudsecctl health --expected-environment development
```

Rollback is simply stopping the dev server and returning to the last known good
Git commit.

## Docker Compose

Use this path to run the API with PostgreSQL:

```powershell
docker compose up --build
cloudsecctl health --expected-environment development
```

Rollback:

1. Stop the stack with `docker compose down`.
2. Check the previous Git commit or image tag.
3. Rebuild with `docker compose up --build`.
4. Re-run `cloudsecctl health` and API smoke checks.

For a clean local database reset:

```powershell
docker compose down -v
```

## Local Kubernetes with kind

Use this path to validate Kubernetes manifests and rollout behavior:

```powershell
docker build --tag cloudsec-copilot:dev .
kind load docker-image cloudsec-copilot:dev --name cloudsec
kubectl apply -k k8s/base
kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
cloudsecctl k8s-check --cluster
```

Health check through port-forward:

```powershell
kubectl -n cloudsec-copilot port-forward svc/cloudsec-copilot-api 8000:8000
cloudsecctl health --url http://localhost:8000/health --expected-environment kubernetes-local
```

Rollback options:

- Restore the previous image tag:

  ```powershell
  kubectl -n cloudsec-copilot set image deployment/cloudsec-copilot-api api=cloudsec-copilot:dev
  kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
  ```

- Use Kubernetes rollout history when a previous ReplicaSet is available:

  ```powershell
  kubectl -n cloudsec-copilot rollout history deployment/cloudsec-copilot-api
  kubectl -n cloudsec-copilot rollout undo deployment/cloudsec-copilot-api
  kubectl -n cloudsec-copilot rollout status deployment/cloudsec-copilot-api
  ```

## AWS Terraform template

Use this path only after reviewing cost and account boundaries. The Terraform
configuration creates an ALB, ECS Fargate service, RDS PostgreSQL, ECR,
Secrets Manager access, IAM, CloudWatch logs, and CloudWatch alarms.

Stage 1: bootstrap ECR.

```powershell
cd infra/terraform
terraform init
terraform apply -target=aws_ecr_repository.app -target=aws_ecr_lifecycle_policy.app
```

Stage 2: push an immutable image.

```powershell
$region = "ap-southeast-2"
$repository = terraform output -raw ecr_repository_url
$registry = $repository.Split('/')[0]
$sha = git rev-parse --short=12 HEAD
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $registry
docker build -t "${repository}:${sha}" ../..
docker push "${repository}:${sha}"
```

Stage 3: apply the full stack.

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
# Set container_image to the pushed URI and restrict allowed_cidr_blocks.
terraform fmt -check
terraform validate
terraform plan -out cloudsec.tfplan
terraform apply cloudsec.tfplan
terraform output application_url
```

Rollback:

1. Identify the last known healthy image SHA.
2. Set `container_image` back to that immutable ECR image URI.
3. Run `terraform plan` and `terraform apply`.
4. Confirm ALB target health, ECS running task count, and `cloudsecctl health`.

## Release checklist

1. `python scripts/validate_dataset.py`
2. `cloudsecctl validate-infra`
3. `python -m pytest`
4. `python -m compileall -q app tests scripts`
5. `docker build --tag cloudsec-copilot:dev .`
6. `kubectl kustomize k8s/base`
7. Update `CHANGELOG.md`.

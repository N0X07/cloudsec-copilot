# AWS deployment with Terraform

This configuration creates a cost-aware portfolio environment in AWS:

- Application Load Balancer in two public subnets
- ECS Fargate service whose port is reachable only from the ALB
- PostgreSQL RDS instance in two private database subnets
- RDS-managed master password in Secrets Manager
- ECR repository with immutable tags and scan-on-push
- CloudWatch logs, container insights, health checks, and rollback
- Least-privilege task and execution IAM roles

Fargate tasks use public IP addresses for outbound package/API access, but their
security group accepts inbound traffic only from the load balancer. This avoids
the ongoing cost of a NAT Gateway in a short-lived portfolio environment. For a
production design, place tasks in private subnets and add NAT gateways or the
required VPC endpoints.

## Cost and safety warning

Running this stack creates billable ALB, Fargate, RDS, Secrets Manager, logging,
and data-transfer resources. Review the Terraform plan, restrict
`allowed_cidr_blocks`, and destroy the demo when it is no longer needed. The
default `protect_data = false` is intended only for disposable synthetic data.

## Two-stage deployment

Prerequisites: Terraform, Docker, AWS CLI, and authenticated AWS credentials.

1. Initialize Terraform and create only the ECR repository:

   ```powershell
   cd infra/terraform
   terraform init
   terraform apply -target=aws_ecr_repository.app -target=aws_ecr_lifecycle_policy.app
   ```

2. Build and push an image tagged with the Git commit SHA:

   ```powershell
   $region = "ap-southeast-2"
   $repository = terraform output -raw ecr_repository_url
   $registry = $repository.Split('/')[0]
   $sha = git rev-parse --short=12 HEAD
   aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $registry
   docker build -t "${repository}:${sha}" ../..
   docker push "${repository}:${sha}"
   ```

3. Copy `terraform.tfvars.example` to `terraform.tfvars`, replace
   `container_image` with the pushed URI, restrict the allowed CIDR, then review
   and apply the complete plan:

   ```powershell
   terraform fmt -check
   terraform validate
   terraform plan -out cloudsec.tfplan
   terraform apply cloudsec.tfplan
   terraform output application_url
   ```

The first full apply can take several minutes while RDS starts. The application
creates its initial schema on startup.

## Optional OpenAI key

Create the API-key secret outside Terraform, then pass only its ARN through
`openai_api_key_secret_arn`. Do not put the secret value in `.tfvars`, command
history, GitHub Actions variables, or Terraform state. If a customer-managed KMS
key protects the secret, also grant the ECS execution role `kms:Decrypt` for that
key.

RDS-managed password rotation does not refresh an environment variable inside
an already-running task. After rotation, force a new ECS deployment so new tasks
receive the current secret value. Production systems should automate that
redeployment or retrieve short-lived credentials at runtime.

## Tear down

For a disposable demo with `protect_data = false`:

```powershell
terraform destroy
```

ECR uses immutable tags and does not force-delete images. Remove retained images
explicitly before destroying the repository. Material deletion is deliberately
not automated by this project.

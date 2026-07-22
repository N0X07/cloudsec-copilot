output "ecr_repository_url" {
  description = "Push the application image to this ECR repository."
  value       = aws_ecr_repository.app.repository_url
}

output "application_url" {
  description = "Load balancer URL. It becomes healthy after container_image is deployed."
  value = format(
    "%s://%s",
    var.certificate_arn == "" ? "http" : "https",
    aws_lb.api.dns_name
  )
}

output "database_endpoint" {
  description = "Private RDS endpoint, reachable only from the API security group."
  value       = aws_db_instance.main.endpoint
}

output "database_secret_arn" {
  description = "RDS-managed Secrets Manager ARN; the password is not in this output."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "service_deployed" {
  description = "False until a non-empty container_image is supplied."
  value       = var.container_image != ""
}

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

output "cloudwatch_log_group_name" {
  description = "Application log group for ECS tasks."
  value       = aws_cloudwatch_log_group.api.name
}

output "alb_5xx_alarm_name" {
  description = "CloudWatch alarm for ALB 5XX responses."
  value       = aws_cloudwatch_metric_alarm.alb_5xx.alarm_name
}

output "ecs_running_tasks_alarm_name" {
  description = "CloudWatch alarm for ECS running task count. Null until the service is deployed."
  value       = var.container_image == "" ? null : aws_cloudwatch_metric_alarm.ecs_running_tasks[0].alarm_name
}

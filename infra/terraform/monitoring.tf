resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${local.name}-alb-5xx"
  alarm_description   = "ALB is returning 5XX responses for CloudSec Copilot."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  threshold           = 1
  period              = 60
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_ELB_5XX_Count"

  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_running_tasks" {
  count = var.container_image == "" ? 0 : 1

  alarm_name          = "${local.name}-ecs-running-tasks"
  alarm_description   = "ECS service is running fewer tasks than expected."
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  threshold           = var.desired_count
  period              = 60
  statistic           = "Average"
  treat_missing_data  = "breaching"
  namespace           = "ECS/ContainerInsights"
  metric_name         = "RunningTaskCount"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.api[0].name
  }
}

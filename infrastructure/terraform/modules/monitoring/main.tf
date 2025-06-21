resource "aws_sns_topic" "alarms" {
  name = "${var.project_name}-alarms"
  
  tags = {
    Name        = "${var.project_name}-alarms"
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "alarm_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "backend_cpu_high" {
  alarm_name          = "${var.project_name}-backend-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors backend CPU utilization"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  
  dimensions = {
    ClusterName = var.backend_cluster_arn
    ServiceName = "${var.project_name}-backend-service"
  }
  
  tags = {
    Name        = "${var.project_name}-backend-cpu-alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "backend_memory_high" {
  alarm_name          = "${var.project_name}-backend-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors backend memory utilization"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  
  dimensions = {
    ClusterName = var.backend_cluster_arn
    ServiceName = "${var.project_name}-backend-service"
  }
  
  tags = {
    Name        = "${var.project_name}-backend-memory-alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average" }],
            [".", "MemoryUtilization", { stat = "Average" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Backend Resource Utilization"
          period  = 300
        }
      }
    ]
  })
}

data "aws_region" "current" {}
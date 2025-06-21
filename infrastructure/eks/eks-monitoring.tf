# EKS CloudWatch Container Insights and PagerDuty Integration
# This file adds comprehensive monitoring for the EKS cluster with PagerDuty alerts

# Reference existing CloudWatch Log Groups created by EKS
data "aws_cloudwatch_log_group" "eks_cluster" {
  name = "/aws/eks/${var.project_name}-eks/cluster"
}

# Create additional log groups for Container Insights if they don't exist
resource "aws_cloudwatch_log_group" "eks_application" {
  name              = "/aws/containerinsights/${var.project_name}-eks/application"
  retention_in_days = 7
  
  lifecycle {
    ignore_changes = [name]
    prevent_destroy = true
  }
  
  tags = {
    Name        = "${var.project_name}-eks-application-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "eks_host" {
  name              = "/aws/containerinsights/${var.project_name}-eks/host"
  retention_in_days = 7
  
  lifecycle {
    ignore_changes = [name]
    prevent_destroy = true
  }
  
  tags = {
    Name        = "${var.project_name}-eks-host-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "eks_dataplane" {
  name              = "/aws/containerinsights/${var.project_name}-eks/dataplane"
  retention_in_days = 7
  
  lifecycle {
    ignore_changes = [name]
    prevent_destroy = true
  }
  
  tags = {
    Name        = "${var.project_name}-eks-dataplane-logs"
    Environment = var.environment
  }
}

# SNS Topic for EKS Alerts (separate from ECS)
resource "aws_sns_topic" "eks_alerts" {
  name = "${var.project_name}-eks-alerts"
  
  tags = {
    Name        = "${var.project_name}-eks-alerts"
    Environment = var.environment
  }
}

# SNS Topic Policy for CloudWatch
resource "aws_sns_topic_policy" "eks_alerts" {
  arn = aws_sns_topic.eks_alerts.arn
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchAlarmsToPublish"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action = [
          "sns:Publish",
          "sns:GetTopicAttributes",
          "sns:SetTopicAttributes",
          "sns:AddPermission",
          "sns:RemovePermission",
          "sns:DeleteTopic",
          "sns:Subscribe",
          "sns:ListSubscriptionsByTopic",
          "sns:Publish",
          "sns:Receive"
        ]
        Resource = aws_sns_topic.eks_alerts.arn
      }
    ]
  })
}

# PagerDuty Integration (placeholder - add your PagerDuty endpoint)
resource "aws_sns_topic_subscription" "pagerduty" {
  count     = var.pagerduty_endpoint != "" ? 1 : 0
  topic_arn = aws_sns_topic.eks_alerts.arn
  protocol  = "https"
  endpoint  = var.pagerduty_endpoint
}

# Email subscription for testing
resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.eks_alerts.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# CloudWatch Alarms for EKS

# 1. High CPU Usage Alarm
resource "aws_cloudwatch_metric_alarm" "eks_cpu_high" {
  alarm_name          = "${var.project_name}-eks-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "cluster_cpu_utilization"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "EKS cluster CPU utilization is above 80%"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ClusterName = module.eks.cluster_name
  }
  
  tags = {
    Name        = "${var.project_name}-eks-cpu-alarm"
    Environment = var.environment
    Severity    = "High"
  }
}

# 2. High Memory Usage Alarm
resource "aws_cloudwatch_metric_alarm" "eks_memory_high" {
  alarm_name          = "${var.project_name}-eks-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "cluster_memory_utilization"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "EKS cluster memory utilization is above 80%"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ClusterName = module.eks.cluster_name
  }
  
  tags = {
    Name        = "${var.project_name}-eks-memory-alarm"
    Environment = var.environment
    Severity    = "High"
  }
}

# 3. Pod Restart Rate Alarm
resource "aws_cloudwatch_metric_alarm" "eks_pod_restarts" {
  alarm_name          = "${var.project_name}-eks-pod-restarts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "pod_restart_total"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "High pod restart rate detected in EKS cluster"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ClusterName = module.eks.cluster_name
  }
  
  tags = {
    Name        = "${var.project_name}-eks-restart-alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# 4. Node Not Ready Alarm
resource "aws_cloudwatch_metric_alarm" "eks_node_not_ready" {
  alarm_name          = "${var.project_name}-eks-node-not-ready"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "cluster_node_count"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Average"
  threshold           = "2"  # Adjust based on your min_size
  alarm_description   = "EKS nodes are not in ready state"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "breaching"
  
  dimensions = {
    ClusterName = module.eks.cluster_name
  }
  
  tags = {
    Name        = "${var.project_name}-eks-node-alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# 5. Failed Pod Alarm
resource "aws_cloudwatch_metric_alarm" "eks_failed_pods" {
  alarm_name          = "${var.project_name}-eks-failed-pods"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "pod_number_of_container_restarts"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "3"
  alarm_description   = "Pods are failing repeatedly in EKS cluster"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ClusterName = module.eks.cluster_name
  }
  
  tags = {
    Name        = "${var.project_name}-eks-failed-pods-alarm"
    Environment = var.environment
    Severity    = "High"
  }
}

# 6. Container Resource Alarm (OOM Detection)
resource "aws_cloudwatch_metric_alarm" "eks_container_memory" {
  alarm_name          = "${var.project_name}-eks-container-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "container_memory_utilization"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "90"
  alarm_description   = "Container memory utilization is critically high"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ClusterName = module.eks.cluster_name
  }
  
  tags = {
    Name        = "${var.project_name}-eks-container-memory-alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# CloudWatch Dashboard for EKS
resource "aws_cloudwatch_dashboard" "eks_dashboard" {
  dashboard_name = "${var.project_name}-eks-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        x      = 0
        y      = 0
        
        properties = {
          metrics = [
            ["ContainerInsights", "cluster_cpu_utilization", "ClusterName", module.eks.cluster_name],
            [".", "cluster_memory_utilization", ".", "."],
            [".", "cluster_node_count", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "EKS Cluster Overview"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        x      = 0
        y      = 6
        
        properties = {
          metrics = [
            ["ContainerInsights", "pod_restart_total", "ClusterName", module.eks.cluster_name],
            [".", "pod_number_of_container_restarts", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Pod Restart Metrics"
          period  = 300
        }
      },
      {
        type   = "log"
        width  = 24
        height = 6
        x      = 0
        y      = 12
        
        properties = {
          query   = "SOURCE '/aws/containerinsights/${module.eks.cluster_name}/application' | fields @timestamp, @message | filter @message like /ERROR|FATAL|CrashLoopBackOff|ImagePullBackOff|OOMKilled/ | sort @timestamp desc | limit 100"
          region  = var.aws_region
          title   = "EKS Error Logs"
          view    = "table"
        }
      }
    ]
  })
}
# Aggressive CloudWatch monitoring for EKS
# This configuration ensures ANY pod issues trigger immediate alerts

# Metric filters for detecting pod issues
resource "aws_cloudwatch_log_metric_filter" "pod_errors" {
  name           = "PodErrors"
  log_group_name = aws_cloudwatch_log_group.eks_application.name
  pattern        = "[time, request_id, event_type, pod_name, error_msg = \"*Error*\" || error_msg = \"*Failed*\" || error_msg = \"*CrashLoop*\" || error_msg = \"*BackOff*\"]"

  metric_transformation {
    name      = "PodErrors"
    namespace = "EKS/CustomMetrics"
    value     = "1"
    default_value = "0"
  }

  depends_on = [aws_cloudwatch_log_group.eks_application]
}

resource "aws_cloudwatch_log_metric_filter" "image_pull_errors" {
  name           = "ImagePullErrors"
  log_group_name = aws_cloudwatch_log_group.eks_application.name
  pattern        = "[time, request_id, event_type, pod_name, error_msg = \"*ImagePull*\" || error_msg = \"*ErrImagePull*\"]"

  metric_transformation {
    name      = "ImagePullErrors"
    namespace = "EKS/CustomMetrics"
    value     = "1"
    default_value = "0"
  }

  depends_on = [aws_cloudwatch_log_group.eks_application]
}

resource "aws_cloudwatch_log_metric_filter" "oom_kills" {
  name           = "OOMKills"
  log_group_name = aws_cloudwatch_log_group.eks_application.name
  pattern        = "[time, request_id, event_type, pod_name, error_msg = \"*OOMKilled*\" || error_msg = \"*memory*\"]"

  metric_transformation {
    name      = "OOMKills"
    namespace = "EKS/CustomMetrics"
    value     = "1"
    default_value = "0"
  }

  depends_on = [aws_cloudwatch_log_group.eks_application]
}

resource "aws_cloudwatch_log_metric_filter" "all_pod_issues" {
  name           = "AllPodIssues"
  log_group_name = aws_cloudwatch_log_group.eks_application.name
  pattern        = "{ ($.reason = \"Failed\" || $.reason = \"BackOff\" || $.reason = \"CrashLoopBackOff\" || $.reason = \"Error\" || $.reason = \"OOMKilled\" || $.reason = \"ImagePullBackOff\" || $.reason = \"ErrImagePull\" || $.reason = \"InvalidImageName\" || $.reason = \"CreateContainerConfigError\" || $.reason = \"CreateContainerError\" || $.reason = \"Killing\" || $.reason = \"Unhealthy\") }"

  metric_transformation {
    name      = "AllPodIssues"
    namespace = "EKS/Instant"
    value     = "1"
    default_value = "0"
  }

  depends_on = [aws_cloudwatch_log_group.eks_application]
}

resource "aws_cloudwatch_log_metric_filter" "stderr_logs" {
  name           = "StderrLogs"
  log_group_name = aws_cloudwatch_log_group.eks_application.name
  pattern        = "{ $.stream = \"stderr\" }"

  metric_transformation {
    name      = "StderrLogs"
    namespace = "EKS/Instant"
    value     = "1"
    default_value = "0"
  }

  depends_on = [aws_cloudwatch_log_group.eks_application]
}

# Aggressive alarms that trigger immediately
resource "aws_cloudwatch_metric_alarm" "any_pod_error" {
  alarm_name          = "eks-any-pod-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "PodErrors"
  namespace           = "EKS/CustomMetrics"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Any pod error detected in EKS"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"

  depends_on = [aws_cloudwatch_log_metric_filter.pod_errors]
}

resource "aws_cloudwatch_metric_alarm" "image_pull_error" {
  alarm_name          = "eks-image-pull-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "ImagePullErrors"
  namespace           = "EKS/CustomMetrics"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Image pull error detected in EKS"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"

  depends_on = [aws_cloudwatch_log_metric_filter.image_pull_errors]
}

resource "aws_cloudwatch_metric_alarm" "oom_kill" {
  alarm_name          = "eks-oom-kill"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "OOMKills"
  namespace           = "EKS/CustomMetrics"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "OOM kill detected in EKS"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"

  depends_on = [aws_cloudwatch_log_metric_filter.oom_kills]
}

resource "aws_cloudwatch_metric_alarm" "instant_pod_issue" {
  alarm_name          = "eks-instant-pod-issue"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "AllPodIssues"
  namespace           = "EKS/Instant"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "INSTANT: Any pod issue in EKS"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"

  depends_on = [aws_cloudwatch_log_metric_filter.all_pod_issues]
}

resource "aws_cloudwatch_metric_alarm" "instant_stderr_logs" {
  alarm_name          = "eks-instant-stderr-logs"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "StderrLogs"
  namespace           = "EKS/Instant"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "INSTANT: Stderr logs detected"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"

  depends_on = [aws_cloudwatch_log_metric_filter.stderr_logs]
}

resource "aws_cloudwatch_metric_alarm" "problem_pods_detected" {
  alarm_name          = "eks-problem-pods-detected"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "ProblemPods"
  namespace           = "EKS/PodMonitoring"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Problem pods detected in EKS cluster"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    Cluster = module.eks.cluster_name
  }
}

# Composite alarm that triggers on ANY issue
resource "aws_cloudwatch_composite_alarm" "any_issue" {
  alarm_name          = "eks-any-issue-composite"
  alarm_description   = "Triggers on ANY issue in EKS cluster"
  alarm_actions       = [aws_sns_topic.eks_alerts.arn]

  alarm_rule = join(" OR ", [
    "ALARM('${aws_cloudwatch_metric_alarm.any_pod_error.alarm_name}')",
    "ALARM('${aws_cloudwatch_metric_alarm.image_pull_error.alarm_name}')",
    "ALARM('${aws_cloudwatch_metric_alarm.oom_kill.alarm_name}')",
    "ALARM('${aws_cloudwatch_metric_alarm.problem_pods_detected.alarm_name}')"
  ])

  depends_on = [
    aws_cloudwatch_metric_alarm.any_pod_error,
    aws_cloudwatch_metric_alarm.image_pull_error,
    aws_cloudwatch_metric_alarm.oom_kill,
    aws_cloudwatch_metric_alarm.problem_pods_detected
  ]
}

# EventBridge rule for pod issues
resource "aws_cloudwatch_event_rule" "pod_issues" {
  name        = "eks-pod-issues"
  description = "Capture any pod issues in EKS"

  event_pattern = jsonencode({
    source      = ["aws.eks"]
    detail-type = ["EKS Pod State Change"]
    detail = {
      status = ["Failed", "Unknown", "Pending"]
      reason = ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "OOMKilled"]
    }
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.pod_issues.name
  target_id = "1"
  arn       = aws_sns_topic.eks_alerts.arn
}

# EventBridge rule for EKS API errors
resource "aws_cloudwatch_event_rule" "eks_api_issues" {
  name        = "eks-api-issues"
  description = "Detect EKS API calls indicating issues"

  event_pattern = jsonencode({
    source = ["aws.eks"]
    detail = {
      eventSource = ["eks.amazonaws.com"]
      eventName   = ["UpdateNodegroupConfig", "DeleteNodegroup", "UpdateClusterConfig"]
      errorCode   = [{ exists = true }]
    }
  })
}

resource "aws_cloudwatch_event_target" "eks_api_sns" {
  rule      = aws_cloudwatch_event_rule.eks_api_issues.name
  target_id = "1"
  arn       = aws_sns_topic.eks_alerts.arn
}

# Monitoring namespace config for focused monitoring
resource "kubernetes_config_map" "cloudwatch_namespace_config" {
  metadata {
    name      = "cloudwatch-namespace-config"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
  }

  data = {
    "cwagentconfig.json" = jsonencode({
      logs = {
        metrics_collected = {
          kubernetes = {
            cluster_name                 = module.eks.cluster_name
            metrics_collection_interval  = 60
            namespace_name              = "fuck-kubernetes-test"
          }
        }
      }
      metrics = {
        namespace = "EKS/NamespaceMetrics"
        metrics_collected = {
          cpu = {
            measurement = ["cpu_usage_idle", "cpu_usage_iowait"]
            metrics_collection_interval = 60
          }
          disk = {
            measurement = ["used_percent"]
            metrics_collection_interval = 60
            resources = ["*"]
          }
          diskio = {
            measurement = ["io_time"]
            metrics_collection_interval = 60
            resources = ["*"]
          }
          mem = {
            measurement = ["mem_used_percent"]
            metrics_collection_interval = 60
          }
          net = {
            measurement = ["bytes_sent", "bytes_recv"]
            metrics_collection_interval = 60
            resources = ["*"]
          }
          netstat = {
            measurement = ["tcp_established"]
            metrics_collection_interval = 60
          }
        }
      }
    })
  }

  depends_on = [
    kubernetes_namespace.amazon_cloudwatch,
    module.eks
  ]
}

# ConfigMap for monitoring script
resource "kubernetes_config_map" "monitor_script" {
  metadata {
    name      = "monitor-script"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
  }

  data = {
    "monitor.sh" = <<-EOT
      #!/bin/bash
      while true; do
        # Check for any pods not in Running state
        PROBLEM_PODS=$(kubectl get pods --all-namespaces -o json | jq -r '.items[] | select(.status.phase != "Running" and .status.phase != "Succeeded") | "\(.metadata.namespace)/\(.metadata.name): \(.status.phase) - \(.status.reason // "Unknown")"')
        
        if [ -n "$PROBLEM_PODS" ]; then
          echo "$(date) - Problem pods detected:"
          echo "$PROBLEM_PODS"
          # Send custom metric
          aws cloudwatch put-metric-data \
            --namespace "EKS/PodMonitoring" \
            --metric-name "ProblemPods" \
            --value 1 \
            --dimensions Cluster=$CLUSTER_NAME
        fi
        
        # Check for restart counts
        kubectl get pods --all-namespaces -o json | jq -r '.items[] | select(.status.containerStatuses != null) | .status.containerStatuses[] | select(.restartCount > 0) | "\(.name): \(.restartCount) restarts"' | while read line; do
          if [ -n "$line" ]; then
            echo "$(date) - Container restarts: $line"
            aws cloudwatch put-metric-data \
              --namespace "EKS/PodMonitoring" \
              --metric-name "ContainerRestarts" \
              --value 1 \
              --dimensions Cluster=$CLUSTER_NAME
          fi
        done
        
        sleep 30
      done
    EOT
  }

  depends_on = [
    kubernetes_namespace.amazon_cloudwatch,
    module.eks
  ]
}

# Monitoring job
resource "kubernetes_job" "eks_monitor" {
  metadata {
    name      = "eks-monitor"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
  }

  spec {
    template {
      metadata {
        labels = {
          app = "eks-monitor"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.cloudwatch_agent.metadata[0].name
        
        container {
          name    = "monitor"
          image   = "amazon/aws-cli:latest"
          command = ["/bin/bash", "/scripts/monitor.sh"]

          env {
            name  = "CLUSTER_NAME"
            value = module.eks.cluster_name
          }

          env {
            name  = "AWS_DEFAULT_REGION"
            value = var.aws_region
          }

          volume_mount {
            name       = "monitor-script"
            mount_path = "/scripts"
          }
        }

        volume {
          name = "monitor-script"
          config_map {
            name         = kubernetes_config_map.monitor_script.metadata[0].name
            default_mode = "0755"
          }
        }

        restart_policy = "OnFailure"
      }
    }
  }

  depends_on = [
    kubernetes_config_map.monitor_script,
    kubernetes_service_account.cloudwatch_agent,
    module.eks
  ]
}
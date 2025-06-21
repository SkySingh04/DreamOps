# CloudWatch Container Insights Agent for EKS
# This deploys the CloudWatch agent to collect metrics from EKS

# IAM Role for CloudWatch Agent
resource "aws_iam_role" "cloudwatch_agent_role" {
  name = "${var.project_name}-cloudwatch-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = module.eks.oidc_provider_arn
        }
        Condition = {
          StringEquals = {
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub" = "system:serviceaccount:amazon-cloudwatch:cloudwatch-agent"
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-cloudwatch-agent-role"
    Environment = var.environment
  }
}

# Attach CloudWatch Agent Policy
resource "aws_iam_role_policy_attachment" "cloudwatch_agent_policy" {
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  role       = aws_iam_role.cloudwatch_agent_role.name
}

# Custom policy for Container Insights
resource "aws_iam_role_policy" "cloudwatch_agent_custom" {
  name = "${var.project_name}-cloudwatch-agent-custom"
  role = aws_iam_role.cloudwatch_agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups",
          "cloudwatch:PutMetricData",
          "ec2:DescribeVolumes",
          "ec2:DescribeTags",
          "autoscaling:DescribeAutoScalingGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# Kubernetes namespace for CloudWatch
resource "kubernetes_namespace" "amazon_cloudwatch" {
  metadata {
    name = "amazon-cloudwatch"
    labels = {
      name = "amazon-cloudwatch"
    }
  }
  
  depends_on = [module.eks]
}

# Service Account for CloudWatch Agent
resource "kubernetes_service_account" "cloudwatch_agent" {
  metadata {
    name      = "cloudwatch-agent"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.cloudwatch_agent_role.arn
    }
  }
  
  depends_on = [module.eks]
}

# ConfigMap for CloudWatch Agent
resource "kubernetes_config_map" "cwagentconfig" {
  metadata {
    name      = "cwagentconfig"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
  }

  data = {
    # Proper Container Insights configuration for EKS
    "otel-config.yaml" = <<-EOT
      extensions:
        health_check:
        server:
          listen_address: 0.0.0.0:8888

      receivers:
        awscontainerinsightreceiver:
          collection_interval: 60s
          cluster_name: ${module.eks.cluster_name}
          add_service_as_attribute: true
          prefer_full_pod_name: true

      processors:
        batch/metrics:
          timeout: 60s

      exporters:
        awsemf/containerinsights:
          namespace: ContainerInsights
          log_group_name: '/aws/containerinsights/${module.eks.cluster_name}/performance'
          dimension_rollup_option: NoDimensionRollup
          metric_declarations:
            - dimensions: [[ClusterName]]
              metric_name_selectors:
                - pod_restart_total
                - pod_number_of_container_restarts
                - cluster_node_count
                - cluster_pod_count
                - cluster_failed_pod_count
                - pod_cpu_utilization
                - pod_memory_utilization
                - container_memory_utilization

      service:
        extensions: [health_check, server]
        pipelines:
          metrics:
            receivers: [awscontainerinsightreceiver]
            processors: [batch/metrics]
            exporters: [awsemf/containerinsights]
    EOT
  }
  
  depends_on = [module.eks]
}

# DaemonSet for CloudWatch Agent
resource "kubernetes_daemonset" "cloudwatch_agent" {
  metadata {
    name      = "cloudwatch-agent"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
  }

  spec {
    selector {
      match_labels = {
        name = "cloudwatch-agent"
      }
    }

    template {
      metadata {
        labels = {
          name = "cloudwatch-agent"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.cloudwatch_agent.metadata[0].name
        
        container {
          name  = "cloudwatch-agent"
          image = "public.ecr.aws/cloudwatch-agent/cloudwatch-agent:latest"
          
          resources {
            limits = {
              cpu    = "200m"
              memory = "200Mi"
            }
            requests = {
              cpu    = "200m"  
              memory = "200Mi"
            }
          }

          # Container Insights specific configuration
          args = ["-config=/etc/cwagentconfig/otel-config.yaml"]

          env {
            name = "HOST_IP"
            value_from {
              field_ref {
                field_path = "status.hostIP"
              }
            }
          }

          env {
            name = "HOST_NAME"
            value_from {
              field_ref {
                field_path = "spec.nodeName"
              }
            }
          }

          env {
            name = "K8S_NAMESPACE"
            value_from {
              field_ref {
                field_path = "metadata.namespace"
              }
            }
          }

          env {
            name = "CI_VERSION"
            value = "k8s/1.3.11"
          }

          volume_mount {
            name       = "cwagentconfig"
            mount_path = "/etc/cwagentconfig"
          }

          volume_mount {
            name       = "rootfs"
            mount_path = "/rootfs"
            read_only  = true
          }

          volume_mount {
            name       = "dockersock"
            mount_path = "/var/run/docker.sock"
            read_only  = true
          }

          volume_mount {
            name       = "varlibdocker"
            mount_path = "/var/lib/docker"
            read_only  = true
          }

          volume_mount {
            name       = "containerdsock"
            mount_path = "/run/containerd/containerd.sock"
            read_only  = true
          }

          volume_mount {
            name       = "sys"
            mount_path = "/sys"
            read_only  = true
          }

          volume_mount {
            name       = "devdisk"
            mount_path = "/dev/disk"
            read_only  = true
          }
        }

        volume {
          name = "cwagentconfig"
          config_map {
            name = kubernetes_config_map.cwagentconfig.metadata[0].name
          }
        }

        volume {
          name = "rootfs"
          host_path {
            path = "/"
          }
        }

        volume {
          name = "dockersock"
          host_path {
            path = "/var/run/docker.sock"
          }
        }

        volume {
          name = "varlibdocker"
          host_path {
            path = "/var/lib/docker"
          }
        }

        volume {
          name = "containerdsock"
          host_path {
            path = "/run/containerd/containerd.sock"
          }
        }

        volume {
          name = "sys"
          host_path {
            path = "/sys"
          }
        }

        volume {
          name = "devdisk"
          host_path {
            path = "/dev/disk/"
          }
        }

        termination_grace_period_seconds = 60
      }
    }
  }
  
  depends_on = [
    module.eks,
    kubernetes_config_map.cwagentconfig,
    kubernetes_service_account.cloudwatch_agent
  ]
}

# ClusterRole for CloudWatch Agent
resource "kubernetes_cluster_role" "cloudwatch_agent" {
  metadata {
    name = "cloudwatch-agent-role"
  }

  rule {
    api_groups = [""]
    resources = [
      "nodes",
      "nodes/proxy",
      "nodes/stats",
      "services",
      "endpoints",
      "pods",
      "pods/proxy"
    ]
    verbs = ["get", "list"]
  }

  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "update"]
  }

  rule {
    api_groups = [""]
    resources = [
      "nodes/stats",
      "configmaps",
      "events"
    ]
    verbs = ["create"]
  }

  rule {
    api_groups     = [""]
    resources      = ["configmaps"]
    resource_names = ["cwagent-clusterleader"]
    verbs          = ["get", "update"]
  }

  depends_on = [module.eks]
}

# ClusterRoleBinding for CloudWatch Agent
resource "kubernetes_cluster_role_binding" "cloudwatch_agent" {
  metadata {
    name = "cloudwatch-agent-role-binding"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.cloudwatch_agent.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.cloudwatch_agent.metadata[0].name
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
  }

  depends_on = [
    module.eks,
    kubernetes_cluster_role.cloudwatch_agent,
    kubernetes_service_account.cloudwatch_agent
  ]
}
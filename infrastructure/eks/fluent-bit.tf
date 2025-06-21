# Fluent Bit for EKS Container Insights
# This deploys Fluent Bit to send logs to CloudWatch

# IAM Role for Fluent Bit
resource "aws_iam_role" "fluent_bit_role" {
  name = "${var.project_name}-fluent-bit-role"

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
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub" = "system:serviceaccount:amazon-cloudwatch:fluent-bit"
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-fluent-bit-role"
    Environment = var.environment
  }
}

# Custom policy for Fluent Bit
resource "aws_iam_role_policy" "fluent_bit_policy" {
  name = "${var.project_name}-fluent-bit-policy"
  role = aws_iam_role.fluent_bit_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Service Account for Fluent Bit
resource "kubernetes_service_account" "fluent_bit" {
  metadata {
    name      = "fluent-bit"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.fluent_bit_role.arn
    }
  }
  
  depends_on = [module.eks]
}

# ClusterRole for Fluent Bit
resource "kubernetes_cluster_role" "fluent_bit" {
  metadata {
    name = "fluent-bit-role"
  }

  rule {
    api_groups = [""]
    resources  = ["namespaces", "pods", "pods/logs", "nodes", "nodes/proxy"]
    verbs      = ["get", "list", "watch"]
  }
}

# ClusterRoleBinding for Fluent Bit
resource "kubernetes_cluster_role_binding" "fluent_bit" {
  metadata {
    name = "fluent-bit-role-binding"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.fluent_bit.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.fluent_bit.metadata[0].name
    namespace = kubernetes_service_account.fluent_bit.metadata[0].namespace
  }
}

# ConfigMap for Fluent Bit configuration
resource "kubernetes_config_map" "fluent_bit_config" {
  metadata {
    name      = "fluent-bit-config"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
    labels = {
      k8s-app = "fluent-bit"
    }
  }

  data = {
    "fluent-bit.conf" = <<-EOT
      [SERVICE]
          Flush                     5
          Grace                     30
          Log_Level                 info
          Daemon                    off
          Parsers_File              parsers.conf
          HTTP_Server               On
          HTTP_Listen               0.0.0.0
          HTTP_Port                 2020
          storage.path              /var/fluent-bit/state/flb-storage/
          storage.sync              normal
          storage.checksum          off
          storage.backlog.mem_limit 5M

      @INCLUDE application-log.conf
      @INCLUDE dataplane-log.conf
      @INCLUDE host-log.conf
    EOT

    "application-log.conf" = <<-EOT
      [INPUT]
          Name                tail
          Tag                 application.*
          Exclude_Path        /var/log/containers/cloudwatch-agent*, /var/log/containers/fluent-bit*, /var/log/containers/aws-node*, /var/log/containers/kube-proxy*
          Path                /var/log/containers/*.log
          Docker_Mode         On
          Docker_Mode_Flush   5
          Docker_Mode_Parser  container_firstline
          Parser              docker
          DB                  /var/fluent-bit/state/flb_container.db
          Mem_Buf_Limit       50MB
          Skip_Long_Lines     On
          Refresh_Interval    10
          Rotate_Wait         30
          storage.type        filesystem
          Read_from_Head      $${READ_FROM_HEAD}

      [INPUT]
          Name                tail
          Tag                 application.*
          Path                /var/log/containers/fluent-bit*
          Parser              docker
          DB                  /var/fluent-bit/state/flb_log.db
          Mem_Buf_Limit       5MB
          Skip_Long_Lines     On
          Refresh_Interval    10
          Read_from_Head      $${READ_FROM_HEAD}

      [INPUT]
          Name                tail
          Tag                 application.*
          Path                /var/log/containers/cloudwatch-agent*
          Docker_Mode         On
          Docker_Mode_Flush   5
          Docker_Mode_Parser  cwagent_firstline
          Parser              docker
          DB                  /var/fluent-bit/state/flb_cwagent.db
          Mem_Buf_Limit       5MB
          Skip_Long_Lines     On
          Refresh_Interval    10
          Read_from_Head      $${READ_FROM_HEAD}

      [FILTER]
          Name                kubernetes
          Match               application.*
          Kube_URL            https://kubernetes.default.svc:443
          Kube_Tag_Prefix     application.var.log.containers.
          Merge_Log           On
          Merge_Log_Key       log_processed
          K8S-Logging.Parser  On
          K8S-Logging.Exclude Off
          Labels              Off
          Annotations         Off
          Use_Kubelet         On
          Kubelet_Port        10250
          Buffer_Size         0

      [OUTPUT]
          Name                cloudwatch_logs
          Match               application.*
          region              $${AWS_REGION}
          log_group_name      /aws/containerinsights/$${CLUSTER_NAME}/application
          log_stream_prefix   $${HOST_NAME}-
          auto_create_group   On
          extra_user_agent    container-insights
    EOT

    "dataplane-log.conf" = <<-EOT
      [INPUT]
          Name                systemd
          Tag                 dataplane.systemd.*
          Systemd_Filter      _SYSTEMD_UNIT=docker.service
          Systemd_Filter      _SYSTEMD_UNIT=containerd.service
          Systemd_Filter      _SYSTEMD_UNIT=kubelet.service
          DB                  /var/fluent-bit/state/systemd.db
          Path                /var/log/journal
          Read_From_Tail      $${READ_FROM_TAIL}

      [INPUT]
          Name                tail
          Tag                 dataplane.tail.*
          Path                /var/log/containers/aws-node*, /var/log/containers/kube-proxy*
          Docker_Mode         On
          Docker_Mode_Flush   5
          Docker_Mode_Parser  container_firstline
          Parser              docker
          DB                  /var/fluent-bit/state/flb_dataplane_tail.db
          Mem_Buf_Limit       50MB
          Skip_Long_Lines     On
          Refresh_Interval    10
          Rotate_Wait         30
          storage.type        filesystem
          Read_from_Head      $${READ_FROM_HEAD}

      [FILTER]
          Name                modify
          Match               dataplane.systemd.*
          Rename              _HOSTNAME                   hostname
          Rename              _SYSTEMD_UNIT               systemd_unit
          Rename              MESSAGE                     message
          Remove_regex        ^((?!hostname|systemd_unit|message).)*$

      [FILTER]
          Name                aws
          Match               dataplane.*
          imds_version        v1

      [OUTPUT]
          Name                cloudwatch_logs
          Match               dataplane.*
          region              $${AWS_REGION}
          log_group_name      /aws/containerinsights/$${CLUSTER_NAME}/dataplane
          log_stream_prefix   $${HOST_NAME}-
          auto_create_group   On
          extra_user_agent    container-insights
    EOT

    "host-log.conf" = <<-EOT
      [INPUT]
          Name                tail
          Tag                 host.dmesg
          Path                /var/log/dmesg
          Parser              syslog
          DB                  /var/fluent-bit/state/flb_dmesg.db
          Mem_Buf_Limit       5MB
          Skip_Long_Lines     On
          Refresh_Interval    10
          Read_from_Head      $${READ_FROM_HEAD}

      [INPUT]
          Name                tail
          Tag                 host.messages
          Path                /var/log/messages
          Parser              syslog
          DB                  /var/fluent-bit/state/flb_messages.db
          Mem_Buf_Limit       5MB
          Skip_Long_Lines     On
          Refresh_Interval    10
          Read_from_Head      $${READ_FROM_HEAD}

      [INPUT]
          Name                tail
          Tag                 host.secure
          Path                /var/log/secure
          Parser              syslog
          DB                  /var/fluent-bit/state/flb_secure.db
          Mem_Buf_Limit       5MB
          Skip_Long_Lines     On
          Refresh_Interval    10
          Read_from_Head      $${READ_FROM_HEAD}

      [FILTER]
          Name                aws
          Match               host.*
          imds_version        v1

      [OUTPUT]
          Name                cloudwatch_logs
          Match               host.*
          region              $${AWS_REGION}
          log_group_name      /aws/containerinsights/$${CLUSTER_NAME}/host
          log_stream_prefix   $${HOST_NAME}-
          auto_create_group   On
          extra_user_agent    container-insights
    EOT

    "parsers.conf" = <<-EOT
      [PARSER]
          Name                docker
          Format              json
          Time_Key            time
          Time_Format         %Y-%m-%dT%H:%M:%S.%LZ

      [PARSER]
          Name                syslog
          Format              regex
          Regex               ^(?<time>[^ ]* {1,2}[^ ]* [^ ]*) (?<host>[^ ]*) (?<ident>[a-zA-Z0-9_\/\.\-]*)(?:\[(?<pid>[0-9]+)\])?(?:[^\:]*\:)? *(?<message>.*)$
          Time_Key            time
          Time_Format         %b %d %H:%M:%S

      [PARSER]
          Name                container_firstline
          Format              regex
          Regex               (?<log>(?<="log":")\S(?!\.).*?)(?<!\\)".*(?<stream>(?<="stream":").*?)".*(?<time>\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2}:\d{2}\.\w*).*(?=})
          Time_Key            time
          Time_Format         %Y-%m-%dT%H:%M:%S.%LZ

      [PARSER]
          Name                cwagent_firstline
          Format              regex
          Regex               (?<log>(?<="log":")\d{4}[\/-]\d{1,2}[\/-]\d{1,2}[ T]\d{2}:\d{2}:\d{2}(?!\.).*?)(?<!\\)".*(?<stream>(?<="stream":").*?)".*(?<time>\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2}:\d{2}\.\w*).*(?=})
          Time_Key            time
          Time_Format         %Y-%m-%dT%H:%M:%S.%LZ
    EOT
  }
  
  depends_on = [module.eks]
}

# DaemonSet for Fluent Bit
resource "kubernetes_daemonset" "fluent_bit" {
  metadata {
    name      = "fluent-bit"
    namespace = kubernetes_namespace.amazon_cloudwatch.metadata[0].name
    labels = {
      k8s-app                         = "fluent-bit"
      version                         = "v1"
      "kubernetes.io/cluster-service" = "true"
    }
  }

  spec {
    selector {
      match_labels = {
        k8s-app = "fluent-bit"
      }
    }

    template {
      metadata {
        labels = {
          k8s-app                         = "fluent-bit"
          version                         = "v1"
          "kubernetes.io/cluster-service" = "true"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.fluent_bit.metadata[0].name
        
        container {
          name  = "fluent-bit"
          image = "public.ecr.aws/aws-observability/aws-for-fluent-bit:stable"
          
          env {
            name  = "AWS_REGION"
            value = var.aws_region
          }

          env {
            name  = "CLUSTER_NAME"
            value = module.eks.cluster_name
          }

          env {
            name = "HTTP_SERVER"
            value = "On"
          }

          env {
            name = "HTTP_PORT"
            value = "2020"
          }

          env {
            name = "READ_FROM_HEAD"
            value = "Off"
          }

          env {
            name = "READ_FROM_TAIL"
            value = "On"
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
            name = "CI_VERSION"
            value = "k8s/1.3.11"
          }

          resources {
            limits = {
              memory = "200Mi"
            }
            requests = {
              cpu    = "500m"
              memory = "100Mi"
            }
          }

          volume_mount {
            name       = "fluentbitstate"
            mount_path = "/var/fluent-bit/state"
          }

          volume_mount {
            name       = "varlog"
            mount_path = "/var/log"
            read_only  = true
          }

          volume_mount {
            name       = "varlibdockercontainers"
            mount_path = "/var/lib/docker/containers"
            read_only  = true
          }

          volume_mount {
            name       = "fluent-bit-config"
            mount_path = "/fluent-bit/etc/"
          }

          volume_mount {
            name       = "runlogjournal"
            mount_path = "/run/log/journal"
            read_only  = true
          }

          volume_mount {
            name       = "dmesg"
            mount_path = "/var/log/dmesg"
            read_only  = true
          }
        }

        volume {
          name = "fluentbitstate"
          host_path {
            path = "/var/fluent-bit/state"
          }
        }

        volume {
          name = "varlog"
          host_path {
            path = "/var/log"
          }
        }

        volume {
          name = "varlibdockercontainers"
          host_path {
            path = "/var/lib/docker/containers"
          }
        }

        volume {
          name = "fluent-bit-config"
          config_map {
            name = kubernetes_config_map.fluent_bit_config.metadata[0].name
          }
        }

        volume {
          name = "runlogjournal"
          host_path {
            path = "/run/log/journal"
          }
        }

        volume {
          name = "dmesg"
          host_path {
            path = "/var/log/dmesg"
          }
        }

        termination_grace_period_seconds = 10
      }
    }
  }
  
  depends_on = [
    module.eks,
    kubernetes_config_map.fluent_bit_config,
    kubernetes_service_account.fluent_bit
  ]
}
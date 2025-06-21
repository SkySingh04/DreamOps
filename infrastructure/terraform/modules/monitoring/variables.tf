variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "backend_cluster_arn" {
  description = "ARN of the backend ECS cluster"
  type        = string
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
}
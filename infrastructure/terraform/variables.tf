variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "oncall-agent"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "anthropic_api_key_arn" {
  description = "ARN of the secret containing Anthropic API key"
  type        = string
}

variable "k8s_config_secret_arn" {
  description = "ARN of the secret containing Kubernetes config"
  type        = string
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
}
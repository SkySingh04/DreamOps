variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "anthropic_api_key_arn" {
  description = "ARN of the secret containing Anthropic API key"
  type        = string
}

variable "k8s_config_secret_arn" {
  description = "ARN of the secret containing Kubernetes config"
  type        = string
}
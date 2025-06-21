variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "oncall-agent"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "testing"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.1.0.0/16"
}
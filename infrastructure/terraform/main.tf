terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "oncall-agent-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source = "./modules/networking"
  
  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
}

module "backend" {
  source = "./modules/backend"
  
  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.networking.vpc_id
  private_subnet_ids    = module.networking.private_subnet_ids
  public_subnet_ids     = module.networking.public_subnet_ids
  anthropic_api_key_arn = var.anthropic_api_key_arn
  k8s_config_secret_arn = var.k8s_config_secret_arn
}

module "frontend" {
  source = "./modules/frontend"
  
  project_name = var.project_name
  environment  = var.environment
  api_url      = module.backend.api_url
}

module "monitoring" {
  source = "./modules/monitoring"
  
  project_name        = var.project_name
  environment         = var.environment
  backend_cluster_arn = module.backend.ecs_cluster_arn
  alarm_email         = var.alarm_email
}
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for GitHub Actions"
  value       = module.frontend.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = module.frontend.cloudfront_domain_name
}

output "api_url" {
  description = "Backend API URL for REACT_APP_API_URL"
  value       = module.backend.api_url
}

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = module.backend.ecr_repository_url
}

output "s3_bucket_name" {
  description = "Frontend S3 bucket name"
  value       = module.frontend.s3_bucket_name
}
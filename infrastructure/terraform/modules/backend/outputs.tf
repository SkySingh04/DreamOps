output "api_url" {
  description = "URL of the backend API"
  value       = "http://${aws_lb.backend.dns_name}"
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}
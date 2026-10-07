output "ecr_repository_url" {
  description = "Repository destination for the immutable Git SHA image."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "Phase 2 ECS cluster name."
  value       = aws_ecs_cluster.app.name
}

output "ecs_service_name" {
  description = "Smoke service name after deploy_service is enabled."
  value       = var.deploy_service ? aws_ecs_service.app[0].name : null
}

output "cloudwatch_log_group" {
  description = "Application log group with seven-day retention."
  value       = aws_cloudwatch_log_group.app.name
}

output "network_scope" {
  description = "Phase 2 networking limitation."
  value       = var.deploy_service ? "default VPC, public IP, no inbound rules, no NAT Gateway" : "networking not deployed"
}

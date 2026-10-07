variable "aws_region" {
  description = "Single explicit AWS region for the Phase 2 dev smoke deployment."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be an explicit AWS region such as eu-central-1."
  }
}

variable "owner_tag" {
  description = "Non-personal owner identifier applied to every supported resource."
  type        = string
  default     = "serviceflow-learning"
}

variable "deploy_service" {
  description = "Create the default-VPC networking, task definition, and one-task ECS service."
  type        = bool
  default     = false
}

variable "image_tag" {
  description = "Immutable full Git SHA tag already pushed to the ECR repository."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.image_tag == null || can(regex("^[0-9a-f]{40}$", var.image_tag))
    error_message = "image_tag must be a full 40-character lowercase Git SHA."
  }
}

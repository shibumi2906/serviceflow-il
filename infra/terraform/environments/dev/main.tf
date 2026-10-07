locals {
  name = "serviceflow-il-dev"
  common_tags = {
    Project     = "ServiceFlowIL"
    Environment = "dev"
    ManagedBy   = "Terraform"
    Owner       = var.owner_tag
  }
}

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_ecr_repository" "app" {
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name}"
  retention_in_days = 7
}

resource "aws_ecs_cluster" "app" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

data "aws_iam_policy_document" "ecs_execution" {
  statement {
    sid       = "EcrAuthorization"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "PullApplicationImage"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.app.arn]
  }

  statement {
    sid    = "WriteApplicationLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.app.arn}:*"]
  }
}

resource "aws_iam_role_policy" "ecs_execution" {
  name   = "${local.name}-pull-and-log"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.ecs_execution.json
}

data "aws_vpc" "default" {
  count   = var.deploy_service ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = var.deploy_service ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}

resource "aws_security_group" "task" {
  count = var.deploy_service ? 1 : 0

  name        = "${local.name}-task-egress"
  description = "Phase 2 task: no ingress, HTTPS and VPC DNS egress only"
  vpc_id      = data.aws_vpc.default[0].id

  tags = {
    Name = "${local.name}-task-egress"
  }
}

resource "aws_vpc_security_group_egress_rule" "https" {
  count = var.deploy_service ? 1 : 0

  security_group_id = aws_security_group.task[0].id
  description       = "ECR, image layers, and CloudWatch Logs over TLS"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "dns_udp" {
  count = var.deploy_service ? 1 : 0

  security_group_id = aws_security_group.task[0].id
  description       = "DNS to the default VPC resolver"
  cidr_ipv4         = "${cidrhost(data.aws_vpc.default[0].cidr_block, 2)}/32"
  from_port         = 53
  to_port           = 53
  ip_protocol       = "udp"
}

resource "aws_vpc_security_group_egress_rule" "dns_tcp" {
  count = var.deploy_service ? 1 : 0

  security_group_id = aws_security_group.task[0].id
  description       = "TCP fallback to the default VPC resolver"
  cidr_ipv4         = "${cidrhost(data.aws_vpc.default[0].cidr_block, 2)}/32"
  from_port         = 53
  to_port           = 53
  ip_protocol       = "tcp"
}

resource "aws_ecs_task_definition" "app" {
  count = var.deploy_service ? 1 : 0

  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name                   = "app"
      image                  = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
      essential              = true
      readonlyRootFilesystem = true
      user                   = "10001:10001"
      environment = [
        { name = "APP_MODE", value = "smoke" },
        { name = "APP_ENV", value = "production" },
        { name = "APP_DEBUG", value = "false" },
        { name = "LOG_LEVEL", value = "INFO" },
      ]
      portMappings = [
        {
          name          = "http"
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      linuxParameters = {
        initProcessEnabled = true
        capabilities = {
          drop = ["ALL"]
        }
      }
      healthCheck = {
        command = [
          "CMD-SHELL",
          "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).read()\"",
        ]
        interval    = 10
        timeout     = 3
        retries     = 3
        startPeriod = 5
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "app"
        }
      }
    }
  ])

  lifecycle {
    precondition {
      condition     = var.image_tag != null && can(regex("^[0-9a-f]{40}$", var.image_tag))
      error_message = "deploy_service requires image_tag to be a full immutable Git SHA."
    }
  }
}

resource "aws_ecs_service" "app" {
  count = var.deploy_service ? 1 : 0

  name                   = local.name
  cluster                = aws_ecs_cluster.app.id
  task_definition        = aws_ecs_task_definition.app[0].arn
  desired_count          = 1
  launch_type            = "FARGATE"
  platform_version       = "LATEST"
  enable_execute_command = false
  wait_for_steady_state  = true
  propagate_tags         = "SERVICE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    assign_public_ip = true
    security_groups  = [aws_security_group.task[0].id]
    subnets          = data.aws_subnets.default[0].ids
  }
}

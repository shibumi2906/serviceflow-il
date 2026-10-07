# Phase 2 architecture

```text
local Docker build
       |
       | immutable Git SHA tag
       v
Amazon ECR ----> ECS task execution role
                       |
                       v
              ECS Fargate service (1 task)
              APP_MODE=smoke, non-root
                       |
                       v
              CloudWatch Logs (7 days)
```

The task uses default-VPC subnets and a temporary public IPv4 address for outbound
ECR and CloudWatch access. Its security group has no ingress and allows only HTTPS
plus DNS egress. There is no ALB, RDS, S3, Secrets Manager, NAT Gateway, custom
VPC, or business persistence in this phase.

The deployment health check calls `/health/live` from inside the container.
`/health/ready` also returns 200 in smoke mode because that mode has no external
critical dependency. Full mode and all Phase 1 behavior remain available locally.

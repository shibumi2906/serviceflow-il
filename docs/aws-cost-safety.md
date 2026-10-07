# AWS cost safety

## Phase 2 status

Phase 1 remains local-only. Phase 2 adds Terraform for a reviewed temporary smoke
deployment, but no AWS resource may be created before its exact plan is approved.

Approximate Phase 2 cost drivers vary by region:

- one 0.25-vCPU/0.5-GiB Fargate task: roughly USD 0.01-0.02 per running hour;
- one public IPv4 address: roughly USD 0.005 per running hour;
- ECR storage: roughly USD 0.10 per GB-month;
- CloudWatch log ingestion and storage: normally cents for this small smoke test;
- ECR repository, ECS cluster, task definitions, IAM roles, and security group:
  no direct hourly charge.

A short verification should cost cents. Leaving the task continuously running can
cost roughly USD 10-15 per month before region-specific taxes and data transfer.
Phase 2 has no NAT Gateway, ALB, RDS, S3, Secrets Manager, or custom VPC.

## Mandatory safeguards for future phases

- Never run `terraform apply`, deploy, migrate an AWS database, or destroy AWS
  resources without explicit approval for the specific plan and environment.
- Use one `dev` environment until another is explicitly requested.
- Do not create a NAT Gateway, EKS cluster, Multi-AZ RDS database, additional
  environments, or paid security/observability products without a separate decision.
- Tag every resource with `Project`, `Environment`, `ManagedBy`, and a non-personal
  `Owner` value.
- Review `terraform plan` before changes and inventory resources after changes.
- Configure an AWS Budget and billing alerts before leaving a paid environment running.
- Use a single ECS task and the smallest validated development sizes.
- Set finite log retention and storage lifecycle rules.
- Never run load tests in AWS without separate approval.
- Use two reviewed plans: create the bootstrap first, then enable the one-task
  service only after its immutable image exists in ECR.

## Expected future cost sources

Before the relevant phase is deployed, document current regional prices and the
expected monthly total. Persistent or usage-based costs can include an Application
Load Balancer, Fargate compute, RDS, Secrets Manager, public IPv4 addresses,
CloudWatch logs/metrics, ECR storage, S3 storage and requests, and data transfer.
Pricing must be checked at deployment time rather than copied into this baseline.

## Shutdown and deletion safety

Future runbooks must list temporary resources and their cleanup procedure. Before
destroying persistent resources, confirm whether database snapshots and S3 objects
must be retained. Never delete RDS data, S3 data, snapshots, Terraform state, or
ECR images based on a broad or unreviewed target.

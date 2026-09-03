# AWS cost safety

## Phase 0 status

Phase 0 is local-only. It creates no AWS resources, makes no AWS API calls, and
contains no Terraform configuration. Its AWS cost is **USD 0**.

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

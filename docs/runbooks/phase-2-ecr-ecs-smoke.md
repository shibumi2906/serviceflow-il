# Phase 2 ECR to ECS smoke runbook

## Scope and expected state

This runbook covers the temporary path `local image -> ECR -> task definition ->
Fargate task -> CloudWatch Logs`. It does not create an ALB, RDS, S3, Secrets
Manager, NAT Gateway, or custom VPC. The task has no inbound security-group rule.

Use a non-root AWS identity obtained through a short-lived profile or SSO session.
Never use access keys belonging to the AWS root account. Set one explicit region
for every command.

## 1. Local image

Run `python scripts/check.py`. Expected: all application tests pass; the image is
built on Python 3.12; local liveness and readiness return 200; business routes
return 404 in smoke mode; UID 10001, a read-only root filesystem, dropped Linux
capabilities, and `no-new-privileges` are confirmed.

If the build fails, inspect the failing Docker layer and `requirements.runtime.lock`.
Do not proceed to ECR with a locally failing image.

## 2. Bootstrap plan and ECR

Run the default plan with an explicit region and save it. Expected: only the ECR
repository, CloudWatch log group, ECS cluster, two IAM roles, and one narrow
execution-role policy are proposed. `deploy_service` must remain `false`.

After explicit approval and apply, obtain `ecr_repository_url` from Terraform.
Authenticate Docker with a short-lived ECR token, tag the already tested image with
the full Git commit SHA, and push it. Never push `latest`.

Verify with `aws ecr describe-images --repository-name serviceflow-il-dev
--region REGION`. Expected: one image whose tag is the exact 40-character Git SHA
and whose digest is present. If the image is missing, verify region, repository URL,
Docker login expiry, and the local tag before checking ECS.

## 3. Task definition and service plan

Create a second saved plan with `deploy_service=true` and `image_tag=FULL_GIT_SHA`.
Expected: one security group with no ingress, HTTPS/DNS-only egress, one Fargate
task definition (0.25 vCPU and 0.5 GiB), and one service with desired count one in
default-VPC subnets. A temporary public IP is enabled; no new VPC or NAT is created.

Apply only after explicit approval of this second plan. If Terraform cannot find a
default VPC, stop: creating a replacement network is outside this plan and requires
a separate user decision.

## 4. Task startup and liveness

Run `aws ecs describe-services` and `aws ecs list-tasks` in the selected region.
Expected: desired and running counts are one. Then inspect the task with
`aws ecs describe-tasks`; expected `lastStatus=RUNNING` and `healthStatus=HEALTHY`.
The container health command calls `/health/live` on loopback, matching the local
smoke test.

If no task starts, inspect service events first. For `CannotPullContainerError`,
verify the SHA tag and execution-role ECR permissions. For networking errors,
verify public-IP assignment, a default-subnet route to an Internet Gateway, HTTPS
egress, and VPC DNS. For an unhealthy task, inspect logs next.

## 5. CloudWatch logs

Read `/ecs/serviceflow-il-dev` with `aws logs tail --since 10m --region REGION`.
Expected: a stream prefixed `app/` and Uvicorn startup messages without secrets or
connection strings. If no stream exists, verify `logs:CreateLogStream` and
`logs:PutLogEvents`, the configured region, and execution-role assignment.

## 6. Stop costs and preserve state

A running 0.25-vCPU/0.5-GiB Fargate task and its public IPv4 address incur hourly
charges. After verification, first produce and review a plan that sets
`deploy_service=false`; applying it removes the service, task definition, and task
security group while retaining ECR, the cluster, roles, and short-retention logs.

Full `terraform destroy`, deletion of ECR images, or removal of local state requires
separate explicit approval. ECR storage and retained CloudWatch logs can continue
to incur small charges after the task stops. Keep the local state file secure until
all managed resources have been deliberately reconciled or destroyed.

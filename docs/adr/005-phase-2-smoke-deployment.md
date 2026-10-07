# ADR-005: Use a constrained smoke mode for the first Fargate deployment

- Status: Accepted
- Date: 2026-09-04

## Context

Phase 2 must prove the image path from ECR to Fargate before RDS, ALB, permanent
networking, and secret delivery exist. Running the Phase 1 application without a
database would either fail readiness or tempt the deployment to use unsafe dummy
credentials and an unsupported cloud database.

## Decision

Add an explicit `APP_MODE=smoke` runtime mode. It exposes only `/health/live` and
`/health/ready`, disables API documentation and all business routes, and requires
neither a database URL nor an application secret. Full mode keeps the Phase 1
configuration and behavior.

For Phase 2 only, run one Fargate task in default-VPC subnets with a public IP so
it can pull from ECR and write CloudWatch logs without a NAT Gateway. Its security
group has no ingress. Liveness is evaluated inside the container. The task uses a
dedicated empty task role and a narrowly scoped execution role.

## Consequences

Phase 2 validates packaging, ECR pull, task startup, container health, and logs,
but it is not a user-facing deployment. The public IPv4 address and running task
incur hourly charges. The service must be scaled to zero or removed after the
exercise. Phase 3 will replace this temporary network posture with an explicit
VPC and ALB path.

## Alternatives considered

- Add RDS now: rejected because persistence belongs to Phase 4.
- Add an ALB now: rejected because request routing belongs to Phase 3.
- Add a NAT Gateway or VPC endpoints: rejected because either adds cost and a
  network design outside the Phase 2 learning goal.
- Open the task port to the internet: rejected because direct public application
  access is not required for the internal container health check.

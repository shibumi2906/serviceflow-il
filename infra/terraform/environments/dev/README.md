# Phase 2 Terraform dev environment

This root intentionally uses local Terraform state. Remote state is deferred until
Phase 7. Never commit `terraform.tfstate`, saved plans, credentials, or generated
`.terraform/` content. Back up the local state securely while resources exist.

Terraform runs through the pinned container wrapper:

```bash
python scripts/terraform_docker.py init
python scripts/terraform_docker.py plan -var aws_region=REGION -out=phase2-bootstrap.tfplan
```

The default `deploy_service=false` bootstrap creates ECR, the log group, cluster,
and IAM roles without starting a task. This lets an approved immutable image be
pushed before a second reviewed plan enables the service:

```bash
python scripts/terraform_docker.py plan \
  -var aws_region=REGION \
  -var deploy_service=true \
  -var image_tag=FULL_GIT_SHA \
  -out=phase2-service.tfplan
```

Do not apply either plan, publish an image, scale the service, or destroy resources
without explicit approval for that exact operation.

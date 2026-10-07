"""Run Phase 2 Terraform formatting, validation, lint, and security checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

TERRAFORM_IMAGE = "hashicorp/terraform:1.13.3"
TFLINT_IMAGE = "ghcr.io/terraform-linters/tflint:v0.59.1"
TRIVY_IMAGE = "aquasec/trivy:0.67.2"
INFRA_DIR = (
    Path(__file__).resolve().parents[1] / "infra" / "terraform" / "environments" / "dev"
)


def docker_tool(image: str, *args: str) -> None:
    """Run a pinned tool image against the Phase 2 Terraform directory."""
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--volume",
            f"{INFRA_DIR}:/workspace",
            "--workdir",
            "/workspace",
            image,
            *args,
        ],
        check=True,
    )


def main() -> int:
    """Validate Terraform without contacting or changing AWS."""
    print("\n==> Terraform format", flush=True)
    docker_tool(TERRAFORM_IMAGE, "fmt", "-check", "-recursive")
    print("\n==> Terraform init (local backend disabled)", flush=True)
    docker_tool(TERRAFORM_IMAGE, "init", "-backend=false", "-input=false")
    print("\n==> Terraform validate", flush=True)
    docker_tool(TERRAFORM_IMAGE, "validate")
    print("\n==> TFLint", flush=True)
    docker_tool(TFLINT_IMAGE, "--chdir=/workspace")
    print("\n==> Trivy Terraform configuration scan", flush=True)
    docker_tool(
        TRIVY_IMAGE,
        "config",
        "--exit-code",
        "1",
        "--severity",
        "HIGH,CRITICAL",
        "/workspace",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

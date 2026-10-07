"""Run pinned Terraform without requiring a host installation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TERRAFORM_IMAGE = "hashicorp/terraform:1.13.3"
INFRA_DIR = (
    Path(__file__).resolve().parents[1] / "infra" / "terraform" / "environments" / "dev"
)


def main() -> int:
    """Forward Terraform arguments and mount only its workspace and AWS profile."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/terraform_docker.py <terraform arguments>")
        return 2
    command = [
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{INFRA_DIR}:/workspace",
        "--workdir",
        "/workspace",
    ]
    aws_config = Path.home() / ".aws"
    if aws_config.is_dir():
        command.extend(["--volume", f"{aws_config}:/root/.aws:ro"])
    for variable in ("AWS_PROFILE", "AWS_REGION", "AWS_DEFAULT_REGION"):
        if os.getenv(variable):
            command.extend(["--env", variable])
    command.extend([TERRAFORM_IMAGE, *sys.argv[1:]])
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

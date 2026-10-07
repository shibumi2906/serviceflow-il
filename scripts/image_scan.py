"""Scan the local Phase 2 image without giving a networked scanner the source."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

IMAGE = "serviceflow-il:phase2-local"
TRIVY_IMAGE = "aquasec/trivy:0.67.2"
TRIVY_CACHE_VOLUME = "serviceflow-trivy-cache"


def run(*args: str) -> None:
    """Run a command and fail on a non-zero exit code."""
    subprocess.run(list(args), check=True)


def main() -> int:
    """Update vulnerability data separately, then scan an image offline."""
    run("docker", "volume", "create", TRIVY_CACHE_VOLUME)
    run(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{TRIVY_CACHE_VOLUME}:/root/.cache/trivy",
        TRIVY_IMAGE,
        "--timeout",
        "15m",
        "image",
        "--db-repository",
        "ghcr.io/aquasecurity/trivy-db:2",
        "--download-db-only",
        "--skip-version-check",
    )
    with tempfile.TemporaryDirectory(prefix="serviceflow-trivy-") as temporary:
        image_archive = Path(temporary) / "image.tar"
        run("docker", "save", "--output", str(image_archive), IMAGE)
        run(
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--volume",
            f"{TRIVY_CACHE_VOLUME}:/root/.cache/trivy",
            "--volume",
            f"{Path(temporary).resolve()}:/scan:ro",
            TRIVY_IMAGE,
            "--timeout",
            "15m",
            "image",
            "--input",
            "/scan/image.tar",
            "--skip-db-update",
            "--skip-version-check",
            "--ignore-unfixed",
            "--severity",
            "HIGH,CRITICAL",
            "--exit-code",
            "1",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

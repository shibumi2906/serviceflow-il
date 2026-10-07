"""Run the complete local Phase 2 quality gate."""

import os
import subprocess
import sys

CHECKS = (
    ("Ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("Ruff lint", [sys.executable, "-m", "ruff", "check", "."]),
    ("mypy", [sys.executable, "-m", "mypy"]),
    (
        "dependency audit",
        [
            sys.executable,
            "-m",
            "pip_audit",
            "-r",
            "requirements.lock",
            "--no-deps",
            "--disable-pip",
        ],
    ),
    (
        "runtime dependency audit",
        [
            sys.executable,
            "-m",
            "pip_audit",
            "-r",
            "requirements.runtime.lock",
            "--no-deps",
            "--disable-pip",
        ],
    ),
    ("unit tests", [sys.executable, "-m", "pytest", "tests/unit"]),
)


def main() -> int:
    """Run each check in sequence and stop at the first failure."""
    for label, command in CHECKS:
        print(f"\n==> {label}", flush=True)
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    if os.getenv("CI") != "true":
        print("\n==> PostgreSQL 16", flush=True)
        result = subprocess.run(
            ["docker", "compose", "up", "--detach", "--wait", "db"], check=False
        )
        if result.returncode != 0:
            return result.returncode
    print("\n==> PostgreSQL integration, API, and web tests", flush=True)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integration"], check=False
    )
    if result.returncode != 0:
        return result.returncode
    phase_two_checks = (
        ("container build and hardened smoke", "container_smoke.py"),
        ("container vulnerability scan", "image_scan.py"),
        ("Terraform format, validate, lint, and security", "infra_check.py"),
    )
    for label, script in phase_two_checks:
        print(f"\n==> {label}", flush=True)
        result = subprocess.run([sys.executable, f"scripts/{script}"], check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

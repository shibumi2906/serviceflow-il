"""Run the complete local Phase 0 quality gate."""

import subprocess
import sys

CHECKS = (
    ("Ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("Ruff lint", [sys.executable, "-m", "ruff", "check", "."]),
    ("mypy", [sys.executable, "-m", "mypy"]),
    ("unit tests", [sys.executable, "-m", "pytest", "tests/unit"]),
)


def main() -> int:
    """Run each check in sequence and stop at the first failure."""
    for label, command in CHECKS:
        print(f"\n==> {label}", flush=True)
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

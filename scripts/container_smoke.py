"""Build and harden-run the Phase 2 smoke image locally."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

IMAGE = "serviceflow-il:phase2-local"


def run(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run Docker with consistent error handling."""
    return subprocess.run(
        ["docker", *args],
        check=True,
        text=True,
        capture_output=capture,
    )


def image_revision() -> str:
    """Return the source revision recorded in the local image label."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def http_status(url: str) -> tuple[int, str]:
    """Fetch an endpoint, retaining expected HTTP error responses."""
    try:
        with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def inspect_container(container_id: str) -> dict[str, Any]:
    """Load Docker's effective container configuration."""
    result = run("inspect", container_id, capture=True)
    return json.loads(result.stdout)[0]  # type: ignore[no-any-return]


def main() -> int:
    """Build, run, probe, and remove a least-privilege smoke container."""
    revision = image_revision()
    run("build", "--build-arg", f"GIT_SHA={revision}", "--tag", IMAGE, ".")
    result = run(
        "run",
        "--detach",
        "--rm",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--publish",
        "127.0.0.1::8000",
        IMAGE,
        capture=True,
    )
    container_id = result.stdout.strip()
    try:
        port_result = run("port", container_id, "8000/tcp", capture=True)
        port = port_result.stdout.strip().rsplit(":", maxsplit=1)[1]
        base_url = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 45
        while True:
            try:
                live_status, live_body = http_status(f"{base_url}/health/live")
                if live_status == 200:
                    break
            except OSError:
                pass
            if time.monotonic() >= deadline:
                logs = run("logs", container_id, capture=True).stdout
                raise RuntimeError(f"Container did not become live:\n{logs}")
            time.sleep(0.5)

        ready_status, ready_body = http_status(f"{base_url}/health/ready")
        api_status, _ = http_status(f"{base_url}/api/v1/requests")
        details = inspect_container(container_id)
        image_details = json.loads(run("image", "inspect", IMAGE, capture=True).stdout)[
            0
        ]
        runtime_uid = run("exec", container_id, "id", "-u", capture=True).stdout.strip()

        assert json.loads(live_body) == {"status": "ok"}
        assert ready_status == 200
        assert json.loads(ready_body) == {"status": "ok", "mode": "smoke"}
        assert api_status == 404
        assert runtime_uid == "10001"
        assert image_details["Config"]["User"] == "10001:10001"
        assert image_details["Config"]["Healthcheck"] is not None
        assert details["HostConfig"]["ReadonlyRootfs"] is True
        assert "ALL" in details["HostConfig"]["CapDrop"]
        assert "no-new-privileges:true" in details["HostConfig"]["SecurityOpt"]
        print(
            "Smoke image passed: live=200 ready=200 business-api=404 "
            "uid=10001 read-only=true cap-drop=ALL no-new-privileges=true"
        )
    finally:
        subprocess.run(
            ["docker", "stop", "--time", "2", container_id],
            check=False,
            text=True,
            capture_output=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

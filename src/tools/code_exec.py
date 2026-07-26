"""Runs untrusted code in an ephemeral, network-disabled, non-root sibling container
built from the 'sandbox_exec' image (see docker/Dockerfile.sandbox). This is a
sibling-container approach (Docker-out-of-Docker via the mounted host socket), not true
Docker-in-Docker -- simpler, avoids privileged-mode complexity, still real isolation."""

import threading

from src.guardrails.limits import sanitize_code_input
from src.tools.registry import register

try:
    import docker
    _HAS_DOCKER = True
except ImportError:
    _HAS_DOCKER = False

SANDBOX_IMAGE = "sandbox_exec"
TIMEOUT_SECONDS = 10


@register(
    name="code_exec",
    description="Run a short Python snippet in an isolated sandbox and return stdout. Input: {code: str}",
)
def code_exec(code: str) -> str:
    try:
        code = sanitize_code_input(code)
    except ValueError as e:
        return f"Error: {e}"

    if not _HAS_DOCKER:
        return "Error: docker SDK not available in this environment."

    #client = docker.from_env()
    try:
        client = docker.from_env()
    except Exception:
        return (
            "Error: no Docker daemon available in this environment. "
            "This tool requires Docker and isn't available in the public demo — "
            "see the README for running it locally."
        )
    container = None
    result = {"output": None, "error": None, "exit_code": None}

    def _run():
        nonlocal container
        try:
            container = client.containers.run(
                SANDBOX_IMAGE,
                [code],
                network_disabled=True,
                mem_limit="128m",
                nano_cpus=500_000_000,  # 0.5 CPU
                read_only=True,
                remove=False,
                detach=True,
            )
            exit_status = container.wait(timeout=TIMEOUT_SECONDS)
            logs = container.logs().decode("utf-8", errors="replace")
            result["output"] = logs
            result["exit_code"] = exit_status.get("StatusCode")
        except Exception as e:
            result["error"] = str(e)

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join(timeout=TIMEOUT_SECONDS + 2)

    if container:
        try:
            container.remove(force=True)
        except Exception:
            pass

    if thread.is_alive():
        return f"Error: execution exceeded {TIMEOUT_SECONDS}s timeout and was killed."
    if result["error"]:
        return f"Error: {result['error']}"
    return result["output"] or "(no output)"

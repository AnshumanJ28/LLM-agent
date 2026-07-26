"""Guardrails enforced in code, not just prompted for."""

import json


class GuardrailViolation(Exception):
    pass


def check_step_budget(step: int, max_steps: int):
    if step >= max_steps:
        raise GuardrailViolation(f"Step budget exceeded: {step}/{max_steps}")


def check_cost_budget(total_tokens: int, cost_ceiling_tokens: int):
    if total_tokens >= cost_ceiling_tokens:
        raise GuardrailViolation(f"Token/cost budget exceeded: {total_tokens} >= {cost_ceiling_tokens}")


def validate_output_schema(final_answer: str, expected_keys: list = None) -> bool:
    """If a task expects structured (JSON) output, validate before accepting it."""
    if not expected_keys:
        return True
    try:
        data = json.loads(final_answer)
    except json.JSONDecodeError:
        return False
    return all(k in data for k in expected_keys)


def sanitize_code_input(code: str) -> str:
    """Cheap first filter against obviously destructive patterns before the sandbox ever
    sees the code. The real security boundary is the sandbox container itself (no
    network, non-root, read-only, resource-limited) -- this is a pre-filter, not the
    defense."""
    banned = ["rm -rf", "shutil.rmtree", "os.system", "subprocess.Popen", "/etc/passwd"]
    for pattern in banned:
        if pattern in code:
            raise ValueError(f"Rejected: code contains banned pattern '{pattern}'")
    return code

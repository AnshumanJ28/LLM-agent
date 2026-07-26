"""From-scratch ReAct loop: no LangChain/LangGraph. Parses the model's structured output
itself, dispatches to tools, and iterates until a Final Answer or a hard step limit."""

import json
import re
from dataclasses import dataclass
from typing import Callable, Optional

from src.agent.llm_groq import call_groq
from src.guardrails.limits import check_step_budget, check_cost_budget, GuardrailViolation

FINAL_ANSWER_RE = re.compile(r"Final Answer:\s*(.*)", re.DOTALL)
ACTION_RE = re.compile(r"Action:\s*(.*?)\s*\n")
ACTION_INPUT_RE = re.compile(r"Action Input:\s*(\{.*\})", re.DOTALL)


@dataclass
class AgentResult:
    final_answer: Optional[str]
    transcript: list
    steps_taken: int
    incomplete: bool
    total_tokens: int


def build_system_prompt(tools: dict) -> str:
    tool_lines = []
    for name, meta in tools.items():
        tool_lines.append(f"- {name}: {meta['description']}\n  input schema: {json.dumps(meta['schema'])}")
    tools_block = "\n".join(tool_lines) if tool_lines else "(no tools registered)"

    return f"""You are an autonomous agent that solves tasks by reasoning step by step and calling tools.

Available tools:
{tools_block}

You MUST respond using exactly this format, one block per turn:

Thought: <your reasoning>
Action: <tool name>
Action Input: <JSON object matching the tool's input schema>

When you have the final answer, respond instead with:

Thought: <final reasoning>
Final Answer: <answer to the user>

Only ever output ONE Thought/Action/Action Input block, or ONE Thought/Final Answer block,
per turn. Then stop and wait for the Observation before continuing.
"""


def parse_response(text: str):
    """Returns one of:
    ("final", answer_str)
    ("action", tool_name, input_dict)
    ("error", error_message)
    """
    action_match = ACTION_RE.search(text)
    final_match = FINAL_ANSWER_RE.search(text)

    if final_match and not action_match:
        return ("final", final_match.group(1).strip())

    if action_match:
        tool_name = action_match.group(1).strip()
        input_match = ACTION_INPUT_RE.search(text)
        if not input_match:
            return ("error", "Could not find a valid 'Action Input: {...}' JSON block.")
        try:
            action_input = json.loads(input_match.group(1))
        except json.JSONDecodeError as e:
            return ("error", f"Action Input was not valid JSON: {e}")
        return ("action", tool_name, action_input)

    return ("error", "Response did not match the required Thought/Action or Thought/Final Answer format.")


def run_agent(
    task: str,
    tools: dict,
    max_steps: int = 8,
    trace_logger=None,
    cost_ceiling: int = None,
) -> AgentResult:
    system_prompt = build_system_prompt(tools)
    transcript = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    total_tokens = 0
    step = 0
    retries_this_step = 0
    max_retries_per_step = 2

    while step < max_steps:
        try:
            check_step_budget(step, max_steps)
            if cost_ceiling is not None:
                check_cost_budget(total_tokens, cost_ceiling)
        except GuardrailViolation as e:
            if trace_logger:
                trace_logger.log_step(step, {"type": "guardrail_stop", "error": str(e)})
            return AgentResult(None, transcript, step, True, total_tokens)

        response_text, usage = call_groq(transcript)
        total_tokens += usage.get("total_tokens", 0)

        parsed = parse_response(response_text)

        if parsed[0] == "final":
            answer = parsed[1]
            transcript.append({"role": "assistant", "content": response_text})
            if trace_logger:
                trace_logger.log_step(step, {
                    "type": "final_answer", "raw": response_text, "final_answer": answer, "tokens": usage,
                })
            return AgentResult(answer, transcript, step + 1, False, total_tokens)

        if parsed[0] == "error":
            retries_this_step += 1
            transcript.append({"role": "assistant", "content": response_text})
            correction = (
                f"Your last response did not match the required format: {parsed[1]} "
                "Reply again using exactly the Thought/Action/Action Input or "
                "Thought/Final Answer format."
            )
            transcript.append({"role": "user", "content": correction})
            if trace_logger:
                trace_logger.log_step(step, {"type": "parse_error", "error": parsed[1], "raw": response_text})
            if retries_this_step > max_retries_per_step:
                step += 1
                retries_this_step = 0
            continue

        # parsed[0] == "action"
        _, tool_name, tool_input = parsed
        transcript.append({"role": "assistant", "content": response_text})

        if tool_name not in tools:
            observation = f"Error: Unknown tool '{tool_name}'. Available tools: {list(tools.keys())}"
        else:
            try:
                observation = tools[tool_name]["fn"](**tool_input)
            except Exception as e:
                observation = f"Error: Tool '{tool_name}' raised an exception: {e}"

        obs_text = f"Observation: {observation}"
        transcript.append({"role": "user", "content": obs_text})

        if trace_logger:
            trace_logger.log_step(step, {
                "type": "tool_call",
                "raw": response_text,
                "tool": tool_name,
                "input": tool_input,
                "observation": str(observation),
                "tokens": usage,
            })

        step += 1
        retries_this_step = 0

    return AgentResult(None, transcript, step, True, total_tokens)

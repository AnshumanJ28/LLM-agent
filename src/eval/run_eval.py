import json
import os
import time

from src.agent.loop import run_agent
from src.eval.judge import llm_judge_score, rule_based_score
from src.tools import calculator, code_exec, vector_lookup, web_search  # noqa: F401 -- registers tools
from src.tools.registry import get_tools
from src.trace.logger import TraceLogger

GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "golden_set.json")


def run_eval(use_llm_judge: bool = False):
    with open(GOLDEN_SET_PATH) as f:
        golden_set = json.load(f)

    tools = get_tools()
    scorecard = []

    for task in golden_set:
        trace_logger = TraceLogger(run_id=f"eval-{task['id']}")
        start = time.time()
        result = run_agent(task["task"], tools, max_steps=8, trace_logger=trace_logger)
        latency = time.time() - start

        scores = rule_based_score(task, result)
        if use_llm_judge:
            scores["llm_judge"] = llm_judge_score(task, result)

        scorecard.append({
            "id": task["id"],
            "steps_taken": result.steps_taken,
            "total_tokens": result.total_tokens,
            "latency_sec": round(latency, 2),
            "incomplete": result.incomplete,
            **scores,
        })

    passed = sum(
        1 for s in scorecard if s["tool_correct"] and s["content_correct"] and s["completed"]
    )
    print(f"\n=== Eval Scorecard: {passed}/{len(scorecard)} passed ===\n")
    for s in scorecard:
        print(json.dumps(s, indent=2))

    return scorecard


if __name__ == "__main__":
    run_eval()

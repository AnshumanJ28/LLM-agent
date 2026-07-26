from src.agent.llm_groq import call_groq


def rule_based_score(task: dict, result) -> dict:
    used_tools = set()
    for turn in result.transcript:
        if turn["role"] == "assistant" and "Action:" in turn.get("content", ""):
            for line in turn["content"].splitlines():
                if line.strip().startswith("Action:"):
                    used_tools.add(line.split("Action:", 1)[1].strip())

    expected_tool = task.get("expected_tool")
    tool_correct = expected_tool in used_tools if expected_tool else True

    expected_contains = task.get("expected_answer_contains")
    content_correct = True
    if expected_contains and result.final_answer:
        content_correct = expected_contains.lower() in result.final_answer.lower()

    return {
        "tool_correct": tool_correct,
        "content_correct": content_correct,
        "completed": not result.incomplete,
    }


def llm_judge_score(task: dict, result) -> str:
    """Optional second-opinion score via Groq, for open-ended tasks where a substring
    check isn't enough (e.g. the web_search task, since real search results vary)."""
    if result.final_answer is None:
        return "0 -- no final answer produced"
    prompt = (
        f"Task: {task['task']}\n"
        f"Agent's final answer: {result.final_answer}\n\n"
        "Score the answer from 0-10 for correctness and relevance. "
        "Respond with just a number and a one-sentence reason."
    )
    text, _ = call_groq([{"role": "user", "content": prompt}])
    return text.strip()

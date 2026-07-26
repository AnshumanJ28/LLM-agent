from unittest.mock import patch

from src.agent.loop import parse_response, run_agent


def test_parse_final_answer():
    text = "Thought: I know the answer.\nFinal Answer: 42"
    parsed = parse_response(text)
    assert parsed[0] == "final"
    assert parsed[1] == "42"


def test_parse_action():
    text = 'Thought: need to compute.\nAction: calculator\nAction Input: {"expression": "2+2"}'
    parsed = parse_response(text)
    assert parsed[0] == "action"
    assert parsed[1] == "calculator"
    assert parsed[2] == {"expression": "2+2"}


def test_parse_malformed():
    text = "I just feel like answering directly without the format."
    parsed = parse_response(text)
    assert parsed[0] == "error"


def test_parse_bad_json_action_input():
    text = "Thought: hmm.\nAction: calculator\nAction Input: {expression: 2+2}"
    parsed = parse_response(text)
    assert parsed[0] == "error"


@patch("src.agent.loop.call_groq")
def test_run_agent_reaches_final_answer(mock_call):
    mock_call.return_value = ("Thought: done.\nFinal Answer: hello", {"total_tokens": 10})
    result = run_agent("say hello", {}, max_steps=3)
    assert result.final_answer == "hello"
    assert result.incomplete is False


@patch("src.agent.loop.call_groq")
def test_run_agent_hits_step_limit(mock_call):
    mock_call.return_value = (
        "Thought: still thinking.\nAction: unknown_tool\nAction Input: {}",
        {"total_tokens": 5},
    )
    result = run_agent("loop forever", {}, max_steps=2)
    assert result.incomplete is True


@patch("src.agent.loop.call_groq")
def test_run_agent_recovers_from_tool_exception(mock_call):
    def flaky_tool(**kwargs):
        raise ValueError("boom")

    responses = [
        ('Thought: try tool.\nAction: flaky\nAction Input: {}', {"total_tokens": 5}),
        ("Thought: ok done.\nFinal Answer: recovered", {"total_tokens": 5}),
    ]
    mock_call.side_effect = responses

    tools = {"flaky": {"fn": flaky_tool, "description": "flaky tool", "schema": {}}}
    result = run_agent("test recovery", tools, max_steps=5)
    assert result.final_answer == "recovered"

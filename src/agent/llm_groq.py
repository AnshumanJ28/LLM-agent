"""Thin wrapper around the Groq chat completions API. Kept separate from loop.py so the
ReAct parsing logic doesn't know or care which LLM provider is behind it."""

import os
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client():
    global _client
    if _client is None:
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Copy .env.example to .env and fill it in."
            )
        _client = Groq(api_key=api_key)
    return _client


def call_groq(messages: list, model: str = "llama-3.3-70b-versatile", temperature: float = 0.2):
    """Returns (response_text, usage_dict)."""
    client = get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    text = resp.choices[0].message.content
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
        "total_tokens": resp.usage.total_tokens,
    }
    return text, usage

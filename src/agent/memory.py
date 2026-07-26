"""Short-term transcript handling + a simple long-term key-value memory the agent can
read/write as an explicit tool. Kept dependency-light on purpose."""

import time


class AgentMemory:
    def __init__(self):
        self._store = {}

    def remember(self, key: str, value: str) -> str:
        self._store[key] = {"value": value, "ts": time.time()}
        return f"Stored '{key}'."

    def recall(self, key: str) -> str:
        entry = self._store.get(key)
        if entry is None:
            return f"No memory found for '{key}'."
        return entry["value"]

    def list_keys(self):
        return list(self._store.keys())


def summarize_transcript(transcript: list, keep_last_n: int = 6) -> list:
    """Collapse older turns into a single placeholder once the transcript grows long, to
    keep the context window bounded. This is a simple truncation placeholder -- swap in
    an LLM summarization call here if you want real compression instead of a stub note."""
    if len(transcript) <= keep_last_n + 1:
        return transcript
    system = transcript[0]
    head = transcript[1:-keep_last_n]
    tail = transcript[-keep_last_n:]
    summary_text = f"[Earlier conversation summarized: {len(head)} turns omitted for brevity]"
    return [system, {"role": "user", "content": summary_text}] + tail

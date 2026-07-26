"""Structured JSONL logging of every agent step, for the Streamlit viewer to replay."""

import json
import os
import time
import uuid


class TraceLogger:
    def __init__(self, run_id: str = None, trace_dir: str = "traces"):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.trace_dir = trace_dir
        os.makedirs(trace_dir, exist_ok=True)
        self.path = os.path.join(trace_dir, f"{self.run_id}.jsonl")

    def log_step(self, step: int, data: dict):
        record = {"run_id": self.run_id, "step": step, "ts": time.time(), **data}
        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]

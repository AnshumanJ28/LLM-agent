import json
import os

import streamlit as st

TRACE_DIR = "traces"

st.title("Agent Trace Viewer")

if not os.path.isdir(TRACE_DIR):
    st.warning("No traces directory found yet -- run the agent at least once.")
else:
    files = sorted(f for f in os.listdir(TRACE_DIR) if f.endswith(".jsonl"))
    if not files:
        st.info("No trace files yet.")
    else:
        chosen = st.selectbox("Select a run", files)
        with open(os.path.join(TRACE_DIR, chosen)) as f:
            steps = [json.loads(line) for line in f if line.strip()]

        for s in steps:
            with st.expander(f"Step {s.get('step')} -- {s.get('type', '')}"):
                st.json(s)

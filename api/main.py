from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent.loop import run_agent
from src.tools import calculator, code_exec, vector_lookup, web_search  # noqa: F401
from src.tools.registry import get_tools
from src.trace.logger import TraceLogger

app = FastAPI(title="From-Scratch Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    task: str
    max_steps: int = 8


@app.post("/run")
def run(req: RunRequest):
    trace_logger = TraceLogger()
    tools = get_tools()
    result = run_agent(
        req.task,
        tools,
        max_steps=req.max_steps,
        trace_logger=trace_logger,
    )
    return {
        "final_answer": result.final_answer,
        "steps_taken": result.steps_taken,
        "incomplete": result.incomplete,
        "total_tokens": result.total_tokens,
        "run_id": trace_logger.run_id,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


BASE_DIR = Path(__file__).resolve().parent.parent

app.mount(
    "/",
    StaticFiles(directory=BASE_DIR / "static", html=True),
    name="static",
)

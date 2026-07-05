"""FastAPI backend (deploys to Alibaba Function Compute / SAE).

Endpoints:
  GET  /health      -> liveness + mode
  GET  /scenarios   -> available demo scenarios
  POST /run         -> run a scenario through ReceiptGuard, return full result
  GET  /            -> the split-screen demo UI
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ..agent import SCENARIOS
from ..config import settings
from ..pipeline import ReceiptGuard

app = FastAPI(title="ReceiptGuard", version="0.1.0")
_STATIC = Path(__file__).resolve().parents[3] / "static"


class RunRequest(BaseModel):
    scenario: str = "refund_damaged"
    max_iterations: int = 3
    adversarial: bool = False  # inject a red-team unbacked claim (demo the catch on real Qwen)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mock": settings.mock,
            "models": {"agent": settings.model_agent, "worker": settings.model_worker}}


@app.get("/scenarios")
def scenarios() -> dict:
    return {"scenarios": {k: v["ticket"] for k, v in SCENARIOS.items()}}


@app.post("/run")
def run(req: RunRequest) -> JSONResponse:
    result = ReceiptGuard(max_iterations=req.max_iterations).run(req.scenario, adversarial=req.adversarial)
    return JSONResponse(result.to_dict())


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")

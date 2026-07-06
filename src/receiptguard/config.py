"""Runtime configuration, loaded from environment (.env).

If DASHSCOPE_API_KEY is unset, ReceiptGuard runs in MOCK mode: deterministic,
no network, the full pipeline + demo still work. Set the key to use real Qwen.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (avoids a hard python-dotenv dependency)."""
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[3] / ".env"):
        if candidate.is_file():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
            break


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_key: str = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    base_url: str = os.environ.get(
        "DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    ).strip()
    model_agent: str = os.environ.get("RG_MODEL_AGENT", "qwen3.7-max").strip()
    model_worker: str = os.environ.get("RG_MODEL_WORKER", "qwen-flash").strip()
    model_embed: str = os.environ.get("RG_MODEL_EMBED", "text-embedding-v4").strip()
    receipt_secret: str = os.environ.get("RG_RECEIPT_SECRET", "dev-only-insecure-secret-change-me")
    ledger_path: str = os.environ.get("RG_LEDGER_PATH", "receiptguard_ledger.db")
    thinking_budget: int = int(os.environ.get("RG_THINKING_BUDGET", "2048"))
    agent_max_tool_steps: int = int(os.environ.get("RG_AGENT_MAX_TOOL_STEPS", "8"))
    # per-LLM-call wall-clock cap (s) — a slow thinking call must not hang the request.
    llm_timeout_s: float = float(os.environ.get("RG_LLM_TIMEOUT_S", "60"))
    # cumulative per-run budget (s) — ~30 sequential calls must fit under FC's 300s ceiling.
    run_budget_s: float = float(os.environ.get("RG_RUN_BUDGET_S", "240"))

    def __post_init__(self) -> None:
        # validate without mutating (frozen): fail fast on a misconfigured live deploy
        if self.api_key and not self.base_url.startswith("http"):
            raise ValueError(f"DASHSCOPE_BASE_URL must be an http(s) URL, got {self.base_url!r}")
        if self.thinking_budget <= 0:
            raise ValueError("RG_THINKING_BUDGET must be positive")
        if self.agent_max_tool_steps <= 0:
            raise ValueError("RG_AGENT_MAX_TOOL_STEPS must be positive")
        if self.llm_timeout_s <= 0 or self.run_budget_s <= 0:
            raise ValueError("RG_LLM_TIMEOUT_S and RG_RUN_BUDGET_S must be positive")

    @property
    def mock(self) -> bool:
        """True when no API key -> deterministic offline mode."""
        return not self.api_key


settings = Settings()

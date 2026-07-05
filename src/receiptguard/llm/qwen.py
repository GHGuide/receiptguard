"""Qwen gateway wrapper — the ONLY place that talks to Alibaba Cloud.

Uses the OpenAI-compatible DashScope endpoint (Alibaba Model Studio). This file
is the submission's "proof of Alibaba Cloud service/API usage".

qwen3-max thinking mode returns a separate `reasoning_content` field; we surface
it so it can be stored as a human-readable audit justification — an artifact the
OpenAI o-series does not expose.

No API key -> deterministic MOCK mode (see llm/mocks.py): the whole pipeline and
demo run offline.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..config import settings
from . import mocks


@dataclass
class LLMResponse:
    content: str
    reasoning_content: str = ""
    model: str = ""
    mock: bool = False
    latency_ms: float = 0.0
    raw: Any = field(default=None, repr=False)


class QwenClient:
    """Thin adapter over the Alibaba DashScope OpenAI-compatible API."""

    def __init__(self) -> None:
        self._client = None  # lazily created real OpenAI client

    def _openai(self):
        if self._client is None:
            from openai import OpenAI  # imported lazily so mock mode needs no install

            self._client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
        return self._client

    def complete(
        self,
        messages: list[dict],
        *,
        task: str = "generic",
        model: str | None = None,
        thinking: bool = False,
        temperature: float = 0.2,
        **mock_kw: Any,
    ) -> LLMResponse:
        """One chat completion.

        `task` routes deterministic mock responses; in real mode it only selects
        the default model (worker vs agent) and is otherwise ignored.
        """
        model = model or (settings.model_agent if thinking else settings.model_worker)
        t0 = time.perf_counter()

        if settings.mock:
            content, reasoning = mocks.respond(task, messages, **mock_kw)
            return LLMResponse(
                content=content,
                reasoning_content=reasoning if thinking else "",
                model=f"mock:{model}",
                mock=True,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

        extra_body: dict[str, Any] = {}
        if thinking:
            # Qwen thinking mode (DashScope OpenAI-compat extension). Stream so the
            # separate `reasoning_content` deltas are reliably surfaced and a slow
            # thinking turn does not hit the Function Compute request timeout.
            extra_body["enable_thinking"] = True
            extra_body["thinking_budget"] = settings.thinking_budget

        stream = self._openai().chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
            extra_body=extra_body or None,
        )
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        usage = None
        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage = chunk.usage
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            rc = getattr(delta, "reasoning_content", None)  # thinking deltas
            if rc:
                reasoning_parts.append(rc)
            if getattr(delta, "content", None):
                content_parts.append(delta.content)
        return LLMResponse(
            content="".join(content_parts),
            reasoning_content="".join(reasoning_parts),
            model=model,
            mock=False,
            latency_ms=(time.perf_counter() - t0) * 1000,
            raw=usage,
        )

    def chat_with_tools(self, messages: list[dict], tools: list[dict], *, model: str | None = None):
        """Raw OpenAI tool-calling turn (real mode only). Returns the message object
        with optional .tool_calls. Used by the real autopilot agent loop."""
        if settings.mock:
            raise RuntimeError("chat_with_tools is real-mode only; mock agent scripts its own plan")
        model = model or settings.model_agent
        resp = self._openai().chat.completions.create(
            model=model, messages=messages, tools=tools, temperature=0.2
        )
        return resp.choices[0].message


client = QwenClient()

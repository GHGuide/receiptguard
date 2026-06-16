"""Unforgeable tool-execution receipts.

Every tool call an agent makes is routed through ToolGateway, which executes the
tool and emits an HMAC-signed receipt. The agent never sees the secret, so it
cannot fabricate a receipt for a tool it never actually called. This is the
ground truth the verifier checks agent claims against.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, asdict
from typing import Any, Callable

from ..config import settings


def _sha256(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class Receipt:
    receipt_id: str
    tool: str
    args: dict
    output: Any
    args_hash: str
    output_hash: str
    output_snippet: str
    ts: float
    sig: str

    def signing_payload(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "tool": self.tool,
            "args_hash": self.args_hash,
            "output_hash": self.output_hash,
            "ts": self.ts,
        }

    def to_public(self) -> dict:
        d = asdict(self)
        d.pop("args", None)  # public view hides raw args
        return d


def sign(payload: dict, secret: str | None = None) -> str:
    secret = secret if secret is not None else settings.receipt_secret
    canonical = json.dumps(payload, sort_keys=True, default=str).encode()
    return hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()


class ReceiptStore:
    """Append-only store of signed receipts for a single agent run."""

    def __init__(self) -> None:
        self._receipts: list[Receipt] = []

    def add(self, tool: str, args: dict, output: Any) -> Receipt:
        rid = f"rcpt_{len(self._receipts)+1:04d}"
        ts = len(self._receipts) + 1.0  # monotonic, deterministic for tests/demo
        args_hash, output_hash = _sha256(args), _sha256(output)
        snippet = json.dumps(output, default=str)[:240]
        payload = {"receipt_id": rid, "tool": tool, "args_hash": args_hash,
                   "output_hash": output_hash, "ts": ts}
        r = Receipt(rid, tool, args, output, args_hash, output_hash, snippet, ts, sign(payload))
        self._receipts.append(r)
        return r

    def verify_signature(self, r: Receipt) -> bool:
        return hmac.compare_digest(r.sig, sign(r.signing_payload()))

    def all(self) -> list[Receipt]:
        return list(self._receipts)

    def for_tool(self, tool: str) -> list[Receipt]:
        return [r for r in self._receipts if r.tool == tool]


class ToolGateway:
    """Routes every tool call through receipt issuance. Agents MUST use this."""

    def __init__(self, tools: dict[str, Callable[..., Any]], store: ReceiptStore | None = None) -> None:
        self._tools = tools
        self.store = store or ReceiptStore()
        self.call_log: list[str] = []

    def call(self, tool: str, **args: Any) -> Any:
        if tool not in self._tools:
            raise KeyError(f"unknown tool: {tool}")
        output = self._tools[tool](**args)
        self.store.add(tool, args, output)
        self.call_log.append(tool)
        return output

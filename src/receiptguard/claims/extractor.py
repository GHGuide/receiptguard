"""Atomic-claim extraction + epistemic-source typing (qwen-flash).

Types follow the NabaOS pramana taxonomy (arXiv 2603.10060):
  tool_derived | inference | absence | opinion
Only tool_derived claims are checked against receipts; inference/opinion are
allowed through (but labeled), absence claims are checked for false-absence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..llm import client

_VALID = {"tool_derived", "inference", "absence", "opinion"}

_SYS = (
    "You split an AI agent's draft answer into atomic factual claims and tag each "
    "by epistemic source. Types: tool_derived (asserts a result that must come from "
    "a tool/database call, e.g. an amount, count, status, id, 'I did X'), "
    "inference (a deduction), absence (claims nothing exists / 'no results'), "
    "opinion (a recommendation/judgement). Return ONLY JSON: "
    '{"claims":[{"text":"...","type":"tool_derived"}]}'
)


@dataclass
class Claim:
    text: str
    type: str


def extract_claims(draft: str) -> list[Claim]:
    # R11: guard non-str / empty input so a bad draft can't 400 the LLM call and
    # crash the whole verify pass. Nothing to extract from an empty draft.
    if not isinstance(draft, str):
        draft = "" if draft is None else str(draft)
    if not draft.strip():
        return []
    resp = client.complete(
        [{"role": "system", "content": _SYS}, {"role": "user", "content": draft}],
        task="claim_extract",
        draft=draft,
        thinking=False,
    )
    claims = _parse(resp.content)
    return claims


def _parse(content: str) -> list[Claim]:
    if not isinstance(content, str):  # R12: never re-raise inside the except on non-str
        return []
    try:
        start, end = content.find("{"), content.rfind("}")
        data = json.loads(content[start : end + 1])
        out = []
        for c in data.get("claims", []):
            t = c.get("type", "inference")
            out.append(Claim(text=str(c.get("text", "")).strip(),
                             type=t if t in _VALID else "inference"))
        return [c for c in out if c.text]
    except Exception:
        # robust fallback: one claim, untyped
        return [Claim(text=line.strip(), type="inference")
                for line in content.splitlines() if line.strip()]

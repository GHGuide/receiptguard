"""Deterministic offline responses used when no API key is set.

Keeps the full pipeline + demo runnable with zero network. The verification
logic (gateway/verify/recovery) is identical in mock and real mode; only the
*content* of LLM turns is synthesized here.
"""
from __future__ import annotations

import json
import re

_TOOL_HINTS = ("refund", "inventory", "stock", "units", "sent", "email", "order",
               "balance", "ticket", "issued", "processed", "found", "result", "$")
_ABSENCE_HINTS = ("no results", "nothing found", "not found", "no record", "none found",
                  "no matching", "couldn't find", "could not find")
_OPINION_HINTS = ("i think", "i recommend", "i suggest", "should", "probably", "in my opinion")


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip(" -•\t") for p in parts if p.strip(" -•\t")]


def _type_claim(sentence: str) -> str:
    low = sentence.lower()
    if any(h in low for h in _ABSENCE_HINTS):
        return "absence"
    if any(h in low for h in _OPINION_HINTS):
        return "opinion"
    if any(h in low for h in _TOOL_HINTS) or re.search(r"\d", sentence):
        return "tool_derived"
    return "inference"


def _extract_claims(draft: str) -> str:
    claims = [{"text": s, "type": _type_claim(s)} for s in _split_sentences(draft)]
    return json.dumps({"claims": claims})


def _adjudicate(unbacked: list[dict]) -> tuple[str, str]:
    if not unbacked:
        return ("All claims are backed by signed tool receipts. PROCEED.",
                "Every tool-derived claim matched a receipt; nothing to block.")
    bullets = "; ".join(f'"{u.get("text","")}" ({u.get("reason","unbacked")})' for u in unbacked)
    content = f"BLOCKED: {len(unbacked)} claim(s) lack a matching tool receipt."
    reasoning = (
        "I compared each tool-derived claim against the signed receipt ledger. "
        f"These have no backing receipt and must not be asserted: {bullets}. "
        "Downgrading to ungrounded and triggering replan: the agent must call the "
        "real tool before restating these claims."
    )
    return content, reasoning


def respond(task: str, messages: list[dict], **kw) -> tuple[str, str]:
    """Return (content, reasoning_content) for a given task."""
    last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    if task == "claim_extract":
        draft = kw.get("draft", last_user)
        return _extract_claims(draft), ""
    if task == "adjudicate":
        return _adjudicate(kw.get("unbacked", []))
    # generic fallback
    return ("OK", "")

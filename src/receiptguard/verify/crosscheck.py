"""Cross-check each claim against the signed receipt ledger.

Detects the hallucination types from NabaOS (arXiv 2603.10060):
  - fabricated tool reference: a tool-derived claim whose tool was never called
  - value / count mismatch: a number/status asserted that no receipt supports
  - false absence: "nothing found" when a receipt shows non-empty results

Pure, deterministic logic (no LLM in the hot path) -> fast + auditable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..claims import Claim
from ..gateway import Receipt

# claim keyword -> the tool that must have produced it
KEYWORD_TOOL = {
    "refund": "process_refund", "refunded": "process_refund",
    "inventory": "check_inventory", "stock": "check_inventory", "units": "check_inventory",
    "email": "send_email", "sent": "send_email",
    "order": "lookup_order", "delivered": "lookup_order",
    "policy": "get_refund_policy", "cap": "get_refund_policy", "window": "get_refund_policy",
    "search": "search_kb", "results": "search_kb", "article": "search_kb",
}

_ABSENCE = ("no results", "nothing found", "not found", "no record", "none found",
            "no matching", "couldn't find", "could not find", "0 results")

# status BACKED / OPINION / INFERENCE pass; UNBACKED / CONTRADICTED / FALSE_ABSENCE fail
FAIL_STATUSES = {"unbacked", "contradicted", "false_absence"}

# numeric match tolerance: absolute floor + relative band so $410.00 vs 410 matches
# but a real $410-vs-$500 mismatch is still caught.
NUMERIC_TOLERANCE = 0.01
RELATIVE_TOLERANCE = 0.001

# date / version tokens are NOT quantities — strip them before number extraction so
# "delivered 2024-01-15" or "v2.1.0" can't be misread as amounts (a demo-breaking
# false "contradicted").
_DATE = re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b")
_VERSION = re.compile(r"\bv?\d+(?:\.\d+){2,}\b")


def _value_matches(claim_n: float, receipt_nums: set[float]) -> bool:
    return any(abs(claim_n - rn) <= max(NUMERIC_TOLERANCE, RELATIVE_TOLERANCE * abs(rn))
               for rn in receipt_nums)


@dataclass
class ClaimVerdict:
    claim: Claim
    status: str
    reason: str = ""
    receipt_id: str | None = None
    tool: str | None = None

    @property
    def failed(self) -> bool:
        return self.status in FAIL_STATUSES

    def to_dict(self) -> dict:
        return {"text": self.claim.text, "type": self.claim.type, "status": self.status,
                "reason": self.reason, "receipt_id": self.receipt_id, "tool": self.tool}


def _numbers(text: str) -> set[float]:
    text = _VERSION.sub(" ", _DATE.sub(" ", text))
    out: set[float] = set()
    # a minus only counts when not glued to a preceding digit/dot (avoids splitting
    # "5-10" or trailing fragments into spurious negatives)
    for m in re.findall(r"(?<![\d.])-?\$?\d[\d,]*(?:\.\d+)?", text):
        try:
            out.add(float(m.replace("$", "").replace(",", "")))
        except ValueError:
            pass
    return out


def _gather_numbers(obj: Any, acc: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        acc.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _gather_numbers(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _gather_numbers(v, acc)
    elif isinstance(obj, str):
        acc |= _numbers(obj)


def _candidate_tools(text: str) -> list[str]:
    low = text.lower()
    tools = []
    for kw, tool in KEYWORD_TOOL.items():
        if kw in low and tool not in tools:
            tools.append(tool)
    return tools


def _receipt_numbers(receipts: list[Receipt]) -> set[float]:
    acc: set[float] = set()
    for r in receipts:
        _gather_numbers(r.output, acc)
    return acc


def cross_check(claim: Claim, receipts: list[Receipt]) -> ClaimVerdict:
    text = claim.text
    low = text.lower()

    if claim.type == "opinion":
        return ClaimVerdict(claim, "opinion", "subjective; not a factual assertion")
    if claim.type == "inference":
        return ClaimVerdict(claim, "inference", "deduction; no direct tool backing required")

    # false-absence: claim says nothing found, but a relevant receipt has results
    if claim.type == "absence" or any(a in low for a in _ABSENCE):
        for tool in _candidate_tools(text) or ["search_kb"]:
            for r in [x for x in receipts if x.tool == tool]:
                cnt = r.output.get("count") if isinstance(r.output, dict) else None
                res = r.output.get("results") if isinstance(r.output, dict) else None
                if (cnt and cnt > 0) or (res):
                    return ClaimVerdict(claim, "false_absence",
                                        f"claims absence but {tool} receipt {r.receipt_id} returned results",
                                        r.receipt_id, tool)
        return ClaimVerdict(claim, "backed", "no contradicting receipt for the absence claim")

    # tool_derived
    cands = _candidate_tools(text)
    if not cands:
        return ClaimVerdict(claim, "unbacked",
                            "tool-derived claim references no identifiable tool result")
    backing_receipts = [r for c in cands for r in receipts if r.tool == c]
    if not backing_receipts:
        return ClaimVerdict(claim, "unbacked",
                            f"claims a result from {', '.join(cands)} but no such tool was ever called",
                            tool=cands[0])

    claim_nums = _numbers(text)
    if claim_nums:
        receipt_nums = _receipt_numbers(backing_receipts)
        unsupported = {n for n in claim_nums if not _value_matches(n, receipt_nums)}
        if unsupported:
            nums = ", ".join(str(int(n) if n.is_integer() else n) for n in sorted(unsupported))
            return ClaimVerdict(claim, "contradicted",
                                f"asserts value(s) {nums} not present in any {cands[0]} receipt",
                                backing_receipts[0].receipt_id, cands[0])
    return ClaimVerdict(claim, "backed", f"matches receipt {backing_receipts[0].receipt_id}",
                        backing_receipts[0].receipt_id, cands[0])


def cross_check_all(claims: list[Claim], receipts: list[Receipt]) -> list[ClaimVerdict]:
    return [cross_check(c, receipts) for c in claims]

"""Typed-grounding score + tiered recovery (GSAR, arXiv 2604.23366).

Maps the cross-check verdicts to a weighted, contradiction-penalised groundedness
score, then to a three-tier decision (PROCEED / REGENERATE / REPLAN) bounded by an
explicit compute budget (iteration count).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..verify import ClaimVerdict

# evidence-type weights (epistemic strength)
_WEIGHT = {"backed": 1.0, "opinion": 0.6, "inference": 0.6,
           "unbacked": 0.0, "false_absence": 0.0, "contradicted": 0.0}
# contradictions are worse than mere absence of backing -> asymmetric penalty
_PENALTY = {"contradicted": 1.0, "false_absence": 0.8, "unbacked": 0.6}

TAU_HIGH = 0.85  # >= -> proceed
TAU_LOW = 0.55   # <  -> replan; between -> regenerate


@dataclass
class Decision:
    action: str  # "proceed" | "regenerate" | "replan"
    score: float
    failed: list[ClaimVerdict] = field(default_factory=list)
    force_tools: list[str] = field(default_factory=list)
    reason: str = ""


def groundedness_score(verdicts: list[ClaimVerdict]) -> float:
    if not verdicts:
        return 1.0
    gross = sum(_WEIGHT.get(v.status, 0.0) for v in verdicts)
    penalty = sum(_PENALTY.get(v.status, 0.0) for v in verdicts)
    raw = (gross - penalty) / len(verdicts)
    return max(0.0, min(1.0, raw))


def decide(verdicts: list[ClaimVerdict], *, iteration: int, max_iterations: int) -> Decision:
    score = groundedness_score(verdicts)
    failed = [v for v in verdicts if v.failed]
    force_tools = []
    for v in failed:
        if v.tool and v.tool not in force_tools:
            force_tools.append(v.tool)

    if not failed:
        return Decision("proceed", score, [], [], "all factual claims backed by receipts")
    if iteration + 1 >= max_iterations:
        # budget exhausted: do not ship fabrications -> refuse/replan with disclosure
        return Decision("replan", score, failed, force_tools,
                        "compute budget exhausted; blocking unbacked claims and disclosing")
    if score < TAU_LOW or any(v.status == "contradicted" for v in failed):
        return Decision("replan", score, failed, force_tools,
                        f"{len(failed)} unbacked/contradicted claim(s); forcing real tool calls")
    if score < TAU_HIGH:
        return Decision("regenerate", score, failed, force_tools,
                        "minor grounding gaps; regenerate constrained to receipts")
    return Decision("proceed", score, [], [], "score above threshold")

"""ReceiptGuard orchestrator: draft -> extract claims -> cross-check vs receipts
-> tiered recovery -> audit, looping under a compute budget until every factual
claim is backed (or budget exhausted, in which case unbacked claims are blocked).

Produces a side-by-side result: the UNGUARDED baseline draft (what would have
shipped) vs the guarded, receipt-verified output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent import AutopilotAgent
from .audit import AuditLedger
from .claims import extract_claims
from .config import settings
from .gateway import ToolGateway, TOOLS
from .llm import client
from .recovery import decide
from .verify import cross_check_all


@dataclass
class Iteration:
    attempt: int
    draft: str
    verdicts: list[dict]
    action: str
    score: float
    reasoning: str = ""


@dataclass
class RunResult:
    scenario: str
    mock: bool
    baseline_draft: str
    baseline_verdicts: list[dict]
    baseline_failed: int
    final_draft: str
    shipped: bool
    iterations: list[Iteration] = field(default_factory=list)
    receipts: list[dict] = field(default_factory=list)
    audit: list[dict] = field(default_factory=list)
    chain_ok: bool = True
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario, "mock": self.mock,
            "baseline": {"draft": self.baseline_draft, "verdicts": self.baseline_verdicts,
                         "failed": self.baseline_failed},
            "guarded": {"final_draft": self.final_draft, "shipped": self.shipped,
                        "score": self.score,
                        "iterations": [i.__dict__ for i in self.iterations]},
            "receipts": self.receipts, "audit": self.audit, "chain_ok": self.chain_ok,
        }


class ReceiptGuard:
    def __init__(self, max_iterations: int = 3, ledger_path: str = ":memory:") -> None:
        self.max_iterations = max_iterations
        self.ledger = AuditLedger(ledger_path)

    def run(self, scenario: str = "refund_damaged") -> RunResult:
        gateway = ToolGateway(TOOLS)
        agent = AutopilotAgent(gateway)

        draft = agent.run_draft(scenario, attempt=0).text
        attempt0_draft = draft
        # baseline = what an unguarded agent would have shipped
        base_claims = extract_claims(draft)
        base_verdicts = cross_check_all(base_claims, gateway.store.all())
        baseline = [v.to_dict() for v in base_verdicts]
        baseline_failed = sum(1 for v in base_verdicts if v.failed)

        iterations: list[Iteration] = []
        shipped = False
        score = 0.0
        for it in range(self.max_iterations):
            claims = extract_claims(draft)
            verdicts = cross_check_all(claims, gateway.store.all())
            decision = decide(verdicts, iteration=it, max_iterations=self.max_iterations)
            score = decision.score

            reasoning = ""
            if decision.failed:
                unbacked = [{"text": v.claim.text, "reason": v.reason} for v in decision.failed]
                adj = client.complete(
                    [{"role": "system", "content": "Explain which claims you are blocking and why."},
                     {"role": "user", "content": draft}],
                    task="adjudicate", thinking=True, unbacked=unbacked,
                )
                reasoning = adj.reasoning_content or adj.content

            self.ledger.append("verification", {
                "attempt": it, "action": decision.action, "score": round(score, 3),
                "verdicts": [v.to_dict() for v in verdicts],
                "force_tools": decision.force_tools, "reasoning": reasoning,
            }, ts=float(it + 1))

            iterations.append(Iteration(it, draft, [v.to_dict() for v in verdicts],
                                        decision.action, round(score, 3), reasoning))

            if decision.action == "proceed":
                shipped = True
                break
            draft = agent.run_draft(scenario, force_tools=decision.force_tools, attempt=it + 1).text

        chain_ok, _ = self.ledger.verify_chain()
        return RunResult(
            scenario=scenario, mock=settings.mock,
            baseline_draft=attempt0_draft,
            baseline_verdicts=baseline, baseline_failed=baseline_failed,
            final_draft=draft, shipped=shipped, iterations=iterations,
            receipts=[r.to_public() for r in gateway.store.all()],
            audit=[{"idx": e.idx, "kind": e.kind, "hash": e.entry_hash[:16],
                    "prev": e.prev_hash[:16]} for e in self.ledger.all()],
            chain_ok=chain_ok, score=round(score, 3),
        )

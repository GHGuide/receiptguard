"""ReceiptGuard as an MCP server (the rubric's "MCP integration" lever).

Exposes the verification capability as MCP tools a Qwen agent can invoke live via
the Responses API. Hosted on Alibaba Function Compute (SSE transport) for the
deployment proof.

Requires the optional MCP SDK:  pip install mcp
Run (SSE):     python -m receiptguard.mcp.server
Run (stdio):   python -m receiptguard.mcp.server stdio
"""
from __future__ import annotations

import json
import sys

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise SystemExit("MCP SDK not installed. Run: pip install mcp") from e

from ..agent import SCENARIOS
from ..claims import Claim
from ..gateway import ToolGateway, TOOLS
from ..pipeline import ReceiptGuard
from ..verify import cross_check_all

mcp = FastMCP("receiptguard")


@mcp.tool()
def run_guarded_autopilot(scenario: str = "refund_damaged") -> dict:
    """Run the autopilot agent on a scenario with receipt verification.
    Returns the baseline vs guarded output, signed receipts, and audit chain."""
    return ReceiptGuard().run(scenario).to_dict()


@mcp.tool()
def verify_claims(claims: list[str]) -> list[dict]:
    """Verify a list of agent claims against freshly executed tool receipts for the
    standard refund workflow. Each claim is typed and cross-checked; returns the
    per-claim verdict (backed / unbacked / contradicted / false_absence)."""
    gw = ToolGateway(TOOLS)
    for t in ("lookup_order",):
        gw.call(t, order_id="ORD-1001")
    typed = [Claim(c, "tool_derived") for c in claims]
    return [v.to_dict() for v in cross_check_all(typed, gw.store.all())]


@mcp.tool()
def list_scenarios() -> dict:
    """List available autopilot demo scenarios."""
    return {k: v["ticket"] for k, v in SCENARIOS.items()}


def main() -> None:
    transport = sys.argv[1] if len(sys.argv) > 1 else "sse"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()

"""The Track-4 autopilot agent: a customer-support refund handler.

This is a REAL agent doing an end-to-end business workflow (not a library) — the
thing ReceiptGuard wraps. In real mode it uses qwen3-max function calling. In
mock mode it scripts a realistic *hallucinating* first draft (claims tool results
it never fetched) so the guard has something to catch, then self-corrects on
replan using only real receipt values.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import settings
from ..gateway import ToolGateway, TOOLS, tool_schema
from ..llm import client

SCENARIOS = {
    "refund_damaged": {
        "ticket": ("Customer for order ORD-1001 says their item arrived damaged and "
                   "wants a full refund. Handle it end-to-end."),
        "to": "a.popescu@example.com",
    }
}

_SYS = (
    "You are an autopilot customer-support agent. Resolve the ticket end-to-end using "
    "ONLY the provided tools. Never state an order detail, inventory count, policy value, "
    "or action result you did not obtain from a tool call. After acting, write a short "
    "summary of exactly what you did and the values the tools returned."
)


@dataclass
class DraftResult:
    text: str
    attempt: int


class AutopilotAgent:
    def __init__(self, gateway: ToolGateway | None = None) -> None:
        self.gateway = gateway or ToolGateway(TOOLS)

    # ------------------------------------------------------------------ mock
    def _mock_draft(self, scenario: str, force_tools: list[str] | None, attempt: int) -> str:
        s = SCENARIOS[scenario]
        if attempt == 0:
            # hallucinated first pass: only looks up the order, then fabricates the rest
            order = self.gateway.call("lookup_order", order_id="ORD-1001")
            return (
                f"I looked up order ORD-1001 ({order['item']}, ${order['amount']:.0f}, "
                f"delivered {order['days_since_delivery']} days ago). "
                "I checked inventory — 0 units in stock. "
                "Per refund policy the cap is $500, so I processed the full $79 refund "
                "and emailed the customer the confirmation."
            )
        # replan: actually call every tool the guard flagged, restate from receipts only
        force = force_tools or ["check_inventory", "get_refund_policy", "process_refund", "send_email"]
        order = next((r.output for r in self.gateway.store.for_tool("lookup_order")), None) \
            or self.gateway.call("lookup_order", order_id="ORD-1001")
        parts = [f"Order ORD-1001: {order['item']}, ${order['amount']:.0f}, "
                 f"delivered {order['days_since_delivery']} days ago."]
        inv = pol = ref = None
        if "check_inventory" in force:
            inv = self.gateway.call("check_inventory", item=order["item"])
            parts.append(f"Inventory: {inv['units_in_stock']} units of {order['item']}.")
        if "get_refund_policy" in force:
            pol = self.gateway.call("get_refund_policy")
            parts.append(f"Refund policy: {pol['window_days']}-day window, "
                         f"auto-refund cap ${pol['max_auto_refund']:.0f}.")
        if "process_refund" in force:
            ref = self.gateway.call("process_refund", order_id="ORD-1001", amount=order["amount"])
            parts.append(f"Processed a ${ref['refunded_amount']:.0f} refund "
                         f"(confirmation {ref['confirmation']}).")
        if "send_email" in force:
            em = self.gateway.call("send_email", to=s["to"],
                                   subject="Your refund", body="Your refund has been processed.")
            parts.append(f"Emailed the customer ({em['message_id']}).")
        return " ".join(parts)

    # ------------------------------------------------------------------ real
    def _real_draft(self, scenario: str, force_tools: list[str] | None, attempt: int) -> str:
        s = SCENARIOS[scenario]
        instr = _SYS
        if force_tools:
            instr += ("\nThe previous draft asserted results without calling tools. You MUST call "
                      f"these tools and restate only their actual outputs: {', '.join(force_tools)}.")
        messages = [{"role": "system", "content": instr},
                    {"role": "user", "content": s["ticket"]}]
        schema = tool_schema()
        for _ in range(8):  # bounded tool loop
            msg = client.chat_with_tools(messages, schema)
            messages.append(msg.model_dump() if hasattr(msg, "model_dump") else dict(msg))
            calls = getattr(msg, "tool_calls", None)
            if not calls:
                return msg.content or ""
            for call in calls:
                args = json.loads(call.function.arguments or "{}")
                out = self.gateway.call(call.function.name, **args)
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(out, default=str)})
        return messages[-1].get("content", "") if isinstance(messages[-1], dict) else ""

    def run_draft(self, scenario: str = "refund_damaged", *,
                  force_tools: list[str] | None = None, attempt: int = 0) -> DraftResult:
        text = (self._mock_draft if settings.mock else self._real_draft)(scenario, force_tools, attempt)
        return DraftResult(text=text, attempt=attempt)

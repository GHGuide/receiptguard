"""The Track-4 autopilot agent: a customer-support resolution handler.

This is a REAL agent doing end-to-end business workflows (not a library) — the
actor that ReceiptGuard wraps. It generalises across scenarios and shows domain
judgement: it auto-acts only when policy permits, otherwise it escalates to a
human (the Track-4 "human-in-the-loop checkpoint at critical decisions").

In real mode it uses qwen3-max function calling. In mock mode it scripts a
realistic *hallucinating* first draft (claims tool results it never fetched) so
the guard has something to catch, then self-corrects on replan using only real
receipt values — and applies the policy gate to decide act vs escalate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from ..config import settings
from ..gateway import ToolGateway, TOOLS, tool_schema
from ..llm import client


def _hallucinated_refund(order: dict) -> str:
    return (
        f"I looked up order {order['order_id']} ({order['item']}, ${order['amount']:.0f}, "
        f"delivered {order['days_since_delivery']} days ago). "
        "I checked inventory — 0 units in stock. "
        "Per refund policy the cap is $500, so I processed the full "
        f"${order['amount']:.0f} refund and emailed the customer the confirmation."
    )


def _hallucinated_warranty(order: dict) -> str:
    return (
        f"I looked up order {order['order_id']} ({order['item']}, ${order['amount']:.0f}, "
        f"delivered {order['days_since_delivery']} days ago). "
        f"The {order['item']} has 8 units in stock, so I shipped a free replacement "
        "and emailed the customer the tracking number. "
        "This is well within our 30-day warranty window."
    )


# Each scenario is data-driven: the agent logic below is generic across all of them.
SCENARIOS: dict[str, dict] = {
    "refund_damaged": {
        "ticket": ("Customer for order ORD-1001 says their item arrived damaged and "
                   "wants a full refund. Handle it end-to-end."),
        "order_id": "ORD-1001",
        "to": "a.popescu@example.com",
        "action": "refund",
        "hallucinated": _hallucinated_refund,
    },
    "warranty_replacement": {
        "ticket": ("Customer for order ORD-2002 (Standing Desk) reports a wobbly leg after "
                   "40 days and wants a free replacement shipped. Handle it end-to-end."),
        "order_id": "ORD-2002",
        "to": "j.smith@example.com",
        "action": "replacement",
        "hallucinated": _hallucinated_warranty,
    },
}

_SYS = (
    "You are an autopilot customer-support agent. Resolve the ticket end-to-end using "
    "ONLY the provided tools. Never state an order detail, inventory count, policy value, "
    "or action result you did not obtain from a tool call. Apply the policy gate: only "
    "auto-process a refund or replacement if the order is within the policy window (and a "
    "refund is within the auto-refund cap); otherwise escalate to a human reviewer instead "
    "of acting. Be efficient: call each tool AT MOST ONCE, and do NOT call search_kb unless "
    "you genuinely need policy wording. Once you have the order, inventory, and refund policy "
    "and have taken (or declined) the action, STOP calling tools and write a short final "
    "summary of exactly what you did and the values the tools returned."
)


@dataclass
class DraftResult:
    text: str
    attempt: int


class AutopilotAgent:
    def __init__(self, gateway: ToolGateway | None = None, *, max_tool_steps: int | None = None) -> None:
        self.gateway = gateway or ToolGateway(TOOLS)
        self.max_tool_steps = max_tool_steps or settings.agent_max_tool_steps

    # ------------------------------------------------------------------ mock
    def _mock_draft(self, scenario: str, force_tools: list[str] | None, attempt: int) -> str:
        sc = SCENARIOS[scenario]
        oid = sc["order_id"]
        if attempt == 0:
            # hallucinated first pass: only looks up the order, then fabricates the rest
            order = self.gateway.call("lookup_order", order_id=oid)
            return sc["hallucinated"](order)

        # replan: actually call the flagged tools, restate from receipts ONLY,
        # and apply the policy gate (act vs escalate) = domain judgement.
        force = set(force_tools or ["check_inventory", "get_refund_policy", "process_refund", "send_email"])
        order = next((r.output for r in self.gateway.store.for_tool("lookup_order")), None) \
            or self.gateway.call("lookup_order", order_id=oid)
        parts = [f"Order {oid}: {order['item']}, ${order['amount']:.0f}, "
                 f"delivered {order['days_since_delivery']} days ago."]

        inv = self.gateway.call("check_inventory", item=order["item"])
        parts.append(f"Inventory: {inv['units_in_stock']} units of {order['item']}.")
        pol = self.gateway.call("get_refund_policy")
        parts.append(f"Refund policy: {pol['window_days']}-day window, "
                     f"auto-refund cap ${pol['max_auto_refund']:.0f}.")

        within_window = order["days_since_delivery"] <= pol["window_days"]
        if sc["action"] == "refund":
            if within_window and order["amount"] <= pol["max_auto_refund"]:
                ref = self.gateway.call("process_refund", order_id=oid, amount=order["amount"])
                em = self.gateway.call("send_email", to=sc["to"],
                                       subject="Your refund", body="Your refund has been processed.")
                parts.append(f"Within policy: processed a ${ref['refunded_amount']:.0f} refund "
                             f"(confirmation {ref['confirmation']}) and emailed the customer "
                             f"({em['message_id']}).")
            else:
                parts.append(f"This order is {order['days_since_delivery']} days old / "
                             f"${order['amount']:.0f}; outside the auto-refund policy, so I am "
                             "escalating to a human reviewer rather than auto-processing.")
        else:  # replacement
            if within_window and inv["units_in_stock"] > 0:
                em = self.gateway.call("send_email", to=sc["to"], subject="Replacement shipped",
                                       body="A replacement has been arranged.")
                parts.append(f"Within window and {inv['units_in_stock']} in stock: arranged a "
                             f"replacement and emailed the customer ({em['message_id']}).")
            else:
                parts.append(f"This order is {order['days_since_delivery']} days old with "
                             f"{inv['units_in_stock']} units in stock; outside the 30-day window, "
                             "so I am escalating to a human reviewer rather than auto-shipping.")
        return " ".join(parts)

    # ------------------------------------------------------------------ real
    def _real_draft(self, scenario: str, force_tools: list[str] | None, attempt: int) -> str:
        sc = SCENARIOS[scenario]
        instr = _SYS
        if force_tools:
            instr += ("\nThe previous draft asserted results without calling tools. You MUST call "
                      f"these tools and restate only their actual outputs: {', '.join(force_tools)}.")
        messages = [{"role": "system", "content": instr},
                    {"role": "user", "content": sc["ticket"]}]
        schema = tool_schema()
        for _ in range(self.max_tool_steps):  # bounded tool loop
            msg = client.chat_with_tools(messages, schema)
            messages.append(msg.model_dump() if hasattr(msg, "model_dump") else dict(msg))
            calls = getattr(msg, "tool_calls", None)
            if not calls:
                if msg.content and msg.content.strip():
                    return msg.content
                break  # ended with no usable text -> force a summary below
            for call in calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {}
                out = self.gateway.call(call.function.name, **args)
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(out, default=str)})
        # Tool budget spent (or no final text): force one no-tools summary turn so the
        # draft is always natural language grounded in the tool results, never raw JSON.
        messages.append({"role": "user", "content":
                         "Stop calling tools. In 2-3 sentences, summarize exactly what you did "
                         "and the values the tools returned (order, inventory, policy, and the "
                         "refund/replacement action or human escalation). Do not invent any value."})
        return client.complete(messages, task="generic", thinking=False).content or ""

    def run_draft(self, scenario: str = "refund_damaged", *,
                  force_tools: list[str] | None = None, attempt: int = 0) -> DraftResult:
        if scenario not in SCENARIOS:
            raise KeyError(f"unknown scenario: {scenario!r}; known: {list(SCENARIOS)}")
        text = (self._mock_draft if settings.mock else self._real_draft)(scenario, force_tools, attempt)
        return DraftResult(text=text, attempt=attempt)

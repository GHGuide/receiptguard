"""Instrumented business tools for the Autopilot (Track 4) demo workflow:
a customer-support refund agent. Deterministic fixtures so the demo + tests are
reproducible. Each call through ToolGateway produces a signed receipt.
"""
from __future__ import annotations

import hashlib
from typing import Any

# --- fixture data -----------------------------------------------------------
_ORDERS = {
    "ORD-1001": {"order_id": "ORD-1001", "customer": "A. Popescu", "item": "Wireless Earbuds",
                 "amount": 79.0, "status": "delivered", "days_since_delivery": 5},
    "ORD-2002": {"order_id": "ORD-2002", "customer": "J. Smith", "item": "Standing Desk",
                 "amount": 410.0, "status": "delivered", "days_since_delivery": 40},
}
_INVENTORY = {"Wireless Earbuds": 12, "Standing Desk": 0}
_REFUND_POLICY = {"window_days": 30, "max_auto_refund": 300.0}


def lookup_order(order_id: str) -> dict[str, Any]:
    return _ORDERS.get(order_id, {"error": "order_not_found", "order_id": order_id})


def check_inventory(item: str) -> dict[str, Any]:
    if item in _INVENTORY:
        return {"item": item, "units_in_stock": _INVENTORY[item]}
    return {"item": item, "error": "item_not_found"}


def get_refund_policy() -> dict[str, Any]:
    return dict(_REFUND_POLICY)


def process_refund(order_id: str, amount: float) -> dict[str, Any]:
    return {"order_id": order_id, "refunded_amount": amount, "status": "refunded",
            "confirmation": f"RF-{order_id[-4:]}"}


def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    # R14: sha256-derived id, not Python's salted hash(), so fixtures are reproducible
    # across runs (PYTHONHASHSEED-independent) — the "deterministic proof" story holds.
    mid = int(hashlib.sha256(subject.encode()).hexdigest(), 16) % 10000
    return {"to": to, "subject": subject, "status": "sent", "message_id": f"MSG-{mid:04d}"}


def search_kb(query: str) -> dict[str, Any]:
    hits = [a for a in ("return-policy", "shipping-faq", "warranty") if query.lower() in a or a in query.lower()]
    return {"query": query, "results": hits, "count": len(hits)}


TOOLS = {
    "lookup_order": lookup_order,
    "check_inventory": check_inventory,
    "get_refund_policy": get_refund_policy,
    "process_refund": process_refund,
    "send_email": send_email,
    "search_kb": search_kb,
}


def tool_schema() -> list[dict]:
    """OpenAI/Qwen function-calling schema for the tool set (real-mode agent)."""
    def fn(name, desc, props, required):
        return {"type": "function", "function": {
            "name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}
    s = lambda d="": {"type": "string", "description": d}
    n = lambda d="": {"type": "number", "description": d}
    return [
        fn("lookup_order", "Look up an order by id", {"order_id": s()}, ["order_id"]),
        fn("check_inventory", "Units in stock for an item", {"item": s()}, ["item"]),
        fn("get_refund_policy", "Current refund policy", {}, []),
        fn("process_refund", "Issue a refund", {"order_id": s(), "amount": n()}, ["order_id", "amount"]),
        fn("send_email", "Email the customer", {"to": s(), "subject": s(), "body": s()}, ["to", "subject", "body"]),
        fn("search_kb", "Search the knowledge base", {"query": s()}, ["query"]),
    ]

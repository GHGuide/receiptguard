# Integration Guide — drop ReceiptGuard onto your Qwen agent

ReceiptGuard is a **verification layer**, not a framework. You keep your agent;
you route its tool calls through the gateway and verify its drafts.

## Scope & production-readiness (honest)
- **Production-ready:** the gateway, receipt signing, claim cross-check, tiered
  recovery, and hash-chained audit ledger are deterministic and tested.
- **Proof-of-concept:** the bundled `AutopilotAgent` + fixture tools (`gateway/tools.py`)
  are a demo workload. Swap them for your real tools to ship.

## 1. Wrap your tools
Replace the fixtures in `gateway/tools.py` with your real callables:
```python
TOOLS = {
    "lookup_order": shopify.get_order,        # your real ERP/CRM/API calls
    "process_refund": stripe.refund,
    "check_inventory": wms.stock,
}
```
Every call through `ToolGateway.call(...)` is executed once and emits a signed
receipt. The agent must use the gateway — that's the whole guarantee.

## 2. Verify your agent's draft
```python
from receiptguard.pipeline import ReceiptGuard
result = ReceiptGuard(max_iterations=3, ledger_path="receipts.db").run(scenario)
# result.shipped, result.final_draft, result.score, result.chain_ok
```
Or call the pieces directly: `extract_claims` → `cross_check_all` → `decide`.

## 3. Or expose it over MCP
`python -m receiptguard.mcp.server` serves `run_guarded_autopilot`, `verify_claims`,
and `list_scenarios` as MCP tools any Qwen agent can call live (SSE transport;
hosted on Alibaba Function Compute for the deployment proof). `stdio` transport
for local agents: `python -m receiptguard.mcp.server stdio`.

## 4. Add a scenario (data-driven)
Add an entry to `SCENARIOS` in `agent/autopilot.py` with `ticket`, `order_id`,
`to`, `action` (`refund`|`replacement`), and a `hallucinated(order)` draft. The
agent logic, policy gate, verifier, and UI pick it up automatically.

## Config
`.env`: `DASHSCOPE_API_KEY` (Alibaba Model Studio), `RG_RECEIPT_SECRET` (keep
server-side — the agent must never see it), `RG_LEDGER_PATH` (SQLite path or point
the same schema at Alibaba RDS PostgreSQL), `RG_AGENT_MAX_TOOL_STEPS`,
`RG_THINKING_BUDGET`.

# ReceiptGuard

**The agent that can't lie about what its tools did.**

A verification gateway for Qwen agents. Every tool call gets an unforgeable
HMAC-signed **receipt**; every claim in the agent's output is typed by epistemic
source and **cross-checked against those receipts**. Any claim a real tool didn't
produce is caught and the agent is forced to regenerate **before the action
commits** — and every decision is written to a tamper-evident, hash-chained audit
log.

> Global AI Hackathon Series with Qwen Cloud — **Track 4: Autopilot Agent**

Production agents fail by **fabricating tool results** — "I issued the refund",
"inventory shows 0 units", "I sent the email" — when the tool was never called or
returned something else. Everyone verifies whether the agent *retrieved* the right
thing; nobody checks what it *claims its tools did*. ReceiptGuard closes that
retrieve→act gap.

---

## The mechanism

```
ticket ─▶ Autopilot agent (qwen3-max) ──tools──▶ ToolGateway ──▶ HMAC-signed receipts
                  │                                                      │
                  ▼ draft answer                                         │
        Claim extractor (qwen-flash)  ── atomic claims, typed ──┐        │
                                                                ▼        ▼
                                              Cross-check claims vs receipts
                                                                │
                                        ┌───────────────────────┤
                                        ▼ all backed             ▼ unbacked / contradicted
                                     PROCEED            Tiered recovery (GSAR): regenerate / replan
                                                          (qwen3-max thinking adjudicates,
                                                           reasoning_content = audit reason)
                                        └──────────┬────────────┘
                                                   ▼
                              SHA-256 hash-chained append-only audit ledger
```

1. **Receipts** — every tool call routes through `ToolGateway`, which emits
   `HMAC(secret, {tool, args_hash, output_hash, snippet, ts})`. The agent never
   sees the secret, so it cannot forge a receipt for a tool it never called.
2. **Typed claims** — `qwen-flash` splits the answer into atomic claims, each
   tagged `tool_derived | inference | absence | opinion`
   (NabaOS *pramana* taxonomy, arXiv 2603.10060).
3. **Cross-check** — each tool-derived claim is matched to the receipt ledger:
   missing receipt → *unbacked*; value/count mismatch → *contradicted*;
   "nothing found" with a non-empty receipt → *false absence*.
4. **Tiered recovery** — groundedness score → `proceed / regenerate / replan`
   under an explicit compute budget (GSAR, arXiv 2604.23366). `qwen3-max`
   thinking-mode adjudicates contested claims; its `reasoning_content` is stored
   as the human-readable justification.
5. **Audit** — every decision is appended to a SHA-256 hash-chained ledger;
   tampering with any row breaks the chain (EU AI Act Art. 12 record-keeping).

Research base (both verified, **no public code** → original implementation):
NabaOS tool-receipts (arXiv 2603.10060), GSAR typed grounding + recovery
(arXiv 2604.23366).

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# runs fully OFFLINE in deterministic MOCK mode (no API key needed)
PYTHONPATH=src python -m receiptguard.cli run          # baseline vs guarded, in the terminal
PYTHONPATH=src python -m receiptguard.cli serve        # demo UI at http://localhost:8000
PYTHONPATH=src python -m receiptguard.cli bench 200    # detection benchmark + chart
PYTHONPATH=src python -m pytest                         # test suite (7 tests)
```

### Going live on Qwen / Alibaba Cloud
Copy `.env.example` → `.env`, set `DASHSCOPE_API_KEY` (Alibaba Model Studio).
With a key, the agent (`qwen3-max`, thinking mode), claim typer (`qwen-flash`),
and the LLM-judge baseline call real Qwen via the OpenAI-compatible DashScope
endpoint. No key → mock mode, everything still runs.

- **Alibaba-usage proof file:** [`src/receiptguard/llm/qwen.py`](src/receiptguard/llm/qwen.py)
- **MCP server (Function Compute, SSE):** `python -m receiptguard.mcp.server` (needs `pip install mcp`)

---

## Why it scores

| Criterion | How |
|---|---|
| **Innovation 30%** (tiebreaker) | unforgeable cryptographic receipts (not an LLM-judge); MCP server Qwen calls live; `reasoning_content` as audit artifact; two-speed qwen-flash/qwen3-max fleet under a `thinking_budget` |
| **Technical Depth 30%** | deterministic verifier (no LLM in the hot path), modular adapters, hash-chained ledger, reproducible benchmark + ablations |
| **Problem Value 25%** | fabricated tool results are the #1 blocker to autonomous agents; drop-in MCP gateway for any Qwen agent |
| **Presentation 15%** | live split-screen demo: watch the agent get caught lying and self-correct, on the record |

## Benchmark
`receiptguard bench` builds an adversarial set (fabricated reference, value
mismatch, false absence) and compares ReceiptGuard vs an LLM-judge with **no**
receipts. A receipt-free judge structurally cannot verify a plausible fabrication;
ReceiptGuard catches it deterministically at sub-millisecond overhead. Run with a
key for the real qwen-flash judge baseline.

## Layout
```
src/receiptguard/  gateway/(receipts,tools) claims/ verify/ recovery/ audit/ agent/ mcp/ api/ llm/
eval/              adversarial benchmark + chart
tests/             pytest invariants
static/            demo UI
```

License: MIT.

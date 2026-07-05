# ReceiptGuard — Devpost submission text

**Track:** Track 4 — Autopilot Agent
**Repo:** https://github.com/GHGuide/receiptguard
**Elevator pitch:** A support autopilot that provably cannot fabricate a tool result — and escalates anything it can't prove to a human.

---

## Inspiration
The #1 reason autonomous agents don't ship in production isn't that they retrieve the wrong fact — it's that they **confidently report tool results that never happened**: "refund issued," "8 units in stock, replacement shipped," "email sent" — when the tool was never called or returned something else. One hallucinated refund is a direct cash loss and a compliance event, multiplied across support volume. Everyone checks whether the agent *retrieved* the right thing; nobody checks what it *claims its tools did*.

## What it does
ReceiptGuard is a `qwen3.7-max` autopilot that resolves customer-support tickets (refunds, warranty replacements) end-to-end, wrapped in a verification layer that makes fabrication **structurally impossible**:
1. **Unforgeable receipts** — every tool call routes through a gateway that returns an `HMAC(secret, {tool, args_hash, output_hash, ts})` receipt. The agent never sees the secret, so it cannot forge one.
2. **Epistemic claim-typing** — `qwen-flash` splits the agent's answer into atomic claims, each typed `tool_derived | inference | absence | opinion`.
3. **Cross-check** — each tool-derived claim is matched against the receipt ledger: no receipt → *unbacked*; wrong value → *contradicted*; "nothing found" over real results → *false absence*.
4. **Tiered recovery + policy gate** — unbacked claims trigger a budgeted regenerate/replan; `qwen3.7-max` thinking-mode adjudicates (its `reasoning_content` stored as the audit reason). When policy forbids auto-acting (e.g. outside the refund window) the agent **escalates to a human**.
5. **Tamper-evident audit** — every decision lands on a SHA-256 hash-chained ledger; altering any row breaks the chain.

Exposed as an **MCP server** any Qwen agent can install.

## How we built it
FastAPI + Python. `qwen3.7-max` (tool-calling + thinking) and `qwen-flash` (claim typer) via the Alibaba Model Studio OpenAI-compatible endpoint. Deterministic verifier (no LLM in the hot path). SHA-256 hash-chained ledger (SQLite → RDS PostgreSQL). Deployed on **Alibaba Function Compute**. MCP server over the standard SDK.

## Benchmarks (reproducible, real Qwen)
| System | Detection | False-positive | Speed |
|---|---|---|---|
| **ReceiptGuard** | **100%** | 0% | 0.007 ms/claim |
| ablation (no value-check) | 66.7% | 0% | — |
| real `qwen-flash` judge (no receipts) | **0%** | 0% | ~1040 ms/claim |

A real LLM judge with no receipts catches **0%** of the fabrications (they're plausible) and is ~1000× slower. ReceiptGuard hits 100%/0% deterministically because it checks cryptographic receipts, not plausibility. A claim-typing eval shows the typer **fails safe** (100% `tool_derived` recall — mis-types over-verify, never under-verify).

## Challenges
Cryptographic tool-receipts are an emerging 2026 pattern (ZeroClaw, Fetch.ai AEVS) — so we don't claim to invent the primitive. The hard part was the **closed loop**: typing every sentence the agent writes, cross-checking each against a receipt, recovering-or-escalating, and proving it — as a deployed Track-4 autopilot, not a library.

## Accomplishments
Deployed and running on Qwen + Alibaba Cloud; an honest benchmark that survives code review (we show the real 0% judge, not a strawman); a fail-safe claim typer; a tamper-evident audit trail (EU AI Act Art. 12).

## What's next
Broader tool coverage, a larger real-Qwen benchmark, and streaming the `reasoning_content` audit trace live in the UI.

## Built with
Qwen3.7-Max · Qwen-Flash · Alibaba Model Studio (DashScope) · Alibaba Function Compute · RDS PostgreSQL · FastAPI · Python · MCP · HMAC-SHA256

## Alibaba Cloud usage proof
Code file: [`src/receiptguard/llm/qwen.py`](https://github.com/GHGuide/receiptguard/blob/master/src/receiptguard/llm/qwen.py) · Backend deployed on Function Compute (see deploy-proof recording).

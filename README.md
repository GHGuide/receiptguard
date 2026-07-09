# ReceiptGuard

**An autopilot agent that can't lie about what its tools did.**

> Global AI Hackathon Series with Qwen Cloud — **Track 4: Autopilot Agent**

A `qwen3.7-max` agent resolves real support tickets end-to-end (refunds, warranty
replacements). Watch what happens without a guard: it confidently reports *"the
Standing Desk has 8 units in stock, so I shipped a free replacement and emailed
the tracking number"* — when it never checked inventory, never shipped anything,
and the order is 40 days past the warranty window. The tool was never called; the
agent fabricated the result. **This is the #1 blocker to trusting autonomous
agents in production**, and every recall/RAG approach misses it: they check
whether the agent *retrieved* the right fact, not what it *claims its tools did*.

ReceiptGuard makes fabrication structurally impossible. Every tool call routes
through a gateway that returns an unforgeable **HMAC-signed receipt**; every claim
in the agent's answer is typed by epistemic source and **cross-checked against
those receipts**. A claim no real tool produced is caught and the agent is forced
to re-ground **before the action commits** — and when policy forbids auto-acting
(e.g. outside the refund window) the agent **escalates to a human** instead. Every
decision lands in a tamper-evident, hash-chained audit log.

### What one fabrication costs
A fabricated *"refund issued / replacement shipped"* is a direct cash loss plus a
compliance event. A first-order exposure model — every input is a knob you can turn:

```
monthly exposure ≈ monthly tickets × share touching money × fabrication rate × avg refund
```

*Illustrative:* 50,000 tickets/mo × 10% refund/replacement × 1% fabricated × $79 avg
refund (our demo order) ≈ **$3,950/mo** in phantom payouts — before re-contact cost,
chargebacks, or the compliance event. And the legal floor is already set: in
[*Moffatt v. Air Canada*, 2024 BCCRT 149](https://www.canlii.org/en/bc/bccrt/doc/2024/2024bccrt149/2024bccrt149.html)
a tribunal held the airline liable for **one fabricated support answer** — its chatbot
invented a refund policy — awarding the customer ~CAD $812 and ruling that a company
owns what its agent says. (Illustrative model; the only hard number here is the case.)

### Why this isn't "just a guardrail"
A guardrail scores how *confident* the model sounds and filters on a threshold.
ReceiptGuard demands **cryptographic proof that each tool actually ran**: claims
are typed by epistemic source and checked against an HMAC-signed receipt the agent
**cannot forge** — and unbacked claims aren't suppressed, they trigger a budgeted
agent loop that re-runs the real tools and re-grounds the answer before it ships.
Proof-of-execution, not vibe-checking.

![ReceiptGuard architecture](docs/architecture.svg)

**The money shot** — inject a fabrication (red-team toggle) and watch the baseline ship 3 lies
while ReceiptGuard blocks each unbacked claim and re-grounds against signed receipts, with
`qwen3.7-max` reasoning shown live:

![ReceiptGuard catching fabrications live](docs/screenshot-money-shot.png)

**Proven:** 100% fabrication-detection at 0% false-positives, sub-millisecond — while a **real `qwen-flash` judge with no receipts catches 0%** of the same fabrications (and is ~1000× slower). An ablation shows the receipt value-check is load-bearing; claim-typing fails **safe** (100% `tool_derived` recall). Runs live on **Qwen3.7-Max + Qwen-Flash** via Alibaba Model Studio. *(Full table below.)*

**vs the field:** [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw/blob/master/docs/book/src/security/tool-receipts.md) / [Fetch.ai AEVS](https://aevs.fetch.ai/) prove a tool *ran* but never check the agent's prose against the receipt (ZeroClaw's own docs: receipts *"don't constrain text output"*). ReceiptGuard does the part they skip — types every claim, cross-checks each against its receipt, recovers or escalates, then resolves the ticket.

---

## The mechanism

```
ticket ─▶ Autopilot agent (qwen3.7-max) ──tools──▶ ToolGateway ──▶ HMAC-signed receipts
                  │                                                      │
                  ▼ draft answer                                         │
        Claim extractor (qwen-flash)  ── atomic claims, typed ──┐        │
                                                                ▼        ▼
                                              Cross-check claims vs receipts
                                                                │
                                        ┌───────────────────────┤
                                        ▼ all backed             ▼ unbacked / contradicted
                                     PROCEED            Tiered recovery (GSAR): regenerate / replan
                                                          (qwen3.7-max thinking adjudicates,
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
   under an explicit compute budget (GSAR, arXiv 2604.23366). `qwen3.7-max`
   thinking-mode adjudicates contested claims; its `reasoning_content` is stored
   as the human-readable justification.
5. **Audit** — every decision is appended to a SHA-256 hash-chained ledger;
   tampering with any row breaks the chain (EU AI Act Art. 12 record-keeping).

### Prior art & what's actually new here
The HMAC tool-receipt is **not** our invention and we don't claim it — it's a 2026
pattern shipped by [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw/blob/master/docs/book/src/security/tool-receipts.md)
and [Fetch.ai AEVS](https://aevs.fetch.ai/), and formalized in
[NabaOS](https://arxiv.org/abs/2603.10060) and [GSAR](https://arxiv.org/abs/2604.23366).
Each stops at a different layer and stops there:
- **ZeroClaw / AEVS** prove *what a tool executed* — a signed receipt you can look up —
  but never check the agent's prose against it. ZeroClaw's docs: receipts *"don't
  constrain text output"*; AEVS verifies *"what an agent executed, not why"* and is
  *"purely a post-execution recording system."*
- **MemTrust** ([arXiv 2601.07004](https://arxiv.org/abs/2601.07004)) secures the
  *memory*, not the truthfulness of the answer.
- **NabaOS / GSAR** do claim-typing and graduated recovery — as a *framework and a
  benchmark*, not a running autopilot that takes an action.

ReceiptGuard's contribution is the **closed loop, deployed**: unforgeable receipt (floor)
→ qwen-flash epistemic claim-typing cross-checked against those receipts → GSAR budgeted
regenerate/replan on unbacked claims → a policy gate that **auto-resolves the refund/warranty
or escalates to a human** → SHA-256 hash-chained ledger → exposed as an MCP server → running
on Qwen + Alibaba Function Compute, with an on-the-record ablation showing the verifier fails
safe. We win on the composition and the deployment, not the primitive — and we say so out loud.

**"Isn't this just a guardrail?"** A guardrail scores how *confident* the model sounds and
filters on a threshold — vibe-checking. ReceiptGuard demands cryptographic proof each tool
actually ran: claims are checked against a receipt the agent **cannot forge**, and unbacked
claims aren't suppressed — they trigger a real tool re-run before the action commits.
Proof-of-execution, not prompt-based filtering.

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# runs fully OFFLINE in deterministic MOCK mode (no API key needed)
PYTHONPATH=src python -m receiptguard.cli run                          # baseline vs guarded (refund)
PYTHONPATH=src python -m receiptguard.cli run warranty_replacement     # 2nd scenario: escalates to human
PYTHONPATH=src python -m receiptguard.cli run refund_damaged --adversarial  # inject a lie -> watch it get caught
PYTHONPATH=src python -m receiptguard.cli serve                        # demo UI at http://localhost:8000
PYTHONPATH=src python -m receiptguard.cli bench 200                     # detection benchmark + ablation + chart
PYTHONPATH=src python tests/test_receiptguard.py                       # test suite (20 tests)
```

### Going live on Qwen / Alibaba Cloud
Copy `.env.example` → `.env`, set `DASHSCOPE_API_KEY` (Alibaba Model Studio).
With a key, the agent (`qwen3.7-max`, thinking mode), claim typer (`qwen-flash`),
and the LLM-judge baseline call real Qwen via the OpenAI-compatible DashScope
endpoint. No key → mock mode, everything still runs.

- **Alibaba-usage proof file:** [`src/receiptguard/llm/qwen.py`](src/receiptguard/llm/qwen.py)
- **MCP server (Function Compute, SSE):** `python -m receiptguard.mcp.server` (needs `pip install mcp`)

---

## Why it scores

| Criterion | How |
|---|---|
| **Innovation 30%** (tiebreaker) | the *composition*, not the primitive: receipts + epistemic claim-typing + GSAR tiered recovery + auto-act/escalate policy gate + audit ledger, served over MCP; `reasoning_content` as audit artifact; two-speed qwen-flash/qwen3.7-max fleet under a `thinking_budget` |
| **Technical Depth 30%** | deterministic verifier (no LLM in the hot path), modular adapters, hash-chained ledger, reproducible benchmark + ablations |
| **Problem Value 25%** | fabricated tool results are the #1 blocker to autonomous agents; a first-order model puts a 1% fabrication rate at **~$4k/mo** in phantom refunds ([dollar model above](#what-one-fabrication-costs)), and *Moffatt v. Air Canada* (2024 BCCRT 149) already made a company pay for one fabricated support answer; ReceiptGuard is a drop-in MCP gateway any Qwen agent installs |
| **Presentation 15%** | live split-screen demo: watch the agent get caught lying and self-correct, on the record |

## Benchmark

`receiptguard bench` builds an adversarial set (fabricated reference, value
mismatch, false absence) and compares ReceiptGuard against an **ablation** and a
**receipt-free judge**. The judge row below is a **real `qwen-flash` call** on
Alibaba Model Studio (run with `DASHSCOPE_API_KEY`):

| System | Detection | False-positive | Overhead |
|---|---|---|---|
| **ReceiptGuard** | **100%** | **0%** | 0.007 ms/claim |
| ReceiptGuard *(no value-check)* — ablation | 66.7% | 0% | 0.004 ms/claim |
| **`qwen-flash` judge *(no receipts)*** | **0.0%** | 0% | ~1040 ms/claim |

![detection benchmark](eval/out/detection.png)

Reading it: the **ablation** (cross-check tool presence but skip numeric matching)
misses every value/count mismatch — proving the receipt value-check is
load-bearing, not decoration. The **real `qwen-flash` judge catches 0%** of the
fabrications — because they are *plausible*, and a model with no receipts
structurally cannot tell a real tool result from an invented one — while costing
**~1000× more latency** per claim. ReceiptGuard hits 100%/0% deterministically at
sub-millisecond cost, because it checks cryptographic receipts, not plausibility.
That contrast (real LLM judge at 0%) is the whole thesis. Methodology +
the offline heuristic fallback: [`eval/BENCHMARK_METHODOLOGY.md`](eval/BENCHMARK_METHODOLOGY.md).

> Honesty note: the judge row is a real `qwen-flash` run (n=24); the set is
> **self-authored** and the point it proves is *structural* — a receipt-free
> checker cannot verify a plausible fabrication, so it lands at 0% while
> ReceiptGuard's deterministic receipt check lands at 100%. Re-run at larger n with
> `python eval/benchmark.py <N>`.

**Extraction-typing eval** (`receiptguard bench` covers the verifier; this covers the
claim typer): `PYTHONPATH=src python eval/extraction_eval.py` scores `extract_claims`
on 15 labeled drafts. Offline: 80% overall typing, **100% `tool_derived` recall** — and
every error is *conservative* (`inference`→`tool_derived`), so a mis-type means the
verifier checks **more** claims, never fewer. With the fail-closed gateway, no
fabrication slips through a typing error.

## Layout
```
src/receiptguard/  gateway/(receipts,tools) claims/ verify/ recovery/ audit/ agent/ mcp/ api/ llm/
eval/              adversarial benchmark + chart
tests/             pytest invariants
static/            demo UI
```

License: MIT.

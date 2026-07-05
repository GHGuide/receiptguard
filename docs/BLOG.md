# Building an AI agent that can't lie about what its tools did — on Qwen

*My entry for the Global AI Hackathon with Qwen Cloud (Track 4: Autopilot Agent).*

## The problem nobody benchmarks
We measure whether agents **retrieve** the right fact. We don't measure what happens next: whether the agent **acts on** it — or fabricates. I kept seeing the same failure in support-automation demos: the agent says *"refund issued, $79 credited, confirmation RF-1001"* — confidently — when it never called the refund tool. It's not a retrieval bug. It's a **fabrication** bug, and it's the single biggest blocker to letting an agent touch money or inventory.

So I built **ReceiptGuard**: a Qwen autopilot that resolves refund/warranty tickets end-to-end and *structurally cannot* report a tool result that didn't happen.

## The mechanism (proof-of-execution, not vibe-checking)
A guardrail scores how *confident* the model sounds and filters on a threshold. ReceiptGuard demands **cryptographic proof each tool ran**:

- Every tool call goes through a gateway that returns an **HMAC-signed receipt**. The agent never holds the secret, so it can't forge one.
- `qwen-flash` types every sentence the agent writes by **epistemic source** (`tool_derived / inference / absence / opinion`).
- Each `tool_derived` claim is cross-checked against the receipt ledger. No receipt → blocked → the agent re-runs the real tool or **escalates to a human**.
- Every decision is appended to a **SHA-256 hash-chained** ledger. Tamper one row, the chain breaks.

`qwen3.7-max` plans and adjudicates; its **thinking-mode `reasoning_content`** becomes the human-readable "why" stored in each audit row — an artifact the OpenAI stack doesn't expose cleanly. A fast cheap model (`qwen-flash`) is spent to keep the expensive one (`qwen3.7-max`) honest.

## The number that made me trust it
I benchmarked ReceiptGuard against a **real `qwen-flash` judge with no receipts** on a set of plausible fabrications:

- **ReceiptGuard: 100% detection, 0% false positives, sub-millisecond.**
- **Real LLM judge: 0% detection** — and ~1000× slower.

That contrast is the whole thesis. A model without ground truth *cannot* tell a real tool result from an invented one, no matter how smart. A receipt check can, deterministically. An ablation (drop the numeric check → 66.7%) proves the value-check is load-bearing, and a claim-typing eval showed the typer **fails safe**: every mis-type over-verifies, never under-verifies — so no fabrication slips through a typing error.

## Building on Qwen + Alibaba Cloud
Qwen3.7-Max's tool-calling + thinking modes, Qwen-Flash for cheap high-frequency claim typing, the OpenAI-compatible DashScope endpoint, deployed on Function Compute, audit ledger on RDS PostgreSQL, exposed as an MCP server. The honest note: cryptographic tool-receipts are an emerging 2026 idea (ZeroClaw, Fetch.ai AEVS shipped versions) — my contribution is the **deployed closed loop**: typing + cross-check + recover-or-escalate + audit, as a real autopilot, benchmarked.

## What I'd tell my past self
Lead with the *product outcome* ("it can't fabricate a tool result"), not the primitive. Show the honest benchmark — the real 0% judge is more convincing than a perfect self-score. And measure the part you're tempted to skip: the claim *typer* was my untested link until I benchmarked it.

*Code: https://github.com/GHGuide/receiptguard*

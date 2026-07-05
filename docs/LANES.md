# ReceiptGuard — 6 robustness-audit lanes (+ integrator) · NO git trees

Analysis lanes: each READS its subsystem, writes a concrete fix-list to `docs/audit/0N-*.md`. **No code edits, no git, no worktrees** — safe to run all at once in the same dir (different output files). Integrator synthesizes 01–06 into one runbook.
Council source: `docs/judge-council-report.md`. Every lane doc ends: fixes as `file:line → exact change → why (rubric criterion) → effort`, then `STATUS: DONE`.

---

## Lane 1 — core-verifier · Opus 4.8 · high
```
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard" && mkdir -p docs/audit && claude --model claude-opus-4-8
```
```
First, in order: 1) /graphify-auto  2) /caveman full  3) /goal Audit the verifier for adversarial-input robustness and write a fix-list  4) invoke superpowers:using-superpowers

ROLE: robustness-audit lane. READ only; edit NOTHING except your one output doc: docs/audit/01-core-verifier.md.
READ: src/receiptguard/verify/crosscheck.py, claims/extractor.py, recovery/controller.py, gateway/receipts.py, gateway/tools.py, tests/test_receiptguard.py.
INVESTIGATE (council gaps #8,#9): non-str/None into extract_claims (LLM BadRequest risk); empty-string claims becoming verdicts; numeric parsing edge cases (".5"→0.5, "-$410", "1e6", thousands separators); tool-exception→error-receipt path on non-dict outputs; fixture-only tools vs a real Shopify/Stripe integration stub.
OUTPUT each fix as: file:line → exact code change → rubric criterion lifted (Depth/Value) → effort (S/M/L) → a test to add. Rank by impact. Do NOT change detection semantics; flag anything that would.
END: STATUS: DONE.
```

---

## Lane 2 — agent-api · Opus 4.8 · high
```
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard" && mkdir -p docs/audit && claude --model claude-opus-4-8
```
```
First, in order: 1) /graphify-auto  2) /caveman full  3) /goal Audit the agent/api for live-stream + timeout-safety + model-name consistency  4) invoke superpowers:using-superpowers

ROLE: robustness-audit lane. READ only; write ONLY docs/audit/02-agent-api.md.
READ: src/receiptguard/agent/autopilot.py, pipeline.py, api/app.py, llm/qwen.py, config.py, cli.py.
INVESTIGATE (council #6,#7 + hang-risk): how to expose an SSE /stream surfacing qwen3-max reasoning_content live; where a slow thinking call can hang under FC's 300s ceiling (need a wall-clock timeout on client.complete/chat_with_tools/_real_draft + graceful degrade); the model-name split-brain (config default qwen3-max vs qwen3.7-max in s.yaml/.env) — list every code/comment occurrence to unify.
OUTPUT each fix as: file:line → exact change → rubric (Innovation for stream, Depth for timeout) → effort → test. Include the exact SSE endpoint sketch.
END: STATUS: DONE.
```

---

## Lane 3 — benchmark-eval · Fable 5 · medium
```
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard" && mkdir -p docs/audit && claude --model claude-fable-5
```
```
First, in order: 1) /graphify-auto  2) /caveman full  3) /goal Audit the benchmark for statistical rigor + offline reproducibility  4) invoke superpowers:using-superpowers

ROLE: robustness-audit lane. READ only; write ONLY docs/audit/03-benchmark-eval.md.
READ: eval/benchmark.py, eval/extraction_eval.py, eval/BENCHMARK_METHODOLOGY.md, eval/out/results.json, tests/test_receiptguard.py.
INVESTIGATE (council #4): the n=24 thinness for a 100%-vs-0% headline; running all 3 systems at one fixed n>=100 stratified by the 4 case types; a --mock/--live split with frozen live-judge outputs committed to eval/out/ so the delta reproduces offline; a determinism test.
OUTPUT each fix as: file:line/function → exact change → rubric (Depth) → effort → the reproduce command. Give the exact CLI + eval/out/ files to freeze.
END: STATUS: DONE.
```

---

## Lane 4 — demo-ui · Fable 5 · medium
```
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard" && mkdir -p docs/audit && claude --model claude-fable-5
```
```
First, in order: 1) /graphify-auto  2) /caveman full  3) /goal Audit the demo UI for live-deploy surfacing + the on-camera money-shot  4) invoke superpowers:using-superpowers

ROLE: robustness-audit lane. READ only; write ONLY docs/audit/04-demo-ui.md.
READ: static/index.html, api/app.py (the /health, /run, /scenarios shapes), docs/video-script.md.
INVESTIGATE (council #3,#6): a header host/region badge driven by /health (LIVE·Alibaba FC vs Local mock); per-claim color-coded verdicts + hover-to-receipt; an "adversarial" toggle so the catch fires on real Qwen; a live reasoning_content pane if /stream exists (graceful if not); mobile no-horizontal-scroll; a committed screenshot for the README.
OUTPUT each fix as: static/index.html section → exact HTML/JS change → rubric (Presentation/Innovation) → effort. Include the fetch/SSE snippets.
END: STATUS: DONE.
```

---

## Lane 5 — mcp-deploy · Opus 4.8 · high
```
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard" && mkdir -p docs/audit && claude --model claude-opus-4-8
```
```
First, in order: 1) /graphify-auto  2) /caveman full  3) /goal Audit deploy-readiness + MCP stability + the ledger persistence boundary  4) invoke superpowers:using-superpowers

ROLE: robustness-audit lane. READ only; write ONLY docs/audit/05-mcp-deploy.md.
READ: Dockerfile, s.yaml, src/receiptguard/mcp/server.py, api/app.py, audit/ledger.py, docs/fc-deployment.md.
INVESTIGATE (council #1,#10): slimming the runtime image (drop pytest/matplotlib via prod-reqs or a build stage); a /health build/version + readiness signal on FC's $FC_SERVER_PORT; MCP SSE+stdio both starting cleanly + a 3-tool smoke; the audit-ledger persistence boundary (SQLite on /tmp resets on FC recycle → breaks tamper-evidence; RDS for prod) — what to document vs implement; the exact `s config add`→`s deploy`→capture runbook.
OUTPUT each fix as: file:line → exact change → rubric (Depth/Innovation) → effort. NOTE which steps are user-gated (AccessKey).
END: STATUS: DONE.
```

---

## Lane 6 — narrative · Fable 5 · medium
```
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard" && mkdir -p docs/audit && claude --model claude-fable-5
```
```
First, in order: 1) /graphify-auto  2) /caveman full  3) /goal Audit all docs for scored value, quantified impact, and a unified honest pitch  4) invoke superpowers:using-superpowers

ROLE: robustness-audit lane. READ only; write ONLY docs/audit/06-narrative.md.
READ: README.md, docs/DEVPOST.md, docs/BLOG.md, docs/integration-guide.md, docs/video-script.md.
INVESTIGATE (council #5,#7): stray "qwen3-max" in prose to unify to Qwen3.7-Max; a quantified "why this matters" dollar model (avg refund × fabrication rate × ticket volume) + ONE real external citation on agent-hallucination/support-error cost; reframing to lead with what it ENABLES (not "better than ZeroClaw"); missing links (BLOG, integration-guide) from README; benchmark+diagram above the fold; a hard record/upload deadline in video-script (Jul 9 2:00pm PDT, reserve 3h).
OUTPUT each fix as: file:section → exact prose change → rubric (Value/Presentation) → effort. Cite the external source honestly (don't invent a stat).
END: STATUS: DONE.
```

---

## Lane 7 — Runbook (integrator) · Opus 4.8 · xhigh — LAUNCH LAST
```
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard" && claude --model claude-opus-4-8
```
```
First, in order: 1) /graphify-auto  2) /caveman full  3) /goal Synthesize the six audit docs into one execution runbook + completeness critic  4) invoke superpowers:using-superpowers

ROLE: integrator/synthesizer. Lanes 1–6 wrote docs/audit/01..06. You READ 01–06 but must NOT edit them. Edit NOTHING else — write ONLY docs/robustness-runbook.md.
DO:
1. Merge all six fix-lists into ONE ordered runbook: each fix as [criterion · effort] file:line → exact change → test/verify. Dedupe overlaps (model-name unify appears in L2+L6 — merge).
2. Order by (rubric-impact ÷ effort): quick high-impact first. Mark each fix user-gated / agent-doable.
3. Split into: (A) DEPLOY-BLOCKING — the Stage-1 gate (`s config add`+`s deploy`+video, user-gated, MUST be first); (B) code/doc hardening (agent-doable); (C) nice-to-have.
4. Completeness critic: name anything the 6 lanes missed (a subsystem unaudited, a claim unverified, a rubric criterion under-served).
5. State the honest expected first-place delta if executed (council bands: ~1% as-is → deploy+video → hardened).
Cite each lane doc. END: STATUS: DONE.
```

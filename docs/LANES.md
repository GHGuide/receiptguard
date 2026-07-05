# ReceiptGuard — 6 parallel lane prompts (+ integrator)

Council-seeded (docs/judge-council-report.md). Each lane = one fresh Claude terminal in its own git worktree.
**Do the user-gated deploy + video FIRST** — the lanes lift the *conditional* score; they're worthless until the backend is live on Alibaba.

Notes for every lane:
- The graphify graph lives at the **project root** (`../graphify-out`), not in the worktree. To query it: `cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud" && graphify query "<q>"`. Your own file-set is small — reading it directly is fine.
- Never `git add -A`. Commit ONLY your OWN globs. Push nothing — the integrator merges.
- No "done" without `docs/verify-<lane>.md` containing command output as evidence.

---

## L1 — core-verifier  (Opus, high effort)
**Launch:**
```bash
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard"
git worktree add -b lane/L1-core-verifier "../wt/L1-core-verifier" master && cd "../wt/L1-core-verifier" && claude
```
**Paste:**
```
Run first, in order: 1) /graphify-auto  2) /caveman full  3) /goal Harden the ReceiptGuard verifier against adversarial input without changing detection semantics  4) invoke superpowers:using-superpowers

You are LANE L1 core-verifier. LOCKED GOAL: make the load-bearing verifier robust to adversarial/malformed input WITHOUT changing what it detects.

OWN (edit only): src/receiptguard/verify/**, src/receiptguard/recovery/**, src/receiptguard/gateway/**, src/receiptguard/claims/**, tests/test_receiptguard.py
FORBIDDEN: every other file. Need a change outside OWN? Append a request to docs/parallel-status.md under "Edit requests" — do not edit others' files.

Use superpowers:test-driven-development (failing test first) for every change. Use superpowers:verification-before-completion before done.

TASKS:
1. Type-guard claims/extractor.py extract_claims(): non-str / None input → safe empty-claims fallback (no LLM BadRequestError). Filter out empty-string claims before they become verdicts.
2. Fix verify/crosscheck.py numeric parsing edge cases: ".5" must NOT become 0.5 spuriously; handle "-$410", "1e6", thousands separators, and a leading-dot bare ".5". Add a dedicated unit test per case. Do NOT change the tolerance or date/version-strip logic that already works.
3. gateway/receipts.py: confirm the tool-exception → signed error-receipt path holds for non-dict tool outputs too; add a test.
4. Add ONE concrete real-tool integration stub (Shopify-order / Stripe-refund shaped dict) in gateway/tools.py-style, wired so a scenario could use it — demonstrates productization, not asserted. Keep it behind the existing TOOLS map.
5. Keep all existing tests green (currently 15/15) + add your new tests.

VERIFY: write docs/verify-L1.md with the pytest output (all green) + the new edge-case tests listed.
COORDINATION: set L1 row in docs/parallel-status.md to "in progress" on start, "done" on finish.
GIT: branch lane/L1-core-verifier. Commit ONLY your OWN globs (git add <paths>, never -A). Message "harden(core-verifier): ...".
DONE: [ ] tasks done [ ] 15+ tests green [ ] docs/verify-L1.md written [ ] status row=done [ ] committed OWN-only
```

---

## L2 — agent-api  (Opus, medium effort)
**Launch:**
```bash
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard"
git worktree add -b lane/L2-agent-api "../wt/L2-agent-api" master && cd "../wt/L2-agent-api" && claude
```
**Paste:**
```
Run first, in order: 1) /graphify-auto  2) /caveman full  3) /goal Expose a live reasoning_content SSE stream and make the agent timeout-safe under the FC ceiling  4) invoke superpowers:using-superpowers

You are LANE L2 agent-api. LOCKED GOAL: make the agent's Qwen usage visibly sophisticated + robust — stream the adjudicator's reasoning live, and never hang.

OWN (edit only): src/receiptguard/agent/**, src/receiptguard/pipeline.py, src/receiptguard/api/app.py, src/receiptguard/config.py, src/receiptguard/cli.py, src/receiptguard/llm/**
FORBIDDEN: everything else. Cross-file need → docs/parallel-status.md "Edit requests".

Use superpowers:test-driven-development + verification-before-completion.

TASKS:
1. Add a wall-clock timeout to llm/qwen.py client.complete() and chat_with_tools() (configurable RG_LLM_TIMEOUT, default e.g. 90s) + to agent/autopilot.py _real_draft() so a slow qwen3-max thinking call cannot hang under FC's 300s ceiling. On timeout: graceful degrade (return partial + flag), never crash.
2. Add an SSE endpoint GET /stream (api/app.py) that runs a scenario and yields events: agent draft, each claim + verdict, and the qwen3-max adjudication reasoning_content tokens as they arrive. Keep the existing POST /run intact.
3. Unify the model name: config.py default RG_MODEL_AGENT → "qwen3.7-max" (matches s.yaml + .env). Grep the codebase for stray "qwen3-max" strings in code/comments you own and fix them.
4. Confirm the real agent never returns raw tool JSON (the forced-summary fallback) — add a mock-mode test asserting the draft is prose.

VERIFY: docs/verify-L2.md with: /stream curl output (SSE events incl reasoning), timeout test output, "grep qwen3-max" showing none left in your files.
COORDINATION: status row L2. GIT: branch lane/L2-agent-api, OWN-only commits, never -A.
DONE: [ ] stream works [ ] timeout safe [ ] model unified [ ] verify-L2.md [ ] status=done [ ] committed
```

---

## L3 — benchmark-eval  (Fable 5, medium effort)
**Launch:**
```bash
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard"
git worktree add -b lane/L3-benchmark-eval "../wt/L3-benchmark-eval" master && cd "../wt/L3-benchmark-eval" && claude
```
**Paste:**
```
Run first, in order: 1) /graphify-auto  2) /caveman full  3) /goal Produce a reproducible n>=100 stratified benchmark with frozen live-judge results  4) invoke superpowers:using-superpowers

You are LANE L3 benchmark-eval. LOCKED GOAL: make the 100%-vs-0% headline statistically solid + reproducible offline.

OWN (edit only): eval/**, tests/test_bench_*.py (new files only — do NOT touch tests/test_receiptguard.py)
FORBIDDEN: everything else. Need a README number change → post to docs/parallel-status.md for L6.

Use superpowers:test-driven-development + verification-before-completion.

TASKS:
1. Parameterize eval/benchmark.py to run all THREE systems (ReceiptGuard / no-value-check ablation / qwen-flash judge) at a single fixed n (default 120), stratified equally across the 4 case types (clean/fabricated_ref/value_mismatch/false_absence).
2. Add a --mock/--live split: --mock uses the heuristic judge (offline, deterministic, reproducible); --live uses real qwen-flash. Freeze the live-judge run's raw outputs into eval/out/ (a committed json) so the delta is reproducible without a key.
3. Regenerate eval/out/results.json + detection.png at n>=100 (mock). If a DASHSCOPE_API_KEY is present, also run --live once and freeze eval/out/live_results.json + note the n.
4. Update eval/BENCHMARK_METHODOLOGY.md with the fixed-n, stratification, and the mock/live reproducibility story. Add a tests/test_bench_repro.py that asserts the mock benchmark is deterministic.
5. Post the final numbers to docs/parallel-status.md so L6 updates the README table.

VERIFY: docs/verify-L3.md with the n>=100 benchmark output + the repro test passing.
COORDINATION: status row L3. GIT: branch lane/L3-benchmark-eval, OWN-only, never -A.
DONE: [ ] n>=100 stratified [ ] mock repro deterministic [ ] artifacts committed [ ] numbers posted for L6 [ ] verify-L3.md [ ] status=done
```

---

## L4 — demo-ui  (Fable 5, medium effort)
**Launch:**
```bash
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard"
git worktree add -b lane/L4-demo-ui "../wt/L4-demo-ui" master && cd "../wt/L4-demo-ui" && claude
```
**Paste:**
```
Run first, in order: 1) /graphify-auto  2) /caveman full  3) /goal Make the demo UI surface the live deploy and stream the adjudicator reasoning  4) invoke superpowers:using-superpowers

You are LANE L4 demo-ui. LOCKED GOAL: make the split-screen demo visceral + prove "real deployment" on screen.

OWN (edit only): static/**
FORBIDDEN: everything else. Need the live URL / a README screenshot block → post to docs/parallel-status.md for L5/L6.

Use superpowers:verification-before-completion. Verify in the browser preview (preview_* tools) — never claim it renders without checking.

TASKS:
1. Header badge showing host/region: reads /health — if mock:false show "● LIVE · Alibaba FC · {region}" (green), else "○ Local mock" (grey).
2. Render claims one-by-one, color-coded by verdict (backed=green, unbacked/contradicted/false_absence=red, inference/opinion=grey), hover a claim → show its matching receipt (or "no receipt").
3. Add an "Adversarial" toggle that calls /run with adversarial:true so the catch fires on a well-behaved real agent; animate the flagged claim → red → escalate.
4. If the L2 /stream SSE endpoint exists, add a live "adjudicator thinking" pane that streams reasoning_content; degrade gracefully if /stream is absent.
5. Keep it mobile-safe (no horizontal scroll on the body). Take a screenshot → save to static/demo-screenshot.png and note the path for L6's README.

VERIFY: docs/verify-L4.md with preview_snapshot/screenshot evidence for both scenarios + the adversarial catch.
COORDINATION: status row L4. GIT: branch lane/L4-demo-ui, OWN-only, never -A.
DONE: [ ] badge [ ] color verdicts+hover [ ] adversarial catch visible [ ] reasoning pane (or graceful) [ ] screenshot saved [ ] verify-L4.md [ ] status=done
```

---

## L5 — mcp-deploy  (Opus, medium effort)
**Launch:**
```bash
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard"
git worktree add -b lane/L5-mcp-deploy "../wt/L5-mcp-deploy" master && cd "../wt/L5-mcp-deploy" && claude
```
**Paste:**
```
Run first, in order: 1) /graphify-auto  2) /caveman full  3) /goal Make the backend fully deploy-ready for Alibaba Function Compute and stabilize the MCP server  4) invoke superpowers:using-superpowers

You are LANE L5 mcp-deploy. LOCKED GOAL: everything needed so a single `s deploy` + `/health` capture succeeds — you make it READY (the actual deploy is user-gated on the AccessKey).

OWN (edit only): src/receiptguard/mcp/**, Dockerfile, s.yaml, docs/fc-deployment.md
FORBIDDEN: everything else (do NOT touch llm/ — L2 owns it). README ledger-note → post to docs/parallel-status.md for L6.

Use superpowers:verification-before-completion — build + run the container locally and curl it as proof.

TASKS:
1. Slim the Dockerfile: drop dev deps (pytest, matplotlib) from the runtime image via a prod requirements or a build stage; keep image small; confirm it still serves /health + /run.
2. Add a readiness/health distinction: /health returns model + mock flag + a build/version tag. Ensure it works with FC's $FC_SERVER_PORT.
3. Harden mcp/server.py: ensure both SSE and stdio transports import + start cleanly (mcp is in requirements); add a tiny smoke that lists the 3 tools.
4. Make the audit-ledger persistence boundary explicit: s.yaml uses /tmp for demo; document the RDS PostgreSQL DSN path for prod in docs/fc-deployment.md (and note the /tmp reset caveat). Post a one-line ledger-boundary note to parallel-status.md for L6's README.
5. Finalize docs/fc-deployment.md as an exact runbook: `s config add` → `s deploy` → capture `/health` (mock:false) → `/run` with receipts → record commands. Include the ACR-or-no-ACR note.

VERIFY: docs/verify-L5.md with: local `docker build` + `docker run` + curl /health (mock:false) output + the 3 MCP tools listed.
COORDINATION: status row L5. GIT: branch lane/L5-mcp-deploy, OWN-only, never -A.
DONE: [ ] slim image serves [ ] health tag [ ] MCP SSE+stdio [ ] ledger boundary documented+posted [ ] runbook exact [ ] verify-L5.md [ ] status=done
```

---

## L6 — narrative  (Fable 5, medium effort)
**Launch:**
```bash
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard"
git worktree add -b lane/L6-narrative "../wt/L6-narrative" master && cd "../wt/L6-narrative" && claude
```
**Paste:**
```
Run first, in order: 1) /graphify-auto  2) /caveman full  3) /goal Convert honesty into scored value across all docs and unify the pitch  4) invoke superpowers:using-superpowers

You are LANE L6 narrative. LOCKED GOAL: maximize the 4 rubric criteria in the READMEs/docs — clarity, quantified value, honest positioning.

OWN (edit only): README.md, docs/** EXCEPT docs/fc-deployment.md, docs/judge-council-report.md, docs/parallel-status.md, docs/LANES.md
FORBIDDEN: code, static, eval, deploy files. You may only change prose/docs. Model-name fix in CODE is L2's; you fix it in prose/README.

Use superpowers:verification-before-completion (re-read for consistency; no dead links).

TASKS:
1. Unify the model name to "Qwen3.7-Max" in ALL prose (README, DEVPOST, BLOG, video-script) — remove stray "qwen3-max" in docs.
2. Problem Value: add a quantified "Why this matters" — a simple dollar model (avg refund × fabrication rate × ticket volume) + ONE external citation (an incident/report on agent hallucination or support-automation error cost). Cite honestly; don't invent a stat.
3. Lead with what ReceiptGuard ENABLES (an autopilot you can trust to act), not "better than ZeroClaw" — keep the honest prior-art note but stop framing around competitors.
4. Ensure benchmark + architecture sit above the fold; when L3 posts new n>=100 numbers to parallel-status.md, update the README table.
5. Link BLOG.md + integration-guide.md from the README. Add a hard record/upload deadline (Jul 9, 2:00 PM PDT — reserve 3h) to docs/video-script.md.
6. When L5 posts the ledger-boundary note + L4 posts the screenshot path + the live URL exists, add a "Live deployment" block to the README (URL + screenshot + region).

VERIFY: docs/verify-L6.md listing each doc changed + a consistency check (one model name, no dead links, numbers match parallel-status.md).
COORDINATION: status row L6. Check "Edit requests" before finishing. GIT: branch lane/L6-narrative, OWN-only, never -A.
DONE: [ ] model name unified [ ] $ model + citation [ ] enables-first framing [ ] links added [ ] deadline in video-script [ ] verify-L6.md [ ] status=done
```

---

## INTEGRATOR  (runs LAST — Opus, medium)
**Launch:**
```bash
cd "/Users/leonardo/Downloads/5 hackathons quick wins/Global AI Hackathon Series with Qwen Cloud/receiptguard"
claude
```
**Paste:**
```
Run first, in order: 1) /graphify-auto  2) /caveman full  3) /goal Merge all six lane branches into master, re-verify, leave one clean tree  4) invoke superpowers:using-superpowers

You are the INTEGRATOR. Do NOT trust any prior "GO" — re-merge the CURRENT HEADs of all six lane branches and re-verify.

STEPS:
1. On master: for each branch lane/L1..L6, `git merge --no-ff` in order L1,L5,L2,L3,L4,L6 (verifier→deploy→agent→bench→ui→narrative). Resolve conflicts favoring the OWNING lane per docs/parallel-status.md.
2. Full re-verify: `PYTHONPATH=src python tests/test_receiptguard.py` (all green) + `python eval/benchmark.py 120` reproduces the table + `docker build` succeeds + read each docs/verify-L*.md exists.
3. Confirm one model name everywhere (grep qwen3-max → only in prior-art/historical notes if any).
4. Update docs/parallel-status.md: all rows done. Commit the merge.
5. Cleanup: `git worktree remove --force ../wt/L1-core-verifier` (and L2..L6); `git branch -d lane/L1-core-verifier` (…L6) once merged. Leave ONE tree.
6. `git push origin master`.

VERIFY: write docs/verify-integration.md with the full test + benchmark + docker output and the final `git log --oneline -8`.
Only declare GO when tests are green on the merged HEAD.
```

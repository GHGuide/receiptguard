# Judge Council Report — ReceiptGuard (simulated panel, 2026-07-06)

5 judges (Innovation / Depth / Value / Presentation / Adversarial) + Opus chair, read the real repo.

## Weighted score: 71/100
| Dimension | Weight | Score |
|---|---|---|
| Innovation (tiebreaker) | 30% | 70 |
| Technical Depth | 30% | 74 |
| Problem Value | 25% | 68 |
| Presentation | 15% | 72 |

**Stage-1 = currently FAIL** (no Alibaba deploy proof, no video). First-place: **~1% as-is → ~9-11% deploy+video → ~14-16% fully hardened** (capped ≤18%: Innovation tiebreaker rewards primitive novelty this entry honestly doesn't claim).

Corrections chair made to ground truth: tests are **15/15** (not 14); the Depth judge's "test regression" finding is **false on execution**. Chair-found defect: **model-name split-brain** (qwen3.7-max vs qwen3-max).

## Top gaps (ranked)
1. **[CRITICAL·mcp-deploy]** No Alibaba FC deploy proof (live URL, `s deploy`, `/health` mock:false). Stage-1. *User AccessKey.*
2. **[CRITICAL·narrative]** Video not recorded. Stage-1. *User + warm endpoint.*
3. **[HIGH·demo-ui]** Live deploy not surfaced in README/UI (no clickable URL/screenshot/region badge).
4. **[HIGH·benchmark-eval]** n=24, thin for a 100%-vs-0% headline; live-judge n not apples-to-apples.
5. **[HIGH·narrative]** Problem value unquantified (no $ model, no external citation).
6. **[MED·demo-ui]** reasoning_content never streamed live to UI (money-shot invisible; no SSE /stream).
7. **[MED·narrative/demo-ui]** Model-name split-brain (qwen3.7-max vs qwen3-max) — /health curl contradicts pitch.
8. **[MED·core-verifier]** Fixture tools only; "swap for Shopify/Stripe" asserted, never shown.
9. **[MED·core-verifier]** extract_claims(non-str)→BadRequest; empty claims→unbacked; numeric regex parses `.5` as 0.5.
10. **[MED·mcp-deploy/core-verifier]** Ledger = SQLite on /tmp (ephemeral on FC recycle) — breaks tamper-evidence at scale; RDS path untested.

## Per-lane seed goals (LOCKED)
- **core-verifier** — type-guard `extract_claims` (non-str→fallback), filter empty claims, fix numeric parsing (`.5`,`-$410`,`1e6`,locale) + unit tests; add one real-tool integration stub (Shopify/Stripe shape). No detection-semantics change.
- **agent-api** — SSE `reasoning_content` stream from the adjudication turn + wall-clock timeout on `_real_draft`/`client.complete` (<300s FC ceiling); unify model default → qwen3.7-max in config.
- **benchmark-eval** — re-run all 3 systems at fixed n≥100 stratified by hallucination type, `--mock`/`--live` split, freeze live-judge results in `eval/out/`, reproducible offline.
- **demo-ui** — host/region badge (Alibaba FC vs Local), per-claim color verdicts + hover-to-receipt, live `reasoning_content` pane; committed screenshot + clickable URL block.
- **mcp-deploy** — make deploy-READY: slim Dockerfile, correct s.yaml, health/readiness, MCP SSE+stdio stable, ledger persistence boundary (RDS prod / /tmp demo) explicit in README. (Actual `s deploy` = user-gated.)
- **narrative** — unify model name everywhere, quantified $ pain model + 1 external citation, lead with what it *enables*, link BLOG + integration-guide from README, hard record/upload deadline in video-script.

## The one gap that most threatens placing
The missing Alibaba FC deploy proof — it's the Stage-1 gate (0 if absent) AND blocks the video + live-URL + on-camera money-shot. Lanes make the app deploy-ready; the binding step (`s deploy` with a real AccessKey + capture + record) needs **Leonardo**, before Jul 9 2:00 PM PDT.

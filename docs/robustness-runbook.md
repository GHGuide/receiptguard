# ReceiptGuard — Robustness Execution Runbook (integrator synthesis of audits 01–06)

Single ordered execution plan merged from the six read-only lane audits:
`docs/audit/01-core-verifier.md` · `02-agent-api.md` · `03-benchmark-eval.md` ·
`04-demo-ui.md` · `05-mcp-deploy.md` · `06-narrative.md`, cross-checked against
`docs/judge-council-report.md` (71/100, Stage-1 = FAIL) and lane ownership in
`docs/parallel-status.md`.

This file is the only artifact written by the integrator lane. The six audit docs are the
source of truth for full patch text; each item below cites its origin `[lane · F#]` and the
exact `file:line`. Where two lanes prescribed the same fix, they are merged once (see
**R1 UNIFY-MODEL**).

---

## How to read this

- **Tag** — the primary rubric criterion the fix serves: `Depth` (30%) · `Innovation` (30%,
  tiebreaker) · `Value` (25%) · `Presentation` (15%). `⚠SEM` = changes a verdict
  (detection semantics); direction noted.
- **Effort** — S ≈ ≤15 min · M ≈ 15–60 min · L ≈ >1 h.
- **Gate** — `USER` = needs Leonardo (AccessKey, DashScope key, model-id confirmation, or a
  human tier-decision sign-off). `AGENT` = an agent can land it unattended.
- **Owner** — the lane that OWNS the file per `parallel-status.md` (cross-file edits are
  requested, never cross-written).
- Ordering within each section is by **rubric-impact ÷ effort** (quick + high-impact first).

Coverage check: all 10 council gaps map to a fix below — #1→R2/§A, #2→§A, #3→R3/R4/R23,
#4→R25/R26/R28, #5→R22, #6→R19/R20, #7→R1, #8→R38, #9→R10–R16, #10→R30/R31.

---

# SECTION A — DEPLOY-BLOCKING (Stage-1 gate). MUST be first. Mostly USER-gated.

Council: *"The one gap that most threatens placing = the missing Alibaba FC deploy proof —
Stage-1 gate (0 if absent) AND blocks the video + live-URL + on-camera money-shot."*
Nothing in Section B or C moves the score above ~1% until Section A is done.

### A0 — Agent pre-flight (land these BEFORE `s deploy`; without them the deploy is broken or self-contradicting)

These are agent-doable code fixes that are hard prerequisites for a clean recording. Do them
first, then hand the deploy to Leonardo.

| Ref | Fix | Tag · Effort · Owner | file:line → change | Verify |
|---|---|---|---|---|
| **R1** | **UNIFY-MODEL** (merged: `[L2·F7]`+`[L5·B3]`+`[L6·FIX1]`) — one canonical id `qwen3.7-max` (code/env) / `Qwen3.7-Max` (prose). Kills the `/health`-vs-pitch split-brain. | Depth+Pres · S · L2+L6 | code (L2): `config.py:35`, `llm/qwen.py:6`, `agent/autopilot.py:8`; prose (L6): `README.md:7,43,53,70,123,136`, `video-script.md:9,10,14,28`, `.env.example:5`; deploy (L5): confirm `s.yaml:22` = the real DashScope id | `grep -rn "qwen3-max" src/ static/ docs/ README.md .env.example` → 0 hits; `GET /health` (env unset) → `agent:"qwen3.7-max"` |
| **R2** | `[L2·F1]` OpenAI client has NO timeout → 600s×3≈1800s vs FC 300s ceiling → FC kills request, ledger turn never written. | Depth(HIGH) · S · L2 | `qwen.py:43` add `timeout=settings.llm_timeout_s, max_retries=1`; new `config.py` setting `llm_timeout_s` (default 60, `>0` guard) | monkeypatch `llm_timeout_s=0.001` → `complete()` raises `APITimeoutError` in <1s |
| **R3** | `[L5·B1]` Dockerfile CMD reads only `${PORT}`; FC injects `$FC_SERVER_PORT` → non-9000 CAPort = dead deploy. | Depth · S · L5 | `Dockerfile:16` → `--port ${FC_SERVER_PORT:-${PORT:-9000}}` | `docker run` + FC bind both 200 on `/health` |
| **R4** | `[L5·C1]` MCP SSE app never mounted → the MCP-on-Alibaba claim is undeployed. | Depth+Innov · M · L5→L2* | `api/app.py` (after L21) `app.mount("/mcp", _mcp.sse_app())` (*app.py is L2-owned — request the edit) | after deploy `curl .../mcp/sse` → `text/event-stream` |
| **R5** | `[L2·F2]` ~30 sequential LLM calls/`run`, zero cumulative deadline → blows 300s even with R2's per-call cap. | Depth(HIGH) · M · L2 | thread monotonic `deadline = time.monotonic()+settings.run_budget_s` (default 240) through `pipeline.run`→`run_draft`/`_real_draft`; break loops on breach | patch `run_budget_s=0` → `run()` returns `RunResult(shipped=False, degraded)` in <1s, not an exception |
| **R6** | `[L2·F6]` timeout propagates raw → 500, iteration ledger row never appended → "logs every step" breaks under load. | Depth · M · L2 | wrap `_real_draft` tool loop + final `complete()` in `try/except (APITimeoutError,APIError)` → human-escalation stub draft | force `APITimeoutError` → `run()` returns `shipped=False, chain_ok=True`, draft contains "escalating" |

> R4/R6 depend on R2/R5 landing first (a mounted SSE / degrade path is only safe once calls
> are time-bounded). R1's config edit and R2/R5's new settings all touch `config.py` (L2) —
> land them in one L2 pass to avoid triple-writing the file.

### A1 — The gate itself (USER-gated — Leonardo, before Jul 9 2:00 PM PDT)

Consolidated from `[L5·§E]` (which closed the gaps in `docs/fc-deployment.md §1–9`).

```bash
# 0. secrets — never bake into the image (s.yaml:20,24 read from env)
export DASHSCOPE_API_KEY=...                                   # intl account key
export RG_RECEIPT_SECRET=$(python -c 'import secrets;print(secrets.token_hex(32))')  # real, not dev default
# 1. [USER] one-time creds (RAM: AliyunFCFullAccess + AliyunContainerRegistryFullAccess)
s config add            # provider alibaba, AccountID + AccessKey, alias 'default' (matches s.yaml:3)
# 2. [USER] ACR: console → Container Registry Personal (ap-southeast-1) → ns receiptguard → repo api
docker login --username=<acr-user> registry-intl.ap-southeast-1.aliyuncs.com
# 3. build+push+deploy — s deploy does all three from s.yaml (confirm fc3 auto-builds; else docker build/push first — [L5·E1])
#    bump s.yaml:18 image tag per deploy so the recorded instance is provably the new image — [L5·E2]
s deploy
# 4. capture URL
s info                  # → https://<fnId>.ap-southeast-1.fcapp.run
# 5. warm + smoke (order matters for the recording)
curl .../health         # expect mock:false + models:{agent:qwen3.7-max,...}   (deep OFF — must return instantly)
curl -X POST .../run -H 'content-type: application/json' -d '{"scenario":"refund_damaged"}'
curl .../mcp/sse        # after R4: text/event-stream
# 6. proof log
s logs                  # capture a live request line showing the real qwen model id
```

- **A1-confirm** `[L5·B3]` **USER**: before deploy, confirm `qwen3.7-max` is a real
  DashScope model id on Leonardo's account — if not, first `/run` 500s on camera.
- **A2 — Video** `[council #2]` **USER**: record on the warm `*.fcapp.run` URL. Money-shot
  flow is enabled by **R7** (adversarial toggle) + **R8** (deploy badge). Follow the hard
  deadline block from **R9**.
- **A3 — Committed screenshot** `[L4·Fix6]` **USER** (gated on deploy): after R7/R8 land and
  the URL is live, capture the adversarial-blocked frame at 1600×1000 →
  `docs/screenshot-live.png`, embed under the README architecture diagram. This is the deploy
  proof for judges who score on README alone (running the project is not required).

---

# SECTION B — Code / doc hardening (AGENT-doable). Ordered by impact ÷ effort.

### B-tier 1 — cheap + high-leverage (do right after A0)

| Ref | Fix | Tag · Effort · Owner | file:line → change | Verify |
|---|---|---|---|---|
| **R7** | `[L4·Fix3]` Adversarial toggle — backend already supports `RunRequest.adversarial`; UI never sends it. Single control that makes the 1:15 money-shot reproducible on camera. **Highest score-per-minute.** | Pres · S · L4 | `index.html:44-48,91` add checkbox + send `adversarial:` in `run()` body | tick box → red unbacked claim appears, badge flips `blocked` |
| **R8** | `[L4·Fix1]` Deploy badge — big LIVE·Alibaba FC·ap-southeast-1 vs MOCK header badge (client-side `location.hostname`, zero backend). | Pres · S · L4 | `index.html:40-43,72-78`; optional server-truth `"region":os.environ.get("FC_REGION","")` in `/health` (L2/L5) | on `*.fcapp.run` badge reads green LIVE + region + models |
| **R9** | `[L6·FIX6]` Hard video deadline block (public + link pasted by 11:00 AM PDT Jul 9, record Jul 8 evening). A video finishing processing at 2:05 PM scores 0 = 15% gone. | Pres/risk · S · L6 | `video-script.md:20` → hard-deadline block, moved to top of Production rules | present as first bullet |
| **R10** | `[L6·FIX4]` Link BLOG / integration-guide / DEVPOST / methodology from README (currently reachable from nowhere). | Pres · S · L6 | `README.md` after L128 add two link lines | links resolve |
| **R11** | `[L1·F2]` `extract_claims(non-str)` → 400 BadRequest crashes whole verify pass. | Value · S · L1 | `extractor.py:33` coerce/guard; empty→`[]` | `extract_claims(None)==[]`; `extract_claims(123)` no raise; LLM not called for empty |
| **R12** | `[L1·F10]` `_parse` fallback re-raises inside its own `except` on non-str `content` (e.g. `content=None`). | Value · S · L1 | `extractor.py:44` normalize at entry | `_parse(None)==[]`; `_parse(42)` no raise |
| **R13** | `[L1·F1]` ⚠SEM(tightens) Numbers from error-receipt `detail` strings leak into the numeric backing set → fabricated `$500 refund` laundered as **backed**. Real bypass of the core invariant. | Depth+Value · S · L1 | `crosscheck.py:106-110` skip receipts whose `output` has `"error"` when gathering numbers | tool raises `RuntimeError("timeout 500")` → claim "$500 refund" is NOT `backed` |
| **R14** | `[L1·F7]` `send_email` `message_id` uses salted `hash()` → non-deterministic across runs, contradicts "deterministic fixtures / reproducible proof". | Value · S · L1 | `tools.py:40` → `sha256(subject)`-derived id | two equal-subject calls → equal `message_id` (stable under `PYTHONHASHSEED=random`) |
| **R15** | `[L1·F3]` ⚠SEM(loosens fail-set) Empty/whitespace claim → `unbacked`→failed → spurious `replan`; padding blank claims = denial-of-progress. | Depth+Value · S · L1 | `crosscheck.py:114` guard → return `opinion` | `cross_check(Claim("   ","tool_derived"),[]).failed is False` |
| **R16** | `[L3·F5]` Provenance metadata (`mode`,`judge_model`,`temperature`,`timestamp_utc`,`case_generator_version`) in every results file — kills the unlabeled-artifact ambiguity class. | Depth · S · L3 | `benchmark.py:97-99` | assert those keys `<= results.keys()` |
| **R17** | `[L3·F2]` Fixed stratified n≥100; populate dead `by_type:{}`; round n to ×4. Adopt n=200 (50/stratum). | Depth · S · L3 | `benchmark.py:97,136` | `by_type=={clean:50,fabricated_ref:50,value_mismatch:50,false_absence:50}` |
| **R18** | `[L3·F3]` Wilson 95% CIs on every rate (6-line stdlib helper). Cheapest signal of statistical literacy; pre-empts the obvious attack question. | Depth · S · L3 | `benchmark.py:125-131,148-153,166-173` | output shows `100.0% [97.5,100.0]` |

### B-tier 2 — medium effort, strong rubric payoff

| Ref | Fix | Tag · Effort · Owner | file:line → change | Verify |
|---|---|---|---|---|
| **R19** | `[L2·F5]` `complete()` buffers stream deltas; add `stream_complete()` generator yielding `(reasoning\|content, delta)`. Surfaces `reasoning_content` as a live artifact (OpenAI stack can't). | Innov · S · L2 | `qwen.py` new method; `complete()` consumes it (no behaviour change) | mock → raises `RuntimeError`; live+thinking → first tuple kind `"reasoning"` |
| **R20** | `[L2·F4]` SSE `GET /stream` endpoint (mock + live). FC serves SSE under custom-container ✓. | Innov · M · L2 | `api/app.py` add `/stream` StreamingResponse | `TestClient` GET `/stream` (mock) → `text/event-stream`, body has `event: reasoning` then `done` |
| **R21** | `[L4·Fix4]` Live reasoning pane, feature-detects `/stream` (HEAD), post-hoc box fallback — ships safe whether or not R20 lands. `[L4·Fix2]` hover-to-receipt tooltip (signed receipt made tangible). `[L4·Fix5]` mobile CSS (no horizontal scroll in screenshot). | Innov+Pres · M · L4 | `index.html` `.reason`/`claimEl()`/`.style` | HEAD 404 → identical to today; hover shows `tool·receipt_id·HMAC`; <760px single-column |
| **R22** | `[L6·FIX2]` Quantified $-pain model + verified citation *Moffatt v. Air Canada* 2024 BCCRT 149 (CAD $812 for one fabricated chatbot answer). **Only fix that adds new scoring substance** (Problem Value 25%). | Value · M · L6 | `README.md` Problem-Value row, `DEVPOST.md` Inspiration, `video-script.md` move 6 | numbers + case cite present; framing = "fabricated support answer" (honest) |
| **R23** | `[L6·FIX5]` Mini benchmark table (100%/66.7%/0%) above the fold, replacing prose "Proven:" line. `[L6·FIX3]` reframe README:36 to lead with "an agent you can let touch money" (demote "vs ZeroClaw"); same flip `BLOG.md:29`. | Pres+Value · M · L6 | `README.md:34,36`, `BLOG.md:29` | table renders above fold; opener is product outcome (depends on R25/R26 final numbers for the table) |
| **R24** | `[L2·F3]` `chat_with_tools` blocking non-stream — subsumed by R2's client-level timeout (mandatory), keep blocking for tool-call parse simplicity. | Depth · S · L2 | covered by R2 | as R2 |

### B-tier 3 — semantics-tagged verifier fixes (land behind the 15/15 regression suite)

These change verdicts and interact with each other in one file (`crosscheck.py`); land as a
group and re-run the full suite (see completeness critic **C-crit #1**). Order: R13/R15 (done
above) → R25 → R27 → R28.

| Ref | Fix | Tag · Effort · Owner | file:line → change | Verify |
|---|---|---|---|---|
| **R25** | `[L3·F1]` Parameterize case generation (index-seeded `random.Random(1000+i)`, ≥4–6 phrasings/kind) so n is a real sample size, not 4 templates ×6. **Single highest-leverage eval fix** — the difference between a demo and a benchmark. | Depth · M · L3 | `benchmark.py:44` | `benchmark.py 200 --mock` → per-type RG still 100/100/100 (a broken phrasing = a real verifier bug) |
| **R26** | `[L3·F4]` `--mock`/`--live` split (mock forces heuristic even with a key set) + frozen sha256-keyed judge cache + `--replay` (offline, no key). The council's core ask: the live delta becomes bit-for-bit reproducible on a judge's laptop. Pin judge `temperature=0.0`. | Depth+Repro · M · L3 | `benchmark.py:79,135`; writes `results_mock/live/replay.json`,`judge_cache.json` | `--replay` diff vs `results_live.json` (minus timing) = empty |
| **R27** | `[L1·F4]` ⚠SEM(both) Substring keyword→tool match (`"stock"⊂"Stockholm"`) misattributes tools → false unbacked. Switch to `\b`-anchored regex; add plural keys (`orders`,`refunds`,`articles`). | Depth+Value · M · L1 | `crosscheck.py:97-103,20-27` | "shipped to Stockholm" not flagged `check_inventory`; "2 orders" still → `lookup_order` |
| **R28** | `[L1·F5]` ⚠SEM(mixed) Numeric regex misses `.5`, splits `1e6`→{1,6}, drops `k`/`M`. Extend token pattern (leading-dot + exponent load-bearing; suffix-fold optional/L). | Depth+Value · M · L1 | `crosscheck.py:74` | `_numbers("$.50")=={0.5}`; `_numbers("1e6")=={1e6}`; date/version regressions still pass |
| **R29** | `[L1·F6]` ⚠SEM(tightens) Non-dict tool output (bare list/str) bypasses false-absence check → a genuine "no results" lie ships as `backed`; also fixes latent `TypeError` on `count:"5"`. **Land before R37 (real provider).** | Depth+Value · M · L1 | `crosscheck.py:126-128` treat any non-empty output as contradicting absence | `output=["a","b"]`+absence claim → `false_absence`; `count:"5"` no raise |

### B-tier 4 — deploy-hardening + eval closeout (medium, do after the gate is proven)

| Ref | Fix | Tag · Effort · Owner | file:line → change | Verify |
|---|---|---|---|---|
| **R30** | `[L5·A1]` Split prod vs dev requirements (drop pytest/matplotlib from runtime — matplotlib→numpy/pillow is the biggest cold-start/attack-surface win). Keep `mcp` in prod `[L5·A3]`. | Depth · S · L5 | new `requirements.txt`(prod) + `requirements-dev.txt` | prod image `/health` 200; smaller image |
| **R31** | `[L5·D1/D2]` Document the ledger boundary honestly: `/tmp` is per-instance/ephemeral → chain resets on FC recycle (fine for live demo, must be stated in README + Verdict copy). Fix the false "DSN works on RDS" docstring — SQLite-only as written. | Depth · S · L5+? | README/Verdict note; `ledger.py:4-5` docstring (see **C-crit #2** ownership) | note present; docstring no longer claims drop-in RDS |
| **R32** | `[L5·B2]` `/health` `build`/version + opt-in deep readiness (`?deep=1`, DashScope probe, 2s, never raises). Keep liveness instant; deep OFF in proof curl. | Depth+Innov · M · L2* | `api/app.py:31-34` (L2-owned — request) | `/health` fast + `build`; `/health?deep=1` adds `ready` |
| **R33** | `[L5·C3]` 3-tool MCP smoke (stdio + post-deploy SSE): `list_scenarios` non-empty, `run_guarded_autopilot` has receipts+audit, `verify_claims` returns verdicts. Use a claim consistent with hardcoded `ORD-1001` `[L5·server.py:43-46]`. | Depth · M · L5 | new `scripts/mcp_smoke.py` | all 3 tools wire end-to-end |
| **R34** | `[L5·E1/E2]` Deploy-doc clarity: state `s deploy` also builds+pushes; bump `s.yaml:18` tag per deploy (tie to `RG_BUILD`). | Depth · S · L5 | `fc-deployment.md`, `s.yaml:18` | doc unambiguous; tag increments |
| **R35** | `[L3·F7]` Determinism test (subprocess, mock-forced) — locks the "deterministic" docstring claim + stratification against R25 regressions. | Depth · M · L3 | `tests/test_receiptguard.py` append | two offline runs identical (minus timing); strata balanced |
| **R36** | `[L3·F6]` Reconcile `BENCHMARK_METHODOLOGY.md:31-38` → two-row mock/live table filled from regenerated artifacts (not hand-typed). Closes the doc-vs-artifact contradiction. | Depth+honesty · S · L3 | after R25/R26 + a live regen | doc numbers `grep`-match the JSON |

---

# SECTION C — Nice-to-have (roadmap / additive; only if time after A + B)

| Ref | Fix | Tag · Effort · Owner · Gate | Note |
|---|---|---|---|
| **R37** | `[L1·F9]` `ToolProvider` protocol + `ShopifyStub`/`StripeStub` (same output shapes, env-flag, fixture default). Proves the receipt/verify layer is provider-agnostic — answers the productionization question. | Value+Depth · L · L1 · AGENT | Additive, no semantics. **R29 must land first** so the verifier tolerates real backend shapes. |
| **R38** | `[L1·F8]` ⚠SEM Zero extracted claims → groundedness 1.0 → silent `proceed` (adversarial "verify nothing" bypass). Thread `draft_nonempty`/`num_claims` into `decide`; refuse clean proceed on empty verdicts from a non-empty draft. | Depth+Value · S(in-module)/M · L1 · **USER** | Touches the tier decision (recovery contract) → **owner sign-off required**, per `[L1·F8]`. High-value but not blind-apply. |
| **R39** | `[L5·D3]` `_Backend` seam in `ledger.py` (SQLite path vs `postgres://`→psycopg, `SERIAL`, `%s`, quoted `"idx"`) → RDS becomes a DSN swap; makes R31's promise real + EU AI Act Art.12 durable chain. | Depth+Innov · L(2-3h) · ? · AGENT | `[L5]` recommendation: DOCUMENT (R31) for the hackathon, keep this as "roadmap" in the Verdict unless the ledger is on-camera surviving a recycle. |
| **R40** | `[L5·D4]` RDS PG15 stand-up for a durability screenshot only. | Depth · M-console · USER | NOT free, needs VPC/NAT; capture then **release** (hourly bill). |
| **R41** | `[L5·A2]` Two-stage Docker build (belt+braces on top of R30). | Depth · M · L5 · AGENT | Optional if R30 lands — R30 already removes matplotlib from prod. |
| **R42** | `[L1·cross-cut]` `search_kb` bidirectional substring: single-char `"a"` matches every article. Fixture-only, subsumed by R37. | — · S · L1 · AGENT | Low priority. |

---

# COMPLETENESS CRITIC — what the six lanes did NOT cover

1. **No lane owns "run the full 15/15 suite after the semantics fixes land."** Six ⚠SEM edits
   (R13, R15, R27, R28, R29, R38) hit one file (`crosscheck.py`) with cross-interactions —
   R27's candidate-tool list feeds R29's false-absence branch and R28's number set. Each lane
   verified its own fix in isolation; nobody verified the *merged* verifier still passes the
   suite and the eval still returns 100/100/100 after R25's new phrasings. **This is the
   integrator's gate:** land B-tier 3 as one group, then run `pytest -q` + `benchmark.py 200
   --mock` before recording. Treat any phrasing that breaks the verifier as a real bug (per
   `[L3·F1]`), not one to delete.

2. **Ownership gap: `src/receiptguard/audit/ledger.py` is orphaned.** `parallel-status.md`
   assigns no lane to `audit/**` (L1 owns gateway/verify/recovery/claims, not audit). R31-D2
   (docstring) and R39 (adapter) have no owner. **Assign audit/ to a lane before those fixes.**

3. **The signed-receipt crypto itself was never audited.** The HMAC signing in
   `gateway/receipts.py` (`sig`, `RG_RECEIPT_SECRET`) is the load-bearing "can't lie"
   primitive and the hover-tooltip headline (R21), yet no lane checked key length, algorithm,
   replay resistance, or what happens when `RG_RECEIPT_SECRET` is the dev default. §A1 sets a
   real secret but nothing *verifies* the signature scheme is sound. **Under-served for a
   claim this central.**

4. **Recovery efficacy is unverified beyond the F8 bypass.** No lane checked whether
   `regenerate`/`replan` tiers actually *raise* groundedness or can livelock within
   `max_iterations` on adversarial input — only that the loop terminates. The recovery loop is
   half the product; its *quality* (not just its safety) is untested.

5. **No automated post-deploy assertion.** R33's smoke is per-tool/stdio; §A1 step 5 curls the
   live URL by hand. There is no test asserting `POST /run` on the live `*.fcapp.run` returns
   `chain_ok:true` + `mock:false`. A one-shot post-deploy smoke script would make the Stage-1
   proof reproducible instead of manual.

6. **DashScope quota / rate-limit / cost unchecked.** R26's live benchmark (~200 qwen-flash
   calls) plus repeated demo `/run` calls (~30 sequential LLM calls each, per `[L2·F2]`) could
   429 mid-recording. No lane confirmed account rate limits or a token budget for the live run
   + the video takes. **Risk to the on-camera money-shot.**

7. **No deploy-failure fallback for the video.** `video-script.md` assumes a live URL. If
   `s deploy` fails on the day, there is no scripted fallback to record against local-mock
   (which R8's badge already labels honestly). A one-line "plan B: local LIVE-key run" would
   de-risk A2 beyond just the R9 deadline.

---

# HONEST EXPECTED FIRST-PLACE DELTA (council bands)

Per `judge-council-report.md:13` — first-place probability, not raw score:

| State | First-place odds | What moves it |
|---|---|---|
| **As-is** | **~1%** | Stage-1 = FAIL. Score 71/100 is irrelevant while the deploy gate is open. |
| **+ Section A (deploy + video)** | **~9–11%** | The step-change. `s deploy` + captured `*.fcapp.run` + video clears Stage-1; R7/R8 make the money-shot real on camera; R1 removes the self-contradiction. Everything else is worth ~nothing until this lands. |
| **+ Section B (fully hardened)** | **~14–16%** | Marginal gains stack: R22 adds the only *new* scoring substance (Value 25%), R25/R26 turn "4 templates ×6" into a defensible n=200 with an offline-reproducible delta, R13/R27/R28/R29 close real detection bypasses (Depth), R19–R21 surface live reasoning (Innovation). |
| **Ceiling** | **≤18%** | Capped by the Innovation tiebreaker (30%): this entry honestly does not claim a novel primitive, so no amount of hardening pushes it past a top-tier novel-primitive competitor. Council's stated cap. |

**Bottom line:** Section A is ~90% of the achievable delta and gates the other 10%. Do A0 →
A1 → A2 → A3 first, in order. Section B is real but incremental. Section C is roadmap. The
single most dangerous omission is **not the code** — it's the missing full-suite re-run after
the six semantics fixes merge (critic #1) and the missing deploy-failure fallback for the
video (critic #7).

STATUS: DONE.

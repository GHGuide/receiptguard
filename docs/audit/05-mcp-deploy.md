# Audit 05 — MCP stability + deploy-readiness + ledger persistence boundary

Lane: robustness-audit (council #1 depth, #10 innovation). READ-only findings; nothing here applied.
Scope files: `Dockerfile`, `s.yaml`, `src/receiptguard/mcp/server.py`, `src/receiptguard/api/app.py`,
`src/receiptguard/audit/ledger.py`, `docs/fc-deployment.md`.

Format per fix: **file:line → exact change → rubric(Depth/Innovation) → effort**. `[USER-GATED]` = needs AccessKey / console.

---

## A. Slim runtime image (drop pytest/matplotlib)

Prod image installs test/plot deps → bigger image, slower cold start, larger attack surface.

- **A1. `requirements.txt:7-9` → split prod vs dev.**
  Create `requirements.txt` (prod only): `fastapi`, `uvicorn[standard]`, `openai`, `pydantic`, `httpx`, `mcp`.
  Move `pytest`, `matplotlib` to new `requirements-dev.txt` (`-r requirements.txt` + the two).
  Rubric: Depth (lean, reproducible runtime). Effort: 5 min.

- **A2. `Dockerfile:5-6` → two-stage build (belt+braces).**
  Change:
  ```dockerfile
  # builder
  FROM python:3.12-slim AS builder
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
  # runtime
  FROM python:3.12-slim
  WORKDIR /app
  COPY --from=builder /install /usr/local
  COPY src ./src
  COPY static ./static
  ```
  matplotlib pulls numpy/pillow/fonts → dropping it is the biggest single win. Verify: `docker images` size before/after; `docker run ... /health` still 200.
  Rubric: Depth. Effort: 15 min. NOTE: if A1 alone lands, A2 optional — A1 already removes matplotlib from prod.

- **A3. `server.py:16-19` caveat.** FastMCP does `raise SystemExit` if `mcp` missing. Keep `mcp` in the **prod** reqs (it is a runtime dep for the MCP transport, NOT dev). Do not strip it during slimming. The `api.app` module does not import `mcp`, so the API function survives without it, but the MCP function does not.
  Rubric: Depth. Effort: 0 (note only).

---

## B. `$FC_SERVER_PORT` + /health build/version + readiness

- **B1. `Dockerfile:13,16` → honor FC's injected port.**
  FC custom-container injects the listen port as `$FC_SERVER_PORT` (default 9000). CMD currently reads only `${PORT}`, so a non-default CAPort silently fails to bind.
  Change L16 CMD to:
  ```dockerfile
  CMD ["sh", "-c", "uvicorn receiptguard.api.app:app --host 0.0.0.0 --port ${FC_SERVER_PORT:-${PORT:-9000}}"]
  ```
  Keep `s.yaml:11 port: 9000` so FC sets `FC_SERVER_PORT=9000` → matches. Local `docker run` without FC still falls back to `PORT`/9000.
  Rubric: Depth (correct FC contract). Effort: 3 min.

- **B2. `app.py:31-34` → add build/version + optional deep readiness.**
  Current `/health` returns `status/mock/models` — good for the proof but has **no build id** and **no dependency readiness** (a warm instance with a dead DashScope key still reports `ok`). Change:
  ```python
  import os
  BUILD = os.getenv("RG_BUILD", "dev")          # set in s.yaml env or Docker ARG
  @app.get("/health")
  def health(deep: bool = False) -> dict:
      out = {"status": "ok", "build": BUILD, "mock": settings.mock,
             "models": {"agent": settings.model_agent, "worker": settings.model_worker}}
      if deep:                                    # readiness: cheap DashScope reachability
          out["ready"] = _probe_dashscope()       # 1 tiny call / TCP check, 2s timeout, never raise
      return out
  ```
  Liveness stays instant (`/health`); readiness opt-in (`/health?deep=1`) so cold-start warm hits and the proof recording are unaffected.
  Rubric: Depth (ops signal) + Innovation (readiness vs liveness split judges notice). Effort: 15 min.
  NOTE: keep `deep` OFF in the proof curl (step 2) — it must return instantly showing `mock:false`.

- **B3. model-name mismatch (blocks the proof).** `s.yaml:22 RG_MODEL_AGENT: qwen3.7-max` but `docs/fc-deployment.md:49,70` say the `/health` + proof must show `"agent":"qwen3-max"`. `/health` echoes `settings.model_agent` verbatim → recording will show `qwen3.7-max`, contradicting the narration/README.
  Fix: pick one name and align `s.yaml:22`, `fc-deployment.md:49,70,71`, and any README claim. Confirm `qwen3.7-max` is the real DashScope model id (if not, deploy 500s on first `/run`).
  Rubric: Depth (proof integrity). Effort: 5 min. `[USER-GATED]` — needs Leonardo to confirm which model id his DashScope account serves.

---

## C. MCP SSE + stdio both start cleanly + 3-tool smoke

Current state: `server.py` defines 3 tools (`run_guarded_autopilot`, `verify_claims`, `list_scenarios`) and `main()` switches transport on `argv[1]` (`sse` default, `stdio`). BUT the SSE app is **never mounted** in `api/app.py` and **no MCP resource exists** in `s.yaml`. Doc plan A ("mount `mcp.sse_app()` at `/mcp`") is unimplemented → the MCP-on-Alibaba claim is currently undeployed.

- **C1. `app.py` (after L21) → mount FastMCP SSE under the same function (doc plan A).**
  ```python
  from ..mcp.server import mcp as _mcp
  app.mount("/mcp", _mcp.sse_app())
  ```
  One URL, one function, reuses the API image (mcp already a runtime dep, B/A3). Avoids a 2nd fc3 resource + its cold starts.
  Rubric: Depth + Innovation (live MCP endpoint = the rubric's MCP lever, actually reachable). Effort: 20 min.
  RISK: FC request-scoped SSE is bounded by function `timeout` (s.yaml:15 = 300s) — fine for demo turns; note SSE dies at timeout. `s.yaml:15` already 300s ✓.

- **C2. `s.yaml:26-31` trigger methods.** SSE mount needs GET (handshake) + POST (messages) — `methods: [GET, POST]` already present ✓. No change; verify after C1 that `/mcp/sse` returns `text/event-stream`.

- **C3. add a 3-tool smoke script (new `scripts/mcp_smoke.py` or a pytest).** Covers stdio + (post-deploy) SSE:
  ```bash
  # stdio (local, no network): spawn server, list tools, call each once
  python -m receiptguard.mcp.server stdio  # driven by an MCP client stub / mcp dev
  ```
  Assert: `list_scenarios()` non-empty dict; `run_guarded_autopilot("refund_damaged")` has `receipts` + `audit`; `verify_claims(["order ORD-1001 exists"])` returns a verdict list. This is the cheapest proof all 3 tools wire end-to-end before recording.
  Rubric: Depth (verification, council #1). Effort: 30 min.
  NOTE `server.py:43-46` `verify_claims` hardcodes `lookup_order(order_id="ORD-1001")` — smoke must use a claim consistent with ORD-1001 or verdicts read as `unbacked` and look broken on camera.

---

## D. Audit-ledger persistence boundary (the tamper-evidence risk)

**Core finding:** `s.yaml:25 RG_LEDGER_PATH=/tmp/receiptguard_ledger.db`. FC `/tmp` is per-instance + ephemeral → on instance recycle/scale the hash chain **resets to GENESIS**. The product's headline claim is *tamper-evident append-only audit*; on FC-as-configured the chain silently truncates. Not a bug for a single live demo, but the deployment story must not overclaim.

Second finding — **false portability claim:** `ledger.py:4-5` docstring: *"the same schema/DSN works against Alibaba RDS PostgreSQL in production."* The code is SQLite-only: `sqlite3.connect` (L35), `AUTOINCREMENT` (L39, Postgres uses `SERIAL/IDENTITY`), `?` placeholders (L54,61 — Postgres uses `%s`), column name `idx` (L38, reserved-ish, quote in PG). A DSN swap does **not** work as written.

### Document (README/deploy doc) — do now, zero code:
- **D1. `fc-deployment.md:89` already flags** "`/tmp` per-instance + ephemeral (chain resets on recycle — fine for live demo, note in README)." → make sure the **README** and the **Verdict/claims copy** repeat it: *"Tamper-evidence holds within an instance lifetime; durable cross-recycle chaining requires RDS (Alibaba RDS PostgreSQL 15, §8)."* Prevents a judge calling the claim overblown.
  Rubric: Depth (honest boundary = credibility). Effort: 10 min.
- **D2. fix the false docstring `ledger.py:4-5`** → "SQLite for local + FC-`/tmp` demo; a Postgres adapter (see §D3) is required for RDS — the DSN is NOT drop-in." Honesty > aspiration.
  Rubric: Depth. Effort: 3 min.

### Implement (only if time) — real durable path:
- **D3. `ledger.py:34-58` → thin DB abstraction so RDS is a config swap.**
  Add a `_Backend` seam: keep `AuditLedger` API, but pick driver from DSN scheme —
  `sqlite://…`/bare path → `sqlite3`; `postgres://…` → `psycopg` with `SERIAL PRIMARY KEY`, `%s` placeholders, quoted `"idx"`. Reader (`all/verify_chain`) is dialect-agnostic once placeholders abstracted.
  This makes the D1 promise real: point `RG_LEDGER_PATH`→`RG_LEDGER_DSN` at RDS and durability + tamper-evidence survive recycle.
  Rubric: Depth (real audit story) + Innovation (EU AI Act Art.12 record-keeping — durable hash chain is a differentiator). Effort: 2-3 h. **Recommendation: DOCUMENT (D1/D2) for the hackathon; keep D3 as "roadmap" in the Verdict — do not spend build time unless the ledger is on-camera surviving a recycle.**
- **D4. RDS stand-up** `[USER-GATED]` — `fc-deployment.md:59,86` correctly warn RDS is NOT free + needs VPC/NAT. For a screenshot only: create RDS PG15 1c2g same region, whitelist FC VPC, capture, **release**. Needs AccessKey + console. Effort: 30 min console. Do NOT leave running (hourly bill).

---

## E. Exact runbook: `s config add` → `s deploy` → capture

All `[USER-GATED]` (AccessKey / ACR credentials / DashScope key from Leonardo's account).
Consolidated from `fc-deployment.md` §1-9 with the gaps closed:

```bash
# 0. secrets (never bake into image — s.yaml:20,24 read them from env)
export DASHSCOPE_API_KEY=...                                  # intl account key
export RG_RECEIPT_SECRET=$(python -c 'import secrets;print(secrets.token_hex(32))')  # MUST be real, not dev default
# 1. [USER-GATED] one-time creds  (RAM user: AliyunFCFullAccess + AliyunContainerRegistryFullAccess)
s config add     # provider 'alibaba', paste AccountID + AccessKeyID/Secret, alias 'default'  (matches s.yaml:3 access: default)
# 2. [USER-GATED] ACR: console → Container Registry Personal (ap-southeast-1) → namespace receiptguard → repo api
docker login --username=<acr-user> registry-intl.ap-southeast-1.aliyuncs.com
# 3. build + push + deploy (s deploy does all three from s.yaml)
s deploy                                                      # builds image (s.yaml:18 tag), pushes ACR, creates fn + HTTP trigger
# 4. capture URL
s info                                                        # → https://<fnId>.ap-southeast-1.fcapp.run
# 5. warm + smoke (order matters for the recording)
curl https://<fnId>.ap-southeast-1.fcapp.run/health          # warm cold start; expect mock:false + models
curl -X POST .../run -H 'content-type: application/json' -d '{"scenario":"refund_damaged"}'
curl .../mcp/sse                                              # after C1: expect text/event-stream  (else MCP not mounted)
# 6. proof log
s logs                                                        # capture a live request line showing the real qwen model id
```

- **E1. gap vs doc:** `fc-deployment.md` never states that `s deploy` **also builds+pushes** (§5 implies it, §3 does a manual `docker login`). Clarify: with `customContainerConfig.image` set (s.yaml:18), `s deploy` builds from local `Dockerfile` and pushes to that tag — no separate `docker build/push` needed. Confirm the `s` fc3 component build behavior for the installed version; if it does NOT auto-build, prepend `docker build -t <image> . && docker push <image>`.
  Rubric: Depth. Effort: 5 min doc.
- **E2.** `s.yaml:18` image tag `0.1.0` is static → re-deploys reuse the tag; FC may cache. Bump tag per deploy (`:0.1.1`) or use a build id (ties to `RG_BUILD` / B2) so the recorded instance is provably the new image.
  Rubric: Depth. Effort: 5 min.

---

## Priority for the recording (do these, skip the rest)

1. **B3** model-name align — otherwise the proof contradicts itself. `[USER-GATED]` 5 min.
2. **B1** `$FC_SERVER_PORT` — otherwise a non-9000 CAPort = dead deploy. 3 min.
3. **C1** mount MCP SSE — otherwise the MCP claim is undeployed. 20 min.
4. **A1** prod-reqs split — cheap image win. 5 min.
5. **D1/D2** document the ledger boundary honestly. 13 min.
6. **B2** `/health` build+readiness — nice depth signal. 15 min.
7. **C3** 3-tool smoke — verification before camera. 30 min.

Defer: **A2** (multi-stage), **D3** (Postgres adapter), **D4** (RDS screenshot) — roadmap unless the ledger is on-camera surviving a recycle.

STATUS: DONE.

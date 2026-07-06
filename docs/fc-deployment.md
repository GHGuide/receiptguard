# ReceiptGuard — Alibaba Function Compute deployment

Path: **FC 3.0 Custom Container**, single function, HTTP trigger.
Why: the Dockerfile already listens on `0.0.0.0:9000` (= FC's default CAPort), so it
deploys with near-zero changes; FC custom-container supports SSE/streaming (needed for
the MCP-over-SSE server); scale-to-zero keeps it ~$0.
Fallback: **SAE** (always-on, ALB supports SSE) only if FC's request-scoped SSE fights
the MCP long connection; ECS last resort. Keep the Dockerfile so the pivot is a 20-min swap.

Region: **ap-southeast-1 (Singapore)** for everything (same as DashScope intl + RDS).

## 0. Local prep
```bash
docker build -t receiptguard:latest .
docker run -p 9000:9000 -e DASHSCOPE_API_KEY=$DASHSCOPE_API_KEY receiptguard:latest
curl localhost:9000/health    # expect {status:ok}
```

## 1. Account / CLI
- International console → activate **Function Compute (FC 3.0)** + **Container Registry (ACR)** in ap-southeast-1.
- Create RAM user with `AliyunFCFullAccess` + `AliyunContainerRegistryFullAccess`; make an AccessKey.

## 2. Serverless Devs
```bash
npm install @serverless-devs/s -g     # use a node version manager, avoid sudo on macOS
s -v
s config add    # 'Alibaba Cloud (alibaba)', paste AccountID + AccessKey, alias 'default'
```

## 3. ACR
- Console → Container Registry → Personal Edition (same region) → namespace `receiptguard` → repo `receiptguard/api`.
- Note login server e.g. `registry-intl.ap-southeast-1.aliyuncs.com`.
```bash
docker login --username=<acr-user> registry-intl.ap-southeast-1.aliyuncs.com
```

## 4. `s.yaml` (already in repo root of receiptguard/ — edit image tag/region)

## 5. Build + push + deploy
```bash
export DASHSCOPE_API_KEY=...
export RG_RECEIPT_SECRET=$(python -c 'import secrets;print(secrets.token_hex(32))')
s deploy     # builds image, pushes to ACR, creates function + HTTP trigger
```

## 6. URL + smoke test
```bash
s info       # prints https://<fnId>.ap-southeast-1.fcapp.run
curl https://<fnId>.ap-southeast-1.fcapp.run/health   # expect "mock":false, "models":{"agent":"qwen3.7-max"}
curl -X POST .../run -H 'content-type: application/json' -d '{"scenario":"refund_damaged"}'
# open the root URL in a browser for the split-screen UI
```

## 7. MCP-over-SSE (pick A)
- **A (simplest, one URL):** mount the FastMCP SSE app under FastAPI (`mcp.sse_app()` at `/mcp`), reuse the same function.
- **B:** second fc3 resource `mcp`, same image, CMD override to run the MCP SSE server, `timeout: 600`, `authType: anonymous`.
- CRITICAL: FC streams ONLY for custom-runtime/container with `Transfer-Encoding: chunked` (FastMCP SSE already does). SSE is bounded by function timeout — keep 300–900s.

## 8. (Optional, durable audit) RDS PostgreSQL 15 (1c2g) same region; whitelist FC VPC; bind via vpcConfig; point ledger DSN at RDS. SQLite-on-`/tmp` is fine for the demo — `/tmp` is per-instance + ephemeral (chain resets on recycle). State this in README.

## 9. Logs
```bash
s logs   # capture a live request showing model qwen3.7-max for the proof recording
```

---

## Proof-recording plan (continuous 60–90s, NO cuts — judges value unedited deploy proof)
1. **0–10s:** show `s.yaml`, run `s deploy` (or `s info`) so FC function name + region + `fcapp.run` URL are visible.
2. **10–35s:** `curl .../health` → response must show `"mock": false` and `"models": {"agent": "qwen3.7-max", ...}` — proves real Qwen on Alibaba, not mock.
3. **35–70s:** `curl -X POST .../run -d '{"scenario":"refund_damaged"}'` → JSON with HMAC-signed receipts + per-claim verdicts + audit hash chain (+ `reasoning_content` if surfaced).
4. **70–90s:** open the `fcapp.run` root URL in a browser → split-screen UI live from Alibaba. Optional 3s of FC console (function + ACR image + region). Narrate the `.fcapp.run` host + region so it's unambiguously Alibaba.

**Alibaba-API-usage proof file to link in Devpost:** `src/receiptguard/llm/qwen.py` (the ONLY caller of Alibaba; builds the OpenAI client against the DashScope base_url, calls qwen3.7-max, reads `reasoning_content`). Secondary: `Dockerfile` + `s.yaml`.

## `reasoning_content` check (run BEFORE deploy, then again in FC logs)
```bash
curl -X POST https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" -H 'Content-Type: application/json' --no-buffer \
  -d '{"model":"qwen3.7-max","messages":[{"role":"user","content":"2+2, think first"}],
       "stream":true,"stream_options":{"include_usage":true},"enable_thinking":true}'
```
Streamed chunks show `delta.reasoning_content` BEFORE the normal `content` deltas. `enable_thinking` is non-standard → stays in `extra_body`; hybrid thinking is OFF by default on qwen3.7-max so the flag is **mandatory**. `qwen.py` now streams the agent/adjudicate call (see PROGRESS) to de-risk timeouts + guarantee `reasoning_content`.

## Cost (comfortably inside $40, likely ~$0 infra)
FC new-account free trial dwarfs a demo; ACR Personal is free. **Real spend is DashScope tokens, not infra** — keep `RG_MODEL_WORKER=qwen-flash`, only call qwen3.7-max on the agent/adjudicate turn, cap `thinking_budget` (2048). WATCH: RDS is NOT free (prefer SQLite-on-`/tmp`, stand RDS up briefly for a screenshot then release); never enable provisioned/reserved instances; SAE/ECS fallbacks bill hourly (stop after recording); NAT/VPC for RDS adds small hourly cost.

## Gotchas
- **Filesystem read-only except `/tmp`** → `RG_LEDGER_PATH=/tmp/receiptguard_ledger.db`; per-instance + ephemeral (chain resets on recycle — fine for live demo, note in README).
- **Port/CAPort** → must listen `0.0.0.0:9000` (Dockerfile does). Reusing image for MCP SSE → set `props.port` to the bound port.
- **SSE is method-gated** → FC streams ONLY for Custom Runtime / Container Image with chunked encoding. A built-in-runtime zip silently breaks SSE + qwen3.7-max streaming + MCP transport.
- **Timeout vs SSE lifetime** → default 60s kills long connections; raise to 300–900s for MCP SSE, 300 for `/run`.
- **Cold start** → hit `/health` once to warm before recording.
- **DashScope intl vs CN** → use `https://dashscope-intl.aliyuncs.com/...` with an intl-account key. Never bake `DASHSCOPE_API_KEY` / `RG_RECEIPT_SECRET` into the image — pass via FC env vars; the receipt secret MUST be a real `token_hex(32)`, not the dev default, or the unforgeable-receipt claim is bogus.

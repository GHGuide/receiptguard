# ReceiptGuard — Deploy-Readiness & Submission Master (single source of truth)

**Deadline: 2026-07-09 2:00 PM PDT.** Track 4 (Autopilot Agent), Qwen Cloud Hackathon.
Status tags: ✅ done · 🟡 agent-in-progress · 🔴 USER-gated (only Leonardo can do it).

---

## 0. Northstar submission checklist (BRIEF.md §Submission) — live status
| # | Required deliverable | State | Owner |
|---|---|---|---|
| 1 | Public OSS repo + LICENSE + run instructions | ✅ github.com/GHGuide/receiptguard (public, MIT LICENSE, README quickstart) | — |
| 2 | **Alibaba Cloud deploy proof** (recording + link to API-usage code file) | 🔴 needs deploy → §A | USER+agent |
| 3 | Architecture diagram | ✅ `docs/architecture.svg` (in README above the fold) | — |
| 4 | ~3-min public demo video | 🟡 pipeline scaffolded + rendering draft → §B; upload 🔴 | agent+USER |
| 5 | Text description of features | ✅ `docs/DEVPOST.md` (paste-ready) | — |
| 6 | Track identification (Track 4) | ✅ README + DEVPOST state Track 4 | — |
| 7 | (optional) Blog post for Blog Prize | ✅ `docs/BLOG.md` | — |

**Two hard gates remain: #2 (deploy proof) and #4 (video upload).** Everything else is done or in-flight.

---

## A. DEPLOY on Alibaba Function Compute — the Stage-1 gate (~90% of score)

### A0 — code prerequisites (agent-doable) — ✅ DONE
- ✅ R2 LLM wall-clock timeout + retry cap (was ~1800s vs FC 300s ceiling)
- ✅ R3 Dockerfile binds `$FC_SERVER_PORT` (was `$PORT` → dead deploy)
- ✅ R1 model id unified `qwen3.7-max` (code + prose; `/health` no longer contradicts pitch)
- ✅ s.yaml valid: fc3, ap-southeast-1, port 9000, timeout 300, secrets env-injected, ledger `/tmp`
- 🟡 R5/R6 cumulative run-budget + escalate-on-timeout (nice-to-have; deploy works without)

### A1 — the deploy itself — 🔴 USER-gated (needs AccessKey)
> **Prerequisite:** start **Docker Desktop** (daemon must be running — `s deploy` builds + pushes
> the custom-container image locally). Confirm with `docker info`. Also log into Alibaba intl first.
```bash
cd receiptguard
# secrets (never bake into image):
export DASHSCOPE_API_KEY=...            # intl DashScope key from Leonardo's account
export RG_RECEIPT_SECRET=$(python -c 'import secrets;print(secrets.token_hex(32))')
# 1. [USER] creds — RAM AccessKey with AliyunFCFullAccess + AliyunContainerRegistryFullAccess
s config add            # provider alibaba, AccountID + AccessKey, alias 'default'
# 2. [USER] ACR Personal (ap-southeast-1) → namespace receiptguard → repo api; then:
docker login --username=<acr-user> registry-intl.ap-southeast-1.aliyuncs.com
# 3. build + push + deploy (s deploy does all three from s.yaml):
s deploy
# 4. capture the live URL:
s info                  # → https://<fnId>.ap-southeast-1.fcapp.run
# 5. warm + smoke (order matters for the recording):
curl .../health         # expect mock:false + models.agent=qwen3.7-max
curl -X POST .../run -H 'content-type: application/json' -d '{"scenario":"refund_damaged"}'
# 6. proof log:
s logs                  # capture a live line showing the real qwen model id
```
**BLOCKER RIGHT NOW:** Alibaba account not logged in (browser shows logout / China site).
Deploy targets the **International** site — sign in at `account.alibabacloud.com`.
- ✅ **A1-confirm DONE (pre-verified):** live-probed the DashScope key — `qwen3.7-max`, `qwen3-max`,
  `qwen-max`, `qwen-flash` all resolve (200 OK). App boots clean in LIVE mode locally:
  `/health` → `{"mock":false,"models":{"agent":"qwen3.7-max","worker":"qwen-flash"}}`. On-camera
  500 risk eliminated. `.env` already holds the DashScope key; only the Alibaba **RAM AccessKey**
  (deploy cred, distinct from the DashScope key) + Docker daemon + ACR repo remain.

### A2 — deploy-proof recording — 🔴 USER
Short screen recording (separate from the demo) proving the backend runs on Alibaba: show the
`*.fcapp.run` URL in the address bar, `curl .../health` → `mock:false`, and `s logs` with a live
qwen call. Link `src/receiptguard/llm/qwen.py` in Devpost as the Alibaba-API-usage code file.

---

## B. DEMO VIDEO via parent `video-pipeline/` (Remotion + Playwright + ElevenLabs)

### B0 — pipeline prep — 🟡 IN PROGRESS (video lane)
- ✅ `video/` scaffolded (theme qwen), toolchain verified (Playwright chromium + ffmpeg + node all present)
- 🟡 Video lane authoring `script/script.json` (ReceiptGuard heist arc) + `capture/scenes.mjs`
  (drives the real demo UI: `#scenario`/`#adv`/`#run` → money-shot = adversarial catch)
- 🟡 Recording captures against local demo (localhost:8000) + rendering a captions/edge-tts DRAFT cut
- The draft proves the pipeline end-to-end; **ElevenLabs key is the ONLY thing between draft and final master.**

### B1 — final master + upload — 🔴 USER
1. (optional, better) put `ELEVENLABS_API_KEY` in `video/.env` → rerun `build.mjs --only vo,mix,package` for Sarah VO.
2. Record the LIVE deploy in the montage beats once §A is up (swap `base_url` → the `*.fcapp.run` URL, re-capture).
3. Upload the master to YouTube/Vimeo **public**, "Not for Kids", English captions.
4. Paste the link into Devpost.
- Hard cut: video public + link pasted by **11:00 AM PDT** (a video still processing at 2:05 PM scores 0).

---

## C. Judging maximization (Depth 30% · Innovation 30% · Value 25% · Presentation 15%)

- ✅ Tier-1 hardening merged: R13 invariant bypass closed, R11/12/14/15/28, 20/20 tests
- ✅ Hardening lane merged (commit `4f535dc`, **22/22 tests**): **R22** $-pain model + *Moffatt v.
  Air Canada* 2024 BCCRT 149 citation (only NEW Value substance); **R16/17/18** benchmark →
  provenance + stratified n=200 (50/type) + Wilson 95% CIs. Live `eval/out/results.json` (n=24)
  preserved; next live run auto-emits the new schema.
- Remaining optional (post-gate): R19-21 live `/stream` reasoning pane (Innovation), R25/26 offline-reproducible bench, R4 mount MCP SSE
- Positioning locked (README): lead with the product outcome, benchmark+diagram above the fold, MCP foregrounded, honest prior-art section

---

## D. Final Devpost submission — 🔴 USER (the last action)
Fields: project name **ReceiptGuard** · Track **1→ actually Track 4 Autopilot Agent** · text = `docs/DEVPOST.md`
· repo URL · video URL · deploy-proof recording URL · architecture diagram · blog URL (optional).

---

## Time budget to 2:00 PM PDT (now ~03:35 AM PDT, ~10.5h)
1. **NOW:** log into Alibaba (unblocks §A). Lanes finish video draft + hardening in background.
2. **§A deploy** (~30–60 min once key is in) → warm URL.
3. **§A2 + B1 recording** (~2–3h): deploy-proof clip + demo video on the live URL, upload.
4. **§D submit** with ≥1h buffer.
**Critical path = login → deploy → record → upload → submit. Reserve 3h for record/upload.**

# Audit 04 — Demo UI: live-deploy surfacing + on-camera money-shot

Lane: robustness-audit (council items #3 HIGH, #6 MED). Read-only pass over
`static/index.html`, `src/receiptguard/api/app.py`, `docs/video-script.md`.
This doc is the only write. Nothing below is applied yet.

## Ground truth found

- Backend routes: `GET /health` `{status, mock, models:{agent,worker}}`,
  `GET /scenarios`, `POST /run` (body already accepts `adversarial: bool` —
  `RunRequest` in `src/receiptguard/api/app.py:25-28`), `GET /` → static UI.
  **No `/stream` endpoint exists.** `/health` does **not** return region/host.
- `POST /run` response (`RunResult.to_dict`, `src/receiptguard/pipeline.py:48`):
  `baseline{draft,verdicts,failed}`, `guarded{final_draft,shipped,score,iterations[]}`,
  `receipts[]` (receipt_id, tool, args_hash, output_hash, snippet, ts, sig),
  `audit[]`, `chain_ok`. Verdicts carry `receipt_id` + `reason` + `tool` —
  everything hover-to-receipt needs is already in the payload.
- UI already has per-claim color dots (green backed / red fabricated / grey
  opinion-inference) and a post-hoc `qwen3-max reasoning:` box. Missing:
  deploy badge, adversarial toggle, receipt hover, live reasoning stream,
  mobile layout, README screenshot.
- Deploy region per `s.yaml`: `ap-southeast-1`. Video script beats 0:35 ("running
  on Alibaba Function Compute" badge) and 1:15 (money-shot: forced unbacked
  claim → blocked/escalate) both depend on fixes 1 and 3 below.

---

## Fix 1 — Header LIVE·Alibaba FC vs Local-mock badge (council #3, HIGH)

**Section:** `header` (index.html:40-43) + `init()` (index.html:72-78).

The `.mode` span already shows `LIVE · qwen3-max` / `MOCK mode (offline)` but
it's tiny, grey, and says nothing about *where* it runs. The judges' Stage-1
gate is deploy proof; the badge must scream host + region on camera.

**HTML** — inside `<header>`, after the `.sub` div:

```html
<div id="deploy-badge" class="deploy neutral">checking…</div>
```

**CSS** — add to `<style>`:

```css
.deploy{display:inline-block;margin-top:8px;padding:4px 12px;border-radius:20px;
        font-size:12px;font-weight:700;letter-spacing:.3px}
.deploy.live{background:#0f2e1a;color:#86efac;border:1px solid #22c55e}
.deploy.mock{background:#2b2410;color:#fcd34d;border:1px solid #f59e0b}
.deploy.neutral{background:var(--panel);color:var(--mut);border:1px solid var(--line)}
```

**JS** — replace the mode line in `init()`:

```js
const r = await fetch('/health').then(x=>x.json());
const onFC = location.hostname.endsWith('.fcapp.run');
const badge = document.getElementById('deploy-badge');
if (!r.mock) {
  badge.className = 'deploy live';
  badge.textContent = (onFC ? '● LIVE · Alibaba Function Compute · ap-southeast-1 · '
                            : '● LIVE · ') + r.models.agent + ' + ' + r.models.worker;
} else {
  badge.className = 'deploy mock';
  badge.textContent = '○ Local mock (offline, deterministic) — set DASHSCOPE_API_KEY for live Qwen';
}
document.getElementById('mode').textContent = r.mock ? 'MOCK' : 'LIVE';
```

Host detection is client-side (`location.hostname`) so **zero backend change**.
Optional 1-line hardening in `api/app.py` if a server-truth region is wanted:
`"region": os.environ.get("FC_REGION", "")` in the `/health` dict — FC injects
`FC_REGION` at runtime; then prefer `r.region` over the hostname sniff.

**Rubric:** Presentation (deploy proof visible in every frame of the video +
README screenshot) · Innovation (judges see real Alibaba stack, not localhost).
**Effort:** ~15 min.

---## Fix 2 — Hover-to-receipt on every claim (council #3)

**Section:** `claimEl()` (index.html:79-86) + `run()` receipts handling
(index.html:102).

Verdicts already carry `receipt_id`; receipts array carries `snippet`,
`args_hash`, `output_hash`, `sig`, `ts`. Join them client-side and show the
signed receipt on hover — this is the "can't lie" claim made tangible.

**JS** — keep receipts in scope, build a map, attach a tooltip:

```js
let RECEIPTS = {};
function claimEl(v){
  const ok = STATUS_OK.has(v.status);
  const cls = v.status==='backed'?'ok':(ok?'neu':'bad');
  const el = document.createElement('div'); el.className='claim '+cls;
  el.innerHTML = `<span class="dot"></span><div><div>${v.text}</div>
    <div class="st">${v.status}${v.receipt_id?(' · '+v.receipt_id):''} — ${v.reason}</div></div>`;
  const rc = v.receipt_id && RECEIPTS[v.receipt_id];
  if (rc) {
    el.classList.add('has-receipt');
    const tip = document.createElement('div');
    tip.className = 'receipt-tip';
    tip.innerHTML = `<b>${rc.tool}</b> ${rc.receipt_id}<br>
      <span>output: ${rc.snippet}</span><br>
      <span>HMAC: ${String(rc.sig).slice(0,20)}… · ${rc.ts}</span>`;
    el.appendChild(tip);
  }
  return el;
}
// in run(), BEFORE the two render() calls:
RECEIPTS = Object.fromEntries(r.receipts.map(x=>[x.receipt_id, x]));
```

**CSS:**

```css
.claim{position:relative}
.claim.has-receipt{cursor:help}
.receipt-tip{display:none;position:absolute;left:12px;top:100%;z-index:10;
  background:#0d1320;border:1px solid var(--blue);border-radius:8px;padding:10px 12px;
  font:11px ui-monospace,Menlo,monospace;color:#cdd9ea;max-width:420px;
  box-shadow:0 8px 24px rgba(0,0,0,.5)}
.claim.has-receipt:hover .receipt-tip{display:block}
```

Field-name check before applying: confirm `Receipt.to_dict()` in
`src/receiptguard/gateway/receipts.py` emits `snippet`/`sig`/`ts` under exactly
those keys; adjust the three property reads if not.

**Rubric:** Innovation (signed-receipt primitive demonstrated, not narrated) ·
Presentation (video beat 0:35 "gateway emitting a signed receipt" gets a
visible artifact). **Effort:** ~25 min.

---

## Fix 3 — Adversarial toggle: fire the catch on real Qwen (money-shot, video beat 1:15)

**Section:** `.bar` (index.html:44-48) + `run()` fetch body (index.html:91).

Backend already supports it — `RunRequest.adversarial` injects a red-team
unbacked claim. The UI just never sends it. This is the single control that
makes the 1:15-1:50 money-shot reproducible on camera against live Qwen.

**HTML** — inside `.bar`, after the run button:

```html
<label class="adv"><input type="checkbox" id="adversarial">
  ⚔ adversarial: inject unbacked claim</label>
```

**CSS:**

```css
.adv{display:flex;gap:6px;align-items:center;font-size:13px;color:var(--mut);cursor:pointer}
.adv input{accent-color:var(--red)}
```

**JS** — one line in `run()`:

```js
body: JSON.stringify({scenario, adversarial: document.getElementById('adversarial').checked})
```

On-camera flow: run clean (guarded ships, grounding 1.0) → tick the box →
re-run → red claim appears, badge flips to `blocked`, reasoning box explains
the block. Zero backend work.

**Rubric:** Presentation (money-shot is one visible click, not a curl command
off-screen) · Innovation (live adversarial recovery on real qwen3-max).
**Effort:** ~10 min. **Do this one first — highest score-per-minute.**

---

## Fix 4 — Live reasoning pane, graceful without /stream (council #6, MED)

**Section:** `.reason` div (index.html:62) + `run()` (index.html:88-106).

**`/stream` does not exist** in `api/app.py` — only `/health /scenarios /run /`.
So: feature-detect once, use SSE when available, keep today's post-hoc box as
fallback. UI ships safely whether or not the backend lane adds the endpoint.

**JS:**

```js
let HAS_STREAM = false;
async function detectStream(){
  try { HAS_STREAM = (await fetch('/stream', {method:'HEAD'})).ok; } catch(e) {}
}
// call detectStream() from init()

function openReasoningStream(scenario){
  const rn = document.getElementById('g-reason');
  rn.style.display='block';
  rn.innerHTML='<b>qwen3-max reasoning (live):</b> <span id="rsn"></span>';
  const es = new EventSource('/stream?scenario='+encodeURIComponent(scenario));
  const out = document.getElementById('rsn');
  es.onmessage = e => { out.textContent += e.data; rn.scrollTop = rn.scrollHeight; };
  es.onerror = () => es.close();   // graceful: post-hoc box still fills in below
  return es;
}
// in run(): const es = HAS_STREAM ? openReasoningStream(scenario) : null;
//           ... after fetch resolves: if (es) es.close();
// keep the existing firstReason block as-is — it overwrites/backfills the pane.
```

If the backend lane adds it, the matching endpoint shape (for reference only —
not this lane's file):

```python
@app.get("/stream")
async def stream(scenario: str = "refund_damaged") -> StreamingResponse:
    def gen():
        for chunk in ReceiptGuard().stream_reasoning(scenario):  # yields reasoning_content deltas
            yield f"data: {chunk}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
```

`reasoning_content` deltas are already captured in
`src/receiptguard/llm/qwen.py:99-101`; today they're joined post-hoc. The
pipeline would need a generator variant to feed SSE — that's backend-lane
scope. UI side is safe to ship now: without `/stream`, `HAS_STREAM` stays
false (404/405 on HEAD) and behavior is identical to today.

**Rubric:** Presentation (thinking-model visibly thinking = video beat 0:35) ·
Innovation (surfacing qwen3-max thinking mode, a named stack feature).
**Effort:** UI ~20 min; backend generator ~1-2 h (other lane).

---

## Fix 5 — Mobile / narrow window: no horizontal scroll

**Section:** `<style>` (index.html:7-37).

Current breakers: `.grid` hard `1fr 1fr`; `.rcpts`/`.audit` monospace
receipt-chains with no wrap; `.bar` doesn't wrap so select+button+badge
overflow < ~560px. Judges open READMEs on laptops with split screens —
and the committed screenshot (fix 6) may be taken at half-width.

**CSS:**

```css
.bar{flex-wrap:wrap}
.rcpts,.audit{overflow-x:auto;word-break:break-all}
.draft{overflow-wrap:anywhere}
@media (max-width: 760px){
  .grid{grid-template-columns:1fr;padding:14px}
  header,.bar,.foot{padding-left:14px;padding-right:14px}
  .mode{margin-left:0;width:100%}
}
```

**Rubric:** Presentation (no broken layout in screenshot/video at any crop).
**Effort:** ~10 min.

---

## Fix 6 — Committed screenshot for README (council #3)

**Section:** repo artifact, not index.html. Take AFTER fixes 1-3 land.

1. Deploy (or run live locally with `DASHSCOPE_API_KEY` set), open the UI on
   the `*.fcapp.run` URL so the badge reads
   `● LIVE · Alibaba Function Compute · ap-southeast-1 · qwen3-max + qwen-flash`.
2. Tick adversarial, run, wait for: red fabricated claim on the left, blocked
   badge + reasoning box on the right, `chain VERIFIED ✓` in the footer.
   That single frame carries deploy proof + money-shot + tamper-evidence.
3. Capture at 1600×1000, save `docs/screenshot-live.png`, commit, embed at the
   top of README under the architecture diagram:

```markdown
![ReceiptGuard live on Alibaba Function Compute — adversarial claim blocked](docs/screenshot-live.png)
*Live `*.fcapp.run` deployment: injected unbacked refund claim caught,
response blocked, hash-chain verified.*
```

**Rubric:** Presentation (judges may score on README + video alone — rules say
running the project is not required; the screenshot IS the deploy proof for
non-runners). **Effort:** ~15 min, gated on Leonardo's `s deploy` + AccessKey.

---

## Order of attack (score-per-minute)

| # | Fix | Effort | Rubric weight |
|---|-----|--------|---------------|
| 1 | Adversarial toggle (fix 3) | 10 min | money-shot enabler |
| 2 | Deploy badge (fix 1) | 15 min | Stage-1 gate proof |
| 3 | Mobile CSS (fix 5) | 10 min | screenshot safety |
| 4 | Hover-to-receipt (fix 2) | 25 min | primitive made visible |
| 5 | Screenshot + README (fix 6) | 15 min | blocked on deploy |
| 6 | Reasoning SSE UI (fix 4) | 20 min UI | graceful either way |

Total UI work ≈ 95 min. No backend file touched except the optional
one-line `FC_REGION` addition to `/health` and the other-lane `/stream`.

STATUS: DONE

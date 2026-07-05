# Audit 02 — agent / api robustness (council #6 stream · #7 timeout/split-brain · hang-risk)

Lane: robustness-audit. READ-only. Scope files: `agent/autopilot.py`, `pipeline.py`,
`api/app.py`, `llm/qwen.py`, `config.py`, `cli.py`.

Canonical model name (per `docs/judge-council-report.md:31`, `docs/parallel-status.md:17`):
**`qwen3.7-max`**. `config.py` is owned by lane **L2** — coordinate before editing line 35
(see F7). This lane flags; L2 lands the config edit.

---

## Verdict summary

| # | Finding | Rubric | Sev | Effort |
|---|---------|--------|-----|--------|
| F1 | OpenAI client built with NO timeout/retries → 600s×3 ≈ 1800s per call vs FC 300s ceiling | Depth | **HIGH** | S |
| F2 | `_real_draft` + `pipeline.run` chain ≤30 sequential LLM calls, zero wall-clock budget → guaranteed FC kill on live Qwen | Depth | **HIGH** | M |
| F3 | `chat_with_tools` blocking, non-stream, no per-call timeout | Depth | MED | S |
| F4 | No SSE surface — `reasoning_content` only visible post-hoc in `/run` JSON | Innovation | MED | M |
| F5 | `complete()` buffers stream deltas instead of yielding → nothing to feed SSE | Innovation | MED | S |
| F6 | No graceful degrade: a timeout throws raw, no partial-draft + escalate, audit turn lost | Depth | MED | M |
| F7 | Model-name split-brain: runtime `qwen3.7-max` vs config default + all comments `qwen3-max` | Depth | MED | S |

---

## HANG-RISK (the load-bearing Depth finding)

### F1 — no client-side timeout/retry cap
`llm/qwen.py:43`
```python
self._client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
```
Proof (`.venv/.../openai/_constants.py:9-10`): `DEFAULT_TIMEOUT = Timeout(600)`,
`DEFAULT_MAX_RETRIES = 2`. So ONE slow/failing call = up to 600s × 3 attempts ≈ **1800s**.
FC ceiling = **300s** (`s.yaml:15`). Single stalled turn already blows the budget → FC
kills request → 500, no result, ledger turn never written.

- **Exact change** `qwen.py:43`:
```python
self._client = OpenAI(
    api_key=settings.api_key,
    base_url=settings.base_url,
    timeout=settings.llm_timeout_s,   # new setting, default 60.0
    max_retries=1,
)
```
- **Rubric:** Depth (deploy correctness under FC ceiling).
- **Effort:** S.
- **Test:** monkeypatch `settings.llm_timeout_s=0.001`, assert `complete()` raises
  `openai.APITimeoutError` in <1s (not 600s). Assert `QwenClient._openai()._client.timeout`
  == configured value.

New setting `config.py` (L2-owned, add alongside line 40):
```python
llm_timeout_s: float = float(os.environ.get("RG_LLM_TIMEOUT_S", "60").strip())
```
`__post_init__` guard: `if self.llm_timeout_s <= 0: raise ValueError(...)`.

### F2 — unbounded call chain, no wall-clock deadline
Worst-case live path per `/run`:
- `pipeline.run` (`pipeline.py:88`) loops `max_iterations=3`.
- Each iteration → `agent.run_draft` → `_real_draft` (`autopilot.py:146`) loops
  `max_tool_steps=8` (`config.py:41`) full `chat_with_tools` calls **+** 1 final
  `complete()` (`autopilot.py:168`) = ≤9 sequential LLM calls.
- Plus 1 `complete(thinking=True)` adjudicator per iteration (`pipeline.py:98`).
- Total ≈ 3 × (9 + 1) = **~30 sequential LLM calls, zero cumulative timeout.**

Even with F1's 60s per-call cap, 30 × up-to-60s ≫ 300s. Must budget total wall-clock.

- **Exact change** — thread a monotonic deadline:
  1. `pipeline.py` `run()` top (after line 72):
     ```python
     import time
     deadline = time.monotonic() + settings.run_budget_s   # new setting, default 240 (< FC 300)
     ```
  2. Pass `deadline` into `agent.run_draft(..., deadline=deadline)` (both call sites
     `pipeline.py:75` and `:120`).
  3. `AutopilotAgent.run_draft` / `_real_draft` accept `deadline: float | None` and check
     `time.monotonic() >= deadline` at top of the tool loop (`autopilot.py:146`); on breach
     stop looping and jump to the forced-summary turn (F6 degrade).
  4. `pipeline.py` iteration loop (`:88`): `if time.monotonic() >= deadline: break` before
     starting a new iteration; mark result degraded.
- **Rubric:** Depth.
- **Effort:** M.
- **Test:** patch `settings.run_budget_s=0`; assert `ReceiptGuard().run("refund_damaged")`
  returns a `RunResult` (not exception) with `shipped=False` and a degraded marker, in <1s.

New setting `config.py` (L2): `run_budget_s: float = float(os.environ.get("RG_RUN_BUDGET_S","240").strip())`.

### F3 — `chat_with_tools` blocking non-stream
`qwen.py:119-122` uses `stream=False`. A stalled thinking-plan here has no delta heartbeat
and (pre-F1) no timeout → silent 600s hang. F1 caps it; optionally stream for parity with
`complete()`. Keep blocking for tool-call parsing simplicity, but F1 timeout is **mandatory**.
- **Rubric:** Depth. **Effort:** S (covered by F1). **Test:** as F1.

### F6 — graceful degrade on timeout
Today a timeout propagates raw out of `_real_draft` → 500 from `/run`; the ledger turn for
that iteration is never appended (`pipeline.py:108` never reached). Pitch claim "logs every
step" breaks under load.
- **Exact change:** wrap the `_real_draft` tool loop body and the final `complete()`
  (`autopilot.py:147`, `:168`) in `try/except (APITimeoutError, APIError)`; on catch return
  a DraftResult whose text is a **human-escalation** stub:
  `"Timed out mid-resolution after N tool steps; escalating this ticket to a human reviewer."`
  Pipeline then records a normal blocked/escalate verdict + ledger row → audit chain stays
  intact, output stays honest.
- **Rubric:** Depth (honesty + audit completeness under failure).
- **Effort:** M.
- **Test:** patch `client.chat_with_tools` to raise `APITimeoutError`; assert `run()` returns
  `shipped=False`, `chain_ok=True`, and final draft contains "escalating".

---

## LIVE STREAM (the Innovation finding)

### F5 — `complete()` buffers instead of yielding
`qwen.py:90-111` already iterates `reasoning_content` / `content` deltas but joins them into
one string. Add a generator so the SSE endpoint can push tokens live. Refactor `complete()`
to consume the generator (no behaviour change for existing callers).

- **Exact change** `qwen.py` — new method:
```python
def stream_complete(self, messages, *, model=None, thinking=False, temperature=0.2):
    """Yield ('reasoning'|'content', delta) tuples live. Real-mode only."""
    model = model or (settings.model_agent if thinking else settings.model_worker)
    extra_body = {"enable_thinking": True, "thinking_budget": settings.thinking_budget} if thinking else None
    stream = self._openai().chat.completions.create(
        model=model, messages=messages, temperature=temperature,
        stream=True, stream_options={"include_usage": True}, extra_body=extra_body)
    for chunk in stream:
        if not getattr(chunk, "choices", None):
            continue
        delta = chunk.choices[0].delta
        rc = getattr(delta, "reasoning_content", None)
        if rc:
            yield ("reasoning", rc)
        if getattr(delta, "content", None):
            yield ("content", delta.content)
```
(Timeout from F1 applies automatically — client-level.)
- **Rubric:** Innovation (reasoning_content as a live artifact; OpenAI stack can't).
- **Effort:** S.
- **Test:** MOCK-guard: `stream_complete` is real-mode only; assert it raises `RuntimeError`
  under `settings.mock`. Real: assert first yielded tuple kind == "reasoning" for `thinking=True`.

### F4 — SSE `/stream` endpoint
`api/app.py` has only blocking `POST /run`. Add an SSE `GET /stream` that surfaces the
adjudicator/agent thinking token-by-token. FC serves SSE **only** under Custom
Runtime / Container Image with chunked encoding (`docs/fc-deployment.md:91`) — our `s.yaml`
uses `custom-container`, so it's supported.

- **Exact change** `api/app.py` — add (after line 45):
```python
import json
from fastapi import Request
from fastapi.responses import StreamingResponse
from ..llm import client

@app.get("/stream")
def stream(scenario: str = "refund_damaged", request: Request = None) -> StreamingResponse:
    if settings.mock:
        # deterministic offline SSE so the demo streams without a key
        def mock_gen():
            for tok in ("Looking up order… ", "checking receipts… ", "backed. "):
                yield f"event: reasoning\ndata: {json.dumps(tok)}\n\n"
            yield "event: done\ndata: {}\n\n"
        return StreamingResponse(mock_gen(), media_type="text/event-stream")

    ticket = SCENARIOS[scenario]["ticket"]
    msgs = [{"role": "system", "content": "Plan the resolution; think step by step."},
            {"role": "user", "content": ticket}]
    def gen():
        try:
            for kind, delta in client.stream_complete(msgs, thinking=True):
                yield f"event: {kind}\ndata: {json.dumps(delta)}\n\n"
        except Exception as exc:                       # graceful SSE degrade (F6 parity)
            yield f"event: error\ndata: {json.dumps(str(exc))}\n\n"
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```
Frontend (`static/index.html`) hook — coordinate with UI lane, out of this lane's scope:
```js
const es = new EventSource(`/stream?scenario=${sc}`);
es.addEventListener('reasoning', e => reasoningEl.textContent += JSON.parse(e.data));
es.addEventListener('done', () => es.close());
```
- **Rubric:** Innovation.
- **Effort:** M.
- **Test:** `TestClient(app)` GET `/stream` in mock mode; assert `text/event-stream`
  content-type and body contains `event: reasoning` then `event: done`.

---

## MODEL-NAME SPLIT-BRAIN (F7) — every occurrence to unify → `qwen3.7-max`

Runtime env already says `qwen3.7-max`; **code default + all comments say `qwen3-max`** →
`/health` shows different name depending on whether env is set. Canonical = `qwen3.7-max`.

**In-scope (this lane's files) — must fix:**
| file:line | current | change |
|---|---|---|
| `config.py:35` | default `"qwen3-max"` | `"qwen3.7-max"` — **L2-owned**, flag to L2 (`parallel-status.md:17`) |
| `llm/qwen.py:6` | docstring "qwen3-max thinking mode…" | `qwen3.7-max` |
| `agent/autopilot.py:8` | comment "uses qwen3-max function calling" | `qwen3.7-max` |

**Out-of-scope (other lanes) — listed for the unify sweep, do NOT edit here:**
- `.env:4` = `qwen3.7-max` ✓ correct (reference)
- `s.yaml:15` comment, `s.yaml:22` = `qwen3.7-max` ✓ correct
- `.env.example:5` = `qwen3-max` → `qwen3.7-max`
- `static/index.html:101` label `qwen3-max reasoning` → `qwen3.7-max`
- `README.md:7,43,53,70,123,136`
- `docs/architecture.md:8,10,41,49`
- `docs/fc-deployment.md:49,63,70,74,80,83,86,91`
- `docs/video-script.md:9,10,14,28`
- `docs/devpost-summary.txt:5,21,28`
- (already correct: `docs/DEVPOST.md`, `docs/BLOG.md`)

- **Rubric:** Depth (the `/health` proof-curl must match the pitch; council #7).
- **Effort:** S (mechanical sed per file; only config.py needs L2 coordination).
- **Test:** after unify, `GET /health` with env unset returns
  `"models": {"agent": "qwen3.7-max", ...}`; `grep -rn "qwen3-max" src/ static/` returns 0.

---

## Coordination notes
- `config.py` edits (F1 `llm_timeout_s`, F2 `run_budget_s`, F7 default) belong to **L2** —
  hand this list over; do not double-write.
- SSE frontend wiring belongs to the UI lane.
- No code written by this lane (READ-only audit).

STATUS: DONE.

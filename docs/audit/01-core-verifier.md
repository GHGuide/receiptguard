# Audit 01 — Core Verifier: Adversarial-Input Robustness

**Lane:** robustness-audit (read-only). **Scope:** `verify/crosscheck.py`, `claims/extractor.py`, `recovery/controller.py`, `gateway/receipts.py`, `gateway/tools.py`, `tests/test_receiptguard.py`.
**Council gaps addressed:** #8 (malformed/adversarial input into the claim pipeline), #9 (numeric-parse edge cases + tool-output shape assumptions).

**Constraint honored:** no detection *semantics* changed here — this is a fix-list. Every item that would alter a verdict is tagged **⚠ SEMANTICS** with the direction of change (tightens = catches more, loosens = passes more). Nothing below is applied.

Ranked by impact (blast radius × likelihood × judging weight).

---

## F1 — Numbers leak from error-receipt detail strings into the backing set ⚠ SEMANTICS (tightens)

**Where:** `gateway/receipts.py:97-98` produces `{"error": "tool_execution_failed", "tool": tool, "detail": str(exc)}`. `verify/crosscheck.py:106-110` (`_receipt_numbers` → `_gather_numbers`) then harvests **every** number in that dict, including digits inside the exception message.

**Failure scenario:** a tool raises `RuntimeError("gateway timeout after 500ms, retry 3")`. The error-receipt's `detail` string yields `{500, 3}` into `receipt_nums`. An agent then hallucinates *"I processed a $500 refund"* — `_value_matches(500, {..,500,..})` is true → verdict **backed**. A fabricated dollar amount is laundered as grounded by an unrelated stack-trace number. This is a real bypass of the core invariant.

**Fix:** `crosscheck.py:106-110` — skip error-receipts when gathering the numeric backing set:
```python
def _receipt_numbers(receipts: list[Receipt]) -> set[float]:
    acc: set[float] = set()
    for r in receipts:
        if isinstance(r.output, dict) and "error" in r.output:
            continue  # error-receipt detail strings are not evidence for values
        _gather_numbers(r.output, acc)
    return acc
```
(A failed tool produced no data, so its receipt must not back any asserted value. The receipt still exists for the fabricated-tool-reference check — only its *numbers* are excluded.)

**Rubric:** Depth (closes a laundering path through the receipt layer) + Value (protects the load-bearing claim→receipt guarantee).
**Effort:** S.
**Test to add:** tool raises `RuntimeError("timeout 500")`; call it; `cross_check(Claim("I processed a $500 refund.", "tool_derived"), receipts)` must be **not** `backed` (should stay `unbacked`/`contradicted`).

---

## F2 — `extract_claims` forwards non-str / None draft straight to the LLM (BadRequest crash)

**Where:** `claims/extractor.py:33-41`. `draft` is passed verbatim as `content` for the user message *and* as `draft=draft` to `client.complete`. No type guard.

**Failure scenario:** upstream hands `extract_claims(None)` or `extract_claims({"text": ...})` (a dict from a partial JSON parse, or a bytes payload). The provider rejects a non-string `content` with a 400 BadRequest, taking down the whole verify pass instead of failing safe. Adversarial callers can force this with any non-text field.

**Fix:** `extractor.py:33` — coerce/guard at the boundary:
```python
def extract_claims(draft: str) -> list[Claim]:
    if not isinstance(draft, str):
        draft = "" if draft is None else str(draft)
    if not draft.strip():
        return []
    ...
```

**Rubric:** Value (robustness / no crash on hostile input) + Depth (defensive boundary before the only LLM call in the hot path).
**Effort:** S.
**Test to add:** `extract_claims(None) == []`; `extract_claims(123)` returns a list without raising; assert `client.complete` not called for empty/None (monkeypatch a spy).

---

## F3 — Empty / whitespace-only claim becomes an `unbacked` failed verdict ⚠ SEMANTICS (loosens the failure set)

**Where:** `verify/crosscheck.py:113`. `cross_check` never guards `claim.text`. `extractor._parse` filters empties (`extractor.py:53`), but `cross_check` is public and called directly (tests, and any future caller). An empty `tool_derived` claim → `_candidate_tools("") == []` → line 137 returns **unbacked → failed**.

**Failure scenario:** a whitespace claim (`Claim("   ", "tool_derived")`) injected via the fallback path or a future extractor bug is scored as a *failure*, dragging groundedness down and forcing a spurious `replan`. An attacker who can pad the draft with blank atomic claims can force the budget to exhaust (F8 interaction) → denial-of-progress.

**Fix:** `crosscheck.py:114` (top of `cross_check`), guard before any typing:
```python
if not text or not text.strip():
    return ClaimVerdict(claim, "opinion", "empty claim; nothing to verify")
```
Tag SEMANTICS: today empty→`unbacked`(fail); after→`opinion`(pass, weight 0.6). Direction is correct (an empty claim is not a fabrication) but confirm no test asserts the old behavior. None does.

**Rubric:** Depth (input hygiene at the verifier core) + Value (blocks a cheap denial-of-progress vector).
**Effort:** S.
**Test to add:** `cross_check(Claim("   ", "tool_derived"), []).failed is False`.

---

## F4 — Substring keyword→tool matching misattributes tools ⚠ SEMANTICS (both directions)

**Where:** `verify/crosscheck.py:97-103` (`_candidate_tools`) uses `if kw in low` against `KEYWORD_TOOL` (`crosscheck.py:20-27`). Plain substring, no word boundary.

**Failure scenario(s):**
- `"stock"` ⊂ `"Stockholm"`, `"order"` ⊂ `"reorder"`/`"border"`, `"cap"` ⊂ `"capacity"`/`"escape"`, `"units"` ⊂ `"opportunities"`. A benign claim *"We shipped to Stockholm"* is mapped to `check_inventory`; if inventory was never called → **false unbacked**. Conversely an adversary phrases a fabricated amount inside a word that *does* contain a called-tool keyword to attract a lenient backing set.
- Because candidate tools drive both the "no such tool called" branch (`crosscheck.py:141`) and which receipts supply `receipt_nums` (`crosscheck.py:147`), a wrong candidate changes the verdict either way.

**Fix:** `crosscheck.py:97-103` — match on word boundaries:
```python
import re
_KW_RE = {kw: re.compile(rf"\b{re.escape(kw)}\b") for kw in KEYWORD_TOOL}
def _candidate_tools(text: str) -> list[str]:
    low = text.lower()
    tools = []
    for kw, tool in KEYWORD_TOOL.items():
        if _KW_RE[kw].search(low) and tool not in tools:
            tools.append(tool)
    return tools
```
Tag SEMANTICS: fixes false matches (tightens) but may drop a previously-matched inflected form like `"orders"`/`"refunds"` (loosens). Mitigate by adding plural keys or a lightweight stem — recommend adding the plurals already used in fixtures (`"orders"`, `"refunds"`, `"articles"`) to `KEYWORD_TOOL` rather than stemming.

**Rubric:** Depth (correctness of the tool-attribution step, which every verdict depends on) + Value (kills a class of demo-breaking false positives).
**Effort:** M.
**Test to add:** `cross_check(Claim("We shipped to Stockholm.", "tool_derived"), [])` is not flagged for `check_inventory`; `cross_check(Claim("I placed 2 orders.", "tool_derived"), <lookup_order receipt>)` still resolves to `lookup_order`.

---

## F5 — Numeric regex misses `.5`, splits `1e6`, ignores `k`/`M` suffixes ⚠ SEMANTICS (mixed)

**Where:** `verify/crosscheck.py:74`, pattern `(?<![\d.])-?\$?\d[\d,]*(?:\.\d+)?`.

**Failure scenarios:**
- **`.5` (leading-dot decimal):** pattern requires a leading `\d`, so `".5"` matches nothing. Claim *"refunded $.50"* extracts **no** number → the value-mismatch branch is skipped → verdict falls through to **backed** if the tool was called. Under-detection (loosens): a wrong sub-dollar amount ships. 
- **`1e6` (scientific):** matches `"1"` then `"6"` as two separate numbers → `{1.0, 6.0}`, never `1_000_000`. A claim *"1e6 units"* vs a receipt of `1000000` → both `1` and `6` unsupported → **contradicted** (false positive, tightens wrongly). 
- **`1.2M` / `12k` suffixes:** `"1.2M"` → `1.2` only. Same false-contradiction / false-match risk.
- Thousands separators (`"1,000"`) and `$`/negative are already handled correctly (`crosscheck.py:74-76`) — keep.

**Fix:** `crosscheck.py:74` — extend the token pattern to allow a leading dot, then normalize suffixes; reject bare-`e` splits by consuming an optional exponent:
```python
_NUM = re.compile(r"(?<![\d.])-?\$?(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?")
# after cleaning $ and , : optionally fold trailing k/m suffix on the source token
```
Tag SEMANTICS: broadens what counts as a number → changes verdicts on `.5`/`1e6`/suffix inputs. Recommend landing behind the existing regression tests (`test_date_not_parsed_as_amount`, `test_relative_numeric_tolerance`) and adding the cases below before merge. Suffix folding (`k`/`M`) is optional (L) — flag but do not require for hackathon scope; the leading-dot and exponent fixes are the load-bearing ones.

**Rubric:** Depth (numeric-grounding is the headline detection) + Value (removes both an under-detection hole and a false-positive source).
**Effort:** M (regex + suffix normalization).
**Test to add:** `_numbers("$.50") == {0.5}`; `_numbers("1e6") == {1000000.0}`; `_numbers("1.2")` unchanged; date/version regressions still pass.

---

## F6 — Non-dict tool output bypasses the false-absence check ⚠ SEMANTICS (tightens)

**Where:** `verify/crosscheck.py:126-128`. `cnt`/`res` are read only `if isinstance(r.output, dict)`. A tool that returns a bare list (`["return-policy", "warranty"]`) or a string yields `cnt=None, res=None`.

**Failure scenario:** `search_kb` (or a future real connector) returns a top-level list of hits instead of `{"results": [...], "count": n}`. Agent claims *"No results were found"* → the loop sees `cnt=None and res=None` → falls to line 132 **backed** ("no contradicting receipt"). A genuine false-absence lie ships. The `false_absence` invariant silently assumes the fixture shape.

**Fix:** `crosscheck.py:126-128` — treat any non-empty output as contradicting an absence claim:
```python
out = r.output
non_empty = False
if isinstance(out, dict):
    cnt, res = out.get("count"), out.get("results")
    non_empty = bool((isinstance(cnt, (int, float)) and cnt > 0) or res)
elif isinstance(out, (list, str)):
    non_empty = len(out) > 0
if non_empty:
    return ClaimVerdict(claim, "false_absence", ...)
```
Also fixes a latent `TypeError` at line 128 if `count` arrives as a string (`"5" > 0` raises) — the `isinstance` guard above closes it.

**Rubric:** Depth (removes a shape assumption in a core detector) + Value (hardens for the real Shopify/Stripe path in F9).
**Effort:** M.
**Test to add:** receipt with `output=["a","b"]` for `search_kb`; absence claim → `false_absence`. Receipt with `output={"count":"5"}` does not raise.

---

## F7 — `send_email` message_id is non-deterministic (breaks "deterministic fixtures")

**Where:** `gateway/tools.py:40` — `f"MSG-{abs(hash(subject)) % 10000:04d}"`. Python's `hash()` on `str` is salted per-process (`PYTHONHASHSEED`), so `message_id` **changes across runs**, contradicting the module docstring ("Deterministic fixtures so the demo + tests are reproducible") and making the resulting receipt's `args_hash`/`output_hash` unstable if ever asserted.

**Failure scenario:** any test or replay that pins a `send_email` receipt hash flakes; the audit-chain hash over that receipt differs run-to-run, undermining the "reproducible proof" story the judges will re-run.

**Fix:** `tools.py:40` — deterministic digest:
```python
import hashlib
mid = int(hashlib.sha256(subject.encode()).hexdigest(), 16) % 10000
return {"to": to, "subject": subject, "status": "sent", "message_id": f"MSG-{mid:04d}"}
```

**Rubric:** Value (reproducibility of the recorded proof — a stated judging criterion) + Depth (determinism of the receipt layer).
**Effort:** S.
**Test to add:** `send_email(...)["message_id"] == send_email(...)["message_id"]` across two calls with equal subject (and stable under a forced `PYTHONHASHSEED=random` subprocess).

---

## F8 — Zero extracted claims → groundedness 1.0 → silent `proceed` (adversarial bypass) ⚠ SEMANTICS (tightens)

**Where:** `recovery/controller.py:32-38` returns `1.0` for empty `verdicts`; `decide` (`controller.py:49-50`) then `proceed`s. Combined with `extractor._parse` (which can return `[]` when the LLM emits `{"claims":[]}`) and F2's new empty-guard, a draft that yields no claims ships **unverified**.

**Failure scenario:** an adversarial draft is phrased so the extractor finds no atomic `tool_derived` claims (e.g. everything reads as opinion, or the model returns an empty list under prompt-injection pressure). `groundedness_score([]) == 1.0` ≥ `TAU_HIGH` → `proceed`. The guard is bypassed by producing *nothing to check*.

**Fix (recommend flag, not blind-apply):** the score function cannot tell "verified clean" from "nothing extracted" — that context lives at the pipeline caller. Add a caller-side rule: if the draft is non-trivial but `verdicts == []`, treat as low-confidence (force at least one `regenerate` or a disclosure), rather than `proceed`. Minimal in-module hardening: have `decide` accept a `num_claims`/`draft_nonempty` signal and refuse a clean `proceed` when zero claims were extracted from a non-empty draft.
Tag SEMANTICS: changes the empty-verdict path from `proceed` to `regenerate`/disclose. **Flag for owner sign-off** — this touches the tier decision, which is the recovery contract.

**Rubric:** Depth (closes the "verify nothing" bypass at the decision boundary) + Value (the guard must not be defeatable by suppressing claims).
**Effort:** S (in-module) / M (threading the signal from the pipeline).
**Test to add:** `decide([], iteration=0, max_iterations=3, draft_nonempty=True).action != "proceed"`.

---

## F9 — Fixture-only tools; no real integration stub (Value/Depth gap, not a bug)

**Where:** `gateway/tools.py` in full — all six tools are in-memory dicts. There is no seam showing how a real Shopify/Stripe call would flow through the same receipt-issuing gateway, which is the productionization question judges will ask.

**Fix (additive, no semantics change):** add a `ToolProvider` protocol and a thin `ShopifyStub`/`StripeStub` implementing the *same* return shapes behind an env flag, with the fixture provider as default:
```python
class ToolProvider(Protocol):
    def lookup_order(self, order_id: str) -> dict[str, Any]: ...
    def process_refund(self, order_id: str, amount: float) -> dict[str, Any]: ...
    # ...
class FixtureProvider: ...          # current dicts
class StripeStub:                    # real client behind, same output contract
    def process_refund(self, order_id, amount):
        # stripe.Refund.create(...) -> normalize to {order_id, refunded_amount, status, confirmation}
        ...
def build_tools(provider: ToolProvider | None = None) -> dict[str, Callable]: ...
```
Key point for the write-up: the receipt/verify layer is provider-agnostic *because* everything routes through `ToolGateway.call` (`gateway/receipts.py:92-101`) — the stub proves the invariant survives a real backend. F6 must land first so the verifier tolerates the real backend's output shapes.

**Rubric:** Value (productionization credibility) + Depth (demonstrates the gateway abstraction is real, not fixture-coupled).
**Effort:** L.
**Test to add:** `build_tools(StripeStub())["process_refund"](...)` returns the same keys as the fixture; a receipt issued through it verifies and cross-checks identically.

---

## F10 — `_parse` fallback crashes on non-str LLM content

**Where:** `claims/extractor.py:44-57`. If `resp.content` is `None`/non-str, `content.find("{")` (line 46) raises, is caught (line 54), then the fallback `content.splitlines()` (line 56) raises **again inside the `except`** and propagates uncaught.

**Failure scenario:** a provider/adapter that returns `content=None` (empty completion, tool-only turn) takes down `extract_claims` despite the "robust fallback" comment. F2's guard covers the *input* draft but not the *response* content.

**Fix:** `extractor.py:44` — normalize at entry of `_parse`:
```python
def _parse(content: str) -> list[Claim]:
    if not isinstance(content, str):
        content = "" if content is None else str(content)
    ...
```

**Rubric:** Value (the fallback must actually fail safe) + Depth (defensive on the LLM-response edge).
**Effort:** S.
**Test to add:** `_parse(None) == []`; `_parse(42)` returns a list without raising.

---

## Cross-cutting notes

- **`gateway/tools.py:44` `search_kb`** substring match (`query.lower() in a or a in query.lower()`) is bidirectional; a single-char query `"a"` matches every article. Minor (fixture only) — subsumed by F9's real provider. **Effort S**, low priority.
- **`decide` force-tools ordering** (`controller.py:44-47`) is fine; no robustness issue found.
- **Receipt numeric harvesting over `output_snippet`/ids** (order ids like `ORD-1001` → `1001`) is intentional and self-consistent (both claim and receipt strings pass through `_numbers`), so id collisions are symmetric — no action, noted for completeness.

## Suggested landing order
F2 → F10 → F3 (safe, no-semantics or clearly-correct) → F1 → F6 (close real holes, add tests) → F7 (reproducibility) → F4 → F5 (semantics-tagged, land behind regression tests) → F8 (owner sign-off on tier change) → F9 (additive productionization).

STATUS: DONE.

# Benchmark Methodology

`eval/benchmark.py` measures hallucination **detection** on a deterministic,
labeled adversarial set and compares three systems at equal information budget.

## Cases
Each case is one agent claim + the signed receipts available at the time. Four
balanced kinds (cycled deterministically):
- `clean` — a true tool-derived claim (receipt supports it). Used to measure false positives.
- `fabricated_ref` — claims a tool result for a tool that was never called.
- `value_mismatch` — claims a plausible but wrong number/count vs the receipt.
- `false_absence` — claims "nothing found" when a receipt returned results.

## Systems
1. **ReceiptGuard** — full deterministic cross-check against signed receipts.
2. **ReceiptGuard (no value-check)** — *ablation*: checks tool presence only, skips
   numeric matching. Isolates the contribution of receipt value-checking.
3. **LLM-judge (no receipts)** — baseline with no ground truth.
   - With `DASHSCOPE_API_KEY`: a real `qwen-flash` judge.
   - Offline (mock): a transparent plausibility heuristic that flags any
     completed-action verb or bare quantity. It is applied **uniformly** to clean
     and hallucinated claims alike — it is NOT tuned to the labels. This is why it
     pays a high false-positive rate rather than scoring an artificial 0% or 100%.

## Metrics
- **detection_rate** = TP / (hallucinated cases) — caught fabrications.
- **false_positive_rate** = FP / (clean cases) — clean claims wrongly flagged.
- **ms_per_claim** — wall-clock overhead.
- per-hallucination-type breakdown.

## Reproduce
```bash
PYTHONPATH=src python eval/benchmark.py 200   # writes eval/out/results.json + detection.png
```
Result (n=200, offline): ReceiptGuard 100% detection / 0% FP; ablation 66.7% (misses
all value mismatches); receipt-free judge 66.7% detection / 100% FP. The honest
takeaway is the *trade-off*: without receipts you cannot get detection without
over-blocking; with receipts you get both, deterministically, at sub-ms cost.

## Claim-extraction typing eval (`extraction_eval.py`)
`benchmark.py` feeds PRE-TYPED claims to the verifier, so it does not measure the
claim extractor (`extract_claims`). `extraction_eval.py` closes that gap: 15 labeled
single-claim drafts across the four epistemic types, scored on the real extractor
(heuristic offline, qwen-flash with a key).

Result (offline heuristic): overall typing accuracy **80%**, but **`tool_derived`
recall 100%** — the safety-critical metric. Every misclassification is *conservative*
(`inference`/`absence` → `tool_derived`), so a mis-type makes the verifier check MORE
claims, never fewer. With the fail-closed gateway, no fabrication can slip through due
to a typing error; the only cost of a mis-type is over-verification of a benign claim.
Run with `DASHSCOPE_API_KEY` for the real qwen-flash typing number.

## Honesty note
An earlier version hardcoded the offline baseline to ~0% via a keyword shortcut.
That was removed — the baseline is now a uniform heuristic (or the real qwen-flash
judge with a key), so every number here is defensible against code review.

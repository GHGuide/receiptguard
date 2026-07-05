# Audit Lane 03 — Benchmark & Eval: Statistical Rigor + Offline Reproducibility

Council item #4. Read-only audit of `eval/benchmark.py`, `eval/extraction_eval.py`,
`eval/BENCHMARK_METHODOLOGY.md`, `eval/out/results.json`, `tests/test_receiptguard.py`.
No code changed by this lane; every finding below is a prescribed change with exact
location, effort, and reproduce command.

---

## Verdict up front

The 100%-vs-0% headline is currently indefensible under judge scrutiny for four
reasons, in severity order:

1. **Effective sample size is 4, not 24.** `_make_case` (benchmark.py:44) has exactly
   one fixed template per case kind. n=24 is six verbatim copies of the same 4 cases.
   Both ReceiptGuard and the judge are (near-)deterministic per input, so duplicates
   add zero statistical information. Any confidence interval computed over the 24 is
   invalid (observations are not independent — they are identical).
2. **The committed artifact contradicts the methodology doc.** `eval/out/results.json`
   is a **live** run (n=24, judge `ms_per_claim` = 1039 ms ⇒ real API; judge 0%
   detection / 0% FP). `BENCHMARK_METHODOLOGY.md:35-38` quotes the **offline** result
   (n=200, judge 66.7% detection / 100% FP). A reviewer diffing the two sees different
   n, different numbers, and no `mode`/`model`/timestamp field in results.json to
   explain which regime produced it.
3. **The live delta does not reproduce offline.** The qwen-flash judge verdicts were
   never persisted. Re-running without `DASHSCOPE_API_KEY` swaps in the heuristic and
   produces different numbers (66.7%/100% FP vs 0%/0%). There is no `--mock`/`--live`
   switch: mode is implicitly decided by env var, and with a key set, mock mode is
   unreachable (config.py:55 `mock = not api_key`).
4. **No uncertainty is reported anywhere.** At n=24 (18 hallucinated cases), 18/18
   detection has a Wilson 95% CI of **[82.4%, 100%]** and 0/18 judge detection has
   **[0%, 17.6%]**. The gap survives — but "100% vs 0%" printed without intervals at
   this n reads as marketing, not measurement. 60% of judging is technical depth;
   showing the CI is cheap credibility.

Also found: benchmark.py:99 writes a top-level `"by_type": {}` that is never populated
(visible as a dead empty dict in the committed results.json, line 3); stratification
silently skews when `n % 4 != 0` (`i % 4` cycling); the judge call does not pin
`temperature=0` (qwen.py `complete()` defaults to 0.2), so even a live re-run is not
repeatable; and there is no test asserting the benchmark itself is deterministic.

---

## Fixes (ordered by rubric leverage)

### F1 — Parameterize case generation so n is a real sample size

- **Where:** `eval/benchmark.py:44` `_make_case(i)`
- **Exact change:** Derive per-case variation from a deterministic
  `rng = random.Random(1000 + i)` (index-seeded — reproducible, no wall-clock).
  Vary, per kind:
  - `clean`: phrasing template pool (≥6 surface forms of "Inventory shows 12 units…"
    incl. dates, currency, filler clauses — the regex value-extractor must survive all).
  - `fabricated_ref`: refund amount drawn from `rng.choice([19, 49, 79, 120, 250, 499])`,
    ≥4 phrasings ("processed a refund", "issued", "refunded the customer", "sent back $X").
  - `value_mismatch`: wrong count drawn from values ≠ 12 (`rng.choice([0,1,3,5,7,90])`),
    ≥4 phrasings.
  - `false_absence`: ≥4 phrasings of "nothing found" over ≥2 queries.
  Keep the kind cycle `i % 4` so strata stay balanced. Record the phrasing-pool version
  as `"case_generator_version": 2` in output.
- **Why (rubric — Depth):** converts "4 cases repeated" into a genuine adversarial set;
  makes CIs meaningful; stress-tests the numeric cross-check regex against surface
  variation instead of one canned string. This is the single highest-leverage fix: it is
  the difference between a demo and a benchmark.
- **Effort:** ~45 min.
- **Reproduce:** `PYTHONPATH=src python3 eval/benchmark.py 200 --mock` — per-type rates
  must remain 100/100/100 for ReceiptGuard; if any phrasing breaks the verifier, that is
  a real bug surfaced (fix in verifier, not by deleting the phrasing).

### F2 — Fixed stratified n ≥ 100, all 3 systems, one committed run

- **Where:** `eval/benchmark.py:97` `run()` and `:136` `main()`
- **Exact change:** In `main()`, round n up to the next multiple of 4 and warn
  (`n = ((n + 3) // 4) * 4`). In `run()`, populate the dead field at line 99:
  `out["by_type"] = {k: n // 4 for k in ["clean"] + HALLUCINATION_TYPES}` (per-stratum
  counts). Adopt **n = 200** (50/stratum, 150 hallucinated) as the committed headline
  run — already the script default; the committed artifact must match it.
- **Why (Depth):** balanced strata at a stated fixed n, per-stratum counts in the
  artifact, no dead fields. At 150/150 detection the Wilson 95% CI is [97.5%, 100%] —
  a headline that survives a statistician.
- **Effort:** ~10 min.
- **Reproduce:** `PYTHONPATH=src python3 eval/benchmark.py 200 --mock` then
  `python3 - <<'EOF'` … assert `results["by_type"] == {"clean":50,"fabricated_ref":50,"value_mismatch":50,"false_absence":50}` `EOF`

### F3 — Wilson 95% CIs on every rate

- **Where:** `eval/benchmark.py:125-131` (metrics dict), `:148-153` (print), `:166-173` (chart)
- **Exact change:** Add a 6-line pure-python helper:

  ```python
  def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
      if n == 0: return (0.0, 0.0)
      p = k / n; d = 1 + z * z / n
      c = (p + z * z / (2 * n)) / d
      h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
      return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))
  ```

  Emit `"detection_ci95": _wilson(tp, halluc)` and `"fp_ci95": _wilson(fp, fp + tn)`
  per system; print as `100.0% [97.5, 100]`; add `plt.errorbar` whiskers to the bars.
- **Why (Depth):** uncertainty reporting is the cheapest possible signal of statistical
  literacy to a technical judging panel; it also preempts the obvious attack question.
- **Effort:** ~15 min.
- **Reproduce:** `PYTHONPATH=src python3 eval/benchmark.py 200 --mock` — output shows
  ReceiptGuard `100.0% [97.5, 100.0]`, judge FP row shows its interval.

### F4 — `--mock` / `--live` split + frozen live-judge cache (offline-reproducible delta)

- **Where:** `eval/benchmark.py:79` `llm_judge_flag()`, `:135` `main()` (argparse)
- **Exact change:**
  1. Replace positional-only argv with argparse: `benchmark.py [N] [--mock|--live]
     [--record|--replay]`. `--mock` forces the heuristic **even when a key is set**
     (today impossible); `--live` errors if no key.
  2. Pin the judge: pass `temperature=0.0` in the `client.complete(...)` call.
  3. In `--live --record`: for each case, key = `sha256(model + "\x00" + claim.text)`,
     append `{key: {"claim": text, "model": model, "raw": content, "flag": bool}}` to
     `eval/out/judge_cache.json` (sorted keys, indent=2 — diffable).
  4. In `--replay` (no key needed): `llm_judge_flag` reads the cache; a cache miss is a
     hard error naming the missing claim (never silently falls back to the heuristic).
  5. Write mode-suffixed artifacts: `eval/out/results_mock.json`,
     `eval/out/results_live.json`. Keep `results.json` as a copy of the live one for
     backward links, or delete it and fix references.
- **Why (Depth + Reproducibility):** this is the council's core ask — the 100%-vs-0%
  live delta becomes bit-for-bit reproducible on a judge's laptop with no API key:
  ReceiptGuard rows are already deterministic, and the judge rows replay from the
  committed cache. Nobody has to trust that qwen-flash "really said that".
- **Effort:** ~40 min.
- **Reproduce (the money command):**

  ```bash
  # one-time, with DASHSCOPE_API_KEY set (~200 qwen-flash calls, ~3.5 min):
  PYTHONPATH=src python3 eval/benchmark.py 200 --live --record
  # forever after, offline, no key:
  PYTHONPATH=src python3 eval/benchmark.py 200 --replay
  diff <(python3 -c "import json;d=json.load(open('eval/out/results_live.json'));d.pop('timestamp_utc',None);[s.pop('ms_per_claim') for s in d['systems'].values()];print(json.dumps(d,indent=2))") \
       <(python3 -c "import json;d=json.load(open('eval/out/results_replay.json'));d.pop('timestamp_utc',None);[s.pop('ms_per_claim') for s in d['systems'].values()];print(json.dumps(d,indent=2))")
  # empty diff = live delta reproduced offline
  ```

### F5 — Provenance metadata in every results file

- **Where:** `eval/benchmark.py:97-99` `run()` output dict
- **Exact change:** Add `"mode"` (`mock`/`live`/`replay`), `"judge_model"`
  (`settings.model_worker` or `"heuristic"`), `"temperature"`, `"timestamp_utc"`
  (stamped in `main()`, not `run()`), `"case_generator_version"`. Mirrors what
  `extraction_eval.py:72-74` already does correctly (`mode`, `model`, `n`).
- **Why (Depth):** the current results.json is unlabeled — finding #2 exists only
  because provenance was dropped. Five keys kill the whole ambiguity class.
- **Effort:** ~5 min.
- **Reproduce:** `python3 -c "import json; d=json.load(open('eval/out/results_live.json')); assert {'mode','judge_model','timestamp_utc','case_generator_version'} <= d.keys()"`

### F6 — Reconcile methodology doc with committed artifacts

- **Where:** `eval/BENCHMARK_METHODOLOGY.md:31-38` (Reproduce section)
- **Exact change:** Replace the single-result paragraph with a two-row table:

  | Mode | n | RG detect [CI] | RG FP | Judge detect [CI] | Judge FP [CI] | Artifact |
  |---|---|---|---|---|---|---|
  | mock (heuristic) | 200 | from results_mock.json | … | … | … | `eval/out/results_mock.json` |
  | live (qwen-flash, temp 0, frozen) | 200 | from results_live.json | … | … | … | `eval/out/results_live.json` + `judge_cache.json` |

  Fill numbers from the regenerated runs — do not hand-type predictions. Add one line:
  "Live judge outputs are frozen in `judge_cache.json`; `--replay` reproduces the live
  table offline." Note the mock-mode expectation explicitly (heuristic judge: high FP,
  partial detection) so the two rows telling different stories reads as intended, not
  as a discrepancy.
- **Why (Depth + honesty):** the doc's own "Honesty note" (line 53) says every number
  is defensible against code review; today the committed number and the documented
  number differ. This closes the last gap.
- **Effort:** ~15 min (after F1–F5 land and runs are regenerated).
- **Reproduce:** numbers in the doc table `grep`-match the JSON artifacts:
  `python3 -c "import json;print(json.load(open('eval/out/results_live.json'))['systems']['ReceiptGuard']['detection_rate'])"`

### F7 — Determinism test

- **Where:** `tests/test_receiptguard.py` (append; also runnable via the `__main__` loop)
- **Exact change:** Subprocess-based (avoids the frozen `settings` import-time trap):

  ```python
  def test_benchmark_deterministic_and_stratified():
      """Two offline runs at the same n produce identical results (minus timing),
      and strata are exactly balanced."""
      import json, os, subprocess, tempfile
      root = Path(__file__).resolve().parents[1]
      env = {**os.environ, "PYTHONPATH": str(root / "src")}
      env.pop("DASHSCOPE_API_KEY", None)          # force mock
      def one_run():
          subprocess.run([sys.executable, str(root / "eval" / "benchmark.py"),
                          "24", "--mock"], check=True, env=env, cwd=root)
          d = json.loads((root / "eval" / "out" / "results_mock.json").read_text())
          d.pop("timestamp_utc", None)
          for s in d["systems"].values():
              s.pop("ms_per_claim")
          return d
      a, b = one_run(), one_run()
      assert a == b, "benchmark is not deterministic offline"
      assert a["by_type"] == {"clean": 6, "fabricated_ref": 6,
                              "value_mismatch": 6, "false_absence": 6}
  ```

- **Why (Depth):** "deterministic" is claimed in benchmark.py's docstring (line 9) but
  never enforced; this locks it, and locks stratification, against regressions from F1's
  new case generator (an accidental `random.Random()` without a seed would fail here).
- **Effort:** ~20 min.
- **Reproduce:** `PYTHONPATH=src python3 -m pytest tests/test_receiptguard.py -k deterministic -q`

---

## Files to freeze in `eval/out/` (commit all)

| File | Producer | Purpose |
|---|---|---|
| `results_mock.json` | `benchmark.py 200 --mock` | offline-anyone number, heuristic judge |
| `results_live.json` | `benchmark.py 200 --live --record` | headline number, real qwen-flash |
| `judge_cache.json` | same `--record` run | frozen per-claim judge verdicts (sha256-keyed, temp 0) |
| `results_replay.json` | `benchmark.py 200 --replay` | proof the live delta reproduces offline |
| `detection.png` | live run | chart with CI whiskers (F3) |
| `extraction_results.json` | `extraction_eval.py` (mock + live variants) | typing-accuracy artifact — apply same mode-suffix convention |

`.gitignore` must NOT cover `eval/out/` after this (verify: `git check-ignore eval/out/judge_cache.json` returns nothing).

## Sequencing + total effort

F1 → F2 → F3 → F5 (code, ~75 min) → F4 (~40 min) → regenerate artifacts (one live run,
~3.5 min, ~200 qwen-flash calls) → F6 doc (~15 min) → F7 test (~20 min).
**Total ≈ 2.5 h.** All fixes are inside `eval/` + one test append; no simulation/product
code touched; no new dependencies (Wilson is 6 lines of stdlib math).

## What this buys at judging

- n=200 stratified 50/50/50/50, distinct parameterized cases, not 4 templates × 6.
- Headline becomes "100% [97.5, 100] vs 0% [0, 2.5] detection, 0% vs measured-FP,
  sub-ms vs ~1 s/claim" — every number with an interval, a mode label, and a frozen
  artifact.
- A judge with no API key runs **one command** (`--replay`) and reproduces the exact
  committed live delta, including the real qwen-flash verdicts.

STATUS: DONE

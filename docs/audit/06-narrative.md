# Audit Lane 06 — Narrative / Robustness (council items #5, #7)

Read-only audit of README.md, docs/DEVPOST.md, docs/BLOG.md, docs/integration-guide.md,
docs/video-script.md. Each fix: **file:section → exact prose change → rubric → effort**.

Verification state: DEVPOST.md and BLOG.md are already clean on model naming. README.md
(6 hits) and video-script.md (5 hits) are not. Bonus finding: `.env.example` contradicts
`s.yaml` on the model ID.

---

## FIX 1 — Unify stray `qwen3-max` → Qwen3.7-Max (11 prose hits + 1 config)

Convention: prose/marketing = **Qwen3.7-Max** / **Qwen-Flash** (product names); code
spans and env values = `qwen3.7-max` (the ID `s.yaml:22` actually pins). A judge who
sees `qwen3-max` in the README but `qwen3.7-max` in the deploy config reads it as
sloppiness or, worse, as "the benchmark ran on a different model than claimed."

| Location | Exact change |
|---|---|
| `README.md:7` (intro) | `A \`qwen3-max\` agent resolves` → `A \`qwen3.7-max\` agent resolves` |
| `README.md:43` (ASCII diagram) | `Autopilot agent (qwen3-max)` → `Autopilot agent (qwen3.7-max)` |
| `README.md:53` (ASCII diagram) | `(qwen3-max thinking adjudicates,` → `(qwen3.7-max thinking adjudicates,` |
| `README.md:70` (The mechanism §4) | `\`qwen3-max\` thinking-mode adjudicates` → `\`qwen3.7-max\` thinking-mode adjudicates` |
| `README.md:123` (Going live) | `the agent (\`qwen3-max\`, thinking mode)` → `the agent (\`qwen3.7-max\`, thinking mode)` |
| `README.md:136` (Why it scores, Innovation row) | `two-speed qwen-flash/qwen3-max fleet` → `two-speed qwen-flash/qwen3.7-max fleet` |
| `video-script.md:9` (0:12–0:35 voiceover) | `is a qwen3-max autopilot` → `is a Qwen3.7-Max autopilot` (spoken line — product name) |
| `video-script.md:10` (0:35–1:15, on-screen + voiceover) | `qwen3-max thinking planning` → `qwen3.7-max thinking planning`; `"It plans with qwen3-max,` → `"It plans with Qwen3.7-Max,` |
| `video-script.md:14` (end card voiceover) | `Built on Qwen3-Max, Qwen-Flash,` → `Built on Qwen3.7-Max, Qwen-Flash,` |
| `video-script.md:28` (positioning move 5) | `make the expensive one (qwen3-max) honest` → `make the expensive one (qwen3.7-max) honest` |
| **Bonus — `.env.example:5`** | `RG_MODEL_AGENT=qwen3-max` → `RG_MODEL_AGENT=qwen3.7-max` (must match `s.yaml:22`; anyone following the README quickstart with a key currently runs a *different model* than the deployed one — that breaks the "real Qwen3.7-Max benchmark" claim) |

- **Rubric:** Presentation (consistency = credibility) + Value (the `.env.example` fix protects the benchmark claim itself).
- **Effort:** 10 min, pure find/replace + one config line.

---

## FIX 2 — Quantified "why this matters" dollar model + ONE real citation (council #5)

Today the money argument is one unquantified clause ("one hallucinated refund is a
direct cash loss… multiplied across support volume", README:138 / DEVPOST:10). Judges
scoring Problem Value 25% reward a number they can sanity-check, plus proof someone has
already paid real money for exactly this failure.

**The real, verified citation (do not invent a stat — this one is a legal fact):**
*Moffatt v. Air Canada*, 2024 BCCRT 149 (B.C. Civil Resolution Tribunal, Feb 2024).
Air Canada's website chatbot **invented a retroactive bereavement-refund policy**; the
tribunal rejected the "the chatbot is a separate entity" defence, held the airline
liable for negligent misrepresentation, and ordered **CAD $812.02** paid
($650.88 damages + fees/interest). One fabricated support answer → real legal liability,
on the record. Sources: [CanLII 2024 BCCRT 149](https://www.canlii.org/en/bc/bccrt/doc/2024/2024bccrt149/2024bccrt149.html),
[McCarthy Tétrault case note](https://www.mccarthy.ca/en/insights/blogs/techlex/moffatt-v-air-canada-misrepresentation-ai-chatbot).
(Note: Moffatt was a *policy* fabrication by a chatbot, not a tool-result fabrication by
an autopilot — say "fabricated support answer", not "fabricated tool call", when citing
it. Honest framing survives a judge who reads the case.)

**The dollar model (label it illustrative — every input is a knob the reader can turn):**

> `monthly exposure ≈ ticket volume × share touching money × fabrication rate × avg refund`
> Illustrative: 50,000 tickets/mo × 10% refund/replacement × 1% fabricated "refund
> issued / replacement shipped" × $79 avg refund (our demo order) ≈ **$3,950/mo direct
> cash loss** — before re-contact cost, chargebacks, or the compliance event. And the
> legal floor is already set: in *Moffatt v. Air Canada* (2024 BCCRT 149) a single
> fabricated support answer cost the airline CAD $812 and a tribunal ruling that the
> company owns everything its agent says.

**Exact placements:**
- `README.md` "Why it scores" table, **Problem Value 25% row** — replace
  `one hallucinated "refund issued / replacement shipped" is a direct cash loss + a compliance event, multiplied across support volume`
  with the formula + the Moffatt sentence (compressed to two lines, keep the
  "drop-in MCP gateway" close).
- `docs/DEVPOST.md` **Inspiration** — append after "multiplied across support volume.":
  `This is already case law: in *Moffatt v. Air Canada* (2024 BCCRT 149) a tribunal made the airline pay CAD $812 for a single answer its chatbot made up — and ruled the company owns what its agent says.`
- `docs/video-script.md` **positioning move 6** — replace
  `**Dollar-stakes line** in Problem Value: cost of one hallucinated refund × support volume.`
  with the concrete voiceover line:
  `**Dollar-stakes line** (say it in 2:20–2:45 or the end card): "At 50k tickets a month, a 1% fabrication rate on refund claims is ~$4k a month in phantom refunds — and Air Canada already got billed by a tribunal for one answer its bot made up."`
- **Rubric:** Value (Problem Value 25% — turns an assertion into checkable arithmetic + precedent).
- **Effort:** 25 min. Citation already verified above; no new research needed.

---

## FIX 3 — Reframe to lead with what it ENABLES, not "better than ZeroClaw" (council #7)

README:36 ("**vs the field:**") sits above the fold and opens combatively — the first
thing a judge learns about ZeroClaw/AEVS is that we beat them. Two problems: it hands
the frame to a competitor, and it buries the buyer outcome. The enabling claim is
stronger and 100% honest: *this is what lets you put an agent in front of money.*

**Exact change — `README.md:36`, replace the paragraph opener:**

Current:
> **vs the field:** [ZeroClaw](…) / [Fetch.ai AEVS](…) prove a tool *ran* but never check the agent's prose against the receipt …

Proposed:
> **What this unlocks:** an agent you can let touch money and inventory — because every "I did X" it ships is either receipt-backed, re-grounded, or handed to a human. Receipt primitives like [ZeroClaw](…) and [Fetch.ai AEVS](…) prove a tool *ran* but never check the agent's prose against the receipt (ZeroClaw's own docs: receipts *"don't constrain text output"*). ReceiptGuard closes that gap: types every claim, cross-checks each against its receipt, recovers or escalates, then resolves the ticket.

Same links, same honest positioning — but the first clause is now the product outcome,
and prior art becomes supporting context instead of the headline. The longer
"Prior art & what's actually new here" section (README:76–102) is already
well-calibrated — keep it; it does the humility work below the fold. Apply the same
one-line flip to `docs/BLOG.md:29`: move "my contribution is the deployed closed loop"
to the *front* of the sentence and the ZeroClaw/AEVS credit after it (currently the
credit leads).

- **Rubric:** Presentation (frame control) + Value (judges buy outcomes, not comparisons).
- **Effort:** 15 min.

---

## FIX 4 — Missing links: BLOG + integration-guide unreachable from README

`docs/BLOG.md` and `docs/integration-guide.md` are linked from **nowhere** — a judge
browsing the repo from README never finds them. The integration guide is the strongest
"this is a product, not a demo" artifact (it's where "swap in your Stripe/Shopify
tools" lives), and the blog is the narrative version of the honest benchmark.

**Exact change — `README.md`, end of the Quickstart section (after line 128, the MCP
server line), add:**

> **Drop it on YOUR agent:** [Integration guide](docs/integration-guide.md) — wrap your real tools, verify your drafts, or install the MCP server.
> **The story + the honest numbers:** [Build blog](docs/BLOG.md) · [Devpost text](docs/DEVPOST.md) · [Benchmark methodology](eval/BENCHMARK_METHODOLOGY.md)

(Also fixes discoverability of DEVPOST.md for the "paste identical pitch" step in
video-script.md:21.)

- **Rubric:** Presentation (judges score what they can find) + Value (integration guide is the adoption argument).
- **Effort:** 5 min.

---

## FIX 5 — Benchmark + diagram above the fold: 90% done, one upgrade

Verified against council claim: architecture SVG is at README:32 and the one-line
"**Proven:**" block at README:34 — both above the fold. video-script.md:25 marks this
"(done)". **Mostly true.** Remaining gap: the *table* — the single most quotable
artifact (100% / 66.7% / 0%) — is at README:149, ~110 lines down. A skimming judge sees
prose, not the kill shot.

**Exact change — `README.md:34`, replace the prose "Proven:" line with a 3-row
mini-table + one sentence:**

> | | Detection | FP | Latency |
> |---|---|---|---|
> | **ReceiptGuard** | **100%** | 0% | 0.007 ms/claim |
> | ablation (no value-check) | 66.7% | 0% | — |
> | real `qwen-flash` judge, no receipts | **0%** | 0% | ~1040 ms/claim |
>
> A real LLM judge with no receipts catches **0%** of the same fabrications — receipts, not vibes, are load-bearing. Runs live on **Qwen3.7-Max + Qwen-Flash** via Alibaba Model Studio. Full methodology + honesty notes [below](#benchmark).

Keep the full Benchmark section as-is (the honesty note at README:166 is a scoring
asset — do not shorten it).

- **Rubric:** Presentation (the number IS the pitch; make it skimmable) .
- **Effort:** 10 min.

---

## FIX 6 — Hard record/upload deadline in video-script (council: Jul 9 2:00 PM PDT, reserve 3h)

Current (`video-script.md:20`): `Reserve 2–3h to record/edit/upload before the **Jul 9,
2:00 PM PDT** cutoff.` That's a soft reservation, not a deadline — it lets recording
start at 11:00 AM on cutoff day with zero margin for an upload failure, YouTube
processing lag, or a busted take. Devpost cutoffs are hard; a video that finishes
processing at 2:05 PM scores zero.

**Exact change — replace `video-script.md:20` with a hard-deadline block (move it to
the TOP of "Production rules", first bullet):**

> - **HARD DEADLINE MATH (cutoff Jul 9, 2:00 PM PDT):**
>   - **Video public on YouTube + link pasted into Devpost by 11:00 AM PDT Jul 9** — 3h buffer, non-negotiable.
>   - Start recording **no later than 8:00 AM PDT Jul 9** (3h record/edit/upload window).
>   - **Target: record Jul 8 evening**, so Jul 9 morning is retake margin, not the only take.
>   - Upload as *unlisted* the moment the export finishes; flip to *public* + paste the link immediately — don't hold the upload for a "final" edit.

- **Rubric:** Presentation (a video that misses processing = 15% of the score gone) + pure risk control.
- **Effort:** 5 min to edit; the real cost is calendar discipline.

---

## Summary table

| # | Fix | Rubric | Effort |
|---|---|---|---|
| 1 | Unify `qwen3-max` → Qwen3.7-Max (README ×6, video ×5, `.env.example` ×1) | Presentation + Value | 10 min |
| 2 | Dollar model + *Moffatt v. Air Canada* 2024 BCCRT 149 citation (verified) | Value (Problem Value 25%) | 25 min |
| 3 | Lead with "agent you can let touch money", demote "vs ZeroClaw" | Presentation + Value | 15 min |
| 4 | Link BLOG / integration-guide / DEVPOST from README | Presentation | 5 min |
| 5 | Mini benchmark table above the fold (replace prose "Proven:" line) | Presentation | 10 min |
| 6 | Hard video deadline: public by 11:00 AM PDT Jul 9, record Jul 8 evening | Presentation / risk | 5 min |

Total: ~70 min. Highest leverage first: #2 (only fix that adds new scoring substance),
then #6 (only fix that can zero out 15% of the score), then #1 (cheap, protects the
benchmark claim).

STATUS: DONE

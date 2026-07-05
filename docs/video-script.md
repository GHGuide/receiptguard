# 3-Minute Demo Video — Beat Sheet (hard cap < 3:00; target 2:58)

Judges may score on the video + README alone (rules: not required to run the project).
The agent must be the star, acting and getting caught, within the first 15 seconds.

| Time | On screen | Voiceover | Why it scores |
|---|---|---|---|
| **0:00–0:12** | COLD OPEN, no logo. Generic agent: *"Refund approved, $240 credited."* Then red stamp: **"TOOL RESULT HALLUCINATED — no refund record exists."** | "AI support agents confidently act on results they made up. ReceiptGuard makes that structurally impossible." | Pitch in the first seconds; failure-first arc. |
| **0:12–0:35** | ONE pass of the guard-loop diagram animating: gateway → HMAC receipt → claim typing → cross-check → GSAR → policy gate. | "ReceiptGuard is a qwen3-max autopilot that resolves refund and warranty tickets end-to-end — and cannot fabricate a tool result." | Architecture diagram is a required deliverable. One pass only; don't narrate every box. |
| **0:35–1:15** | Live happy path on the deployed `*.fcapp.run` endpoint. qwen3-max thinking planning, gateway emitting a signed receipt, qwen-flash tagging claims, auto-act. Small **"running on Alibaba Function Compute"** badge + ledger row appearing live. | "It plans with qwen3-max, signs every tool result, types every claim, and acts only on what's backed." | "Real deployment, real data" separates winners from demos. This IS your deploy proof on camera. |
| **1:15–1:50** | **MONEY SHOT.** Force a refund claim with NO backing receipt. Cross-check flags unbacked → GSAR tiers up (regenerate→replan) → recovery fails → policy gate **ESCALATE TO HUMAN**. | "Unbacked claim. It cannot act. It hands off to a human." | The single most differentiating 8 seconds — the safety floor competitors only approximate. |
| **1:50–2:20** | SHA-256 ledger: **tamper one row, the chain breaks visibly.** Then the 3 MCP tools (`run_guarded_autopilot` / `verify_claims` / `list_scenarios`) called from an MCP client. | "Every decision is on an append-only, tamper-evident ledger. And it's an installable MCP server." | Hits Innovation's named "MCP integrations". Two artifacts in 30s = "feels like a product." |
| **2:20–2:45** | Hold the benchmark table readable: 100% detect / 0% FP (self-authored); ablation 66.7%; LLM-judge 100% FP; typing 80% / 100% tool_derived recall, fails-safe. | "On our self-authored adversarial set — here's exactly what we tested." (state ONE honest caveat) | 60% of score is Tech Depth + Innovation; visible integrity beats inflated claims. |
| **2:45–2:58** | End card: name, tagline, GitHub URL, deployed `*.fcapp.run` URL. | "A support autopilot that acts only on what it can prove, escalates the rest to humans, logs every step. Built on Qwen3-Max, Qwen-Flash, and Alibaba Function Compute." | Close on stakes + stack. |

## Production rules
- Real rehearsed script (no AI-voiced filler), clean screen-capture audio, never speed up audio.
- Host PUBLIC on YouTube/Vimeo, set "Not for Kids". No copyrighted music/trademarks. English captions.
- Pre-run both scenarios once before recording (warm matplotlib font cache + FC instance — hit `/health` first).
- Reserve 2–3h to record/edit/upload before the **Jul 9, 2:00 PM PDT** cutoff.
- Paste the identical elevator pitch into the Devpost text field.

## Top positioning moves (ReceiptGuard-specific)
1. **Lead with the product outcome, never "HMAC receipts"** — the primitive is commoditized; a knowledgeable judge docks novelty. Lead: *"a support autopilot that provably cannot fabricate a tool result and escalates anything it can't prove to a human."*
2. **Benchmark + architecture above the fold** in README (done — proof block sits under the diagram).
3. **Make the Alibaba deploy a dated, clickable artifact** — live `*.fcapp.run` URL + ledger screenshot + the exact `s deploy` command.
4. **Foreground the MCP server** with a "connect this to your MCP client" snippet — Innovation literally names "MCP integrations."
5. **Frame the dual-Qwen split as a decision:** "we spend a fast cheap model (qwen-flash) to make the expensive one (qwen3-max) honest." Stack-sophistication, not two API calls.
6. **Dollar-stakes line** in Problem Value: cost of one hallucinated refund × support volume.

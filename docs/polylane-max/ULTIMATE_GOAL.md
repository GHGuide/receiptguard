# ULTIMATE GOAL — ReceiptGuard fully deploy-ready + submission-maxed

Get ReceiptGuard (Qwen Cloud Hackathon, **Track 4 Autopilot Agent**) to a state where it is
**fully ready to deploy on Alibaba Cloud and fully ready to submit on Devpost**, with every
agent-doable item done and every user-gated item reduced to a single clear action — maximizing
the four judging criteria, before the **July 9 2026 2:00 PM PDT** deadline.

If a demo/deploy-proof video is needed, it MUST be produced with the parent folder's
`video-pipeline/` (Remotion + Playwright + ElevenLabs), not ad-hoc.

## Success criteria (mapped to northstar submission checklist + judging weights)
- **c1 (Depth 30% + Stage-1 gate):** Backend deployed on Alibaba Function Compute; live
  `*.fcapp.run` URL warm; deploy-proof recording captured; `qwen.py` linked as the Alibaba-API
  proof file. Deploy-blocking code (R1–R6) done so the deploy cannot fail on our side.
- **c2 (Presentation 15% + required):** ~3-min public demo video produced via `video-pipeline/`,
  uploaded (YouTube/Vimeo, public), link in Devpost.
- **c3 (Depth 30% + Innovation 30%):** highest-leverage hardening merged (benchmark rigor
  R16/17/18/25/26, value model R22, live reasoning R19-21), full test suite green.
- **c4 (Problem Value 25% + Presentation):** Devpost submission complete — public repo + LICENSE,
  architecture diagram, text description, Track 4 id, blog post; all links resolve.

## NEEDS FROM YOU (user-gated — cannot be done by the agent)
1. Alibaba Cloud AccessKey → `s config add` (then agent drives `s deploy`).
2. Record the deploy-proof + demo video on the warm URL (or approve the pipeline auto-capture).
3. ElevenLabs API key for VO (else video renders captions-only).
4. Final Devpost form submit.

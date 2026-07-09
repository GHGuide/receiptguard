// scenes.mjs — ReceiptGuard capture scene scripts. One async fn per `capture` ref in
// script.json. Each fn drives the LIVE demo UI at cfg.capture.base_url (http://localhost:8000)
// deterministically; capture-kit records retina PNG frames (no cursor) + actions.json.
//
// Run:  node video/capture/run.mjs            # records plan, moneyshot, reveal
//       node video/capture/run.mjs moneyshot   # records just one
//
// The demo UI (static/index.html) exposes:
//   #scenario  <select>   (refund_damaged | warranty_replacement)
//   #adv       checkbox    (inject fabrication — red-team)
//   #run       button
// result containers: #b-badge (baseline: "N fabricated"), #g-badge (guarded: "shipped · grounding N"),
//   #g-reason (qwen3.7-max reasoning that blocked the unbacked claim), #rcpts (signed receipts),
//   #audit (hash-chained audit → chain VERIFIED ✓).

import path from "node:path";
import { fileURLToPath } from "node:url";
import { record } from "../../../../video-pipeline/capture/capture-kit.mjs";
import cfg from "../video.config.json" with { type: "json" };

const HERE = path.dirname(fileURLToPath(import.meta.url));
// capture output lives at <project video dir>/captures/<name>/ — orchestrator sync reads here.
const captureDir = (name) => path.join(HERE, "..", "captures", name);

const base = {
  url: cfg.capture.base_url,
  viewport: cfg.capture.viewport,
  dsf: cfg.capture.device_scale_factor,
  fps: cfg.fps === 60 ? 60 : 60, // capture high, the editor decides playback
};

// --- helpers ----------------------------------------------------------------
// viewport-center pixel [x,y] of a selector (CSS px, what actions.json/markZoom expect).
// Scrolls the element into the viewport first so the zoom focus is on-screen.
async function focusOf(r, sel) {
  const el = r.page.locator(sel).first();
  await el.waitFor({ state: "visible" });
  await el.scrollIntoViewIfNeeded();
  const b = await el.boundingBox();
  return [Math.round(b.x + b.width / 2), Math.round(b.y + b.height / 2)];
}
// wait until the guarded run has painted its results (rcpts line filled in).
async function waitForResults(r) {
  await r.page.waitForFunction(
    () => (document.querySelector("#rcpts")?.textContent || "").includes("signed receipts ("),
    null,
    { timeout: 20000 },
  );
}

// ---- s05_run / captures/plan: the live happy path --------------------------
// refund_damaged, adversarial OFF. Baseline hallucinates (red "N fabricated"),
// ReceiptGuard verifies + ships (green "shipped · grounding 1"), audit chain VERIFIED.
export const plan = () =>
  record({ ...base, outDir: captureDir("plan") }, async (r) => {
    await r.hold(0.9); // hero breath on landing
    await r.page.selectOption("#scenario", "refund_damaged");
    await r.hold(0.5);
    await r.clickAt("#run", { moveSec: 0.55 }); // POST /run — guard loop runs
    await waitForResults(r);
    await r.hold(1.3); // both columns paint: baseline vs ReceiptGuard
    await r.mark("verified");
    await r.markZoom(await focusOf(r, "#g-badge"), 1.6, { holdSec: 1.5 }); // "shipped · grounding 1"
    await r.hold(1.5);
    await r.markZoom([base.viewport[0] / 2, base.viewport[1] / 2], 1.0, { holdSec: 0.3 }); // pull back wide
    await r.hold(0.4);
    await r.scrollBy(300, { sec: 0.9 }); // reveal the ledger foot
    await r.hold(0.5);
    await r.markZoom(await focusOf(r, "#audit"), 1.55, { holdSec: 1.5 }); // chain VERIFIED ✓
    await r.hold(1.6);
  });

// ---- s06_catch / captures/moneyshot: the catch (money shot) ----------------
// refund_damaged, adversarial ON. Baseline ships 3 fabrications (red). ReceiptGuard
// catches the injected unbacked claim, shows qwen3.7-max reasoning, regenerates clean.
export const moneyshot = () =>
  record({ ...base, outDir: captureDir("moneyshot") }, async (r) => {
    await r.hold(0.8);
    await r.page.selectOption("#scenario", "refund_damaged");
    await r.hold(0.3);
    await r.clickAt("#adv", { moveSec: 0.45 }); // tick "inject fabrication (red-team)"
    await r.hold(0.4);
    await r.clickAt("#run", { moveSec: 0.5 });
    await waitForResults(r);
    await r.hold(1.3);
    await r.markZoom(await focusOf(r, "#b-badge"), 1.75, { holdSec: 1.6, punch: true }); // red "3 fabricated"
    await r.hold(1.7);
    await r.markZoom([base.viewport[0] / 2, base.viewport[1] / 2], 1.0, { holdSec: 0.3 }); // pull back
    await r.hold(0.4);
    await r.markZoom(await focusOf(r, "#g-reason"), 1.5, { holdSec: 1.6 }); // qwen3.7-max caught it
    await r.hold(1.7);
    await r.markZoom(await focusOf(r, "#g-badge"), 1.6, { holdSec: 1.3 }); // shipped clean, grounding 1
    await r.hold(1.4);
  });

// ---- s07_ledger / captures/reveal: signed receipts + tamper-evident chain --
// slow reveal on the append-only ledger: signed receipts + hash chain VERIFIED.
export const reveal = () =>
  record({ ...base, outDir: captureDir("reveal") }, async (r) => {
    await r.hold(0.7);
    await r.page.selectOption("#scenario", "refund_damaged");
    await r.hold(0.3);
    await r.clickAt("#run", { moveSec: 0.5 });
    await waitForResults(r);
    await r.hold(1.0);
    await r.scrollBy(340, { sec: 1.0 }); // glide down to the ledger foot
    await r.hold(0.6);
    await r.markZoom(await focusOf(r, "#rcpts"), 1.5, { holdSec: 1.6 }); // signed receipts (5)
    await r.hold(1.7);
    await r.markZoom(await focusOf(r, "#audit"), 1.65, { holdSec: 1.8, punch: true }); // chain VERIFIED ✓
    await r.hold(2.0);
  });

export const scenes = { plan, moneyshot, reveal };

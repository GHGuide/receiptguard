// run.mjs — per-project capture runner. Records all scenes (or one by name),
// then assembles each into base.mp4. Idempotent: re-running re-captures cleanly.
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { scenes } from "./scenes.mjs"; // copy scenes.example.mjs -> scenes.mjs and edit

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ASSEMBLE = path.join(HERE, "..", "..", "..", "..", "video-pipeline", "capture", "assemble.sh");

const only = process.argv[2];
const names = only ? [only] : Object.keys(scenes);

for (const name of names) {
  const fn = scenes[name];
  if (!fn) {
    console.error(`no scene named "${name}". have: ${Object.keys(scenes).join(", ")}`);
    process.exit(1);
  }
  console.log(`\n=== capturing ${name} ===`);
  const manifest = await fn();
  // captures live under the PROJECT's own video/ dir at captures/<name>/ — this is
  // exactly where orchestrator/build.mjs `sync` reads from. Keeps projects isolated.
  const dir = path.join(HERE, "..", "captures", name);
  console.log(`  ${manifest.frame_count} frames, ${manifest.duration_sec.toFixed(1)}s`);
  execFileSync("bash", [ASSEMBLE, dir, String(manifest.fps)], { stdio: "inherit" });
}
console.log("\ncapture done.");

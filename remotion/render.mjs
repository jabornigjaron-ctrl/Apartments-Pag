// Rendert ein Reel mit Remotion.
// Aufruf:  node render.mjs <props.json> <ausgabe.mp4>
// Die Props-Datei beschreibt Vorlage, Clips, Texte und Musik (siehe src/Reel.tsx, Typ ReelProps).
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const [propsFile, out] = process.argv.slice(2);
if (!propsFile || !out) {
  console.error("Aufruf: node render.mjs <props.json> <ausgabe.mp4>");
  process.exit(1);
}
const raw = JSON.parse(readFileSync(propsFile, "utf8"));
// Fehlende optionale Felder explizit leeren, sonst ergaenzt Remotion sie aus den Beispiel-Props
const inputProps = { hook: null, items: [], end: null, music: null, bpm: null, location: null, accent: null, ...raw };

// Vorinstalliertes Chromium der Cloud-Umgebung nutzen (kein Download noetig)
const candidates = [
  "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell",
  "/opt/pw-browsers/chromium",
];
const browserExecutable = candidates.find((p) => existsSync(p)) ?? null;

const serveUrl = await bundle({ entryPoint: path.join(here, "src/index.ts"), publicDir: path.join(here, "public") });
const composition = await selectComposition({ serveUrl, id: "Reel", inputProps, browserExecutable });
await renderMedia({
  composition, serveUrl, codec: "h264", outputLocation: out, inputProps, browserExecutable,
  crf: 20, pixelFormat: "yuv420p", audioCodec: "aac", concurrency: 4,
  chromiumOptions: { gl: "swangle" },
  onProgress: ({ progress }) => {
    const pct = Math.round(progress * 100);
    if (pct % 20 === 0) process.stdout.write(`\r${pct}%`);
  },
});
console.log(`\nReel fertig: ${out} (${(composition.durationInFrames / composition.fps).toFixed(1)} s)`);

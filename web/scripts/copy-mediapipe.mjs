// Copies MediaPipe's WebAssembly files from node_modules into public/, so the
// site serves them itself instead of loading them from someone else's CDN.
// Runs before `npm run dev` and `npm run build` (see package.json).
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const from = join(web, "node_modules", "@mediapipe", "tasks-vision", "wasm");
const to = join(web, "public", "mediapipe");
mkdirSync(to, { recursive: true });
for (const name of ["vision_wasm_internal.js", "vision_wasm_internal.wasm"]) {
  copyFileSync(join(from, name), join(to, name));
}
console.log("Copied MediaPipe's wasm files to public/mediapipe");

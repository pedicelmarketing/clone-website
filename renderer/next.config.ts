import type { NextConfig } from "next";
import { resolve } from "node:path";

// Lock Next.js's workspace inference to the renderer/ subdirectory so the
// presence of an unrelated lockfile at /home/openclaw/package-lock.json
// (from other tooling on the dev box) doesn't trigger a build warning.
const nextConfig: NextConfig = {
  outputFileTracingRoot: resolve(import.meta.dirname, ".."),
  // Static export: emits a self-contained `out/` directory (HTML + CSS + JS).
  // This is what makes the renderer compatible with the rest of the pipeline —
  // validate_site.py and critique_pass.py both serve a plain directory, so the
  // Next output can go through the same 8 gates and the same vision critique
  // as the static composer. It is also the deployable artifact.
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
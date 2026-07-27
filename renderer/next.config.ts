import type { NextConfig } from "next";
import { resolve } from "node:path";

// Lock Next.js's workspace inference to the renderer/ subdirectory so the
// presence of an unrelated lockfile at /home/openclaw/package-lock.json
// (from other tooling on the dev box) doesn't trigger a build warning.
const nextConfig: NextConfig = {
  outputFileTracingRoot: resolve(import.meta.dirname, ".."),
};

export default nextConfig;
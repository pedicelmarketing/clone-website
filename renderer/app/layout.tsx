import type { Metadata } from "next";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { Inter, Outfit, Poppins, Fraunces, Archivo } from "next/font/google";
import "./globals.css";

/**
 * Brand-driven typography.
 *
 * These used to be hardcoded to Inter / Poppins / JetBrains Mono, so every
 * brand got the same three faces regardless of what its synthesized tokens
 * asked for — the same class of bug as the hardcoded token path that once made
 * every brand render in the FIRST brand's palette.
 *
 * `next/font/google` requires static imports (it downloads and self-hosts at
 * build time), so families cannot be fully dynamic. Instead we import a small
 * registry of open-licence faces and SELECT from it using the token, falling
 * back to Inter. Adding a face is one line.
 *
 * Every face here is SIL OFL 1.1. Nothing proprietary is vendored — paid faces
 * are substituted upstream in synthesize_tokens.py.
 *
 * There is deliberately no monospace face: it was being loaded purely to set
 * small uppercase labels, which the `.u-label` utility now does in the display
 * face. That is one fewer webfont on every page.
 */
const inter = Inter({ variable: "--font-inter", subsets: ["latin"], display: "swap" });
const outfit = Outfit({
  variable: "--font-outfit", subsets: ["latin"],
  weight: ["300", "400", "500", "600"], display: "swap",
});
const poppins = Poppins({
  variable: "--font-poppins", subsets: ["latin"],
  weight: ["400", "500", "600"], display: "swap",
});
const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"], display: "swap" });
const archivo = Archivo({ variable: "--font-archivo", subsets: ["latin"], display: "swap" });

const REGISTRY: Record<string, { variable: string; className: string }> = {
  Inter: inter, Outfit: outfit, Poppins: poppins, Fraunces: fraunces, Archivo: archivo,
};

/** First family out of a CSS stack: `"Outfit", sans-serif` -> `Outfit`. */
function firstFamily(stack: unknown): string | null {
  if (typeof stack !== "string") return null;
  const first = stack.split(",")[0]?.trim().replace(/^["']|["']$/g, "");
  return first || null;
}

function loadFontChoice(): { display: string; body: string } {
  const dir = process.env.WEB_DESIGNER_TOKENS_DIR
    ? resolve(process.env.WEB_DESIGNER_TOKENS_DIR, "tokens/dist")
    : resolve(process.cwd(), "..", "reports", "m3-token-synthesis", "tokens", "dist");
  try {
    const json = JSON.parse(readFileSync(resolve(dir, "tailwind-tokens.json"), "utf8"));
    const fam = json?.theme?.extend?.fontFamily ?? {};
    return {
      display: firstFamily(fam.display) ?? "Inter",
      body: firstFamily(fam.body) ?? "Inter",
    };
  } catch {
    return { display: "Inter", body: "Inter" };
  }
}

const choice = loadFontChoice();
const displayFont = REGISTRY[choice.display] ?? inter;
const bodyFont = REGISTRY[choice.body] ?? inter;

export const metadata: Metadata = {
  title: "Renderer",
  description: "Site generated from a validated design plan",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body
        // Alias the chosen faces onto the names the token layer expects, so
        // `font-display` / `font-body` keep resolving through one source of truth.
        style={{
          ["--font-display" as string]: `var(${displayFont.variable})`,
          ["--font-body" as string]: `var(${bodyFont.variable})`,
        }}
        // ONLY the two chosen faces are applied. Applying every registry
        // entry's `.variable` class injects that font's @font-face rules and
        // ships its files — five families on a page that uses two, which cost
        // real Lighthouse performance before it was caught.
        className={`${displayFont.variable} ${bodyFont.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}

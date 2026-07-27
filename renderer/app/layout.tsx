import type { Metadata } from "next";
import { Inter, Poppins, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Brand-typography bindings. Each font exposes its own CSS variable name
// (e.g. --font-display, --font-body, --font-mono); we then *alias* those
// to the upstream synthesized tokens in app/_tokens.generated.css so the
// browser sees a single source of truth.
//
// The font names come straight from
// reports/m3-token-synthesis/tokens/dist/tailwind-tokens.json
// (`fontFamily.display = Inter`, `body = Poppins`, `mono = JetBrains Mono`).
const display = Inter({
  variable: "--font-display",
  subsets: ["latin"],
  display: "swap",
});
const body = Poppins({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});
const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Renderer",
  description:
    "Re-versioned brand site generated from reports/m6-design/design-plan.json",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${display.variable} ${body.variable} ${mono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
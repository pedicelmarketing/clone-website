/**
 * Site chrome — the morphing pill nav and the footer.
 *
 * `PillNav` is harvested pattern #1: a fixed pill that spans the page at rest
 * and collapses to a compact capsule once you scroll, its link cluster fading
 * out as it narrows. The geometry is measured from the reference (62px tall,
 * 1400px → 440px); everything else — colour, type, wordmark — is this brand's.
 *
 * Nothing here is invented. `nav` comes from the plan's own `pages[].in_nav`,
 * and the wordmark from `site.wordmark`. If the plan supplies no wordmark the
 * header renders without one rather than fabricating a brand name.
 *
 * Gate 11 requires a <nav> on EVERY route, so the mobile menu is a native
 * <details> — its links are in the DOM at all times, work with JS disabled, and
 * cost no bundle.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export interface NavItem {
  href: string;
  label: string;
}

export function PillNav({
  wordmark, tagline, nav, currentHref,
}: {
  wordmark: string | null;
  tagline: string | null;
  nav: NavItem[];
  currentHref: string;
}) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className="fixed inset-x-0 top-0 z-[100] flex justify-center px-4 pt-4">
      <div
        className={[
          "flex h-[62px] w-full items-center gap-5 rounded-full px-5",
          "border border-foreground/10 bg-background/80 backdrop-blur-xl",
          "transition-[max-width] duration-500 ease-out",
          scrolled ? "max-w-[560px]" : "max-w-[1400px]",
        ].join(" ")}
      >
        {wordmark && (
          <Link
            href="/"
            className="font-display text-[15px] tracking-[-0.01em] whitespace-nowrap text-foreground"
          >
            {wordmark}
          </Link>
        )}
        {tagline && !scrolled && (
          <span className="u-label hidden text-foreground/70 xl:inline">{tagline}</span>
        )}

        {nav.length > 0 && (
          <>
            {/* Desktop cluster — fades out as the pill collapses, but stays in
             *  the DOM so Gate 11 still sees a populated <nav> on every route. */}
            <nav
              aria-label="Main"
              className={[
                "ml-auto hidden transition-opacity duration-300 md:block",
                scrolled ? "pointer-events-none opacity-0" : "opacity-100",
              ].join(" ")}
            >
              <ul className="flex items-baseline gap-7">
                {nav.map((item) => {
                  const active = item.href === currentHref;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        className={[
                          "u-label transition-colors",
                          active
                            ? "text-foreground"
                            : "text-foreground/70 hover:text-foreground",
                        ].join(" ")}
                      >
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </nav>

            {/* Compact menu — the only nav below md, and the nav once the pill
             *  has collapsed. <details> keeps its contents in the DOM. */}
            <details className="group/menu relative ml-auto md:ml-0 md:group-data-[scrolled]:block">
              <summary
                aria-label="Menu"
                className="flex h-9 cursor-pointer list-none items-center gap-2 rounded-full border border-foreground/15 px-4 outline-none focus-visible:ring-2 focus-visible:ring-primary [&::-webkit-details-marker]:hidden"
              >
                <span className="u-label text-foreground/70">Menu</span>
              </summary>
              <nav
                aria-label="Compact"
                className="absolute right-0 top-[calc(100%+12px)] w-56 rounded-2xl border border-foreground/10 bg-background/95 p-3 shadow-xl backdrop-blur-xl"
              >
                <ul className="flex flex-col">
                  {nav.map((item) => (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        aria-current={item.href === currentHref ? "page" : undefined}
                        className="block rounded-lg px-3 py-2 font-body text-sm text-foreground/75 transition-colors hover:bg-foreground/5 hover:text-foreground"
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            </details>
          </>
        )}
      </div>
    </header>
  );
}

export function SiteFooter({
  wordmark, nav, children,
}: { wordmark: string | null; nav: NavItem[]; children?: React.ReactNode }) {
  return (
    <footer className="mt-8 w-full">
      <div className="mx-auto w-full max-w-[1440px] px-6 lg:px-12">
        <div className="grid grid-cols-1 gap-8 border-t border-foreground/15 py-14 lg:grid-cols-12">
          <div className="lg:col-span-5">
            {wordmark && (
              <p className="font-display text-2xl tracking-[-0.01em] text-foreground lg:text-3xl">
                {wordmark}
              </p>
            )}
          </div>
          {nav.length > 0 && (
            <nav aria-label="Footer" className="lg:col-span-7">
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {nav.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="font-body text-sm text-foreground/70 transition-colors hover:text-foreground"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          )}
        </div>
        {children}
      </div>
    </footer>
  );
}

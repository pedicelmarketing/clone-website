/**
 * Site chrome — header, navigation, footer.
 *
 * The rendered output contained ZERO <nav>, <header> and <footer> elements.
 * Every section went into one flat <main> stack, which is why the pages read as
 * a scroll of text blocks rather than as a website.
 *
 * Nothing here is invented. The design pass already decides, per section,
 * whether it belongs in navigation (`in_nav`) and what to call it
 * (`nav_label`) — `in_nav` was being ignored outright. The wordmark is the
 * masthead section's own headline, which the pass writes from real brand-brief
 * facts. If the plan supplies no masthead, the header renders without a
 * wordmark rather than inventing one.
 */

"use client";

import { useEffect, useState } from "react";

export interface NavItem {
  id: string;
  label: string;
}

export function SiteHeader({
  wordmark, tagline, nav,
}: { wordmark: string | null; tagline: string | null; nav: NavItem[] }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-40 w-full border-b bg-background/90 backdrop-blur-sm transition-colors ${
        scrolled ? "border-border" : "border-transparent"
      }`}
    >
      <div className="mx-auto flex w-full max-w-[1440px] items-baseline gap-6 px-6 py-4 lg:px-12">
        {wordmark && (
          <a href="#top" className="font-display text-base tracking-tight text-foreground lg:text-lg">
            {wordmark}
          </a>
        )}
        {tagline && (
          <span className="hidden font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground xl:inline">
            {tagline}
          </span>
        )}
        {nav.length > 0 && (
          <nav aria-label="Sections" className="ml-auto">
            <ul className="flex flex-wrap items-baseline gap-5 lg:gap-8">
              {nav.map((item) => (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    className="font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
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
        <div className="grid grid-cols-1 gap-8 border-t border-border py-14 lg:grid-cols-12">
          <div className="lg:col-span-5">
            {wordmark && (
              <p className="font-display text-2xl tracking-tight text-foreground lg:text-3xl">
                {wordmark}
              </p>
            )}
          </div>
          {nav.length > 0 && (
            <nav aria-label="Footer" className="lg:col-span-7">
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {nav.map((item) => (
                  <li key={item.id}>
                    <a
                      href={`#${item.id}`}
                      className="font-body text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {item.label}
                    </a>
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

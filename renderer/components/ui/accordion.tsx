/**
 * Accordion — native `<details>` / `<summary>`, no Radix.
 *
 * This is a correctness change as much as a bundle change. Radix mounts
 * `AccordionContent` only when the item is open, so on a STATIC EXPORT every
 * closed item's content is simply absent from the emitted HTML — invisible to
 * Gate 11 (content fidelity), invisible to search engines, and unreachable
 * without JavaScript. `<details>` keeps its content in the DOM at all times and
 * works with JS disabled.
 *
 * Keyboard behaviour, focus management and `aria-expanded` are supplied by the
 * browser, which is the other reason this is not a downgrade.
 */

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Accordion({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("w-full", className)}>{children}</div>;
}

export function AccordionItem({
  children, className, defaultOpen = false,
}: { children: ReactNode; className?: string; defaultOpen?: boolean }) {
  return (
    <details
      open={defaultOpen}
      className={cn("group/acc border-b border-current/10", className)}
    >
      {children}
    </details>
  );
}

export function AccordionTrigger({
  children, className,
}: { children: ReactNode; className?: string }) {
  return (
    <summary
      className={cn(
        "flex cursor-pointer list-none items-center justify-between gap-6 py-5",
        "text-left transition-opacity hover:opacity-70",
        "outline-none focus-visible:ring-2 focus-visible:ring-primary",
        "[&::-webkit-details-marker]:hidden",
        className,
      )}
    >
      <span className="flex min-w-0 flex-1 items-baseline gap-4">{children}</span>
      {/* Rotates via the parent <details open> state — no JS, no state. */}
      <svg
        aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
        className="shrink-0 opacity-50 transition-transform duration-200 group-open/acc:rotate-45"
      >
        <path d="M12 5v14M5 12h14" />
      </svg>
    </summary>
  );
}

export function AccordionContent({
  children, className,
}: { children?: ReactNode; className?: string }) {
  if (!children) return null;
  return <div className={cn("pb-5 pr-10", className)}>{children}</div>;
}

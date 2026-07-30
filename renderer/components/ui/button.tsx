/**
 * Button — dependency-free.
 *
 * This was a shadcn/cva component carrying 7 variants and 8 sizes, of which the
 * renderer uses exactly one variant and two sizes across five call sites. It
 * pulled in `class-variance-authority` and `@radix-ui/react-slot` for that,
 * against a 300 KB gzipped bundle budget with under 5 KB of headroom.
 *
 * Colour note: the filled variant uses `text-primary-foreground`, which
 * resolves through `--color-primary-text` — derived by measured contrast
 * against the brand's primary, NOT a positional neutral. On a brand whose
 * neutral-0 was a cream and whose primary was a yellow, the positional version
 * rendered every button at 1.47:1.
 */

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

const BASE =
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-full font-medium " +
  "whitespace-nowrap transition-colors outline-none select-none " +
  "focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary " +
  "disabled:pointer-events-none disabled:opacity-50";

const VARIANTS = {
  default: "bg-primary text-primary-foreground hover:bg-primary/85",
  outline: "border border-current/25 bg-transparent hover:border-current/60",
} as const;

const SIZES = {
  default: "h-10 px-5 text-sm",
  lg: "h-12 px-7 text-base",
} as const;

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
  children?: ReactNode;
}

export function Button({
  className, variant = "default", size = "default", type = "button", ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      data-slot="button"
      className={cn(BASE, VARIANTS[variant], SIZES[size], className)}
      {...props}
    />
  );
}

/** Anchor styled as a button — for real navigation, which a <button> is not. */
export function ButtonLink({
  className, variant = "default", size = "default", ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
}) {
  return (
    <a
      data-slot="button"
      className={cn(BASE, VARIANTS[variant], SIZES[size], className)}
      {...props}
    />
  );
}

export default Button;

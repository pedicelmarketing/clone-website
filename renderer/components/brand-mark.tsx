/**
 * The client's actual identity, redrawn as SVG from their designer's brand board.
 *
 * Every detail here is taken from that board rather than invented:
 *  - a circle standing for the ball;
 *  - two DASHED arcs inside it — the board's own caption reads "las líneas
 *    discontinuas simbolizan las costuras de la pelota de tenis/pádel", so the
 *    dashes are the seams and are load-bearing, not decorative;
 *  - an outlined initial in the centre, captioned "una R moderna, limpia y con
 *    fuerza visual" — drawn as stroked type with no fill to match;
 *  - the three-tier lockup: name, then a middle line flanked by gold rules,
 *    then the discipline line, all widely letterspaced ("minimalismo y
 *    elegancia", "tipografía sofisticada y composición equilibrada").
 *
 * The board's primary colourway is gold on dark forest green, which is the one
 * the site is built on.
 *
 * NOTE FOR THE CLIENT: the board's initial is "R" for Riki Padrón, while the
 * chosen site name is Premium Padel Academy Marbella. The mark is reproduced as
 * supplied; whether the academy keeps the personal initial is a branding
 * decision for them, not one to make silently in code.
 *
 * This replaces the supplied JPEG, which is a flattened screenshot of a
 * presentation slide. A raster of a slide is not a logo asset — the real vector
 * should still be requested before production.
 */

export function BallMark({
  className = "", initial = "R", size,
}: { className?: string; initial?: string; size?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      role="img"
      aria-label={`${initial} ball monogram`}
      className={className}
      style={size ? { width: size, height: size } : undefined}
      fill="none"
      stroke="currentColor"
    >
      {/* the ball */}
      <circle cx="50" cy="50" r="45" strokeWidth="1.6" />
      {/* the seams — dashed, per the board's stated rationale */}
      <path d="M20.5 16 A 45 45 0 0 0 20.5 84" strokeWidth="1.2"
            strokeDasharray="3.5 4.5" strokeLinecap="round" />
      <path d="M79.5 16 A 45 45 0 0 1 79.5 84" strokeWidth="1.2"
            strokeDasharray="3.5 4.5" strokeLinecap="round" />
      {/* the initial: stroked, unfilled, in the page's display face */}
      <text
        x="50" y="50"
        textAnchor="middle" dominantBaseline="central"
        fontFamily="var(--font-display), ui-sans-serif, system-ui, sans-serif"
        fontSize="46" fontWeight={400}
        fill="none" stroke="currentColor" strokeWidth="1.1"
      >
        {initial}
      </text>
    </svg>
  );
}

/**
 * The full lockup — mark above a three-tier name block, as composed on the board.
 * Used at large scale; the header uses a compact horizontal variant instead.
 */
export function BrandLockup({
  name, middle, discipline, className = "",
}: { name: string; middle?: string | null; discipline?: string | null; className?: string }) {
  return (
    <div className={`flex flex-col items-center text-center ${className}`}>
      <BallMark className="text-primary" size="clamp(72px, 9vw, 132px)" />
      <p className="mt-6 font-display text-[clamp(1.1rem,2.4vw,2rem)] font-light uppercase leading-none tracking-[0.28em] text-foreground">
        {name}
      </p>
      {middle && (
        // The gold rules either side of the middle line are the board's one
        // piece of ornament. They are rules, not text, so gold is unrestricted.
        <div className="mt-4 flex w-full items-center justify-center gap-4">
          <span aria-hidden="true" className="h-px w-full max-w-[110px] bg-primary/70" />
          <span className="u-label whitespace-nowrap text-foreground/75">{middle}</span>
          <span aria-hidden="true" className="h-px w-full max-w-[110px] bg-primary/70" />
        </div>
      )}
      {discipline && (
        <p className="mt-3 u-label text-foreground/55">{discipline}</p>
      )}
    </div>
  );
}

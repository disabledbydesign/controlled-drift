/**
 * Starfield generator — matched to the canonical gallery's measured distribution.
 *
 * WHY THIS EXISTS: the tuned look is the full phone mockup's density, but the gallery ships
 * it as a literal wall of hand-emitted CSS (~14 kB of radial-gradients). Rather than trade
 * the look for the payload, we regenerate the same distribution at runtime — a few hundred
 * bytes of code for an identical sky.
 *
 * MEASURED FROM `design/mockups/color-system.html` section 4a (172 gradients):
 *
 *   TWO POPULATIONS, and this is the important part —
 *     · 165 stars   0.51–2.01px, alpha 0.18–0.78 (median 0.39)
 *     ·   7 glows   4.9–6.4px,   alpha 0.09 flat — large, barely-visible nebulosity
 *   The depth in the design comes from that second layer, NOT from clustering the stars.
 *
 *   SIZE CORRELATES WITH BRIGHTNESS (bigger = brighter, as in a real sky):
 *     0.5–0.8px → mean alpha 0.379   |   0.8–1.1px → 0.410
 *     1.1–1.4px → mean alpha 0.405   |   1.4–3.0px → 0.556
 *
 *   SPATIALLY UNIFORM: quadrant counts 38/42/39/46. The canonical design does NOT cluster.
 *
 *   TINTS, by observed frequency (n=172):
 *     white 89 · blue 34 · rose 22 · warm 9 · deep blue 8 · pink 6 · pale blue 4
 *
 * The seed is fixed, so the sky is STABLE — it does not reshuffle on render or reload.
 */

/** mulberry32 — small, fast, well-distributed. Deterministic for a given seed. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Observed tint frequencies, normalised to cumulative weights. */
const TINTS: readonly [number, string][] = [
  [89 / 172, '255,255,255'],
  [34 / 172, '208,226,255'],
  [22 / 172, '255,214,232'],
  [9 / 172, '255,240,214'],
  [8 / 172, '190,214,255'],
  [6 / 172, '255,224,238'],
  [4 / 172, '215,232,255'],
];

function pickTint(r: number): string {
  let acc = 0;
  for (const [w, rgb] of TINTS) {
    acc += w;
    if (r <= acc) return rgb;
  }
  return '255,255,255';
}

/**
 * Star radius, skewed small. `r**1.7` biases toward the low end, reproducing the observed
 * shape: many sub-1px stars, a thin tail out to ~2px.
 */
function starSize(r: number): number {
  return 0.51 + Math.pow(r, 1.7) * 1.5;
}

/**
 * Brightness rises with size (the measured correlation), plus scatter so the field doesn't
 * look mechanical. Clamped to the observed 0.18–0.78 range.
 */
function starAlpha(size: number, jitter: number): number {
  const t = (size - 0.51) / 1.5; // 0..1 across the size range
  const base = 0.37 + t * 0.19; // 0.37 → 0.56, matching the measured means
  const scatter = (jitter - 0.5) * 0.28;
  return Math.min(0.78, Math.max(0.18, base + scatter));
}

export interface StarfieldOptions {
  /** Star count. The gallery's phone mockup has 165. */
  count?: number;
  /** Large faint nebulosity blobs. The gallery has 7. This layer creates the depth. */
  glowCount?: number;
  /** Fixed seed keeps the sky stable across renders and reloads. */
  seed?: number;
  /**
   * OFF by default, because the canonical gallery is spatially uniform.
   * Set 0..1 to pull stars toward a few centres (a Thomas cluster process) for a more
   * astronomical, less even sky. Provided so the look can be compared by eye rather than
   * argued about — if it isn't adopted, delete it.
   */
  clustering?: number;
}

export function starfield({
  count = 165,
  glowCount = 7,
  seed = 0x5eed,
  clustering = 0,
}: StarfieldOptions = {}): string {
  const rand = mulberry32(seed);
  const layers: string[] = [];

  // Nebulosity first so it sits behind the stars in paint order.
  for (let i = 0; i < glowCount; i++) {
    const x = (rand() * 100).toFixed(1);
    const y = (rand() * 100).toFixed(1);
    const size = (4.9 + rand() * 1.5).toFixed(1);
    const rgb = pickTint(rand());
    layers.push(`radial-gradient(${size}px ${size}px at ${x}% ${y}%,rgba(${rgb},0.09),transparent 62%)`);
  }

  // Optional cluster centres — only consulted when clustering > 0.
  const centres = Array.from({ length: 6 }, () => [rand() * 100, rand() * 100] as const);

  for (let i = 0; i < count; i++) {
    let x = rand() * 100;
    let y = rand() * 100;

    if (clustering > 0) {
      const c = centres[i % centres.length]!;
      // Box–Muller gaussian offset around the chosen centre.
      const u = Math.max(rand(), 1e-9);
      const mag = Math.sqrt(-2 * Math.log(u)) * 18;
      const ang = rand() * Math.PI * 2;
      x = x * (1 - clustering) + (c[0] + Math.cos(ang) * mag) * clustering;
      y = y * (1 - clustering) + (c[1] + Math.sin(ang) * mag) * clustering;
      x = Math.min(100, Math.max(0, x));
      y = Math.min(100, Math.max(0, y));
    }

    const size = starSize(rand());
    const alpha = starAlpha(size, rand());
    const rgb = pickTint(rand());

    layers.push(
      `radial-gradient(${size.toFixed(2)}px ${size.toFixed(2)}px at ${x.toFixed(1)}% ${y.toFixed(1)}%,rgba(${rgb},${alpha.toFixed(2)}),transparent 62%)`,
    );
  }

  return layers.join(',');
}

/*
 * Falloff note: the gallery's stars use `transparent 62%` (153 of 175 gradients);
 * the remaining 60%/70%/55% values belong to the ambient wash layers, not the stars.
 */

# Token reconciliation — gallery vs. v4 buildThemes

**Date:** 2026-07-17
**Canonical source:** `design/mockups/color-system.html` (the rendered gallery — what the values were tuned against)
**Structural source:** `design/mockups/review-reorganize-mobile-v4.html` → `buildThemes()` (~L134–166) — key names and nesting only
**Output:** `design/tokens/tokens.ts`

Rule applied throughout: where the two disagree, **the gallery wins**. Where the gallery is silent or internally inconsistent, the v4 value is kept and the token is marked `// UNVERIFIED` in `tokens.ts` and listed under [Ambiguities](#ambiguities) below — never silently decided.

**Regions mined (only these):**

| Region | Gallery lines | What it is |
|---|---|---|
| `4a` | 31–80 | Celestial phone mockup |
| `4c` | 81–138 | Hardware phone mockup |
| `5a` | 139–220 | Celestial component kit (acceptance reference) |
| `5c` | 221–296 | Hardware component kit (acceptance reference) |

**Regions deliberately excluded:** `3a/3b/3c` (L317–468), `2a/2b` (L469–616), `1a/1b` (L617–817), and the page's own chrome/section headers. These are superseded explorations — the page itself notes around L605 that the palette "grew into ~10 competing bright hues" before being cut back. No value in `tokens.ts` comes from them.

**Instruction-shaped text:** none found. Both files scanned for prompt-injection patterns (`ignore previous`, `you must`, `system prompt`, `as an AI`); zero hits. Both were treated purely as data.

---

## 1. Discrepancy table

Every difference between the gallery and `buildThemes()`, however small. 63 rows.

### 1a. Celestial colours

| Token | Gallery value | v4 buildThemes | Taken | Gallery line(s) |
|---|---|---|---|---|
| `bg` | `#060512` | `#0a0812` | gallery | L34 (phone body base) |
| `panel` | `rgba(255,255,255,.04)` | `rgba(255,255,255,0.045)` | gallery | L40, L71–73, L180, L181, L195, L196 |
| `border` | `rgba(255,255,255,.09)` | `rgba(255,255,255,0.11)` | gallery | L40, L71–73, L181, L195, L196 |
| `roseBg` | `rgba(239,146,189,.07)` | `rgba(239,146,189,0.08)` | gallery | L55 |
| `roseBorder` | `rgba(239,146,189,.24)` | `rgba(239,146,189,0.26)` | gallery | L55 |
| `roseDim` | `#b07f96` | `#b98aa0` | gallery | L55 ("why this matters" eyebrow) |
| `gold` | `#f0a86a` | `#f0b46a` | gallery | L59, L148, L152, L194 — **see Ambiguity A3** |
| `goldDim` | hue `#f0a86a` | `rgba(240,180,106,0.22)` | gallery hue, v4 alpha | alpha UNVERIFIED |
| `amber` | `#f0a86a` | `#f0b46a` | gallery | L59, L148, L194 — **see Ambiguity A3** |
| `on` | `#14101a` | `#150c18` | gallery | L154 (solid accent chip label) |
| `inkBg` | `rgba(255,255,255,.03)` | `rgba(0,0,0,0.32)` | gallery | L75, L198 — celestial input is a white veil, not an ink well |
| `inkBorder` | `rgba(255,255,255,.08)` | `rgba(255,255,255,0.09)` | gallery | L75, L198 |
| `actBg` | `rgba(240,168,106,.14)` | `rgba(240,180,106,0.13)` | gallery | L148, L194 (hue **and** alpha differ) |
| `actBorder` | `rgba(240,168,106,.4)` | `rgba(240,180,106,0.4)` | gallery | L148, L194 (hue differs) |

Celestial colours confirmed identical (no change): `panel2`, `surface`, `surface2`, `hair`, `rose`, `text`, `dim`, `dimmer`, `green`, `teal`, `purple`, `orange`, `red`, `strategy`, `side`, `sig`, `onGreen`.

### 1b. Celestial structure

| Token | Gallery value | v4 buildThemes | Taken | Gallery line(s) |
|---|---|---|---|---|
| `r.field` | `999px` | `13px` | gallery | L193, L194–196, L198 (all celestial fields are pills) |
| `r.ctl` | `999px` | `11px` | gallery | L146–154, L179–184, L211 |
| `r.mod` | `14px` | `18px` | gallery | L203 (menu) |
| `pane` | `rgba(30,20,32,.92)` | `rgba(10,7,19,0.58)` | gallery | L203 |
| topAccent gradient | `linear-gradient(90deg,#ef92bd,#d58fd8,#5fc6d6)` | `linear-gradient(90deg,`+`C.rose`+`,`+`C.strategy`+` 50%,`+`C.teal`+`)` — i.e. starts at `#f2a6c8` | gallery | L140 (starts at `sig`, not `rose`; no 50% stop) |
| topAccent glow | `0 8px 14px -8px rgba(239,146,189,.8)` | `0 0 12px `+`C.rose`+`99` | gallery | L44 |
| `star` | 9-star + ambient recipe | 26-star recipe | gallery | L139 — **see Ambiguity A7** |

### 1c. Hardware colours

| Token | Gallery value | v4 buildThemes | Taken | Gallery line(s) |
|---|---|---|---|---|
| `panel` | `rgba(18,22,34,.66)` → `rgba(10,12,20,.66)` gradient | `rgba(20,24,38,0.62)` flat | gallery | L102, L107 — flat top stop stored in `c.panel`; full gradient via `panelBackground()` |
| `surface` | `rgba(255,255,255,.03)` | `rgba(16,20,32,0.72)` | gallery | L95–97, L277, L278 |
| `hair` | `rgba(255,255,255,.06)` | `rgba(255,255,255,0.07)` | gallery | L223 |
| `rose` | `#f593c1` | `#f6aecd` | gallery | L115, L222, L229, L252, L286, L294 — **see Ambiguity A1** |
| `roseBg` | `rgba(240,122,181,.08)` | `rgba(240,122,181,0.07)` | gallery | L105 |
| `roseBorder` | `rgba(240,122,181,.22)` | `rgba(240,122,181,0.26)` | gallery | L105 |
| `dimmer` | `#6f7a92` | `#63708c` | gallery | L101, L226, L240, L250, L259, L272, L284, L291 — **see Ambiguity A5** |
| `blue` | `#3aa0da` | `#49ade0` | gallery | L102, L103 — **see Ambiguity A2** |
| `teal` | `#45cfc0` | `#56c9d6` | gallery | L245 — **see Ambiguity A2** |
| `red` | `#ef7683` | `#ff6b6b` | gallery | L255, L288 (hardware shares the celestial red) |
| `strategy` | `#d071d8` | `#df7ad0` | gallery | L246 |
| `side` | `#9aa0e0` | `#7f97d6` | gallery | L231 (hardware reuses the celestial side hue) |
| `on` | `#07080f` | `#04060c` | gallery | L223 — **see Ambiguity A4** |
| `onGreen` | `#07120e` | `#04160f` | gallery | L236, L268, L293 |
| `box` | `rgba(0,0,0,.3)` | `rgba(0,0,0,0.4)` | gallery | L263 (segmented well) |
| `inkBg` | `rgba(0,0,0,.35)` | `rgba(0,0,0,0.38)` | gallery | L119, L275, L280 |
| `actBg` | `rgba(234,179,106,.15)` | `rgba(234,179,106,0.14)` | gallery | L108, L276 |
| `goldDim` | rendered as a `.15`→`.05` gradient, no flat equivalent | `rgba(234,179,106,0.2)` | v4 (UNVERIFIED) | L108, L276 |

Hardware colours confirmed identical (no change): `bg`, `panel2`, `surface2`, `border`, `roseDim`, `gold`, `text`, `dim`, `green`, `amber`, `sig`, `inkBorder`, `actBorder`.

### 1d. Hardware structure

| Token | Gallery value | v4 buildThemes | Taken | Gallery line(s) |
|---|---|---|---|---|
| `r.chip` | `3px` | `4px` | gallery | L228–231, L235, L236, L264, L268, L276–278 |
| `r.card` | `5px` | `6px` | gallery | L102, L107, L263, L285 |
| `r.field` | `3px` | `5px` | gallery | L264, L275, L277, L278 |
| `r.ctl` | `4px` | `5px` | gallery | L94–97, L119, L252, L253, L255, L280, L293 |
| `r.mod` | `5px` | `6px` | gallery | L285 |
| `chrome` | `linear-gradient(180deg,rgba(20,24,38,.7),rgba(10,12,22,.7))` | `linear-gradient(180deg,rgba(19,23,36,0.94),rgba(9,11,20,0.94))` | gallery | L88 |
| `pane` | `rgba(10,13,22,.96)` | `#090b13` | gallery | L285 |
| `star` | 26px instrument grid | `''` (empty) | gallery | L221 |
| topAccent gradient | `linear-gradient(90deg,#f593c1,#58c4e6)` | `linear-gradient(90deg,transparent,`+`C.blue`+`aa 20%,`+`C.blue`+`aa 80%,transparent)` | gallery | L222 |
| topAccent height | `2px` | `1px` | gallery | L222 |
| topAccent glow | none | `0 0 6px `+`C.blue`+`66` | gallery | L222 |

### 1e. Chip derivation (near-agreement, normalised)

v4's `chipEl()` (L338–341) builds chips by hex-alpha concatenation: `c.color+'24'` (= 0.141), `c.color+'0d'` (= 0.051), `c.color+'66'` (= 0.400). The gallery writes the same thing as explicit `rgba(r,g,b,.14)` / `.05` / `.4` (L146–149, L228–231). These are within rounding of each other; **the gallery's round numbers are taken** and exported as `chipFillAlpha = 0.14`, `chipFillAlphaBottom = 0.05`, `chipBorderAlpha = 0.40`, with `chipFill()` / `chipBorder()` helpers.

Note the brief's example (`C.sig+'22'`, `C.blue+'66'`) comes from v4's *selected-control* call sites (L295, L489, L563, L652), not `chipEl()`. `'22'` = 0.133; the gallery renders selected segments at `.16` celestial (L182) and `.18`→`.06` hardware (L264). Captured separately as `selectedFillAlpha`.

---

## 2. New tokens added

Values that were inline literals in v4's render code (or absent entirely) and are now named.

### 2a. Neutral ramp extensions (per theme)

Both themes render **six** neutral text tones; `buildThemes()` named only three (`text`/`dim`/`dimmer`).

| Token | Celestial | Cel. lines | Hardware | HW lines | Role |
|---|---|---|---|---|---|
| `textSoft` | `#d7d0da` | L160–164, L205 | `#c5cddd` | L242–246 | list-row labels, menu items |
| `dim2` | `#8a8090` | L32, L39, L45–48, L60, L172, L183, L184, L195, L196 | `#7f8aa2` | L82, L89, L95–97, L109, L254, L265, L266, L277, L278 | ghost buttons, inactive tabs/segments |
| `dimmest` | `#6f6480` | L75, L198 | `#5f6a86` | L111, L119, L262, L268, L280 | placeholders, "off" numerals, meta labels |
| `disabled` | `#4f4a5e` | L60, L153 | `#454e68` | L109 | non-text disabled strokes/glyphs |

Note: celestial does *not* distinguish `dimmest` from `dimmer` (both `#6f6480`); hardware does. See Ambiguity A5.

### 2b. `effects` sub-object

| Token | Celestial value | Cel. lines | Hardware value | HW lines |
|---|---|---|---|---|
| `bevelHighlight` | `inset 0 1px 0 rgba(255,255,255,0.05)` | L139 | `inset 0 1px 0 rgba(255,255,255,0.08)` | L90, L228–231 |
| `bevelHighlightStrong` | `inset 0 1px 0 rgba(255,255,255,0.12)` | (from v4 `glow()` L170; celestial has no gallery bevel) | `inset 0 1px 0 rgba(255,255,255,0.13)` | L252 |
| `bevelShadow` | `inset 0 -1px 0 rgba(0,0,0,0.32)` | (hardware-derived; celestial does not bevel) | `inset 0 -1px 0 rgba(0,0,0,0.32)` | L252, L253 |
| `bevelInset` | `inset 0 0 4px rgba(0,0,0,0.5)` | L180 | `inset 0 1px 2px rgba(0,0,0,0.4)` | L263, L275 |
| `bevelInsetDeep` | `inset 0 1px 3px rgba(0,0,0,0.5)` | — | `inset 0 1px 3px rgba(0,0,0,0.4)` | L119, L280 |
| `containerHighlight` | `inset 0 1px 0 rgba(255,255,255,0.05)` | L139 | `inset 0 1px 0 rgba(255,255,255,0.05)` | L221 |
| `containerShadow` | `0 34px 90px rgba(0,0,0,0.6)` | L139 | `0 34px 90px rgba(0,0,0,0.62)` | L221 |
| `paneShadow` | `0 16px 34px rgba(0,0,0,0.5)` | L203 | `0 16px 34px rgba(0,0,0,0.55)` | L285 |
| `glassFill` | `rgba(255,255,255,0.05)` | L171 | `linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.01))` | L116, L253 |
| `glassFillFaint` | `rgba(255,255,255,0.03)` | L75, L198 | `rgba(255,255,255,0.03)` | L95–97, L277 |
| `glassBorder` | `1px solid rgba(255,255,255,0.06)` | L139 | `1px solid rgba(255,255,255,0.07)` | L221 |
| `topAccent` | `linear-gradient(90deg,#ef92bd,#d58fd8,#5fc6d6)` | L140 | `linear-gradient(90deg,#f593c1,#58c4e6)` | L222 |
| `topAccentHeight` | `2px` | L140 | `2px` | L222 |
| `topAccentGlow` | `0 8px 14px -8px rgba(239,146,189,0.8)` | L44 | `none` | L222 |
| `star` | 9-star radial recipe | L139 | 26px two-axis grid | L221 |
| `ambient` | 3 nebula washes | L34 | 2 nebula washes | L84 |

### 2c. Glow formulas (functions of an accent colour)

| Token | Celestial | Cel. lines | Hardware | HW lines |
|---|---|---|---|---|
| `glowSm(c)` | `0 0 7px rgba(c,.6)` | L160–164 | `0 0 7px rgba(c,.7)` | L242–246 |
| `glowLg(c)` | `0 0 4px rgba(c,.85),0 0 11px 2px rgba(c,.45)` | L53, L59 | `0 0 4px rgba(c,.85),0 0 10px 2px rgba(c,.45)` | L103, L108 |
| `glowRing(c)` | `0 0 3px rgba(c,.6),0 0 9px 1px rgba(c,.4),inset 0 0 4px rgba(c,.3)` | L64 | same | L111 |
| `glowText(c)` | `0 0 3px rgba(c,.9),0 0 9px rgba(c,.65)` | L60 | same | L109 |
| `glowToast(c)` | `0 0 18px rgba(c,.5)` | L211 | `0 0 16px rgba(c,.45)` | L293 |
| `glowButton(c)` | `0 0 16px rgba(c,.24)` | L170 | `0 0 14px rgba(c,.2)` | L115, L252 |

v4 had a single `glow(col)` (L170) covering all of these with one formula per theme. The gallery uses six distinct ones.

### 2d. Other additions

| Token | Value | Source |
|---|---|---|
| `chipFillAlpha` / `chipFillAlphaBottom` / `chipBorderAlpha` | `0.14` / `0.05` / `0.40` | L146–149, L228–231 |
| `selectedFillAlpha` | `{ celestial: 0.16, hardware: 0.18 }` | L182, L264 |
| `panelBackground(mode)` | hardware card gradient | L102, L107 |
| `typeRamp` | 5 hues per theme | L160–164, L242–246 |
| `alpha()` / `rgbTriplet()` / `chipFill()` / `chipBorder()` | helpers | — |

---

## Ambiguities

**These need a human decision. Nothing below was silently resolved.**

### A1 — Hardware `rose`: `#f593c1` or `#f6aecd`?

The hardware kit uses `#f593c1` everywhere an accent is *lit* (L115, L222, L229, L252, L286, L294 — 10 occurrences). But the hardware phone's "why this matters" note body is `#f6aecd` (L105), which is exactly the v4 value, and its eyebrow is `#c98caa` (= `roseDim`). So `#f6aecd` may be a deliberate *body-text* rose distinct from the accent rose, rather than a stale value.

- Taken: `#f593c1` (kit is the acceptance reference).
- **Question:** is `#f6aecd` a second token (`roseText`?) or a leftover? A third value `#f2a0c4` (L132, L310) exists but is page-header chrome, not theme.

### A2 — Hardware `blue`, `teal`, `purple`, `orange` have competing or no evidence

| Token | v4 | Candidates in the gallery | Lines |
|---|---|---|---|
| `blue` | `#49ade0` | `#3aa0da` (card accent bar + project dot, phone) vs `#4f7fe6` (TASK dot, structure ramp) | L102, L103 vs L244 |
| `teal` | `#56c9d6` | `#45cfc0` (RECURRING dot) vs `#49c8d6` (page-header gradient only — chrome, not theme) | L245 vs L132/L310 |
| `purple` | `#b98aec` | none in 4c/5c. `#c9a2e0` appears only in page-header gradient chrome; `#b8b0c8` is a menu neutral | — |
| `orange` | `#e2915a` | none in 4c/5c at all | — |

- Taken: `#3aa0da` for `blue`, `#45cfc0` for `teal`; `purple` and `orange` left at their v4 values and marked UNVERIFIED.
- **Question:** the structure-ramp dots may be a *separate* ramp (see A6) rather than the theme's `blue`/`teal`. If so `blue` should stay `#49ade0` and `teal` `#56c9d6`. This one decision flips four tokens.

### A3 — Celestial `gold` / `amber`: `#f0b46a` never appears

v4 has both `amber: '#f0b46a'` and `orange: '#f0a86a'` in celestial. The gallery renders `#f0a86a` in *every* place `amber`/`gold` would be used — the "4h chunk" duration chip (L59), the "Open" tag (L148), "Needs clarifying" (L152), the "week" recurrence unit (L194). `#f0b46a` appears nowhere in 4a or 5a.

- Taken: `#f0a86a` for `gold`, `amber` and `orange`, collapsing three tokens onto one hue.
- **Question:** did the tuning intentionally collapse gold/amber/orange in celestial, or was `#f0b46a` simply never exercised? If intentional, `gold`/`amber` should probably be deleted as aliases rather than kept as duplicate keys. `goldDim`'s alpha (`0.22`) has no gallery witness either way.

### A4 — Both themes' `on` colour is rendered as three different values

| Theme | Values | Lines | Context |
|---|---|---|---|
| Celestial | `#14101a` / `#070513` / `#050410` | L154 / L141 / L32 | solid chip label / kit badge / section badge |
| Hardware | `#07080f` / `#03030b` | L223 / L82 | kit badge / section badge |

The section badges (L32, L82) sit on the gallery *page*, not inside the mockup, so they are weaker evidence. Celestial's `#070513` is also the 5a kit's own container base (see A8), which may make it coincidental.

- Taken: `#14101a` (celestial, L154 — the only true in-component solid chip) and `#07080f` (hardware, L223).
- **Question:** confirm celestial `on` = `#14101a` and not `#070513`.

### A5 — The neutral ramp is not 1:1 across the two themes

Celestial uses `#6f6480` for *both* section captions (L144, L158, L190, L202, L209) and input placeholders (L75, L198). Hardware splits these: `#6f7a92` for captions (L101, L226, L240, …) and `#5f6a86` for placeholders (L119, L280).

- Taken: `dimmer` = caption tone in both (`#6f6480` / `#6f7a92`), `dimmest` = placeholder tone (`#6f6480` / `#5f6a86`), so celestial's two are identical.
- **Question:** should celestial gain a distinct placeholder tone to match hardware's structure, or should hardware collapse to one? As it stands celestial `dimmer === dimmest`, which is a smell.

### A6 — The object-type ramp contradicts v4's `TYPE` map

v4 (L168) maps `GOAL→amber, PROJECT→blue, TASK→green, RECURRING→orange, STRATEGY→strategy`. The gallery's "structure ramp" rows use an entirely different, cooler set:

| | GOAL | PROJECT | TASK | RECURRING | STRATEGY |
|---|---|---|---|---|---|
| Celestial (L160–164) | `#9fe0e8` | `#5fc6d6` | `#3f8fd0` | `#4fb8a6` | `#d58fd8` |
| Hardware (L242–246) | `#9be2f0` | `#58c4e6` | `#4f7fe6` | `#45cfc0` | `#d071d8` |

Only `STRATEGY` agrees. `GOAL` is a pale cyan in both, not amber. `TASK` is blue, not green — yet the gallery *also* renders task completion controls in green (L60, L64, L109, L111).

- Taken: exported verbatim as a separate `typeRamp`, **not** merged into the theme colours.
- **Question:** is this ramp meant to replace `TYPE`, or is it a distinct "structure depth" indicator that coexists with the type colours? This determines whether `blue`/`teal` in A2 are even in play.

### A7 — Three different starfields

1. `5a` kit container (L139): 9 stars + 2 nebula washes over `#070513`.
2. `4a` phone body (L34): a ~200-star procedurally generated field (14 kB of CSS) over `#060512`, with 7 large soft blooms.
3. v4 `star` token: a hand-authored 26-star recipe.

- Taken: the `5a` recipe as `star`, the `4a` washes as `ambient`.
- **Question:** the phone (4a) is the real app surface and its field is far denser than either alternative. If that density is the tuned look, `star` should be generated at runtime rather than stored as a literal. Flagging rather than inlining 14 kB.

### A8 — Celestial `bg`: `#060512` (phone) vs `#070513` (kit container)

The 4a phone body sits on `#060512`; the 5a kit container sits on `#070513`. Both are inside trusted regions. Neither matches v4's `#0a0812`.

- Taken: `#060512` (the phone is the app surface; the kit container is gallery furniture).
- **Question:** confirm. The difference is ~1/255 per channel and may be incidental.

### A9 — Celestial `r.card` and `chrome` have no clean witness

Celestial cards in the phone mockup are borderless (rows on the background), so no card radius is rendered. Nearest evidence: the "why this matters" note box at `13px` (L55) and the menu at `14px` (L203). Similarly the celestial header (L39–43) is fully transparent over the starfield with only a `rgba(255,255,255,.06)` bottom hairline — there is no chrome fill to read.

- Taken: v4's `16px` and `rgba(12,8,22,0.4)`, both marked UNVERIFIED.
- **Question:** should celestial cards be `13px`, and is the celestial chrome genuinely transparent (in which case `chrome` should be `'transparent'`, not a tinted glass)?

### A10 — Celestial `horizon`, `box`; hardware `horizon`

`horizon` (`#9fb4cf` / `#8fa6c8`) appears nowhere in any of the four trusted regions, in either theme. Celestial `box` (`rgba(0,0,0,0.28)`) likewise has no flat-well counterpart — the celestial surfaces that would use it are white veils (`rgba(255,255,255,.03–.05)`), and the only celestial blacks are shadow/inset values at `.5`/`.6`.

- Taken: v4 values kept, marked UNVERIFIED.
- **Question:** are these still live tokens, or dead keys that should be dropped from the shape?

### A11 — Celestial chip alphas differ between phone and kit

The kit renders accent chips at `.14` fill / `.4` border (L146–149, L194). The phone renders the same conceptual chip at `.11`/`.36` (L59, "4h chunk") and the primary button at `.12`/`.42` (L70) vs the kit's `.14`/`.45` (L170).

- Taken: kit values (per the brief, the kits are the acceptance reference).
- **Question:** the phone consistently sits ~2 points lower. If the phone is the truer render, every chip alpha shifts down. Low stakes visually, but it is a systematic offset, not noise.

---

## Coverage note

The gallery contains **695 hex literals** (181 distinct) and **666 `rgba()` literals**.

| Region | Hex occurrences | Distinct |
|---|---|---|
| `4a` (L31–80) | 41 | 16 |
| `4c` (L81–138) | 55 | 28 |
| `5a` (L139–220) | 66 | 22 |
| `5c` (L221–296) | 73 | 25 |
| **Trusted total** | **235 (34%)** | **74** |

Of the 74 distinct hexes in trusted regions, **68 (≈92%) resolve to a token** in `tokens.ts` (including `typeRamp`). The 6 that do not are: `#241826` and `#10202a` (the phone-bezel hairline rings, L33/L83 — device frame, not app chrome), `#000` (the phone bezel itself), and three page-header gradient stops that bleed into the region boundary (`#f2a0c4`, `#c9a2e0`, `#7fb2f5` at L132).

The remaining **460 hex occurrences (66%)** lie outside the trusted regions: sections `1a/1b`, `2a/2b`, `3a/3b/3c` (the superseded ~10-hue explorations the page itself describes as cut back, ~L605), plus the gallery's own page chrome — section headings, gradient display type, prose, and inter-section links. These are demo/historical content and are correctly not represented in the token set.

Alpha coverage is looser by nature: the `rgba()` literals are dominated by the 4a starfield (well over 300 of the 666 are individual star stops in the L34 procedural field), which is captured as one `star`/`ambient` recipe rather than per-stop tokens.

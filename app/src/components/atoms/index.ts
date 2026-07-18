/**
 * Visual primitives ported from `design/mockups/review-reorganize-mobile-v4.html`.
 *
 * Styles are INLINE STYLE OBJECTS reading from the token module, deliberately. Do not convert
 * them to CSS classes, CSS variables, styled-components or a `css` prop — that translation is
 * exactly where the finetuned detail leaks. See
 * `docs/handoff_2026-07-17_surface_rebuild.md` §"The load-bearing build decisions".
 *
 * Every component takes the theme as a `T` prop rather than calling `useTheme()` itself:
 * `useTheme` holds its own `useState`, so per-component calls would each own an independent
 * copy of the theme and the switcher would only move one of them.
 */
export { appBg, bevel, glow } from './effects';
export { TopAccent } from './TopAccent';
export type { TopAccentProps } from './TopAccent';
export { TaskCheck } from './TaskCheck';
export type { TaskCheckProps } from './TaskCheck';
export { Switch } from './Switch';
export type { SwitchProps } from './Switch';
export { Badge } from './Badge';
export type { BadgeProps } from './Badge';
export { Rail } from './Rail';
export type { RailProps } from './Rail';
export { Chip } from './Chip';
export type { ChipProps, ChipValue } from './Chip';
export { RoundCheck } from './RoundCheck';
export type { RoundCheckProps } from './RoundCheck';
export { EditChip } from './EditChip';
export type { EditChipProps } from './EditChip';
export { typeColor } from './typeColor';
export type { TypeLevel } from './typeColor';

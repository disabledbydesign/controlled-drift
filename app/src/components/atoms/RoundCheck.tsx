import type { Theme } from "@tokens";
import { TaskCheck } from "./TaskCheck";

export interface RoundCheckProps {
  T: Theme;
  done: boolean;
  onClick: () => void;
}

/**
 * v4 `roundCheck(done,onClick)` (~1042) — Today's round checkbox.
 *
 * Not a separate visual: it is a bare button wrapping `TaskCheck` at the rose accent and
 * size 15. Size 15 is below the 17 threshold, so the hardware variant takes the 3px radius
 * and the 1.5px border — that is why this reads smaller and tighter than a tree checkbox.
 *
 * `top:'2px'` is v4's optical nudge to sit the box on the first text line.
 * `stopPropagation` keeps the click off the surrounding row.
 *
 * ── tap-target expansion (2026-07-18, TRIAL — revert if it misbehaves) ───────
 * The glyph stays 15px: v4's value, and below the 17 threshold that would flip the hardware
 * variant's radius and border. Only the *hit area* grows, via padding cancelled by an equal
 * negative margin, so no caller's layout shifts.
 *
 * Vertical padding is capped at 5px ON PURPOSE. `TaskRow` stacks rows on a ~26px pitch
 * (13px text at 1.35, plus 9px `marginBottom`), so a taller target would overlap the
 * neighbouring row — and because a tap here completes a task with no undo, an overlapping
 * target would cause exactly the mis-completion this change is meant to reduce. Reaching the
 * 44px guideline needs looser row spacing first; that is a visual-density decision, not this one.
 */
export function RoundCheck({ T, done, onClick }: RoundCheckProps) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      aria-label="mark done"
      aria-pressed={done}
      style={{
        flex: "0 0 auto",
        border: "none",
        background: "none",
        cursor: "pointer",
        padding: "5px 10px",
        margin: "-5px -10px",
        position: "relative",
        top: "2px",
        display: "flex",
      }}
    >
      <TaskCheck T={T} done={done} col={T.c.rose} size={15} />
    </button>
  );
}

import type { Theme } from '@tokens';
import { TaskCheck } from './TaskCheck';

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
 */
export function RoundCheck({ T, done, onClick }: RoundCheckProps) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      aria-label="mark done"
      style={{
        flex: '0 0 auto',
        border: 'none',
        background: 'none',
        cursor: 'pointer',
        padding: 0,
        position: 'relative',
        top: '2px',
        display: 'flex',
      }}
    >
      <TaskCheck T={T} done={done} col={T.c.rose} size={15} />
    </button>
  );
}

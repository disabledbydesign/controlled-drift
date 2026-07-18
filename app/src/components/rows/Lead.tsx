import type { Theme } from '@tokens';
import { Switch, TaskCheck } from '../atoms/index.ts';
import { toggleActive, toggleDone } from '../../model/index.ts';
import type { ModelNode } from '../../model/index.ts';
import { D } from './types.ts';
import type { RowCtx } from './types.ts';

/**
 * v4 `recSwitch(n)` (~394) — the leading control on a RECURRING row.
 *
 * A recurring item is either SCHEDULED (repeats on a cadence) or AS-NEEDED (no cadence; it is
 * simply open or closed). v4 renders those as two different controls, not one control
 * recoloured:
 *   · as-needed → a small dot with a text label under it, teal, pulsing while open
 *   · scheduled → the shared `switchEl` pill/LED, orange
 *
 * ⚠ The `openpulse` keyframe this branch names is NOT in `app/index.html` (only navfwd,
 * navback, slidein, slideout, panelin, savedpulse, ringpulse are). An unknown animation name
 * is ignored by CSS, so the dot renders correctly but does not pulse. Reported, not fixed —
 * `index.html` is outside this task's file scope. See the task report.
 */
function RecSwitch({ T, n }: { T: Theme; n: ModelNode }) {
  const C = T.c;
  const act = !n.vals.paused;
  const asNeeded = n.vals.unit === 'as_needed';
  const col = asNeeded ? C.teal : C.orange;

  if (asNeeded) {
    return (
      <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px' }}>
        <span
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: act ? col : 'transparent',
            border: '1.5px solid ' + (act ? col : C.dimmer),
            color: col,
            boxShadow: act ? '0 0 0 3px ' + col + '22, 0 0 9px ' + col : 'none',
            animation: act ? 'openpulse 1.8s ease-in-out infinite' : 'none',
          }}
        />
        <span
          style={{
            fontSize: '7px',
            fontWeight: 800,
            letterSpacing: '.06em',
            fontFamily: T.mono,
            color: act ? col : C.dimmer,
          }}
        >
          {act ? 'OPEN' : 'OFF'}
        </span>
      </span>
    );
  }
  return <Switch T={T} on={act} col={col} />;
}

export interface LeadProps {
  ctx: RowCtx;
  n: ModelNode;
  expandable: boolean;
  open: boolean;
  onExpand?: (() => void) | undefined;
}

/**
 * v4 `lead(n,expandable,open,onExpand)` (~385) — the leading element of a row.
 *
 * FOUR MUTUALLY EXCLUSIVE BRANCHES, in v4's order. The order is the semantics: expandable is
 * tested FIRST, so an expandable TASK would show a chevron rather than its checkbox. (No call
 * site does that today — `treeBody` sets `canDrill` false for TASK and RECURRING — but the
 * precedence is v4's and is preserved rather than reasoned away.)
 *
 *   1. expandable  → 24px chevron button, rotated 90° when open
 *   2. TASK        → 24px checkbox (`TaskCheck`), toggles done
 *   3. RECURRING   → 40px `RecSwitch`, toggles paused. Note the WIDER well: 40px, not 24px.
 *   4. otherwise   → a 24px inert spacer, so every row's text starts on the same line
 *
 * Every branch stops propagation: the lead control must not also fire the row's `onTap`.
 *
 * The theme SHAPE forks live inside `TaskCheck` and `Switch` (round+glow vs square+bevel);
 * `lead` itself is theme-neutral apart from the mono label in `RecSwitch`.
 */
export function Lead({ ctx, n, expandable, open, onExpand }: LeadProps) {
  const { T } = ctx;
  const C = T.c;

  if (expandable) {
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (onExpand) onExpand();
        }}
        aria-label="expand"
        style={{
          width: '24px',
          minHeight: D.leadH,
          flex: '0 0 auto',
          border: 'none',
          background: 'none',
          color: C.dim,
          cursor: 'pointer',
          padding: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <svg
          width={15}
          height={15}
          viewBox="0 0 24 24"
          fill="none"
          style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }}
        >
          <path
            d="M9 6l6 6-6 6"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    );
  }

  if (n.level === 'TASK') {
    const done = !!n.vals.done || n.vals.status === 'Done';
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          ctx.apply(toggleDone(ctx.graph, n.id));
        }}
        aria-label="mark done"
        style={{
          width: '24px',
          minHeight: D.leadH,
          flex: '0 0 auto',
          border: 'none',
          background: 'none',
          cursor: 'pointer',
          padding: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <TaskCheck T={T} done={done} col={C.green} size={19} />
      </button>
    );
  }

  if (n.level === 'RECURRING') {
    const act = !n.vals.paused;
    const asNeeded = n.vals.unit === 'as_needed';
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          ctx.apply(toggleActive(ctx.graph, n.id));
        }}
        aria-label={act ? 'pause in plan' : 'activate in plan'}
        title={
          act
            ? asNeeded
              ? 'Open — tap to close'
              : 'In plan — tap to pause'
            : asNeeded
              ? 'Closed — tap to open'
              : 'Paused — tap to add to plan'
        }
        style={{
          width: '40px',
          minHeight: D.leadH,
          flex: '0 0 auto',
          border: 'none',
          background: 'none',
          cursor: 'pointer',
          padding: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <RecSwitch T={T} n={n} />
      </button>
    );
  }

  return <span style={{ width: '24px', flex: '0 0 auto' }} />;
}

import { FocusEditor } from './FocusEditor.tsx';
import { NAV } from './types.ts';
import type { FocusCtx } from './types.ts';

export interface FocusOverlayProps {
  ctx: FocusCtx;
  /** v4's `st.detail==='__focus__'` — the shell owns the detail route, so it decides. */
  open: boolean;
}

/**
 * v4 `focusDetail()` (813) — the full-bleed pane the focus editor renders into.
 *
 * v4 reaches it from inside `detail(id)` (541): `if(id==='__focus__') return this.focusDetail()`.
 * Here it is a sibling of `DetailOverlay` in the shell instead, and `Detail.tsx` keeps its
 * existing `if (id === '__focus__') return null` guard. The reason is the CONTEXT split: the
 * focus editor needs `periods` and `applyPeriods`, which `DetailCtx` does not carry and must
 * not start carrying — `DetailCtx` is the object-editor's contract. Same z-index (30), same
 * `slidein` animation, same absolute fill, so the rendered result is v4's.
 *
 * ⚠ NO TWO-PHASE CLOSE. `DetailOverlay` keeps the object pane mounted for 260ms so its
 * slide-OUT can play; v4's focus editor has no equivalent — its `‹ Back` sets `detail:null`
 * directly (888) and never calls `closeDetail()`, so the pane just disappears. Preserved.
 */
export function FocusOverlay({ ctx, open }: FocusOverlayProps) {
  if (!open) return null;
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: ctx.T.pane,
        backdropFilter: ctx.T.paneBlur,
        WebkitBackdropFilter: ctx.T.paneBlur,
        overflowY: 'auto',
        animation: 'slidein ' + NAV,
        zIndex: 30,
      }}
    >
      {/* v4:813 — the ONLY reader of `focusView`: 'author' gets the author flow, everything
          else (including a stale 'list') gets the edit form. */}
      <FocusEditor ctx={ctx} view={ctx.ui.focusView === 'author' ? 'author' : 'edit'} />
    </div>
  );
}

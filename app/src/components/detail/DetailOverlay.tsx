import { useCallback, useEffect, useRef, useState } from 'react';
import { Detail } from './Detail.tsx';
import type { DetailCtx } from './types.ts';

export interface DetailOverlayProps {
  ctx: DetailCtx;
}

/** v4's `closeDetail` timeout (~306): `setTimeout(…, 260)` against a .26s animation. */
const CLOSE_MS = 260;

/**
 * The detail editor's mount point — v4's `renderShell()` overlay slot (929) plus
 * `closeDetail()` (~306).
 *
 * ── WHY THE CLOSE IS TWO-PHASE ───────────────────────────────────────────────
 * v4:
 *   closeDetail(){ const id=this.st.detail; if(!id||this.st.detailClosing)return;
 *     this.up({detailClosing:id, moveFor:null, menuFor:null, chipEdit:null, headerTypeOpen:false});
 *     clearTimeout(this._closeT);
 *     this._closeT=setTimeout(()=>this.up({detail:null,detailClosing:null,_returnFrom:null}),260); }
 *
 * The pane cannot unmount on the tap, because the slide-out animation has to play on an
 * element that still exists. So `detailClosing` keeps it mounted, running `slideout … forwards`
 * for 260ms, and only then is `detail` cleared. The `if(this.st.detailClosing) return` guard is
 * what stops a second tap restarting the timer and stranding the pane.
 *
 * `detailClosing` is LOCAL here rather than in the shared UI bag: it is a property of this
 * overlay's animation, nothing else reads it, and holding it in shell state would mean every
 * consumer of `UiState` has to know that `detail` being set does not mean the pane is open.
 * The `moveFor`/`menuFor`/`chipEdit` clears do go through `up`, because those are shared.
 *
 * ── the tab-change interaction ───────────────────────────────────────────────
 * `AppShell` clears `detail` on every tab change (v4:954). That bypasses this component's
 * close sequence entirely — the pane just unmounts, with no slide-out. That is v4's behaviour
 * too (its `up({detail:null})` from the tab handler does not go through `closeDetail`), so it
 * is preserved. The effect below resets the local closing flag when `detail` changes underneath
 * it, so a pane closed that way does not leave the flag armed for the next object.
 */
export function DetailOverlay({ ctx }: DetailOverlayProps) {
  const { ui, up } = ctx;
  const id = ui.detail;
  const [closing, setClosing] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // If `detail` changes by any route other than `onClose` (tab change, delete, a mutation's
  // `ui` patch), drop the stale closing flag.
  useEffect(() => {
    if (closing && closing !== id) setClosing(null);
  }, [id, closing]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const onClose = useCallback(() => {
    if (!id || closing) return; // v4's re-entry guard
    setClosing(id);
    up({ moveFor: null, menuFor: null, chipEdit: null });
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setClosing(null);
      up({ detail: null, returnFrom: null });
    }, CLOSE_MS);
  }, [id, closing, up]);

  if (!id) return null;
  return <Detail ctx={ctx} id={id} closing={closing === id} onClose={onClose} />;
}

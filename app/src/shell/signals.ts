/**
 * THE ONE PLACE THAT DECIDES HOW A SIGNAL IS SHOWN.
 *
 * ── why this file exists ─────────────────────────────────────────────────────
 * June, 2026-07-18: *"I tend to hate validation toasts that pop up at the bottom and say
 * 'done' — and I may want to cut that out later or make it more subtle. So let's make sure
 * it's easy to do that. What matters more is error logging if something fails, and UI that
 * provides intuitive feedback of 'this worked' or 'this didn't work' without necessarily
 * needing text."*
 *
 * So the two directions are NOT symmetrical:
 *
 *   SUCCESS  quiet, and AT THE CONTROL the user just touched. She already knows what she did;
 *            she needs to know it landed, not to read a sentence about it. Default presentation
 *            is `inline` — a brief settle on the affected row — and for most writes even that is
 *            redundant, because the chip re-renders with the new value or the title strikes
 *            through. Nothing appears at the bottom of the screen.
 *
 *   FAILURE  loud, textual, names what did not save, and STAYS until dismissed. A silent failure
 *            in a system whose whole promise is "you never have to wonder if it saved" is the
 *            worst outcome available, so this one does not fade.
 *
 * ── how to change or remove success feedback ─────────────────────────────────
 * Edit `present()` below. Nothing else in the app decides presentation: every component asks
 * this function. Concretely —
 *   - success should show NOTHING at all      → return `{ mode: 'none' }` for `success`
 *   - success should show the bottom bar again → return `{ mode: 'bar', persist: false }`
 *   - failure should be a modal instead of a bar → add a `mode` and handle it in `SignalBar`
 * There is no second place to hunt. `SignalBar` renders whatever `present()` names; `Row` reads
 * `mode === 'inline'` and nothing else.
 *
 * ── the dev-verbose escape hatch ─────────────────────────────────────────────
 * *"the more textual toast probably is useful for dev time."* — so the verbose bar survives, as
 * OPT-IN, off by default, and deliberately not a Settings row: it is a developer affordance, not
 * one of June's controls, and putting it in Settings would make the quiet default look like a
 * preference she has to maintain. Turn it on in the console with
 * `localStorage.setItem('cd.verboseSignals','1')`, or load the page with `?verbose=1`.
 */

/**
 * What kind of thing happened. Failure is not a louder success; it is a different case.
 *
 * `notice` is the THIRD case, added for the focus write path: the server declined a write
 * because a required field is still empty ("you have not put an end date in yet"). That is
 * neither of the other two. It is not a success — nothing was written, and unlike a success its
 * result is invisible at the control, so it has to be read. It is not a failure either — nothing
 * broke, and routing it through `fail` would both address her as if something had gone wrong and
 * fill the error log with non-defects.
 */
export type SignalKind = 'success' | 'failure' | 'notice';

/**
 * One thing the app has to tell the user about.
 *
 * `seq` is what makes two identical messages in a row distinguishable — without it, saving the
 * same field twice produces an unchanged state object and React never re-renders, so the second
 * confirmation is invisible. It was already on the state shape before this task; it is only
 * documented here now that something actually reads it.
 *
 * `nodeId` is the "target" — which object the signal is ABOUT, so an inline success can settle
 * on that row rather than somewhere generic. Null when the signal has no single object behind
 * it (a plan regeneration, a period save).
 *
 * `hold` says: THE RESULT OF THIS IS NOT VISIBLE AT THE CONTROL, so the text is the only thing
 * carrying it and it must not fade. Only the raiser of a signal can know that, which is why it
 * is data on the signal rather than a rule inside `present()` — but `present()` is still the only
 * thing that turns it into a presentation. It matters for `notice` and nothing else: a failure
 * persists regardless, and a success is quiet regardless.
 *
 * Concretely, the two notices differ exactly here. The focus-period notice ("you have not put an
 * end date in yet") holds: nothing on screen changed, so if the sentence fades she believes the
 * write landed. A refusal does NOT hold, because the control it came from reverts to the stored
 * value in the same breath — the screen already tells the truth, and the sentence is there to
 * explain it, not to protect her from a wrong screen.
 */
export interface Signal {
  kind: SignalKind;
  msg: string;
  seq: number;
  nodeId: string | null;
  hold?: boolean;
}

/** How a signal should be presented. The only vocabulary the render layer understands. */
export interface Presentation {
  /**
   * `none`   — show nothing; an in-place affordance already carries it.
   * `inline` — settle the row the signal is about. No text.
   * `bar`    — the bottom bar, with the message.
   */
  mode: 'none' | 'inline' | 'bar';
  /** `bar` only: stay until dismissed rather than fading. */
  persist: boolean;
  /** `bar` only: milliseconds before auto-dismiss. Ignored when `persist`. */
  ms: number;
}

/**
 * Whether the verbose textual bar is on. Read at call time rather than captured, so flipping the
 * flag in the console and re-rendering takes effect without a reload.
 *
 * Guarded for a missing `localStorage` / `location`: the component tests run in jsdom without
 * either in some configurations, and a signal-presentation question must never be the thing that
 * throws.
 */
export function verboseSignals(): boolean {
  try {
    if (typeof localStorage !== 'undefined' && localStorage.getItem('cd.verboseSignals') === '1') {
      return true;
    }
    if (typeof location !== 'undefined' && location.search.includes('verbose=1')) return true;
  } catch {
    // Private-mode Safari throws on localStorage access. Quiet default is the right fallback.
  }
  return false;
}

/**
 * THE SEAM. Signal in, presentation out.
 *
 * Success is `inline` and not `bar`, deliberately — see the header. Note that `inline` is
 * itself close to invisible for most writes and that is the point: for a chip edit the chip has
 * already re-rendered with the new value, and the settle is a confirmation of the same fact, not
 * a second one. It earns its place on the writes whose result is NOT visible at the control
 * (a move, where the row leaves the list you were looking at).
 */
export function present(sig: Signal): Presentation {
  if (sig.kind === 'failure') {
    // Textual, and it does not go away on its own. A silent failure is the worst outcome
    // available in a system whose promise is "you never have to wonder if it saved".
    return { mode: 'bar', persist: true, ms: 0 };
  }
  if (sig.kind === 'notice') {
    /**
     * A notice is always TEXTUAL — it has to be read, which is the whole reason it is not a
     * success. What varies is whether it stays.
     *
     * HOLDING notice: its result is invisible at the control (a period the server declined
     * because a date is still empty). Nothing on screen changed, so a bar that fades leaves her
     * believing the write landed. Persist.
     *
     * FADING notice — refusals and instructions: June, 2026-07-20, on a duration box that kept
     * displaying a value the server had refused — *"if a change can't be made, the UI content
     * needs to show what's really in the data — that's essential."* Once the control reverts to
     * the stored value, the screen is already truthful and the sentence is explanation. It may
     * fade. 5s, not the 900ms of the success timing, which is far too short to read a sentence.
     */
    if (sig.hold) return { mode: 'bar', persist: true, ms: 0 };
    return { mode: 'bar', persist: false, ms: 5000 };
  }
  if (verboseSignals()) {
    // Dev mode: v2/v3's green pill, 1.6s, exactly as those mockups had it before v4 stubbed
    // `toast()` to `return null` (v2/v3 line 321).
    return { mode: 'bar', persist: false, ms: 1600 };
  }
  return { mode: 'inline', persist: false, ms: 900 };
}

import type { Theme } from '@tokens';
import { CAPTURE_PROJECT_ID, capture as captureMutation, node as findNode } from '../model/index.ts';
import type { Graph, GraphIndex, MutationResult } from '../model/index.ts';
import type { LogTag, ReceiptEntry } from '../shell/useAppState.ts';

/**
 * The Add / Log tab — v4 `addLogTab()` (1108), `captureTab()` (1109), `logTab()` (1126) and
 * `capture()` (1136, ported to `model/mutations.ts`).
 *
 * All three v4 methods live in one file because `captureTab` and `logTab` have exactly one
 * caller each (`addLogTab`), and `addLogTab` has exactly one (the shell's tab switch, v4:935).
 * Splitting them across three modules would add importers without adding a seam.
 *
 * Styles are INLINE STYLE OBJECTS, transcribed from v4. Do not lift them into classes or
 * variables — see `components/atoms/index.ts` for why.
 */

/** The slice of the UI bag this tab reads. `UiState` satisfies it structurally. */
export interface AddUi {
  addText: string;
  logText: string;
  logTag: LogTag;
  receipt: readonly ReceiptEntry[];
}

export interface AddCtx {
  T: Theme;
  graph: Graph;
  idx: GraphIndex;
  ui: AddUi;
  up: (patch: Partial<AddUi>) => void;
  apply: (result: MutationResult) => void;
  /**
   * v4's `up({detail:r.id,_returnFrom:'add'})` (v4:1121), behind a callback for the same
   * reason `TodayCtx` does it: `detail` and `returnFrom` are shell-wide ROUTING state, and
   * putting them in `AddUi` would let this tab write the router.
   */
  openDetail: (id: string) => void;
  /** v4's `flash(msg)` with no model change behind it. */
  flash: (msg: string) => void;
  /**
   * The Log button's real write. Resolves `true` only once the server has confirmed, so the
   * text box is cleared on a proven save and never on a dropped one.
   */
  logDay: (text: string, tags: string[]) => Promise<boolean>;
}

export function AddScreen({ ctx }: { ctx: AddCtx }) {
  const C = ctx.T.c;
  // v4:1108 — the two halves are separated by an 8px band of page background with a top rule.
  return (
    <div>
      <CaptureTab ctx={ctx} />
      <div style={{ height: '8px', borderTop: '1px solid ' + C.border, background: C.bg }} />
      <LogTab ctx={ctx} />
    </div>
  );
}

/** v4 `captureTab()` (1109). */
function CaptureTab({ ctx }: { ctx: AddCtx }) {
  const { T, ui } = ctx;
  const C = T.c;

  /**
   * v4's `capture()` split in two: the model mutation files the task, and the receipt is
   * composed here from the returned node. The destination title is read BEFORE `apply`, off
   * the pre-mutation graph — the node is the same object either way, and `ctx.graph` is still
   * the old reference at this point in the handler.
   */
  const onCapture = () => {
    const res = captureMutation(ctx.graph, ui.addText);
    if (!res.node) return; // empty input, or the destination project is missing
    const project = findNode(ctx.idx, CAPTURE_PROJECT_ID)?.title ?? '';
    const entry: ReceiptEntry = { id: res.node.id, text: res.node.title, project };
    ctx.apply(res); // carries v4's `up({addText:''})` and the 'Sorted into …' toast
    ctx.up({ receipt: [entry, ...ui.receipt] }); // v4:1140 — newest first
  };

  return (
    <div>
      <div style={{ padding: '14px 14px 10px' }}>
        <div style={EYEBROW(C.dimmer)}>add a task, or dump a tangle to sort</div>
        <div style={{ display: 'flex', gap: '7px', alignItems: 'flex-end' }}>
          <textarea
            value={ui.addText}
            placeholder={'e.g. call the surgeon’s office, and I keep meaning to meditate daily…'}
            onChange={(e) => ctx.up({ addText: e.target.value })}
            style={{
              flex: 1,
              background: C.inkBg,
              border: '1px solid ' + C.inkBorder,
              borderRadius: T.r.field,
              color: C.gold,
              fontSize: '13px',
              fontFamily: 'inherit',
              padding: '7px 10px',
              resize: 'none',
              minHeight: '150px',
              lineHeight: 1.4,
              outline: 'none',
            }}
          />
          <button onClick={onCapture} style={ACTION_BUTTON(T)}>
            + Add
          </button>
        </div>
        <div
          style={{
            fontSize: '10.5px',
            color: C.dimmer,
            marginTop: '7px',
            lineHeight: 1.4,
            opacity: 0.85,
          }}
        >
          It sorts what you write into the right places and links it to your work. Tap an item
          below to edit or re-file it in the Map.
        </div>
      </div>

      <div style={{ padding: '4px 14px 16px' }}>
        {/* v4:1117 — same eyebrow, but `margin:'6px 0 7px'` rather than `marginBottom:'7px'`. */}
        <div
          style={{
            fontSize: '10px',
            color: C.dimmer,
            textTransform: 'uppercase',
            letterSpacing: '.08em',
            margin: '6px 0 7px',
          }}
        >
          added this session
        </div>
        {ui.receipt.length ? (
          ui.receipt.map((r, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'baseline',
                gap: '8px',
                padding: '7px 0',
                borderBottom: '1px solid ' + C.hair,
              }}
            >
              <span style={{ color: C.rose, flex: '0 0 auto' }}>✓</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '12px', color: C.text, lineHeight: 1.4 }}>{r.text}</div>
                <div style={{ fontSize: '11px', color: C.dimmer, marginTop: '2px' }}>
                  sorted into <span style={{ color: C.dim }}>{r.project}</span>
                </div>
              </div>
              <button
                onClick={() => ctx.openDetail(r.id)}
                style={{
                  flex: '0 0 auto',
                  background: 'none',
                  border: '1px solid ' + C.border,
                  borderRadius: T.r.card,
                  color: C.dim,
                  fontSize: '11px',
                  fontFamily: 'inherit',
                  padding: '3px 11px',
                  cursor: 'pointer',
                }}
              >
                edit
              </button>
            </div>
          ))
        ) : (
          <div style={{ fontSize: '12px', color: C.dimmer, opacity: 0.7, lineHeight: 1.4 }}>
            {'Nothing yet today. What’s on your mind?'}
          </div>
        )}
      </div>
    </div>
  );
}

/** v4's two log tags, in v4's order (v4:1130). Hardcoded there, not schema-driven. */
const LOG_TAGS: readonly LogTag[] = ['The day', 'Friction'];

/**
 * Her label -> the tag `/api/logday` stores. The server keeps only `"day"` and `"issue"` and
 * silently substitutes `["day"]` for anything else, so a wrong mapping here would file every
 * friction entry as a day entry — losing exactly the issue-tagged subset the triage passes read.
 */
const TAG_WIRE: Record<LogTag, string> = { 'The day': 'day', Friction: 'issue' };

/**
 * v4 `logTab()` (1126).
 *
 * ── WIRED 2026-07-18 ────────────────────────────────────────────────────────
 * Previously ported as-is from v4, which did:
 *     if((st.logText||'').trim()){this.flash('Logged');this.up({logText:''});}
 * — a toast, a cleared box, and her text discarded. v4 had no store to write to, so Track A
 * left the drop in place rather than invent a client-side one.
 *
 * It now posts to `/api/logday`, which was already live and appends to
 * `scripts/data/signal_log.jsonl` (`signal_log.log_signal(source="log_day")`) — the friction
 * log the triage sessions actually read.
 *
 * Two rules the old code broke and this one keeps:
 *   · the toast is raised only AFTER the server confirms — an unconditional "Logged" makes a
 *     silent drop indistinguishable from a save
 *   · her text is cleared only on a confirmed write, so a failure leaves it recoverable on screen
 */
function LogTab({ ctx }: { ctx: AddCtx }) {
  const { T, ui } = ctx;
  const C = T.c;
  const tag = ui.logTag;

  return (
    <div>
      <div style={{ padding: '14px 14px 10px' }}>
        <div style={EYEBROW(C.dimmer)}>log the day, or a friction as it comes up</div>
        <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
          {LOG_TAGS.map((t) => {
            const on = tag === t;
            return (
              <button
                key={t}
                onClick={() => ctx.up({ logTag: t })}
                style={{
                  background: on ? C.roseDim : C.surface,
                  border: '1px solid ' + (on ? C.rose : C.border),
                  borderRadius: T.r.card,
                  color: on ? C.text : C.dimmer,
                  fontSize: '12px',
                  fontFamily: 'inherit',
                  padding: '5px 13px',
                  cursor: 'pointer',
                }}
              >
                {t}
              </button>
            );
          })}
        </div>
        <div style={{ display: 'flex', gap: '7px', alignItems: 'flex-end' }}>
          <textarea
            value={ui.logText}
            placeholder={'barely worked, migraine, rested on the couch… — or a friction that came up'}
            onChange={(e) => ctx.up({ logText: e.target.value })}
            style={{
              flex: 1,
              background: C.inkBg,
              border: '1px solid ' + C.inkBorder,
              borderRadius: T.r.field,
              color: C.gold,
              fontSize: '13px',
              fontFamily: 'inherit',
              padding: '7px 10px',
              resize: 'none',
              minHeight: '150px',
              lineHeight: 1.4,
              outline: 'none',
            }}
          />
          <button
            onClick={() => {
              if (!ui.logText.trim()) return;
              // Fire and let the shell own both toasts. The box is cleared only on a confirmed
              // write — see this component's header.
              void ctx.logDay(ui.logText, [TAG_WIRE[tag]]).then((saved) => {
                if (saved) ctx.up({ logText: '' });
              });
            }}
            // v4 gives this button no `whiteSpace:'nowrap'`, unlike "+ Add" (v4:1114). One word.
            style={{ ...ACTION_BUTTON(T), whiteSpace: undefined }}
          >
            Log
          </button>
        </div>
        <div
          style={{
            fontSize: '10.5px',
            color: C.dimmer,
            marginTop: '7px',
            lineHeight: 1.4,
            opacity: 0.85,
          }}
        >
          {'Just for you — a faithful record in your own words. Nothing here is graded, sorted, or judged.'}
        </div>
      </div>
    </div>
  );
}

/** The section eyebrow both halves share, character for character (v4:1111, 1116, 1128). */
function EYEBROW(color: string): React.CSSProperties {
  return {
    fontSize: '10px',
    color,
    textTransform: 'uppercase',
    letterSpacing: '.08em',
    marginBottom: '7px',
  };
}

/** The gold action button both halves share (v4:1114, 1132). */
function ACTION_BUTTON(T: Theme): React.CSSProperties {
  return {
    background: T.c.actBg,
    border: '1px solid ' + T.c.actBorder,
    borderRadius: T.r.field,
    color: T.c.gold,
    fontSize: '12px',
    padding: '0 11px',
    cursor: 'pointer',
    fontFamily: 'inherit',
    height: '36px',
    whiteSpace: 'nowrap',
  };
}

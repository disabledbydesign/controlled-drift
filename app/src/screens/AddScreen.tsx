import { useEffect, useState } from 'react';
import type { Theme } from '@tokens';
import type { Graph, GraphIndex, MutationResult } from '../model/index.ts';
import type { CreatedItem, WeedEntry, WhenToken } from '../api/capture.ts';
import { WHEN_TOKENS } from '../api/capture.ts';
import type { GenerationRequest } from '../shell/useAppState.ts';
import type { LogTag } from '../shell/useAppState.ts';

/**
 * The Add / Log tab.
 *
 * ── WIRED TO THE REAL WEEDER 2026-07-18 ─────────────────────────────────────
 * This tab shipped running a CLIENT-SIDE MOCK ported from the v4 design mockup: `capture()` in
 * `model/mutations.ts` filed the whole typed string as one plain Task under a HARDCODED project
 * id (`'vyzxdu'`) and weeded nothing. That id is the v4 mockup's, and it happens to be the last
 * six characters of the real Anytype id — so against live data it matched nothing, the mutation
 * no-opped, and the button did nothing at all, silently. June: "the buttons on add/log tab
 * aren't working."
 *
 * It was a DOCUMENTED Track A deferral ("no network calls in this track"), but the plan written
 * to close Track A's deferrals — `docs/superpowers/plans/2026-07-18-persistence-seam.md` — never
 * lists the Add tab, so the follow-up never came. The backend was complete the whole time.
 *
 * The behaviour here is the OLD surface's (`docs/overlay_daily.html`), which drove this
 * correctly, against `docs/api_contract_v2.md` §2.6/§6. June: "We already had it working in the
 * old UI, so i just want the same thing."
 *
 * ── what the receipt is ─────────────────────────────────────────────────────
 * Server truth, not a list built as she types: `GET /api/session?stream=capture`. Only the
 * weeder knows how many objects one sentence became. It also means a reload does not lose it,
 * and an undo dims a row because storage says so rather than because the client spliced.
 *
 * Styles are INLINE STYLE OBJECTS and every colour is a token — the two load-bearing rules for
 * this surface (`track-a-component-port.md`). Both skins fork on SHAPE as well as colour, so
 * nothing here hardcodes a hex or invents a radius.
 */

/** The slice of the UI bag this tab reads. `UiState` satisfies it structurally. */
export interface AddUi {
  addText: string;
  logText: string;
  logTag: LogTag;
}

export interface AddCtx {
  T: Theme;
  graph: Graph;
  idx: GraphIndex;
  ui: AddUi;
  up: (patch: Partial<AddUi>) => void;
  apply: (result: MutationResult) => void;
  openDetail: (id: string) => void;
  flash: (msg: string) => void;
  logDay: (text: string, tags: string[]) => Promise<boolean>;

  // ── the real capture flow ──────────────────────────────────────────────────
  captureEntries: readonly WeedEntry[];
  captureSummary: string | null;
  loadCapture: () => Promise<void>;
  runCapture: (text: string) => Promise<boolean>;
  undoCapture: (id: string) => Promise<void>;
  setCapturedWhen: (id: string, when: WhenToken) => Promise<void>;
  setCapturedEngagement: (id: string, from: string, to: string) => Promise<void>;
  regenerate: (req: GenerationRequest, label: string) => Promise<void>;
  /** Non-null while a generation (this capture, or a plan build) is running. */
  busy: string | null;
}

/** One receipt row: a created object, plus whether a later undo entry retired it. */
interface Row {
  item: CreatedItem;
  undone: boolean;
}

/**
 * Flatten the session log into rows, newest first.
 *
 * `undo` entries name a `target_id`; the row stays VISIBLE and dims rather than disappearing.
 * That is the old surface's behaviour and it is deliberate — a row that vanishes gives her
 * nothing to check her memory against, which is the whole point of a receipt.
 */
export function rowsFrom(entries: readonly WeedEntry[]): Row[] {
  const undone = new Set<string>();
  for (const e of entries) {
    if (e.intent === 'undo' && e.target_id) undone.add(e.target_id);
  }
  const rows: Row[] = [];
  for (const e of entries) {
    if (e.intent !== 'weed') continue;
    for (const item of e.created ?? []) rows.push({ item, undone: undone.has(item.id) });
  }
  return rows.reverse(); // the log is oldest-first; she reads newest-first
}

/** The most recent weed turn — what the verify gate is scoped to. */
export function latestWeed(entries: readonly WeedEntry[]): WeedEntry | null {
  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    if (e && e.intent === 'weed') return e;
  }
  return null;
}

export function AddScreen({ ctx }: { ctx: AddCtx }) {
  const C = ctx.T.c;
  return (
    <div>
      <CaptureTab ctx={ctx} />
      <div style={{ height: '8px', borderTop: '1px solid ' + C.border, background: C.bg }} />
      <LogTab ctx={ctx} />
    </div>
  );
}

function CaptureTab({ ctx }: { ctx: AddCtx }) {
  const { T, ui } = ctx;
  const C = T.c;
  const { loadCapture } = ctx;

  // Read the receipt when the tab opens. The old surface did the same (`loadSession` on tab
  // open) — without it a reload shows an empty list beside objects that do exist.
  useEffect(() => {
    void loadCapture();
  }, [loadCapture]);

  /**
   * Dismissal of the verify gate, scoped to the turn it was raised for, so answering "not now"
   * about one capture does not suppress the question for the next one.
   */
  const [dismissed, setDismissed] = useState<string | null>(null);

  const rows = rowsFrom(ctx.captureEntries);
  const last = latestWeed(ctx.captureEntries);
  const todayCount = (last?.created ?? []).filter((c) => c.is_today && c.id).length;
  const gateKey = last?.ts ?? '';
  const showGate = todayCount > 0 && dismissed !== gateKey && !ctx.busy;

  const onCapture = () => {
    void ctx.runCapture(ui.addText).then((saved) => {
      // Cleared only on a proven capture, so a failure leaves her words recoverable on screen.
      if (saved) ctx.up({ addText: '' });
    });
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
            // Enter submits, Shift+Enter makes a newline — the old surface's binding.
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!ctx.busy) onCapture();
              }
            }}
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
            onClick={onCapture}
            disabled={!!ctx.busy}
            style={{
              ...ACTION_BUTTON(T),
              // Single-slot generation lock on the server: a second press would only earn a
              // "busy" answer, so the button says so instead of pretending to queue.
              opacity: ctx.busy ? 0.5 : 1,
              cursor: ctx.busy ? 'default' : 'pointer',
            }}
          >
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
          It sorts what you write into the right places, links it to your work, and reads when
          each one is for. Tap a time to fix it, or undo anything it got wrong.
        </div>
        {ctx.busy ? (
          <div style={{ fontSize: '11px', color: C.dim, marginTop: '7px' }}>thinking it through…</div>
        ) : null}
      </div>

      {/*
        The verify gate. Nothing rebuilds her day on its own: the weeder can file something for
        today, and only she decides whether that changes the plan she is already working from.
        Scoped to the MOST RECENT turn, and not raised at all when nothing landed for today.
      */}
      {showGate ? (
        <div style={{ padding: '0 14px 12px' }}>
          <div
            style={{
              background: C.panel,
              border: '1px solid ' + C.border,
              borderRadius: T.r.card,
              padding: '12px',
            }}
          >
            <div style={{ fontSize: '12.5px', color: C.text, lineHeight: 1.45 }}>
              <b>{todayCount}</b>
              {todayCount === 1 ? ' of these is for today.' : ' of these are for today.'} Add it to
              today’s plan and rebuild it now?
            </div>
            <div style={{ display: 'flex', gap: '7px', marginTop: '10px' }}>
              <button
                onClick={() => {
                  setDismissed(gateKey);
                  void ctx.regenerate({ kind: 'refresh' }, 'Regenerate today');
                }}
                style={{ ...ACTION_BUTTON(T), height: '32px' }}
              >
                Regenerate today
              </button>
              <button
                onClick={() => setDismissed(gateKey)}
                style={{
                  background: 'none',
                  border: '1px solid ' + C.border,
                  borderRadius: T.r.field,
                  color: C.dim,
                  fontSize: '12px',
                  fontFamily: 'inherit',
                  padding: '0 11px',
                  height: '32px',
                  cursor: 'pointer',
                }}
              >
                Not now
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div style={{ padding: '4px 14px 16px' }}>
        <div
          style={{
            fontSize: '10px',
            color: C.dimmer,
            textTransform: 'uppercase',
            letterSpacing: '.08em',
            margin: '6px 0 7px',
          }}
        >
          just added — {rows.length} {rows.length === 1 ? 'item' : 'items'}
        </div>

        {/*
          `result_summary` is the ONLY place a skipped duplicate or a failed item is ever
          mentioned — `failed[]` and `skipped[]` never reach the client. Dropping this line
          would rebuild the silent-failure path BUILD_DOC §5.1 forbids.
        */}
        {ctx.captureSummary ? (
          <div style={{ fontSize: '11px', color: C.dim, marginBottom: '8px' }}>
            {ctx.captureSummary}
          </div>
        ) : null}

        {rows.length ? (
          rows.map((r) => <ReceiptRow key={r.item.id} ctx={ctx} row={r} />)
        ) : (
          <div style={{ fontSize: '12px', color: C.dimmer, opacity: 0.7, lineHeight: 1.4 }}>
            {'Nothing yet today. What’s on your mind?'}
          </div>
        )}
      </div>
    </div>
  );
}

/** Open → Steady → Backburner → Open, the cycle the old receipt's chip used. */
const ENGAGEMENTS = ['Open', 'Steady', 'Backburner'];

function ReceiptRow({ ctx, row }: { ctx: AddCtx; row: Row }) {
  const { T } = ctx;
  const C = T.c;
  const { item, undone } = row;

  const chip = (label: string, onClick: (() => void) | null, tone: string) => (
    <button
      onClick={onClick ?? undefined}
      disabled={!onClick}
      style={{
        background: 'none',
        border: '1px solid ' + C.border,
        borderRadius: T.r.card,
        color: tone,
        fontSize: '10.5px',
        fontFamily: 'inherit',
        padding: '2px 8px',
        cursor: onClick ? 'pointer' : 'default',
      }}
    >
      {label}
    </button>
  );

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: '8px',
        padding: '7px 0',
        borderBottom: '1px solid ' + C.hair,
        // Undone rows stay VISIBLE and dim. She can still see what she undid.
        opacity: undone ? 0.45 : 1,
      }}
    >
      <span style={{ color: C.rose, flex: '0 0 auto' }}>{undone ? '↩' : '✓'}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: '12px',
            color: C.text,
            lineHeight: 1.4,
            textDecoration: undone ? 'line-through' : undefined,
          }}
        >
          {item.name}
        </div>
        <div style={{ fontSize: '11px', color: C.dimmer, marginTop: '2px' }}>
          {item.project ? (
            <>
              sorted into <span style={{ color: C.dim }}>{item.project}</span>
            </>
          ) : (
            <>added as {item.type.toLowerCase()}</>
          )}
        </div>

        {undone ? null : (
          <div style={{ display: 'flex', gap: '5px', marginTop: '5px', flexWrap: 'wrap' }}>
            {/*
              The when-chip. Tapping cycles a resolver TOKEN — never the rendered label — and the
              server re-anchors it to a real date, so "tomorrow" keeps meaning tomorrow.
              Only tasks carry a when; a created Project has none.
            */}
            {item.when_label
              ? chip(
                  item.when_label,
                  () => {
                    const i = WHEN_TOKENS.findIndex(
                      (t) => t.toLowerCase() === (item.when_label ?? '').toLowerCase(),
                    );
                    const next = WHEN_TOKENS[(i + 1) % WHEN_TOKENS.length] ?? 'today';
                    void ctx.setCapturedWhen(item.id, next);
                  },
                  item.is_today ? C.rose : C.dim,
                )
              : null}

            {/* Projects only: correct the engagement the weeder proposed. */}
            {item.engagement
              ? chip(
                  item.engagement,
                  () => {
                    const i = ENGAGEMENTS.indexOf(item.engagement ?? '');
                    const next = ENGAGEMENTS[(i + 1) % ENGAGEMENTS.length] ?? 'Open';
                    void ctx.setCapturedEngagement(item.id, item.engagement ?? '', next);
                  },
                  C.dim,
                )
              : null}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '5px', flex: '0 0 auto' }}>
        {undone ? null : (
          <button
            onClick={() => void ctx.undoCapture(item.id)}
            style={{
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
            undo
          </button>
        )}
        <button
          onClick={() => ctx.openDetail(item.id)}
          style={{
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
    </div>
  );
}

const LOG_TAGS: readonly LogTag[] = ['The day', 'Friction'];

/**
 * Her label -> the tag `/api/logday` stores. The server keeps only `"day"` and `"issue"` and
 * silently substitutes `["day"]` for anything else, so a wrong mapping here would file every
 * friction entry as a day entry — losing exactly the issue-tagged subset the triage passes read.
 */
const TAG_WIRE: Record<LogTag, string> = { 'The day': 'day', Friction: 'issue' };

/**
 * ── THE LOG HALF, AND WHY IT GREW A RECEIPT ─────────────────────────────────
 * The Log button was never broken — every entry June wrote was saved (verified in
 * `scripts/data/signal_log.jsonl`). She reported it as broken because NOTHING ON SCREEN SAID SO:
 * a toast, a cleared box, and then no trace it exists. "the log just didnt seem to send when i
 * clicked the button?"
 *
 * The project's own rule is that "a save that produces no signal is not clearly better than a
 * false one, because nothing then distinguishes saved from broken". So this keeps a session
 * receipt of what she has logged.
 *
 * ⚠ DERIVED, NOT TRANSCRIBED. There is no design for a log receipt anywhere — the flow mockup
 * draws the Add pane only and never renders the Log pane, and no doc describes log history.
 * `POST /api/logday` returns `{ok, tags}` and no entry body, so there is nothing to read a
 * server-truth list back from without a contract change. This list is therefore SESSION-LOCAL
 * and says so, rather than implying a history it cannot load. Its shape is taken from the Add
 * receipt above so the two halves of one tab do not look like two different products.
 */
function LogTab({ ctx }: { ctx: AddCtx }) {
  const { T, ui } = ctx;
  const C = T.c;
  const tag = ui.logTag;

  const [logged, setLogged] = useState<readonly { text: string; tag: LogTag }[]>([]);

  const onLog = () => {
    if (!ui.logText.trim()) return;
    const text = ui.logText;
    void ctx.logDay(text, [TAG_WIRE[tag]]).then((saved) => {
      if (!saved) return;
      ctx.up({ logText: '' });
      setLogged((prev) => [{ text, tag }, ...prev]);
    });
  };

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
          <button onClick={onLog} style={{ ...ACTION_BUTTON(T), whiteSpace: undefined }}>
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

      {logged.length ? (
        <div style={{ padding: '0 14px 16px' }}>
          <div
            style={{
              fontSize: '10px',
              color: C.dimmer,
              textTransform: 'uppercase',
              letterSpacing: '.08em',
              margin: '6px 0 7px',
            }}
          >
            logged this session
          </div>
          {logged.map((l, i) => (
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
                <div style={{ fontSize: '12px', color: C.text, lineHeight: 1.4 }}>{l.text}</div>
                <div style={{ fontSize: '11px', color: C.dimmer, marginTop: '2px' }}>
                  saved — {l.tag.toLowerCase()}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}
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

import { useCallback, useEffect, useRef, useState } from 'react';
import type React from 'react';
import type { Theme } from '@tokens';
import { CHROME_ATTR, type PressTarget } from './capture.ts';
import type { Mark } from '../shell/useAppState.ts';

/** One freehand stroke, as the points it passed through in image coordinates. */
type Stroke = Array<[number, number]>;

const STROKE_WIDTH = 4;

export interface AnnotateOverlayProps {
  T: Theme;
  /** The snapshot, or null when the render failed — then this is a text-only entry. */
  shot: string | null;
  target: PressTarget | null;
  onCancel: () => void;
  /**
   * Returns whether it landed. False keeps the overlay open with everything intact.
   *
   * `size` is the image dimensions the marks were drawn against — mark coordinates are
   * meaningless without it, so the two always travel together.
   */
  onSend: (
    text: string,
    shot: string | null,
    marks: Mark[],
    size: { w: number; h: number } | null,
  ) => Promise<boolean>;
}

/**
 * The capture editor: what she was looking at, whatever she draws on it, and what she wants to
 * say about it.
 *
 * ── why the marks are held as points, not painted ───────────────────────────
 * Strokes live in state as arrays of points and the canvas is re-rendered from them on every
 * change, so undo is a `pop`. Painting straight onto a single canvas would be less code and make
 * undo impossible without a pixel-history buffer.
 *
 * ── why the image is composited only at send ────────────────────────────────
 * The snapshot stays an untouched <img> underneath and the strokes sit on a canvas above it.
 * They are flattened into one PNG once, in `composite()`, when she sends. Until then the
 * original is intact, so Clear genuinely restores it.
 *
 * ── theme keys ──────────────────────────────────────────────────────────────
 * The plan assumed flat `T.warn` / `T.card` / `T.line` / `T.accent`. The real token set nests
 * colours under `T.c` and has no `warn`, `card`, `line` or `accent`. Substituted against
 * `design/tokens/tokens.ts`: mark colour `T.c.red`, panels `T.c.surface`, hairlines `T.c.border`,
 * and the primary button uses the gold action treatment the rest of the app already uses
 * (`T.c.actBg` / `T.c.actBorder` / `T.c.gold`, see `AddScreen.tsx:589`) rather than an invented
 * accent.
 */
export function AnnotateOverlay({ T, shot, target, onCancel, onSend }: AnnotateOverlayProps) {
  const [text, setText] = useState('');
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [sending, setSending] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawing = useRef(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);

  /** Re-render every stroke. Runs on any change to `strokes`, including an undo. */
  useEffect(() => {
    const c = canvasRef.current;
    const ctx = c?.getContext('2d');
    if (!c || !ctx) return;
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.strokeStyle = T.c.red;
    ctx.lineWidth = STROKE_WIDTH;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (const s of strokes) {
      if (s.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(s[0]![0], s[0]![1]);
      for (const [x, y] of s.slice(1)) ctx.lineTo(x, y);
      ctx.stroke();
    }
  }, [strokes, T]);

  /** Pointer position in CANVAS coordinates — the canvas is displayed scaled to fit. */
  const at = useCallback((e: React.PointerEvent<HTMLCanvasElement>): [number, number] => {
    const c = canvasRef.current!;
    const r = c.getBoundingClientRect();
    return [
      ((e.clientX - r.left) / (r.width || 1)) * c.width,
      ((e.clientY - r.top) / (r.height || 1)) * c.height,
    ];
  }, []);

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    drawing.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    const p = at(e);
    setStrokes((prev) => [...prev, [p]]);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return;
    const p = at(e);
    setStrokes((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1]!;
      return [...prev.slice(0, -1), [...last, p]];
    });
  };

  const onPointerUp = () => {
    drawing.current = false;
  };

  /** Flatten the snapshot and the strokes into one PNG. Null when there was no snapshot. */
  const composite = useCallback((): string | null => {
    const img = imgRef.current;
    const marks = canvasRef.current;
    if (!img || !marks) return null;
    const out = document.createElement('canvas');
    out.width = marks.width;
    out.height = marks.height;
    const ctx = out.getContext('2d');
    if (!ctx) return shot;
    try {
      ctx.drawImage(img, 0, 0, out.width, out.height);
      ctx.drawImage(marks, 0, 0);
      const url = out.toDataURL('image/png');
      // ⚠ A try/catch alone is NOT enough here. jsdom's unimplemented `toDataURL` RETURNS
      // undefined instead of throwing, and a real browser can return "data:," from a tainted or
      // zero-size canvas — both slip past a catch and would hand `undefined` to the server as
      // the image. Check the result is actually a PNG data URL, exactly as `snapshot()` does.
      return typeof url === 'string' && url.startsWith('data:image/png') ? url : shot;
    } catch {
      // Any future canvas restriction: fall back to the unannotated original rather than losing
      // the image. Her comment is the part that must never be lost.
      return shot;
    }
  }, [shot]);

  /**
   * The strokes as data: each one's bounding box, and whether it closed back on itself.
   *
   * This is the answer to "would an arrow tool read more clearly than a hand-drawn circle" —
   * the shape is not what a later reader is missing, the COORDINATES are. Emitting these lets a
   * hand-drawn loop say "the trouble is in this rectangle" as precisely as any shape tool could,
   * with no tool palette standing between June and writing the entry.
   */
  const geometry = useCallback((): Mark[] => {
    return strokes
      .filter((s) => s.length >= 2)
      .map((s) => {
        const xs = s.map((p) => p[0]);
        const ys = s.map((p) => p[1]);
        const x = Math.min(...xs);
        const y = Math.min(...ys);
        const w = Math.max(...xs) - x;
        const h = Math.max(...ys) - y;
        const [sx, sy] = s[0]!;
        const [ex, ey] = s[s.length - 1]!;
        // "Closed" = it ended near where it began, relative to its own size. A loop reads as
        // circling something; an open stroke reads as pointing at something.
        const span = Math.max(w, h, 1);
        const closed = Math.hypot(ex - sx, ey - sy) < span * 0.35;
        return { points: s, box: [x, y, w, h] as [number, number, number, number], closed };
      });
  }, [strokes]);

  const send = async () => {
    if (!text.trim() || sending) return;
    setSending(true);
    const c = canvasRef.current;
    const size = c && c.width ? { w: c.width, h: c.height } : null;
    const ok = await onSend(text.trim(), shot ? composite() : null, geometry(), size);
    setSending(false);
    // On failure we deliberately do NOT clear the text or the strokes: `useAppState.fail` has
    // already told her nothing was saved, and throwing away her comment at that moment would be
    // the worst possible move. The overlay closes ONLY on a confirmed true.
    if (ok) onCancel();
  };

  const btn = (extra: React.CSSProperties = {}): React.CSSProperties => ({
    padding: '10px 16px',
    borderRadius: T.r.field,
    border: `1px solid ${T.c.border}`,
    background: T.c.surface,
    color: T.c.text,
    font: 'inherit',
    cursor: 'pointer',
    ...extra,
  });

  return (
    <div
      {...{ [CHROME_ATTR]: '' }}
      role="dialog"
      aria-label="Log what is wrong here"
      style={{
        position: 'fixed', inset: 0, zIndex: 9999, background: T.c.bg,
        display: 'flex', flexDirection: 'column', gap: 12, padding: 16, overflow: 'auto',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <strong style={{ color: T.c.text }}>Log what is wrong here</strong>
        {target?.label ? (
          <span style={{ color: T.c.dim, fontSize: 13 }}>You pressed: {target.label}</span>
        ) : null}
      </div>

      {shot ? (
        <div style={{ position: 'relative', maxHeight: '45vh', overflow: 'hidden', borderRadius: T.r.card, border: `1px solid ${T.c.border}` }}>
          <img
            ref={imgRef}
            src={shot}
            alt="What you were looking at"
            onLoad={(e) => {
              const c = canvasRef.current;
              if (!c) return;
              c.width = e.currentTarget.naturalWidth || e.currentTarget.width;
              c.height = e.currentTarget.naturalHeight || e.currentTarget.height;
            }}
            style={{ display: 'block', width: '100%', height: 'auto' }}
          />
          <canvas
            ref={canvasRef}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', touchAction: 'none', cursor: 'crosshair' }}
          />
        </div>
      ) : (
        <p style={{ color: T.c.dim, margin: 0 }}>
          Could not take a picture of this screen. You can still write down what is wrong.
        </p>
      )}

      {shot && strokes.length > 0 ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" style={btn()} onClick={() => setStrokes((p) => p.slice(0, -1))}>
            Undo mark
          </button>
          <button type="button" style={btn()} onClick={() => setStrokes([])}>
            Clear marks
          </button>
        </div>
      ) : shot ? (
        <p style={{ color: T.c.dim, margin: 0, fontSize: 13 }}>You can draw on the picture to point at something.</p>
      ) : null}

      <textarea
        aria-label="What is wrong here"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="What is wrong here?"
        style={{
          width: '100%', minHeight: 150, resize: 'vertical', padding: 12,
          borderRadius: T.r.field, border: `1px solid ${T.c.border}`, background: T.c.surface,
          color: T.c.text, font: 'inherit',
        }}
      />

      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button type="button" style={btn()} onClick={onCancel}>Cancel</button>
        <button
          type="button"
          style={btn({
            background: T.c.actBg,
            color: T.c.gold,
            borderColor: T.c.actBorder,
            opacity: text.trim() && !sending ? 1 : 0.5,
          })}
          onClick={send}
        >
          {sending ? 'Saving…' : 'Send'}
        </button>
      </div>
    </div>
  );
}

import { alpha } from "@tokens";
import type { PlanArcStep } from "../../fixtures/index.ts";
import { TaskCheck } from "../atoms/index.ts";
import type { TodayCtx } from "./types.ts";

export interface ArcStepProps {
  ctx: TodayCtx;
  step: PlanArcStep;
  /** Address of the step inside the plan — see `toggleArcStep`. */
  bandIndex: number;
  itemIndex: number;
  stepIndex: number;
}

/**
 * v4 `arcStep(s,key,arc,i)` (~1099) — one step of a work block's arc.
 *
 * Three visual states, all carried by `s.state`:
 *   · `done`  — struck through, `dimmer`
 *   · `here`  — the current step: rose text, a rose left rail (`inset 2px 0 0`), a rose
 *               left-to-right wash, medium weight and a rose text glow
 *   · `ahead` — plain `dim`
 *
 * The wrapper stops click propagation so tapping a step does not also collapse the block
 * (the block header is the toggle; the arc sits inside it).
 *
 * v4 wrote `C.rose+'24'` / `'04'` / `'73'` — hex alpha suffixes, transcribed here as `alpha()`
 * calls at the same values (0x24=.141, 0x04=.016, 0x73=.451).
 *
 * The state change itself — including spec §14's "here" advance — lives in the pure
 * `toggleArcStep` in `model/plan.ts`, not in this component. It is applied by the shell's
 * `completeArcStep`, which redraws the plan AND writes the step's completion to the server.
 * This component called `ctx.applyPlan(toggleArcStep(...))` directly until 2026-07-19; that
 * seam has no `write` on it, so every step June ever checked off was lost on reload.
 */
export function ArcStep({
  ctx,
  step,
  bandIndex,
  itemIndex,
  stepIndex,
}: ArcStepProps) {
  const C = ctx.T.c;
  const here = step.state === "here";
  const done = step.state === "done";

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "9px",
        padding: "3px 6px",
        borderRadius: ctx.T.r.ctl,
        fontSize: "12.5px",
        lineHeight: 1.4,
        ...(here
          ? {
              background: `linear-gradient(90deg,${alpha(C.rose, 0.141)},${alpha(C.rose, 0.016)} 70%)`,
              boxShadow: "inset 2px 0 0 " + C.rose,
            }
          : {}),
      }}
    >
      <button
        onClick={(e) => {
          e.stopPropagation();
          // ⚠ THE STEP'S OWN TASK ID, not the block's. This completes a real Anytype task; the
          // block header's check one level up records a chunk of work and must never finish the
          // project. Sending the wrong one of the two is a write that looks right and is not.
          ctx.completeStep(
            { id: step.id ?? "", bandIndex, itemIndex, stepIndex },
            !done,
          );
        }}
        aria-label="mark done"
        aria-pressed={done}
        style={{
          flex: "0 0 auto",
          border: "none",
          background: "none",
          cursor: "pointer",
          // Tap-target expansion (2026-07-18, TRIAL) — see `RoundCheck`. Glyph stays 14; only
          // the hit area grows, cancelled by an equal negative margin. Capped at 4px vertical
          // to stay inside this row's ~23px pitch (12.5px text at 1.4, plus 3px padding).
          padding: "4px 8px",
          margin: "-4px -8px",
          display: "flex",
        }}
      >
        <TaskCheck T={ctx.T} done={done} col={C.rose} size={14} />
      </button>
      <span
        style={{
          color: done ? C.dimmer : here ? C.rose : C.dim,
          textDecoration: done ? "line-through" : "none",
          fontWeight: here ? 500 : 400,
          ...(here ? { textShadow: `0 0 11px ${alpha(C.rose, 0.451)}` } : {}),
        }}
      >
        {step.text}
      </span>
    </div>
  );
}

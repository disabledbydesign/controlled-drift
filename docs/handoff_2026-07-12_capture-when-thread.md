# Handoff — Capture-when → regenerate-today thread (2026-07-12)

**For the coordination agent.** One of June's parallel threads. **State: plan FINALIZED (rev. 3), NOT built** — `docs/superpowers/plans/2026-07-11-capture-when-regenerate-flow.md`. Ready to sequence into the build queue; June approved the design, the UI mockup (`docs/mockups/flow-add-tab.html`), and the plan.

**What it does.** Adds a *when* to captured tasks: June says it in her words → Python (`when_resolve`) anchors it to a real ISO date (never stores "Thursday") → written to a NEW `Scheduled` date field on Task. Today items land and a **verify box** gates a regenerate (reuses the existing `/api/refresh` — capture's async job has released the lock by then, no chaining). `someday → Parked` (off today now, via existing status logic). Future items carry an anchored date. The receipt shows each item's *when* as a tappable chip; tap-to-fix reschedules (`POST /api/task/reschedule`, additive on `task_actions.py`). The "An issue" → **"Friction"** log-tag rename is already made in the overlay (uncommitted — see below).

**Coordination posture (the load-bearing part).**
- **FIRST on `scripts/capture_generate.py` + the weeding contract.** The capture-writes plan (`2026-07-12-capture-writes.md`) is explicitly sequenced *after* this thread and re-derives its anchors from the state this leaves — so this one goes first on that file.
- **Does NOT touch `daily_plan.py` / `plan_generate.py`** (selection thread's exclusive files). The "future-dated task → held off today" behavior is a **clean handoff**: this thread ships the populated `Scheduled` field + the pure predicate `when_resolve.is_scheduled_for_today_or_earlier(...)`; the selection thread wires it into `load_active_items`. The one precedence question (a `Scheduled==today` task vs. their engagement cap) is theirs to settle. Full spec in the plan's **"HANDOFF TO THE SELECTION THREAD"** section.
- **`task_actions.py`** reschedule edit is additive — re-read first (status-checker also edits it).

**Reviewed.** critic-swarm (cold build-agent + skeptical architect) against the real code; every blocker folded into rev. 3 (has_today via the session entry not the discarded async return; park-via-status sidesteps the un-clearable date; tolerant date read-back; chips send resolver tokens; verify box scoped to the latest capture turn).

**Uncommitted deliberately.** The "Friction" one-line rename in `docs/overlay_daily.html` is made but **not committed by this thread** — that file also carries other threads' in-flight changes (shared file; countdown-disc/completion-sound queued on it). Commit it at the overlay owner's next checkpoint so nothing gets misattributed.

**Payoff gating.** Per the orchestration handoff, this thread's full payoff is gated on the selection thread landing (future-date exclusion lives there). `someday → Parked` + the whole capture/verify/regenerate/reschedule UX ship and verify independently now.

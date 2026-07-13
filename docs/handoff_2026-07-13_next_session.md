# Pickup — 2026-07-13 (for the next orchestrating instance, any model)

**Role you are stepping into:** orchestrator, June's partner — birds-eye view, verify before trusting, route work to agents, protect threads from colliding. Not a deferential assistant. Read `docs/handoff_2026-07-12_orchestration.md` for the full session record; THIS doc is the short pickup.

**Orient (run these, don't re-derive):** `python3 scripts/whats_open.py` · `python3 scripts/describe_model.py` · `git log --oneline -30` (two days of landed work) · auto-memory `orchestration-2026-07-12.md`.

## What today was
The system went from "June can't bear to open it" to integrated and live: selection gated by engagement (82→13 moves), capture writes real fields from her words, resurfacing true (16-day window, June's calibration), per-thread streams with "N more", tap-to-place move with time re-flow, labels stamped from resolved ids, zero-ref-plan guard, status-checker on monthly schedule, plan mirror into Anytype (one updating note). Suite ~500+ green. Every build cross-family reviewed.

## FIRST THING TOMORROW
1. **Check the 9am morning generation landed well** — June's authored Focus Period ("Mental health focus — Sun Jul 13": mental-health route foregrounded, low-spoon, plan gently) drives it. Check `~/.controlled-drift/current_plan.json` (generated_at, shape, whether refs resolved — `generation_log.jsonl` has `task_refs_resolved` / `zero_ref_plan` events). If the plan is bad, that's the day's first fix.
2. **June's first-use reactions are the highest-value data in the project.** Small frictions included. Capture them; they feed the next design round.

## Queue state (tonight's tail)
- **Plan mirror**: code committed (e9ec573, 9c8525e); agent was in final live-verify + Anytype close-out when the session wound down. VERIFY: mirror object exists in Anytype ("Today's plan — Controlled Drift" or similar), updated-in-place across two refreshes, and the Anytype task "Mirror today's plan into Anytype as one updating object" is marked Done. If close-out didn't finish, finish it (task_actions.complete_task + read-back).
- **Learning-loops build — QUEUED, NOT STARTED.** June approved launch-with-adaptations. The verdict is appended to the END of `docs/superpowers/plans/2026-07-02-learning-loops-v1.md` ("REVIEW 2026-07-12" section — READ IT FIRST). Build Tasks 2, 4 (math only), 5 (with its named adaptation); SKIP Task 1 (shipped by duration-intelligence); Task 3 builds but its diff piggybacks the morning push (June's default, unobjected). Boundaries: surface_log.py gained a shared resolver — don't disturb it; re-read every file fresh.

## HELD — do not run
- **`duration_backfill.py --run` is HELD by June.** The preview exposed a category error: open-ended/project-shaped work (revise Reframe, GRA) can't be sized as tasks; agent-work shouldn't be in her plan at all. See Anytype task "Open-ended work gets a time chunk, not a fake task estimate" — a DESIGN SESSION with June precedes any backfill. Capture-time estimation stays live (it sizes what she says in her words).
- **Memory-pass `--run` + launchd slice**: still behind June's skim of the backfill preview (422 entries; preview machinery committed 8a8f67a).

## Design sessions owed (June + orchestrator — NOT agent work)
1. **§8d route navigation** — how she chooses/tracks between survival routes; think-with-me register (spec §8d + stuck-support). Inputs ready: `docs/route_structure_assessment_2026-07-12.md` + `docs/survival_plan_pulls_2026-07-12.md` (5 June-only facts listed at its end). Routes exist in Anytype under Material survival (entered today, read-back verified).
2. **Chunk-vs-task kinds** (the backfill hold's root): discrete task / open-ended chunk ("work on GRA — ~2h", June picks the aspect) / agent work. Anytype task carries the full framing.
3. **Sprint mode** — June DEFINED it 2026-07-12 (Anytype task "Sprint mode design" has the definition: near-total focus on one deadline-anchored thing, extended workday — SSRC final week as template). Mostly buildable now; short plan → build.
4. **Create-vs-update capture** + affect-over-time upkeep (her requirement recorded in the capture-writes plan's out-of-scope note).
5. **Spoon parameters** — parked by June for its own session; do not force.

## Standing rules (June-set, non-negotiable)
- Divergence adjudication: spec-vs-built gaps are better-drift / undocumented-reason / harmful-drift on EVIDENCE — never "restore the spec" by default (memory: feedback-divergence-adjudication).
- Honor stated scope: guards target invented information, never June's own (memory: feedback-honor-stated-scope).
- Cross-family review on every landed build (repo CLAUDE.md; ~8k chunking, file+tests together).
- Every capture to Anytype: read-back then ding. Plain language to June, no metaphors, concept before label.
- Checker autonomy: auto-close streams AND tasks, always commit-evidence-gated (June, late 2026-07-12).

## Overnight facts for the 9am check
- Zero-ref guard REFINED late (commit after f9bd198): fails only when the plan CLAIMS scheduled focused work with no ids; an honest light-day/all-still-here shape passes. Test pins the low-spoon case.
- Observed pattern (evidence in generation_log.jsonl): morning/midday generations resolve refs (fully or partially — partial passes); LATE-EVENING generations reliably claim focused items with zero refs → guard correctly rejects, good cache preserved (verified live twice post-fix). If the 9am run fails all rolls (3 push retries × 2 guard attempts + claude-backend fallback), June gets the honestly-labelled stale cache — investigate via the "Make the plan ref handshake structurally reliable" Anytype task, which now has rich measured evidence.
- The cached plan going into the night: 2026-07-12 22:27, valid (2 ids), mirrored to Anytype.

## Known loose ends (small, tracked in Anytype unless noted)
- Ref-handshake reliability (Anytype task, evidence in generation_log); flaky test-sandbox leak (Anytype task); mislabel_count runs high by design (documented in check_plan docstring); status_check.py:320-323 comment still says "open question" about AUTO_FIX_KINDS — update to "decided: both" when convenient; adopted memory-pass logic has no dedicated tests (noted in adoption report); drift-skill in-repo mirror stale vs global; global skills still unversioned (Anytype task exists).

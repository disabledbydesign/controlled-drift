# Completed bodies of work — candidates to record as Done streams

*Produced by a review subagent in session 11 (2026-06-20), persisted so the review isn't lost. These are coherent, built bodies of work in the Controlled Drift build. **Not yet recorded as Done streams in Anytype.** When recording them: note that "Done" should mean verified, not just "code exists" — see the verification flags below. Finished streams won't show on the map (finished is off the map → project wins mirror), but recording them matters for the record and the future wins mirror.*

Naming/description follow `work_stream_register.md` (plain language, one "what it is" line).

1. **The data model** — the object kinds the system stores your work as (goals, projects, tasks, recurring things, strategies), each with the fields it needs.
   - Evidence: `build_*.py` + `build_model.py`; `verify_model.py` checks every type/field; ROADMAP marks the data model live. **Verified.**

2. **Writing into Anytype** — the reliable way the system creates and updates your items without getting the fields wrong.
   - Evidence: `gsdo_objects.py` (create/update + tag-id resolution), `gsdo_anytype.py` (idempotent schema helpers, pagination); `test_gsdo_objects.py` + `test_gsdo_anytype.py`. **Verified** (the `update()` helper was added + live-tested this session).

3. **Folder binding** — ties a folder on your computer to the right part of your work in Anytype, so being in that folder points the system at the right place.
   - Evidence: `gsdt_bind.py`; `test_gsdt_bind_claude_md.py`; ROADMAP Build 1. **Verified live in session 10.**

4. **Placing a day in real time (clock scheduling)** — lays the things you mean to do across the actual hours of your day, fitting flexible work around fixed appointments.
   - Evidence: `scheduler.py`, `datetime_seam.py`; `test_scheduler.py`. **June confirmed the clock-time piece is done.**

5. **The file sweep** — reads a project's files and surfaces the loose ends not yet captured.
   - Evidence: `sweep.py`, `sweep_log.py`; `test_sweep.py`, `test_sweep_log.py`. ⚠️ **NOT fully verified (June, session 11) — do not mark Done until verified.**

6. **Resurfacing neglected work** — finds work you haven't looked at in a while so it can honestly come back up.
   - Evidence: `neglect.py`, `surface_log.py`; `test_neglect.py`. ⚠️ **Unverified — exists as scaffolding, never run in real use. Verify before Done.**

7. **Remembering your plan edits** — records the changes you make to a proposed plan, so the system can learn your rhythm later.
   - Evidence: `plan_corrections_log.py`; `test_plan_corrections_log.py`. ⚠️ **Unverified — verify before Done.**

**Excluded on purpose:** the orientation map / arc renderer (actively built this session), the daily-plan pipeline (already recorded as a Done stream). **Not complete, so not listed:** the weeding pipeline (prompt drafted, not wired — ROADMAP marks it 🔶).

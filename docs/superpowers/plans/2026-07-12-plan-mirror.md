# Plan mirror — one updating Anytype object (2026-07-12)

## Why
The founding spec (`AI_LAYER_SPEC.md` §10) required June's confirmed plan to stay
human-readable even when the AI layer is down. The built system inverted that: the plan lives
only in a local cache (`~/.controlled-drift/current_plan.json`) + the overlay. If the server
is down, the plan is unreadable. This mirrors it into Anytype, which renders on its own.

## June's decision (2026-07-12, handoff decisions)
Mirror the plan into Anytype as **ONE object, updated idempotently each generation** — a cheap
in, **NO per-day accumulation**. The learning loop already keeps daily history
(`plan_snapshots.jsonl`); this object is only the current readable copy.

## Build
1. **`scripts/plan_mirror.py`**
   - `render_body(plan, now=None)` — pure. Renders the cached plan dict into a plain-language
     Markdown body: age line first ("Built today at 9:50 PM"), then the blocks (label + time,
     then each item's time + task name) OR, for a fragmented day, the ordered priority list;
     then the still-waiting items; then the honest footer. June-facing: plain words, no
     metaphors, no internal jargon (the mirror does NOT echo `woven_frame` / per-block framing
     prose — just times + names, so no LLM metaphors leak in).
   - `mirror_plan(plan, now=None)` — find-or-create ONE Note by stable name
     `"Today's plan — Controlled Drift"`, then UPDATE its body. Read-back verify. Returns oid.
   - `mirror_plan_safe(plan)` — best-effort wrapper: swallows any failure, logs one honest
     stderr line, never raises. This is what the generation path calls.

2. **API asymmetry (verified live 2026-07-12):** create sets the body via the `body` field;
   PATCH **ignores `body`** (returns 200, no change) and updates the body only via the
   **`markdown`** field (confirmed against the live API + the update-object schema). So
   `gsdo_objects.update()` gains a `body=` param that sends `markdown` in the PATCH payload
   (additive, shared write layer — future callers benefit).

3. **Wire-in:** `generate_plan()` success path, right after the snapshot-log block
   (`plan_generate.py` ~line 1032). Chosen because `generate_plan()` is the ONE function both
   the morning push (`morning_push.py`) and `/api/refresh` (`server.py`) call — one call site
   covers both. It sits AFTER the zero-ref raise, so the mirror only fires on a VALID cached
   plan. Best-effort (`mirror_plan_safe`): a mirror failure never breaks or delays generation.
   (Deliberately NOT wired into `reorder()` — the task scoped the seam to the fresh-generation
   path; reorder is a separate negotiate path. Noted as a known follow-up.)

4. **Footer (verbatim):** "This is a copy for when the main surface is down. The live plan is
   in the overlay." — keeps the two-surfaces relationship honest.

5. **Type:** built-in **Note** (`gsdo_objects.create("Note", ...)`; `find_type('Note')`
   confirmed live). No new schema/types.

## Tests
- render body pure (clock shape, priority shape, still-waiting, age-line relative days, footer).
- find-or-create-then-update idempotency (mocked): first call creates, second updates SAME id.
- best-effort failure swallows + logs (mocked `mirror_plan` raising → `mirror_plan_safe`
  returns None, prints stderr, does not raise).
- wire-in fires on success, not on failure (mocked).

## Live verify
Server running → ONE `/api/refresh` → read the mirror object back from live Anytype (direct
GET), confirm body matches the cached plan (age line + first block + item count). SECOND
refresh → confirm SAME object id was updated (no second object). Then complete the Anytype
task "Mirror today's plan into Anytype as one updating object" and read it back.

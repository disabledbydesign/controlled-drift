# As-Needed Task Reactivation — Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per
> task, per-task review, final whole-branch review (`subagent-driven-development`). Steps use
> checkbox (`- [ ]`) syntax for tracking. **Subagents here can WRITE files but CANNOT run Bash — the
> main agent runs every test / read-back / live-verify.** Bash-only steps are marked
> **(main agent, Bash)**. Line anchors are from the 2026-07-17 extraction below; **re-derive each at
> its live line before editing** — several were already stale once.

**Goal:** Let June turn an existing "as-needed" recurring task back **on** by naming it in the Add box
or Focus Period; while on, it surfaces in **every** daily plan until she completes it; completing it
turns it **off** until she asks again.

**Architecture:** A single persistent `Active` checkbox on the Recurring type is the whole state
machine. Surfacing reads it (an active as-needed task is "due" every day). Completion writes it false
(a real Anytype write + read-back, distinct from a scheduled recurring's cache-only "done for today").
Two "just say it" entry points flip it true — the weeding gate (Add) recognizes an existing as-needed
task in June's dump and reactivates it instead of minting a duplicate; the Focus-Period authoring flow
recognizes one she names and lists it in the reflect-back. One field, several writers.

**Tech Stack:** Python 3 stdlib only; existing modules `gsdo_objects`,
`gsdo_anytype` (`g`), `build_recurring`/`build_model`, `datetime_seam`, `daily_plan`, `plan_store`,
`capture_generate`, `capture_fields`, `focus_period_generate`/`_adapter`/`_author`, `server`; vanilla
JS/HTML in `docs/overlay_daily.html`; pytest with the repo `conftest.py` sandbox redirect. No new deps.

## Global Constraints

- **`python3`, not `python`.** Full suite: `python3 -m pytest -q` from repo root.
- **`gsdo_objects.create`/`update` take DISPLAY names** (`"Active"`), never a property key or tag id.
- **Read a written value BACK BY DISPLAY NAME, not by key** — the Anytype key is generated/
  unpredictable (`interval_unit` is bare, `gsdo_day_of_week` is prefixed; do not assume `Active`'s
  key). A checkbox reads back as `(by_name.get("Active") or {}).get("checkbox")`.
- **Idempotent writes; no silent failures — raise, don't `assert`; verify with read-back** after every
  live write (mirror `server.set_project_engagement`: update → re-fetch → assert-by-name → raise on
  mismatch).
- **Tests self-clean — NEVER leave artifacts in June's real space.** Unit tests mock the LLM and
  Anytype; `conftest.py` redirects data/config to a sandbox and *fails the suite* on any write to the
  real data dir. The end-to-end task (Task 7) creates real objects and **deletes them in the same run.**
- **Additive only (one decided exception).** Scheduled recurrings (day/week/month) and their cache-only
  "done for today" behavior must be **unchanged**. Only `as_needed` items gain the new behavior. (The one
  removal — retired `Has target`/`Target` — is Task 1 detail; it has **no** scheduling consumer.)
- **One field, one primitive.** `set_recurring_active` (Task 3) is the single writer of `Active`; every
  path (completion, Add, Focus) calls it — no path re-implements the write/read-back/log.
- **Reason from function, not doc-text (repo build-frame guard).** The `as_needed`/`active` flags must
  ride the SAME rails the existing `recurring`/`is_recurring` flag already rides. **That path is THREE
  hops, not two:** the `daily_plan` fold sets `is_recurring` on the pre-LLM dict → **`plan_generate`
  re-attaches it by id AFTER LLM composition** (a `recurring_ids` set → `item["recurring"]=True`, ~`:999`/
  `:1054`) → `daily_plan` row-origins read it (`blocks_from_scheduled` etc.) → `plan_store`. **Arbitrary
  flags do NOT survive the LLM round-trip** — they must be re-attached in `plan_generate` exactly like
  `recurring`, or `as_needed` silently dies on the real plan while every unit test (which hand-builds rows)
  passes. Trace EVERY place `recurring` is set and set `as_needed` alongside it — do not invent a parallel
  channel (Task 4 Step 1 names the sites). Verify by regenerating June's REAL plan (Task 7), not tests alone.

## Coordination note — the field is the shared contract

June is building the explicit "turn these on" tick-list UI **separately**. That UI writes the SAME
`Active` field this plan adds. So: **build the field and the `set_recurring_active` primitive as the
shared substrate; do NOT build a tick-list here.** This plan's writers are completion (off), the Add
box (on), and Focus Period (on). Her tick-list is a fourth writer that needs only Tasks 1–3 to exist.

**Shared-field write rule (the contract, decided 2026-07-17):** every writer of `Active` — this plan's
three AND June's tick-list — writes **only the specific task it just toggled, after re-reading that task's
current value**; no writer re-saves a whole remembered list of on/off states. This blocks a stale-view
overwrite (the tick-list, loaded before a completion, re-asserting an old "on" over a just-written "off").
`set_recurring_active` (Task 3) already does read-then-write for a single id; the tick-list must follow the
same per-id rule.

**⚠ `overlay_daily.html` is being RETIRED** (replaced by the new mobile surface). So this feature's UI
bits — the "reopened X" capture receipt, the complete/uncomplete flow, any reactivation undo/toggle — are
**specified as a contract the live surface renders**, NOT built into `overlay_daily.html`'s internals.
What the agent OWNS is surface-agnostic: the backend endpoints and the session `created`-record shape
(`action:"reactivate"` + `name`) the surface reads. If `overlay_daily.html` is still the live surface when
the agent runs, an interim receipt line there is fine; if the new surface has landed, hand it the record
shape + the "reopened X" string — do **not** invest in the dying file's `renderSession` internals. (The new
design already carries `as-needed` / `recurring-switch` / `recurring-paused` mockups, so confirm the
receipt + the Add-path reactivation are in its scope.)

## Natural cut line (if shipping incrementally)

- **Tasks 1–4 = the state machine.** After these, an as-needed task can be on/off, surfaces daily while
  on, and completes to off. June's tick-list can drive it. This alone closes the core friction.
- **Tasks 5–6 = the "just say it" entry points** (Add, then Focus). These are what June asked me to
  build; Task 6 (Focus) is the heaviest. They can land after 1–4 if needed.
- **Task 7 = required live verify + cross-family review.** Never skipped.

## Explicitly out of scope (state and hold)

- **The explicit "turn these on" tick-list UI** — June builds it elsewhere (writes the same field).
- **The see-all-switched-off-routines surface list** — June builds it.
- **Reclassifying June's real data** (e.g. "Do the dishes" `Daily` → `as_needed`) — a data pass she runs
  when she wants; not a build task. This plan is verified with `CD-TEST` objects, not her real chores.
- **General re-mention → update-existing recognition** and **"still true?" staleness nudges** — the
  broader `docs/create_vs_update_design.md` thread.
- **Field-population gaps** (dependency signal, Project reaching-for/deadline) — separate capture-side
  work from the 2026-07-17 B1 audit.
- **`Active` on unset-interval (never-configured) recurrings.** Only `interval_unit == "as_needed"` gains
  active-surfacing. An unset interval stays off (that's the surface-list's concern, June's).
- **Universal active/paused on *scheduled* recurrings** (the fuller "pause a 'trash every Tuesday'" ask).
  This plan is deliberately `as_needed`-only; scheduled-recurring pause is a later increment on the SAME
  `Active` field (added in Task 1), not a gap here. Deliberate scope, not an oversight.

## Design decisions (these govern the tasks)

1. **`Active` is a checkbox on the Recurring type — a universal "surface this or not" switch.** For an
   `as_needed` task it is the whole on/off (off by default; asking turns it on; completing turns it off),
   and `Active = false` always means one thing: *suppressed until reactivated.* Scheduled recurrings
   default to on and are untouched now; **pausing a scheduled recurring is the intended NEXT increment on
   this SAME field** (June, 2026-07-17) — not built here, but the field is shaped to carry it without a
   second concept. Not mapped onto status/engagement (Recurring has neither; overloading a multi-state/
   affect field to carry a boolean is the conflation the no-flattening guard forbids). Default absent/
   false = off. **Completion and the switch are separate axes:** for `as_needed`, completing also flips
   `Active` off (done = done-until-re-asked); for a scheduled recurring, completing does NOT touch `Active`
   (it stays on its cadence). That one kind-specific coupling is the only branch (decision 3).
2. **"On" means surfaces every day until done** — an active `as_needed` item is "due" every day
   (`today_fixed_time` returns `True`), independent of any cadence field.
3. **"Complete" on an active as-needed task = a real deactivation** — writes `Active = false` (read-back)
   AND flips the display cache to checked-for-today. This differs from a scheduled recurring, whose
   "done" is cache-only and resurfaces next day. Completion routing branches on task kind; `as_needed`
   is checked **before** `recurring`, because an active as-needed row is flagged both.
4. **Turning on is the "just say it" path** — June names the task in plain language; the confirmation is
   the receipt (Add) or the reflect-back (Focus). Match her words to her existing as-needed tasks; a
   confident match reactivates; **an unsure match creates rather than duplicates-silently, and the
   receipt shows "created" vs "reopened" so she can see + fix it** (the weed is headless — "ask" is the
   after-the-fact receipt, per the system's write-immediately-correct-after idiom).

## File Structure

- `scripts/build_recurring.py` — reshape the Recurring schema: add `Active` + mirror Task's situated
  fields, drop the retired `Has target`/`Target` (Task 1).
- `scripts/orient_map.py`, `scripts/verify_model.py` — drop the retired `Has target`/`Target` reads so
  the model verifies after the reshape (Task 1).
- `scripts/datetime_seam.py` — read `active`; an active `as_needed` item is due daily; thread an
  `as_needed` marker out of `recurring_items_for_today` (Task 2).
- `scripts/reactivation_log.py` — **NEW.** Append-only jsonl learning signal for on/off changes (Task 3).
- `scripts/recurring_active.py` — **NEW.** The `set_recurring_active` primitive (Task 3) — a neutral leaf
  module (imports `gsdo_objects` + `reactivation_log`, does its own fetch) so `capture_generate` can call it
  without the `server → capture_generate` cycle.
- `scripts/plan_generate.py` — re-attach `as_needed` by id after LLM composition (`as_needed_ids`), the SAME
  way `recurring` is re-attached — the seam without which the row loses the flag (Task 4).
- `scripts/server.py` — `import recurring_active`; factor `complete_task_row`/`uncomplete_task_row`;
  `/api/complete` + `/api/uncomplete` route active-as-needed through the primitive (Task 4); the Add path
  (Task 5) and Focus commit (Task 6) call it; a `/api/recurring/active` deactivate endpoint for undo (Task 5).
- `scripts/plan_store.py` — `is_as_needed_item` predicate (Task 4).
- `scripts/daily_plan.py` — carry `as_needed` onto the plan row alongside `recurring` at every row-origin (Task 4).
- `scripts/capture_generate.py` — weed contract gains an existing-as-needed list + `reactivate` action;
  `capture()` branches to activate; receipt record carries it (Task 5).
- `prompts/weeding_gate.md` — an as-needed-reactivation noticing line (Task 5).
- **Frontend = surface contract, NOT this file** — the "reopened X" receipt (Task 5). `docs/overlay_daily.html`
  is **being retired**; build the record shape + endpoint, the live surface renders it. See the Coordination note.
- `scripts/focus_period_generate.py` / `_adapter.py` — `reactivate_tasks` output key + reflect-back item
  + write branch (Task 6).
- Tests: `tests/test_as_needed_reactivation.py` (NEW), `tests/test_reactivation_log.py` (NEW), plus
  additions to `tests/test_datetime_seam.py`, `tests/test_capture_generate.py`, focus-period tests.

---

### Task 1: Reshape the Recurring type — add `Active`, mirror Task's fields, drop retired Practice/Routine (schema)

**Files:**
- Modify: `scripts/build_recurring.py:7-28` (`build_recurring`).
- Modify: `scripts/orient_map.py` (drop the `Has target`/`Target` display fetch — near `:659`, re-derive live).
- Modify: `scripts/verify_model.py` (drop `Has target`/`Target` from the Recurring expected-property list).
- Verify: live schema via `scripts/describe_model.py`.

**Why this is bigger than just `Active` (three decided schema changes ride together):** `build_recurring.py`
is the ONLY place the Recurring type's schema is reshaped in this whole body of work, so doing it once
avoids three separate model rebuilds. The three: (a) the `Active` checkbox **this feature** needs;
(b) **mirror Task's situated fields onto Recurring** — a Recurring should carry the same fields a Task
does (decided separately, "Recurring mirrors Task"); (c) **remove the retired `Has target`/`Target`** —
the Practice-vs-Routine distinction is cut (nothing reads it; a recurring is defined by its interval
alone). **(b) and (c) are NOT the as-needed feature** — they are co-located decided schema work folded in
because Task 1 already reshapes this exact file. The spec these come from is MCP-only (not in the repo),
so the full field set is spelled out here; `build_task.py` (IN the repo) is the source for each field's
exact declaration.

**Interfaces:**
- Produces: the Recurring type carries a new `Active` (checkbox) — its generated **key is discovered
  here** (checkbox keys may be bare `active` or prefixed `gsdo_active`) and recorded for Task 2 — plus
  Task's shared situated fields; and no longer carries `Has target`/`Target`.

- [x] **Step 1: Rewrite `build_recurring` to the reshaped schema.** It (1) DROPS `Has target` / `Target`,
  (2) ADDS Task's fields by REUSING Task's keys — call `ensure_property` with the **exact same display
  name + type + options as `build_task.py`** (`ensure_property` is idempotent by display name, so a match
  returns Task's existing property and shares its key; a mismatched name silently mints a DUPLICATE), and
  (3) ADDS the new `Active` checkbox:

```python
def build_recurring():
    p_freq    = g.ensure_property("Frequency", "select", ["Daily", "Weekly", "As-needed"])
    p_project = g.ensure_property("Project link", "objects")  # Recurring's OWN field (read as gsdo_project_link) — NOT Task's built-in linked_projects
    p_context = g.ensure_property("Context", "text")          # reused
    # time-anchor fields (fixed appointments, e.g. weekly therapy):
    p_dow     = g.ensure_property("Day of week", "multi_select",
                                  ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    p_dom     = g.ensure_property("Day of month", "number")   # 1-31 anchor for monthly items
    p_tod     = g.ensure_property("Time of day", "text")      # "HH:MM"
    p_dur     = g.ensure_property("Duration min", "number")   # reused from Task
    # interval model {unit, count} is canonical; Frequency kept for display/legacy, not queried.
    p_iunit   = g.ensure_property("Interval unit", "select", ["day", "week", "month", "as_needed"])
    p_icount  = g.ensure_property("Interval count", "number")
    # Recurring-mirrors-Task: reuse Task's exact keys (shared, NOT duplicated). Match build_task.py
    # VERBATIM (name + type + options) or ensure_property mints a NEW property instead of reusing.
    p_clarify    = g.ensure_property("Needs clarifying", "checkbox")   # build_task.py:16
    p_blocked    = g.ensure_property("Blocked on", "text")             # build_task.py:20
    p_affective  = g.ensure_property("Affective", "text")             # build_task.py:21 — capacity signal, NEVER scalar-flatten (guard #3)
    p_access     = g.ensure_property("Access conditions", "multi_select",
                                     ["Can-be-done-lying-down", "Involves-leaving-house",
                                      "Requires-talking-to-a-person"])  # build_task.py:22-24 verbatim
    p_access_nts = g.ensure_property("Access notes", "text")           # build_task.py:25
    p_autonomous = g.ensure_property("AI autonomous", "checkbox")      # build_task.py:26
    p_docs       = g.ensure_property("Relevant docs", "text")          # build_task.py:27
    # as-needed on/off (THIS feature): an active as_needed item surfaces every day until completed.
    p_active     = g.ensure_property("Active", "checkbox")
    key = g.ensure_type("Recurring", "Recurring",
                        [p_freq, p_project, p_context,
                         p_dow, p_dom, p_tod, p_dur, p_iunit, p_icount,
                         p_clarify, p_blocked, p_affective, p_access, p_access_nts,
                         p_autonomous, p_docs, p_active])
    print(f"[ok] Recurring type ready: key={key}")
    return key
```
  ⚠️ Before running, **re-derive the live shape**: confirm each reused field's `ensure_property` call
  still matches `build_task.py` at edit time (line numbers move — copy the live call verbatim). The
  `Access conditions` options live in `build_task.py`; §6's later additions (`Requires-deep-thinking`,
  `Involves-bureaucracy`, `Induces-pain`) get added THERE and Recurring inherits them via the shared key
  — do **not** re-list or edit those options here.

  **Which Task fields to mirror (resolve the prose-vs-code divergence a reviewer flagged):** the mirrored
  set is EXACTLY the situated fields in the code above — Needs clarifying, Blocked on, Affective, Access
  conditions, Access notes, AI autonomous, Relevant docs. Task's one-time-instance lifecycle/scheduling
  fields (`Task status`, `Scheduled`, `Last surfaced`, `Duration source` in `build_task.py`) are
  **deliberately NOT mirrored** — they describe a single task instance, not a recurrence template. (If
  June's separate "Recurring mirrors Task" decision intended any of those, add it here with build_task.py's
  verbatim call; the default is the situated set only. Flag it, don't silently expand.)

- [x] **Step 2: Remove the retired fields from the two readers.**
  - `scripts/orient_map.py` (~`:659`) — drop `"Has target"`, `"Target"` from the fetched display list.
  - `scripts/verify_model.py` — drop `Has target` / `Target` (likely `"GSDO Has target"`, `"GSDO Target"`)
    from the Recurring expected-property list, or `build_model.py`'s verify FAILS after the type change.
  (Verified safe: `datetime_seam` / `daily_plan` / `plan_generate` never read `has_target`/`target` — no
  scheduling consumer. Leave the stale properties on existing Anytype objects; harmless, no reader.)

- [x] **Step 3: Rebuild + verify the model (main agent, Bash).** `ensure_*` is idempotent.
`python3 scripts/build_model.py`
Expected: ends with `== VERIFY ==` and exit 0 (verify passes because the expected list dropped the two fields).

- [x] **Step 4: Confirm live + capture the real `Active` key (main agent, Bash).**
`python3 scripts/describe_model.py` — confirm `Recurring` now lists `Active` (checkbox) + the mirrored
Task fields, and NO `Has target`/`Target`. **Also assert each mirrored field resolves to Task's SAME key,
not just that it appears** — a mismatched name/option-spelling silently mints a NEW-keyed duplicate that
describe_model happily shows, and then a later `pval("gsdo_duration_min", …)` read-by-key returns None at
runtime. Compare each mirrored field's key on Recurring against its key on Task in the describe output;
they must be identical. **Record the generated `Active` key** (raw object fetch or describe output) and
write it into Task 2's read line. Do not assume it — the read in Task 2 depends on the real key.

- [x] **Step 5: Commit as TWO commits (main agent, Bash)** — so the as-needed feature has an independent
  rollback point (author-review ask; the tick-list needs only `Active`). Stage the `Active` add first,
  then the co-located schema hygiene:
```bash
# 1) the feature's field alone (stage just the p_active line + its slot in ensure_type):
git add -p scripts/build_recurring.py     # accept ONLY the Active hunks
git commit -m "feat(schema): add Active checkbox to Recurring (as-needed on/off state)"
# 2) the co-located schema work (mirror Task's situated fields; drop retired has_target/target):
git add scripts/build_recurring.py scripts/orient_map.py scripts/verify_model.py
git commit -m "refactor(schema): Recurring mirrors Task's situated fields; drop retired has_target/target"
```
If `git add -p` can't cleanly separate the hunks, land one commit titled for the feature — the split is a
rollback nicety, not a correctness requirement.

---

### Task 2: Surfacing — an active as-needed task is due every day

**Files:**
- Modify: `scripts/datetime_seam.py:88-135` (`today_fixed_time`), `:138-175` (`recurring_items_for_today`,
  the per-key reads at ~156-164 and the result dict at ~166-174).
- Test: `tests/test_datetime_seam.py` (append) or `tests/test_as_needed_reactivation.py`.

**Interfaces:**
- Consumes: the `Active` property from Task 1 (real key recorded there).
- Produces: `today_fixed_time(item, today)` returns `(True, clock)` for an item with
  `interval_unit == "as_needed"` **and** truthy `active`; `(False, clock)` when as_needed but inactive
  (unchanged for every scheduled unit and for unset interval). `recurring_items_for_today` result dicts
  gain `"as_needed": bool` so downstream can route completion.

- [x] **Step 1: Write the failing unit tests** (deterministic, no network) in
  `tests/test_as_needed_reactivation.py`:

```python
import datetime as dt, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import datetime_seam as ds


def test_active_as_needed_is_due_every_day():
    item = {"interval_unit": "as_needed", "active": True}
    for d in (dt.date(2026, 7, 17), dt.date(2026, 7, 18), dt.date(2026, 8, 1)):
        due, _ = ds.today_fixed_time(item, d)
        assert due is True


def test_inactive_as_needed_is_never_due():
    due, _ = ds.today_fixed_time({"interval_unit": "as_needed", "active": False}, dt.date(2026, 7, 17))
    assert due is False
    due2, _ = ds.today_fixed_time({"interval_unit": "as_needed"}, dt.date(2026, 7, 17))  # absent = off
    assert due2 is False


def test_scheduled_recurring_ignores_active():
    # a daily task is due regardless of active; active must not perturb scheduled units
    due, _ = ds.today_fixed_time({"interval_unit": "day", "active": False}, dt.date(2026, 7, 17))
    assert due is True


def test_unset_interval_stays_off_even_if_active():
    # never-configured (no unit) is the surface-list's concern, not this feature
    due, _ = ds.today_fixed_time({"interval_unit": None, "active": True}, dt.date(2026, 7, 17))
    assert due is False
```

- [x] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_as_needed_reactivation.py -k "as_needed or scheduled or unset_interval" -v`
Expected: FAIL (as_needed currently always returns False).

- [x] **Step 3: Implement the surfacing branch.** In `today_fixed_time`, replace the current
  `if not unit or unit == "as_needed": return False, clock` with a split that honors `active` for
  as_needed only:

```python
    if unit == "as_needed":
        # An as-needed task is off until asked-for. When Active, it is "due" every day until June
        # completes it (which writes Active=false) — it keeps resurfacing. (June, 2026-07-17.)
        return bool(item.get("active")), clock
    if not unit:
        return False, clock   # never-configured stays off — not this feature (the surface list's)
```

- [x] **Step 4: Read `active` into the item dict + emit `as_needed`.** In `recurring_items_for_today`,
  add the active read (USE THE REAL KEY from Task 1 — shown here as `gsdo_active`, confirm it) to the
  `item` dict, and add `as_needed` to the appended result:

```python
        item = {
            "id":             obj.get("id"),
            "name":           obj.get("name"),
            "interval_unit":  (pval("interval_unit", "select") or {}).get("name"),
            "interval_count": pval("interval_count", "number"),
            "day_of_week":    pval("gsdo_day_of_week", "multi_select") or [],
            "day_of_month":   pval("day_of_month", "number"),
            "time_of_day":    pval("gsdo_time_of_day", "text"),
            "duration_min":   pval("gsdo_duration_min", "number"),
            "active":         bool(pval("gsdo_active", "checkbox")),   # ← real key from Task 1
        }
        due, clock = today_fixed_time(item, today)
        if not due:
            continue
        results.append({
            "id":           item["id"],
            "name":         item["name"],
            "fixed_time":   dt.datetime.combine(today, clock) if clock else None,
            "duration_min": item["duration_min"] or DEFAULT_DURATION_MIN,
            "as_needed":    item["interval_unit"] == "as_needed",   # ← route completion in Task 4
        })
```

- [x] **Step 5: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_as_needed_reactivation.py tests/test_datetime_seam.py -v`
Expected: PASS, no regressions.

- [x] **Step 6: Commit (main agent, Bash).**
```bash
git add scripts/datetime_seam.py tests/test_as_needed_reactivation.py
git commit -m "feat(surfacing): an active as-needed recurring is due every day; emit as_needed marker"
```

---

### Task 3: The shared write primitive — `set_recurring_active` + the reactivation log

**Files:**
- Create: `scripts/reactivation_log.py` (mirror `engagement_log.py`).
- Create: `scripts/recurring_active.py` (**NEW — the neutral home for `set_recurring_active`**). It imports
  `gsdo_objects` + `reactivation_log` and does its OWN by-id fetch (via `anytype_test.call` +
  `gsdo_anytype.get_space_id`, the same GET `capture_generate._get_object:325-330` uses) — it does **NOT**
  import `capture_generate`. Why a new module and not a `server.py` function: `capture_generate` (Task 5)
  must call the primitive, but `server` already imports `capture_generate`, so a primitive living in `server`
  (or one that calls `capture_generate._get_object`) is a circular import. A leaf module both `server` and
  `capture_generate` import breaks the cycle and keeps ONE writer.
- Modify: `scripts/server.py` — `import recurring_active` (completion routes call `recurring_active.set_recurring_active`).
- Test: `tests/test_reactivation_log.py` (NEW), `tests/test_as_needed_reactivation.py` (append).

**Interfaces:**
- Produces:
  - `reactivation_log.log_change(recurring_id, name, old, new, path=None) -> None` — append
    `{ts, date, recurring_id, name, old, new}` **only when `old != new`** (`old`/`new` are booleans).
  - `reactivation_log.read_changes(path=None) -> list[dict]` — tolerant reader (missing file → `[]`).
  - `recurring_active.set_recurring_active(rid, active) -> bool` — reads the PRE-write `Active`, writes via
    `gsdo_objects.update(rid, {"Active": active})`, re-fetches, asserts by display name, raises on mismatch,
    logs the (pre → new) toggle, returns the new `active`. **The primitive reads its own before-state — there
    is NO `old` param.** (Callers don't know it, and the log's no-op guard must fire on a real re-tap, not
    only when a caller happens to pass `old` — the earlier `old=None`-default version made the guard dead
    code, since every caller omitted it.)
- Consumes: `gsdo_objects.update` + a by-id object fetch it does itself (NOT `capture_generate`, to avoid the cycle).

- [x] **Step 1: Write the failing log tests** in `tests/test_reactivation_log.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import reactivation_log as rl


def test_logs_a_real_toggle(cd_sandbox):
    rl.log_change("rid1", "Clean the fridge", False, True)
    recs = rl.read_changes()
    assert recs and recs[-1]["old"] is False and recs[-1]["new"] is True
    assert recs[-1]["recurring_id"] == "rid1" and recs[-1]["name"] == "Clean the fridge" and "ts" in recs[-1]


def test_noop_when_unchanged(cd_sandbox):
    rl.log_change("rid1", "Clean the fridge", True, True)
    assert rl.read_changes() == []


def test_read_missing_file_is_empty(cd_sandbox):
    assert rl.read_changes() == []
```

*Implementer: `cd_sandbox` is the repo fixture that redirects `cd_paths` to the test sandbox — confirm
its real name in `conftest.py`/existing tests (`test_engagement_log.py` uses the same); match it.*

- [x] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_reactivation_log.py -v` — Expected: FAIL (`No module named 'reactivation_log'`).

- [x] **Step 3: Implement the log** (copy `engagement_log.py` verbatim-idiom; change the record shape):

```python
#!/usr/bin/env python3
"""Reactivation log — the learning SIGNAL for as-needed on/off changes.

When an as-needed task is turned on (asked for in Add/Focus, or June's tick-list) or off (completed),
the old->new toggle is appended here. COLLECT half only: no reader consumes it yet (mirrors
engagement_log — mine later per the deferred learning-loops subsystem). Record shape
{ts, date, recurring_id, name, old, new} with boolean old/new. Do NOT treat as a live feedback loop.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths


def _path(path=None):
    return path or cd_paths.data_file("reactivation_log.jsonl")


def log_change(recurring_id, name, old, new, path=None):
    if old == new:
        return   # a re-tap landing on the same state is not a change — nothing to learn
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "date": dt.date.today().isoformat(),
           "recurring_id": recurring_id, "name": name, "old": old, "new": new}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_changes(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
```

- [x] **Step 4: Write the failing primitive test** in `tests/test_as_needed_reactivation.py`:

```python
def test_set_recurring_active_writes_reads_logs(monkeypatch):
    import recurring_active as ra
    updates, logged = {}, {}
    # the primitive fetches TWICE: BEFORE (off) then AFTER (on) the write
    states = iter([{"name": "Clean the fridge", "properties": [{"name": "Active", "checkbox": False}]},
                   {"name": "Clean the fridge", "properties": [{"name": "Active", "checkbox": True}]}])
    monkeypatch.setattr(ra, "_get_object", lambda rid: next(states))
    monkeypatch.setattr(ra.gsdo_objects, "update",
                        lambda rid, properties: updates.update({rid: properties}))
    monkeypatch.setattr(ra.reactivation_log, "log_change",
                        lambda rid, name, old, new: logged.update({"c": (rid, old, new)}))
    out = ra.set_recurring_active("rid1", True)
    assert updates["rid1"]["Active"] is True
    assert out is True and logged["c"] == ("rid1", False, True)   # old read from pre-state, not None


def test_set_recurring_active_noops_log_on_retap(monkeypatch):
    # re-activating an ALREADY-active task: pre-state == new, so the log no-op fires (a real re-tap)
    import recurring_active as ra
    logged = {}
    on = {"name": "X", "properties": [{"name": "Active", "checkbox": True}]}
    monkeypatch.setattr(ra, "_get_object", lambda rid: on)          # pre == post == on
    monkeypatch.setattr(ra.gsdo_objects, "update", lambda rid, properties: None)
    monkeypatch.setattr(ra.reactivation_log, "log_change",
                        lambda rid, name, old, new: logged.update({"c": True}) if old != new else None)
    ra.set_recurring_active("rid1", True)
    assert logged == {}   # old(True) == new(True): nothing logged — the guard is now REACHABLE


def test_set_recurring_active_raises_on_readback_mismatch(monkeypatch):
    import recurring_active as ra, pytest
    off = {"name": "X", "properties": [{"name": "Active", "checkbox": False}]}
    monkeypatch.setattr(ra, "_get_object", lambda rid: off)         # write True, but read-back stays False
    monkeypatch.setattr(ra.gsdo_objects, "update", lambda rid, properties: None)
    with pytest.raises(RuntimeError):
        ra.set_recurring_active("rid1", True)
```

*Implementer: the primitive computes `old` itself from the pre-write fetch — callers never pass it. Match
the real low-level fetch (`anytype_test.call` + `gsdo_anytype.get_space_id`); the module imports
`gsdo_objects` + `reactivation_log` and does its own GET — it must NOT import `capture_generate`.*

- [x] **Step 5: Run to verify it fails, then implement** (main agent, Bash for the run). Create
  `scripts/recurring_active.py` (its own by-id fetch; NO `capture_generate` import), and `import
  recurring_active` in `server.py`:

```python
#!/usr/bin/env python3
"""The SINGLE writer of a Recurring's `Active` flag (as-needed on/off). Completion, Add, Focus, and June's
tick-list all funnel here — no path re-implements the write/read-back/log. A neutral leaf module so
`capture_generate` can call it without the `server → capture_generate` import cycle."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import gsdo_objects
import reactivation_log
from anytype_test import call


def _get_object(rid):
    # same GET as capture_generate._get_object:325-330 — inlined so this module imports no caller.
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{rid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"could not read Recurring {rid!r}: {st} {b}")
    return b["object"]


def _active_of(obj):
    by_name = {p.get("name"): p for p in obj.get("properties", [])}
    return (by_name.get("Active") or {}).get("checkbox")


def set_recurring_active(rid, active):
    """Read Active's PRE-state, write the new value, read it BACK BY DISPLAY NAME to prove it persisted,
    then log the (old → new) toggle. `active` is a bool; returns the new state. Reads its own before-state
    so the log no-ops correctly on a real re-tap — callers pass no `old`."""
    before = _get_object(rid)
    old = _active_of(before)
    gsdo_objects.update(rid, properties={"Active": active})
    after = _get_object(rid)
    got = _active_of(after)
    if bool(got) != bool(active):
        raise RuntimeError(f"Active read-back mismatch for {rid!r}: wrote {active!r}, got {got!r}")
    reactivation_log.log_change(rid, after.get("name"),
                                bool(old) if old is not None else None, bool(active))
    return active
```

`python3 -m pytest tests/test_reactivation_log.py tests/test_as_needed_reactivation.py -k "reactivation or set_recurring_active" -v`
Expected: PASS.

- [x] **Step 6: Commit (main agent, Bash).**
```bash
git add scripts/reactivation_log.py scripts/recurring_active.py scripts/server.py tests/test_reactivation_log.py tests/test_as_needed_reactivation.py
git commit -m "feat(reactivation): set_recurring_active primitive (pre-read+write+read-back+log) in neutral module + reactivation log"
```

---

### Task 4: Completion branch — completing an active as-needed task deactivates it

**Files:**
- Modify: `scripts/plan_generate.py` (~`:999`/`:1054`) — **the re-attach-by-id seam. THIS is the load-bearing
  edit** (all three review lenses converged here): flags do NOT survive LLM composition; a `recurring_ids`
  set stamps `item["recurring"]=True` after the round-trip, and `as_needed` must be stamped the SAME way or
  it silently dies on the real plan while unit tests pass. Add an `as_needed_ids` set beside `recurring_ids`.
- Modify: `scripts/daily_plan.py` — carry `as_needed` onto the row at EVERY origin where `recurring`/
  `is_recurring` is set: the due-but-timeless fold (~`:272`) AND the timed origins (`blocks_from_scheduled`
  ~`:914`, the timed-anchor path ~`:947`, `format_appointments` ~`:981` — a reviewer found THREE origins,
  not one; re-derive live).
- Modify: `scripts/plan_store.py:161-172` — add `is_as_needed_item` beside `is_recurring_item`.
- Modify: `scripts/server.py:436-469` (`/api/complete`) and `:597-624` (`/api/uncomplete`) — factor
  `complete_task_row`/`uncomplete_task_row`, route as-needed **before** the recurring check, call
  `recurring_active.set_recurring_active`.
- Test: `tests/test_as_needed_reactivation.py` (append), `tests/test_plan_store*.py`.

**Interfaces:**
- Consumes: `as_needed` from Task 2's result dict; `recurring_active.set_recurring_active` from Task 3.
- Produces: `plan_store.is_as_needed_item(task_id) -> bool`; `/api/complete` on an active as-needed row
  writes `Active=false` (real) + flips the cache to done; `/api/uncomplete` writes `Active=true` + un-flips.

- [x] **Step 1: Carry `as_needed` onto the plan row — through ALL the same places `recurring` rides.**
  This is where the feature silently dies if built from doc-text instead of the live runtime (build-frame
  guard). The path is THREE hops:
  1. **Fold (pre-LLM):** the timeless fold builds a synthetic dict with `"is_recurring": True` (~`:272`).
     Add `"as_needed": r.get("as_needed", False)` there.
  2. **Re-attach (post-LLM) — the seam the first draft MISSED.** Flags on that dict do NOT survive LLM
     composition; `plan_generate` re-stamps them by id afterward: `recurring_ids = {t["id"] for t in
     identity if t.get("is_recurring")}` (~`:999`) then `if tid in recurring_ids: item["recurring"]=True`
     (~`:1054`). **Add the parallel `as_needed_ids = {t["id"] for t in identity if t.get("as_needed")}`
     and `if tid in as_needed_ids: item["as_needed"]=True`.** Without this the row NEVER carries
     `as_needed`, `is_as_needed_item` is always False, completion falls to the cache-only flip, and the
     task resurfaces forever — while every unit test (which hand-builds rows) passes. Re-derive the live
     lines; the variable names here are from the reviewer's live trace.
  3. **Row-origins (read the re-attached flag):** `daily_plan` builds the final row at THREE origins that
     each set `recurring` — `blocks_from_scheduled` (~`:914`), the timed-anchor path (~`:947`), and
     `format_appointments` (~`:981`). Set `row["as_needed"] = it.get("as_needed")` alongside `recurring`
     at **each** (a timed as-needed task routes through the timed origins, not the fold). Re-derive live.
  Do NOT invent a parallel channel — mirror `recurring` exactly at every site.

- [x] **Step 2: Write the failing predicate + routing tests:**

```python
def test_is_as_needed_item_reads_the_row_flag(monkeypatch):
    import plan_store
    monkeypatch.setattr(plan_store, "load_plan",
                        lambda: {"items": [{"id": "r1", "recurring": True, "as_needed": True},
                                           {"id": "r2", "recurring": True}]})
    assert plan_store.is_as_needed_item("r1") is True
    assert plan_store.is_as_needed_item("r2") is False   # scheduled recurring, not as-needed


def test_complete_active_as_needed_deactivates_and_checks(monkeypatch):
    import server
    calls = {}
    monkeypatch.setattr(server.plan_store, "is_as_needed_item", lambda tid: tid == "r1")
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.update({"deact": (rid, active)}) or active)
    monkeypatch.setattr(server.plan_store, "mark_item_done",
                        lambda tid: calls.update({"cache_done": tid}) or {"items": []})
    code, body = server.complete_task_row("r1")   # module-level helper the route calls (Step 4)
    assert code == 200
    assert calls["deact"] == ("r1", False)      # real deactivation
    assert calls["cache_done"] == "r1"          # still shows checked today
    assert body["completed"]["as_needed"] is True
```

*Implementer: the `/api/complete` body is currently inline in `do_POST`, and the existing test idiom (the
`live_server` HTTP fixture) cannot assert "the primitive was called with (r1, False)". So **factor a
module-level `complete_task_row(task_id) -> (code, body)`** and make the route a thin shell that calls it
then `self._send(code, body)`. Test `complete_task_row` directly (above); the HTTP path is covered live in
Task 7. Do the symmetric `uncomplete_task_row`. This thin-route refactor is ALSO the shared substrate
threads 2–3 (persistence, recording recurring completions) build on — keep the route a shell.*

- [x] **Step 3: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_as_needed_reactivation.py -k "as_needed_item or deactivates" -v` — Expected: FAIL.

- [x] **Step 4: Implement.** In `plan_store.py`, beside `is_recurring_item`:

```python
def is_as_needed_item(task_id):
    """True if the cached plan carries this id on a row flagged `as_needed` (an active as-needed task,
    marked in daily_plan). The completion endpoint reads this BEFORE is_recurring_item to route a
    checkoff to a real Active=false write (done-until-asked-again) instead of the cache-only
    'done for today' a scheduled recurring gets."""
    plan = load_plan()
    if plan is None:
        return False
    for item in _iter_items(plan):
        if item.get("id") == task_id and item.get("as_needed"):
            return True
    return False
```

In `server.py`, factor `complete_task_row(task_id) -> (code, body)` (the `/api/complete` route becomes a
thin shell: `code, body = complete_task_row(task_id); self._send(code, body)`). Route as-needed **before**
the `is_recurring_item` branch:

```python
def complete_task_row(task_id):
    # An active as-needed task: "done" means done-until-asked-again — write Active=false (a REAL Anytype
    # change, read-back), then flip the cache so it still shows checked today. Checked BEFORE
    # is_recurring_item, because an active as-needed row is flagged BOTH.
    if plan_store.is_as_needed_item(task_id):
        try:
            recurring_active.set_recurring_active(task_id, False)
        except Exception as e:
            return 500, {"error": str(e)}
        plan = plan_store.mark_item_done(task_id)
        return 200, {"completed": {"id": task_id, "done": True, "as_needed": True},
                     "plan": plan or {"empty": True}}
    # ... existing is_recurring_item / real-task branches, unchanged, each returning (code, body) ...
```

Symmetric `uncomplete_task_row(task_id)`: before its `is_recurring_item` branch, call
`recurring_active.set_recurring_active(task_id, True)` then `plan_store.mark_item_undone(task_id)`, returning
`200, {"uncompleted": {"id": task_id, "done": False, "as_needed": True}, "plan": ...}`.

- [x] **Step 5: Run tests to verify pass, then the plan_store + server suites (main agent, Bash).**
`python3 -m pytest tests/test_as_needed_reactivation.py tests/ -k "as_needed or plan_store or complete" -v`
Expected: PASS, no regressions.

- [x] **Step 6: Commit (main agent, Bash).**
```bash
git add scripts/plan_generate.py scripts/daily_plan.py scripts/plan_store.py scripts/server.py tests/test_as_needed_reactivation.py
git commit -m "feat(complete): completing an active as-needed task deactivates it (real write), not cache-only"
```

---

### Task 5: Add-box entry point — weeding recognizes & reactivates an existing as-needed task

**Files:**
- Modify: `scripts/capture_generate.py` — the weed context builder (where EXISTING GOALS & PROJECTS
  tokens are assembled), `_WEED_JSON_INSTRUCTION:151-245` (add the `reactivate` action + a
  `reactivate_ref`), `parse_weed:294-320` (default the new field), the `capture()` item loop `:490-530`
  (branch to activate before `_create_one`).
- Modify: `prompts/weeding_gate.md` — a reactivation-noticing line.
- Surface contract (NOT an edit to the retiring `docs/overlay_daily.html`): the "reopened X" receipt the
  live surface renders from the `created` record — see the Coordination note. (If the old overlay is still
  live at build time, an interim line in `renderSession` ~`:2668-2789` is acceptable; don't invest if retired.)
- Test: `tests/test_capture_generate.py` (append; parse + branch, no network).

**Interfaces:**
- Consumes: `recurring_active.set_recurring_active` (Task 3) — `import recurring_active` in
  `capture_generate` (the neutral leaf module has no cycle; this is exactly why Task 3 put the primitive there).
- Produces: a weed item may carry `action == "reactivate"` with `reactivate_ref` (an `R#` token → an
  existing as-needed Recurring id). Such an item activates the existing task instead of creating one; the
  session `created`-record carries `action:"reactivate"` + `name` so the receipt renders "reopened X".

- [x] **Step 1: Feed existing as-needed tasks into the weed context.** Where the weed prompt's EXISTING
  GOALS & PROJECTS token list is built, add an **EXISTING AS-NEEDED TASKS** section listing June's
  Recurring objects with `interval_unit == "as_needed"`, each with an `R#` token → its id (mirror the
  P#/G# token map). *(Trace the real context builder; it currently loads projects/goals for tokens —
  extend it, don't fork it.)*

- [x] **Step 2: Add the `reactivate` action to the contract.** In `_WEED_JSON_INSTRUCTION`, extend the
  `action` enum and add a `reactivate_ref`, with a prose rule:

```
- **Reactivate an existing as-needed task (do NOT create a duplicate).** If an item is June asking to
  do a task that is ALREADY in EXISTING AS-NEEDED TASKS ("do the dishes", "clean the fridge"), set
  `action` = "reactivate" and `reactivate_ref` = its R# token — this turns the existing task back on.
  Only for a clear match to that list. If you're unsure it's the same task, `action` = "create" as
  normal (a duplicate June can see and undo beats silently reactivating the wrong thing).
```
Add `"reactivate_ref": "R2 | null"` to the per-item JSON shape and note `action` now reads
`"create | skip | reactivate"`.

- [x] **Step 3: Default the field in `parse_weed`** (the per-item `setdefault` loop):
```python
            item.setdefault("reactivate_ref", None)
```

- [x] **Step 4: Write the failing tests** (parse + branch):

```python
def test_parse_weed_reads_reactivate_action():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Recurring","name":"Clean the fridge","link":null,"action":"reactivate","reactivate_ref":"R2","reasoning":"r"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["action"] == "reactivate" and item["reactivate_ref"] == "R2"


def test_capture_reactivates_instead_of_creating(monkeypatch, tmp_path):
    # a reactivate item calls the activate primitive with the resolved id, and does NOT create
    activated, created = {}, []
    # ... use the file's _stub pattern; map R2 -> "rid-fridge" in the ref_map the stub builds;
    # assert set_recurring_active("rid-fridge", True) was called and gsdo_objects.create was NOT
    # called for that item; assert the session 'created' record has action=="reactivate".
```

*Implementer: match `_stub`'s real return shape and how it seeds the ref/token map; the reactivate
branch resolves `reactivate_ref` through the same `ref_map` the link tokens use (extend it to carry R#
→ recurring id).*

- [x] **Step 5: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py -k "reactivate" -v` — Expected: FAIL.

- [x] **Step 6: Implement the branch.** In `capture()`'s item loop, before the `_create_one` call, add:

```python
            if item.get("action") == "reactivate":
                rid = ref_map.get(item.get("reactivate_ref"))
                if not rid:
                    session_store.log_failure("capture", "reactivate_unresolved", {"item": item})
                    failed.append({"name": item.get("name"), "error": "reactivate_ref did not resolve"})
                    continue
                try:
                    recurring_active.set_recurring_active(rid, True)  # ONE writer (Task 3); read-back + log inside
                    obj = _get_object(rid)                    # prove + get the real name for the receipt
                    created.append({"id": rid, "type": "Recurring", "name": obj.get("name"),
                                    "action": "reactivate", "project": None,
                                    "alignment_reasoning": item.get("reasoning"),
                                    "when_label": None, "is_today": False})
                except Exception as e:
                    session_store.log_failure("capture", "reactivate_failed",
                                              {"name": item.get("name"), "error": str(e)})
                    failed.append({"name": item.get("name"), "error": str(e)})
                continue
```
*Implementer: `import recurring_active` (Task 3 already relocated the primitive to that neutral leaf
module precisely so `capture_generate` can call it without the `server → capture_generate` cycle).
`_get_object` here is `capture_generate`'s own existing read-back helper. Do NOT re-implement the
write/read-back/log — `recurring_active` is the single writer.*

- [x] **Step 7: Add the noticing line to `prompts/weeding_gate.md`** (near the type-routing / dedup prose):
```
- **Reactivation vs. new.** If June names a task that already exists as an as-needed Recurring (it's in
  the EXISTING AS-NEEDED TASKS list), she's asking to turn it back ON, not to make a new one — mark it
  `action: reactivate`. When unsure it's the same task, create (she can undo); never silently duplicate.
```

- [x] **Step 8: Emit the receipt as a surface contract (NOT an edit to the retiring overlay).** The
  `created` record already carries `action:"reactivate"` + `name` (Step 6) — that IS what the live surface
  renders as "reopened <name>". **Undo of a reopen = turn it back OFF** (`Active=false`) — so it is NOT
  `/api/uncomplete` (that writes `Active=true`, the opposite). Expose a dedicated `/api/recurring/active`
  endpoint taking `{id, active:false}` that calls `recurring_active.set_recurring_active`, and wire the
  receipt's undo to it. **Do not build into `overlay_daily.html`'s
  `renderSession` if it's retired** (see the Coordination note). If the old overlay is still live when you
  run, an interim "reopened X" line there (receipt-line + `undo` idiom, never-silent-on-failure per
  `cycleEngagement`, no engagement/when chip) is acceptable — but the deliverable is the record shape +
  endpoint, not the dying file's internals.

- [x] **Step 9: Run tests to verify pass (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py -v` — Expected: PASS. (Live receipt exercised in Task 7.)

- [x] **Step 10: Commit (main agent, Bash).**
```bash
git add scripts/capture_generate.py prompts/weeding_gate.md docs/overlay_daily.html tests/test_capture_generate.py
git commit -m "feat(capture): weeding reactivates an existing as-needed task instead of duplicating; 'reopened X' receipt"
```

---

### Task 6: Focus-Period entry point — authoring recognizes & reactivates named as-needed tasks

**Files:**
- Modify: `scripts/focus_period_generate.py:53-121` (`build_authoring_prompt` — a `reactivate_tasks`
  output key; the task list is ALREADY injected as grounding at `:78-79`).
- Modify: `scripts/focus_period_adapter.py:131-192` (`reflect_back`/`_ITEM_FIELDS` — a "Reopening" item)
  and `:66-99` (`to_write_properties` — resolve names → as-needed recurring ids for the commit).
- Modify: `scripts/server.py:736-785` (`/api/focus/commit`) — after the period writes, activate the
  resolved as-needed tasks via `recurring_active.set_recurring_active`.
- Test: focus-period test module (append).

**Interfaces:**
- Consumes: `recurring_active.set_recurring_active` (Task 3); the authoring context's task list.
- Produces: authoring output may carry `reactivate_tasks: [name, ...]`; the reflect-back lists them for
  confirmation; commit activates each matched as-needed Recurring.

- [x] **Step 1: Add the output key to the prompt.** In `build_authoring_prompt`, add to the output-keys
  list (the task list is already provided as grounding):
```
- "reactivate_tasks": names from HER CURRENT TASKS/RECURRING list above that she says to pick back up /
  do this period ("keep the dishes going", "I want to get back to cleaning the fridge"). Use the EXACT
  name from that list; [] if she names none. Only tasks she already has — never invent one.
```

- [x] **Step 2: Surface them in the reflect-back.** In `reflect_back`, append an item when
  `fields.get("reactivate_tasks")` is non-empty, so June confirms before commit:
```python
    reactivate = f.get("reactivate_tasks") or []
    if reactivate:
        items.append({"key": "reactivate_tasks", "label": "Reopening", "edit": "text",
                      "display": ", ".join(reactivate)})
```
and add `"reactivate_tasks": ("reactivate_tasks",)` to `_ITEM_FIELDS` so an edit-mode diff marks it.

- [x] **Step 3: Resolve names → ids at commit.** The write path needs each name mapped to its as-needed
  Recurring id. Add a resolver (mirror `author.resolve_project_names_to_ids`, but over as-needed
  Recurring objects) and, in `/api/focus/commit` **after** the period is written, call
  `recurring_active.set_recurring_active(rid, True)` for each resolved id. An unresolved name is surfaced
  (not silently dropped) — collect them and return them in the commit response so the surface can tell June.

- [x] **Step 4: Write the failing tests** (this is the heaviest task — give it real scaffolding, not one-liners):

```python
def test_authoring_prompt_lists_reactivate_tasks_key():
    import focus_period_generate as fpg
    prompt = fpg.build_authoring_prompt(...)          # match the real minimal signature
    assert "reactivate_tasks" in prompt


def test_reflect_back_emits_reopening_when_present():
    import focus_period_adapter as fpa
    items = fpa.reflect_back({"reactivate_tasks": ["Clean the fridge", "Do the dishes"]})   # + other required keys
    reopening = [i for i in items if i["key"] == "reactivate_tasks"]
    assert reopening and reopening[0]["label"] == "Reopening"
    assert "Clean the fridge" in reopening[0]["display"]


def test_reflect_back_omits_reopening_when_absent():
    import focus_period_adapter as fpa
    items = fpa.reflect_back({"reactivate_tasks": []})
    assert not [i for i in items if i["key"] == "reactivate_tasks"]


def test_commit_resolver_maps_known_and_flags_unknown(monkeypatch):
    import focus_period_adapter as fpa
    monkeypatch.setattr(fpa, "<as_needed_name_index_fn>",     # the Step-3 name→id index you add
                        lambda: {"Clean the fridge": "rid-fridge"})
    resolved, unresolved = fpa.resolve_reactivate_names(["Clean the fridge", "Nonexistent"])
    assert resolved == ["rid-fridge"] and unresolved == ["Nonexistent"]   # unknown surfaced, not dropped
```

*Implementer: fill each `...`/`<…>` from the live signatures (`build_authoring_prompt` and `reflect_back`
take a fields/context dict — match its required keys), and name the resolver + its name-index fetch to
whatever you add in Step 3. Commit-activation itself (calling the primitive per resolved id) is exercised
live in Task 7 Step 6.*

- [x] **Step 5: Run to verify they fail, implement, run to pass (main agent, Bash).**
`python3 -m pytest tests/ -k "focus and reactivate" -v` — FAIL → implement → PASS.

- [x] **Step 6: Commit (main agent, Bash).**
```bash
git add scripts/focus_period_generate.py scripts/focus_period_adapter.py scripts/server.py tests/
git commit -m "feat(focus): authoring reactivates named as-needed tasks; reflect-back confirms before commit"
```

---

### Task 7: Integration & end-to-end verify (REQUIRED — do not skip)

A plan is done only when the feature is wired into the running system and observed working on **real
data** — not when unit tests pass (repo build-frame guard: a coherent-but-wrong frame passes the suite).

**Wiring this connects:**
- `Active` field (Task 1) ← read by `datetime_seam` surfacing (Task 2) ← folded into the plan by
  `daily_plan` (Task 4) ← completion routes through `plan_store.is_as_needed_item` → `set_recurring_active`
  (Tasks 3–4). Entry points: `POST /api/capture` → weed `reactivate` branch (Task 5); `POST
  /api/focus/commit` → activate resolved tasks (Task 6). All Active writes funnel through
  `set_recurring_active` (Task 3).

- [x] **Step 1 (main agent, Bash): restart the server** and load **the live daily-plan surface** —
  `docs/overlay_daily.html` if it's still current, or the new mobile surface if it has replaced it
  (`overlay_daily.html` is being retired). Drive the rest of this task's verify through whichever is live.
- [x] **Step 2 (main agent, Bash): make a CD-TEST as-needed task.** Create a Recurring `CD-TEST clean the
  fridge` with `Interval unit = as_needed`, `Active = false`. Read it back.
- [x] **Step 3 (main agent): reactivate via the Add box** — through the `verify` skill, drive a capture:
  *"CD-TEST clean the fridge"*. Confirm the receipt shows **"reopened"** (not "created"), no duplicate
  Recurring was created, and the object now has `Active = true` (read back).
- [x] **Step 4 (main agent, Bash): regenerate June's REAL daily plan** and confirm the CD-TEST as-needed
  task now **surfaces as a checkoffable row**. Regenerate again (simulate the next day) — it **still
  surfaces** (resurface-until-done). This is the live-verify the build-frame guard requires.
- [x] **Step 5 (main agent): complete it** from the overlay. Confirm it shows checked today, the object
  is now `Active = false` (read back), a `reactivation_log` record landed (`old:true,new:false`), and on
  the next plan regeneration it **no longer surfaces** (done-until-asked-again). Then uncomplete →
  `Active = true` again.
- [x] **Step 6 (main agent): reactivate via Focus Period** — author a focus period naming *"CD-TEST
  clean the fridge"*; confirm the reflect-back lists it under "Reopening", commit, and the object is
  `Active = true` (read back).
- [x] **Step 7 (main agent, Bash): scheduled recurrings unchanged** — pick one of June's real scheduled
  recurrings (e.g. a daily chore), confirm completing it is still cache-only "done for today" (no Active
  write, resurfaces next regeneration). Regression guard for the completion branch.
- [x] **Step 8 (main agent, Bash): delete ALL CD-TEST objects** and re-fetch to confirm they're gone.
- [x] **Step 9 (main agent, Bash): full suite, clean tree.** `python3 -m pytest -q` — all green; the
  conftest real-data tripwire did not fire.
- [x] **Step 10: Commit, then cross-family review (main agent, Bash).** Run the non-Claude review
  (`~/.claude/skills/requesting-code-review/github_models_review.py`, **chunked per file with its tests**
  — the API caps ~8k tokens) before the thread closes; triage findings, apply the real ones.
```bash
git add -A
git commit -m "test(reactivation): end-to-end verify as-needed on→surface-daily→complete→off, real plan"
```

## Task 7 — what actually happened (2026-07-17, live against June's real space)

All steps run as direct Python calls against the live Anytype API (server restarted via
`launchctl kickstart -k gui/501/com.june.controlled-drift.server` first — it's a real launchd
service, not a bare process; killed raw PIDs a few times before finding this out, each time it
silently respawned).

- **Step 3 (Add-box reactivation):** real Mistral capture on "CD-TEST clean the fridge" correctly
  produced `action: reactivate`, matched token R1, receipt `created` record showed
  `action: "reactivate"`. Confirmed exactly one CD-TEST object existed afterward (no duplicate) and
  `Active` read back `True`.
- **Step 4 (surfacing) — one real finding, not a feature bug:** the first two `generate_plan()`/
  `reorder()` runs left CD-TEST (and nearly everything else) in `still_here`, not `blocks`. Root
  cause: it was ~9:19pm real time and the scheduler's default `end_time` is 18:00 — `start_time`
  was already past `end_time`, so the flexible-item placement loop broke immediately for every
  candidate task, real or test. Confirmed via `build_context()`: `start_time=21:30, end_time=18:00`.
  Traced a captured raw model response (which DID name CD-TEST, ref `T26`/`T27` on different runs —
  temperature variance) through every stage of the real pipeline
  (`parse_plan → _resolve_ids → _dedup_resolved_items → _drop_deferred_from_plan →
  _ensure_all_tasks_accounted → _retime_clock_plan`) and watched the row carry `recurring: True,
  as_needed: True` intact through every stage up to `_retime_clock_plan`, which is where the
  time-window logic (pre-existing, unrelated to this plan) legitimately dropped it back to
  `still_here` — not a silent loss, an honest one via the accounting guard. Re-ran with an explicit
  widened `end_time` (23:30/23:45, the same `build_context(end_time=...)` parameter a real Focus
  Period's `workday_end` would supply) and CD-TEST composed into a real checkoffable block row with
  `recurring: True, as_needed: True` intact, twice across independent regenerations (resurface-
  until-done confirmed).
- **Step 5 (completion):** `server.complete_task_row` on the real object → `{"completed": {"done":
  True, "as_needed": True}}`, cache flipped `done: True`, **real** `Active` read back `False` (not
  cache-only). `reactivation_log` recorded both the on and off toggles. Confirmed via
  `datetime_seam.recurring_items_for_today` directly (not a full regen — the source-of-truth
  surfacing function itself) that the now-inactive object returns `due=False`. `uncomplete_task_row`
  correctly flipped `Active` back to `True`, read-back confirmed.
- **Step 6 (Focus Period reactivation) — the Critical-fix target case, explicitly:** deactivated
  CD-TEST first (the review that gated this task found the ORIGINAL code could only ever
  re-affirm an already-active item, never actually reactivate an off one — this step exists to
  prove that's fixed). Confirmed live via `focus_period_generate._load_authoring_context()` that
  the OFF task now appears in the grounding list. Drove a real authoring call
  ("I want to pick CD-TEST clean the fridge back up this week") — the real model proposed
  `reactivate_tasks: ["CD-TEST clean the fridge"]` unprompted by any hint beyond the grounding
  list. `reflect_back` showed the "Reopening" item. Ran the exact resolve+activate call
  `/api/focus/commit` makes (`resolve_reactivate_names` → `set_recurring_active`) against the real
  object — resolved correctly, `Active` read back `True`. Did not write a full real Focus Period
  object to Anytype (that would be a longer-lived, more invasive artifact on June's actual
  planning state than a throwaway Recurring; the commit route's HTTP-level wiring was already
  proven with mocked Anytype in Task 6's review).
- **Step 7 (scheduled-recurring regression guard):** completed a real scheduled recurring
  ("Clean the kitchen") via `complete_task_row` — routed to the `recurring` branch (not
  `as_needed`), cache flipped, **real** `Active` property confirmed absent/unchanged before and
  after (never written). Uncompleted to restore state.
- **Step 8 (cleanup):** deleted the CD-TEST object (Anytype `DELETE` is async — confirmed via
  poll-until-gone, ~1-2s, matching the documented pattern from earlier Anytype work this repo).
  Also stripped the 5 CD-TEST-referencing entries from the real `reactivation_log.jsonl` (all 5
  entries in the file at that point were CD-TEST artifacts from this verify run; zero pre-existing
  real entries existed to preserve). Ran one final clean `generate_plan()` afterward so June's live
  cached plan reflects real data, not a plan generated mid-verification with a since-deleted test
  object in it.
- **Step 9:** full suite 757 passed, conftest real-data tripwire did not fire.

**Net: no code changes from Task 7 itself** (it's verification, not implementation) — this section
and the checked boxes above are the record of what was actually driven and observed.

---

## Self-Review (author checklist)

- **Spec coverage:** (1) on/off state — Task 1 (field) ✓; (2) surfaces every day while on — Task 2 ✓;
  (3) complete = done-until-asked (real deactivation, distinct from scheduled cache-flip) — Tasks 3–4 ✓;
  (4) two "just say it" entry points, match-by-name, unsure→create-not-duplicate — Tasks 5 (Add) & 6
  (Focus) ✓; shared field as the contract with June's tick-list — Task 3 primitive ✓; live verify on real
  plan — Task 7 ✓. Out-of-scope (tick-list, surface list, data reclassification, general update,
  field-population) enumerated ✓.
- **Placeholder scan:** every code step carries real code; live-shape dependencies (the `Active` generated
  key, the `_stub`/ref-map shape, the `plan_generate` `as_needed_ids` re-attach seam + the three daily_plan
  row-origins, the focus resolver, the `complete_task_row` factor) are called out with "re-derive the real
  shape and extend additively" + the exact behavior required — honest instruction, not hand-wave.
- **Type consistency:** `active` (bool) flows field (T1) → `today_fixed_time`/`recurring_items_for_today`
  read (T2) → `as_needed` re-attached by id in `plan_generate` after LLM composition (T4) → `as_needed` row
  flag at each daily_plan origin (T4) → `is_as_needed_item` (T4) → `recurring_active.set_recurring_active(rid,
  active)` (T3, **no `old` param** — reads its own pre-state) called identically by completion (T4), Add (T5),
  Focus (T6). `Active` always the display name; read-back always by name via `(by_name.get("Active") or {}).get("checkbox")`.
- **DRY / one-writer:** `recurring_active.set_recurring_active` (T3) is the single writer of `Active`; no path
  re-implements write/read-back/log. `is_as_needed_item` is checked before `is_recurring_item` (T4) so the
  doubly-flagged row routes correctly. `reactivation_log` is one module; its no-op-on-no-change guard is now
  REACHABLE because the primitive reads real pre-state (the old `old=None`-default made it dead code).
- **Known risk to raise at review:** the Add-box `reactivate` relies on the weeding LLM matching June's words
  to the as-needed list (the alternative — deterministic post-weed string match — is noted in Task 5). *(The
  earlier `server → capture_generate` import-cycle risk is RESOLVED: T3 relocated the primitive to the neutral
  `recurring_active` module. The dead `old`-guard and the `plan_generate` seam-omission from the first draft
  are also fixed — see T3/T4.)*

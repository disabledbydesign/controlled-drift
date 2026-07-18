# Completion Rail + Persistence Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking.

> **STATUS: BUILT + REVIEWED + VERIFIED — 2026-07-18.** All 7 tasks committed (`fc06cc3`, `e4e29bd`,
> `c6bdcf5`, `64789c9`, `1d3447c`, `d293785`; plan/design `6c82377`). Built by sonnet/haiku subagents in
> ordered chains, each diff reviewed. Schema flag live-confirmed on the real Recurring type. Cross-family
> review (GitHub Models gpt-4o/gpt-4o-mini) found no correctness bugs. Render-confirmed via June's REAL
> morning plan (2026-07-18): recurrings surface as checkoffable rows (dishes / clean kitchen / laundry);
> the persisted re-injection rows share that exact `synthetic_recurring_row` shape.
> **Two known follow-ups (not blockers):** (1) `build_context`'s rollover-glue (`tasks += extra_rec`,
> `rollover_ids` union) has no dedicated unit test — it's live-drive-verified and both helpers are
> unit-tested; a real test needs heavy/brittle mocking, deferred. (2) No overlay UI yet to TOGGLE
> `Fixed appointment` — schema + backend logic are ready; the control is the UI thread's (folded into the
> backend spec §2). A separate parked thread: the daily-plan focus logic backgrounds some time-sensitive
> admin + splits household-chore grain (observed 2026-07-18; June parked it).

**Goal:** Make unfinished things keep surfacing until done — silently — and make a recurring "done" durable so a finished chore is never mislabeled "carried over."

**Architecture:** There is ONE rail — `completion_log`, the durable per-day record of what June actually finished. Real-task completions already write to it; this plan routes recurring + as-needed completions through the same log, then reads that real state in rollover instead of guessing from cadence. Two behaviors ride the one rail: **persist** (an unfinished item stays on the plan until done — one-off tasks already do this via `rollover_ids`; missed non-appointment recurrings get re-injected daily) and **wait-for-cadence** (a `Fixed appointment` recurring, e.g. weekly therapy, that is missed returns on its own schedule, never nagging daily). Whether an item comes back tomorrow is decided by its *source* (the active pool for tasks, the recurrence cadence for recurrings) plus the completion log — not by a separate mechanism per type. The LLM's "decide what carries over" narration is removed; persistence becomes a plain deterministic rule.

**Tech Stack:** Python 3, Anytype local API (`gsdo_*` scripts), pytest. No new dependencies.

## Global Constraints

- **Sequencing:** This plan lands *after* the thread-1 as-needed reactivation work is committed. It builds on the existing `complete_task_row` / `uncomplete_task_row` dispatch (`scripts/server.py:125-192`) and `scripts/recurring_active.py` — it extends that surface, it does not race it. Do not start execution until `feat/overlay-actionable`'s as-needed work is committed and the tree is clean.
- **Idempotent Anytype writes, read-back before trusting** (repo guard #2/#3). The schema add (Task 3) uses the existing `ensure_property` idempotent pattern.
- **No silent failures** — raise, don't `assert`. Completion-log writes are the one deliberate exception: best-effort, mirroring `task_actions.complete_task:57-61` (the checkoff already persisted; a logging hiccup must never fail it).
- **Tests self-clean** — never write to June's real space or real data files. `completion_log`/`plan_snapshot_log` resolve their paths through `cd_paths` at call time, so the pytest sandbox redirect keeps runs out of real data. Schema tests must not mutate the live space; assert against the build function's return/structure, not a live type.
- **Shared file coordination:** Task 6 edits `scripts/plan_generate.py`'s prompt/output contract (removing the carryover block). The UI's §14 "drop per-item `why`" cleanup edits the *same* contract (`why` at `plan_generate.py:283,307,316,327-328,363-364,374,385,388,1209,1302`). Whichever lands second rebases; this plan does NOT touch `why` (out of scope).
- **Flag name:** the June-facing label for the skip-if-missed setting is **"Fixed appointment"** (machine key surfaced as the display-name string `"Fixed appointment"`). If June revises the word, it is a single-string swap in Task 3 and Task 5.

---

### Task 1: `plan_store.item_name` — name a cached row by id

A recurring/as-needed completion is cache-only (no Anytype read-back to get a name from, unlike a real task). To log it durably we need its display name from the plan cache.

**Files:**
- Modify: `scripts/plan_store.py` (add function near `mark_item_done:142`)
- Test: `tests/test_plan_store_item_name.py`

**Interfaces:**
- Produces: `plan_store.item_name(task_id) -> str | None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_plan_store_item_name.py
import plan_store

def test_item_name_returns_cached_row_name(monkeypatch):
    monkeypatch.setattr(plan_store, "load_plan",
                        lambda: {"items": [{"id": "rec-1", "task": "Do the dishes"}]})
    assert plan_store.item_name("rec-1") == "Do the dishes"

def test_item_name_none_when_no_match(monkeypatch):
    monkeypatch.setattr(plan_store, "load_plan", lambda: {"items": []})
    assert plan_store.item_name("nope") is None

def test_item_name_none_when_no_cache(monkeypatch):
    monkeypatch.setattr(plan_store, "load_plan", lambda: None)
    assert plan_store.item_name("rec-1") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_plan_store_item_name.py -v`
Expected: FAIL with `AttributeError: module 'plan_store' has no attribute 'item_name'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/plan_store.py — add after mark_item_done (after line 164)
def item_name(task_id):
    """The display name of the cached plan row carrying this id (its 'task'/'name' field),
    or None if there's no cache / no match. The completion route uses this to name a recurring
    or as-needed 'done for today' for completion_log — a real task gets its name from the Anytype
    read-back, but a recurring checkoff is cache-only, so the name comes from here."""
    plan = load_plan()
    if plan is None:
        return None
    for item in _iter_items(plan):
        if item.get("id") == task_id:
            return item.get("task") or item.get("name")
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_plan_store_item_name.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/plan_store.py tests/test_plan_store_item_name.py
git commit -m "feat(plan_store): item_name(id) — name a cached plan row for durable completion logging"
```

---

### Task 2: Recurring + as-needed completions write to `completion_log` (the thread-3 fix)

Today a recurring "done" flips only the in-memory cache (`server.py:143-146`) and never reaches `completion_log`, so next-day rollover can't see it and mislabels a finished daily chore as "carried over." Route both the recurring and as-needed branches through the durable log.

**Files:**
- Modify: `scripts/server.py` (`complete_task_row:125-162`, `uncomplete_task_row:165-192`)
- Test: `tests/test_recurring_completion_logged.py`

**Interfaces:**
- Consumes: `plan_store.item_name` (Task 1); `completion_log.log_completion(id, name)`, `completion_log.log_uncompletion(id)`, `completion_log.completed_ids_on(date)` (existing, `scripts/completion_log.py`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_recurring_completion_logged.py
import datetime as dt
import server, plan_store, completion_log

def _stub_plan(monkeypatch, *, recurring=False, as_needed=False):
    monkeypatch.setattr(plan_store, "is_as_needed_item", lambda tid: as_needed)
    monkeypatch.setattr(plan_store, "is_recurring_item", lambda tid: recurring)
    monkeypatch.setattr(plan_store, "is_block_item", lambda tid: False)
    monkeypatch.setattr(plan_store, "mark_item_done", lambda tid: {"items": []})
    monkeypatch.setattr(plan_store, "mark_item_undone", lambda tid: {"items": []})
    monkeypatch.setattr(plan_store, "item_name", lambda tid: "Do the dishes")

def test_recurring_done_lands_in_completion_log(monkeypatch, tmp_path):
    log = tmp_path / "completion_log.jsonl"
    monkeypatch.setattr(completion_log, "_path", lambda path=None: str(log))
    _stub_plan(monkeypatch, recurring=True)
    status, body = server.complete_task_row("rec-1")
    assert status == 200 and body["completed"]["recurring"] is True
    assert "rec-1" in completion_log.completed_ids_on(dt.date.today(), path=str(log))

def test_as_needed_done_lands_in_completion_log(monkeypatch, tmp_path):
    log = tmp_path / "completion_log.jsonl"
    monkeypatch.setattr(completion_log, "_path", lambda path=None: str(log))
    monkeypatch.setattr(server.recurring_active, "set_recurring_active", lambda rid, active: active)
    _stub_plan(monkeypatch, as_needed=True)
    status, body = server.complete_task_row("an-1")
    assert status == 200 and body["completed"]["as_needed"] is True
    assert "an-1" in completion_log.completed_ids_on(dt.date.today(), path=str(log))

def test_recurring_undo_nets_out(monkeypatch, tmp_path):
    log = tmp_path / "completion_log.jsonl"
    monkeypatch.setattr(completion_log, "_path", lambda path=None: str(log))
    _stub_plan(monkeypatch, recurring=True)
    server.complete_task_row("rec-1")
    server.uncomplete_task_row("rec-1")
    assert "rec-1" not in completion_log.completed_ids_on(dt.date.today(), path=str(log))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_recurring_completion_logged.py -v`
Expected: FAIL — the recurring id is not in `completed_ids_on` (no durable write happens yet).

- [ ] **Step 3: Write minimal implementation**

Add two best-effort helpers near `complete_task_row` in `scripts/server.py`:

```python
def _log_recurring_done(task_id):
    """Record a recurring/as-needed 'done for today' in the durable completion_log so next-day
    rollover reads real done-state instead of guessing from cadence (a finished daily chore was
    being mislabeled 'carried over'). Best-effort: the cache flip already stands; a log hiccup
    must never fail the checkoff (mirrors task_actions.complete_task's best-effort logging)."""
    try:
        import completion_log
        completion_log.log_completion(task_id, plan_store.item_name(task_id))
    except Exception:
        pass

def _log_recurring_undone(task_id):
    """Undo counterpart of _log_recurring_done (mis-tap fix). Netted out by completed_ids_on
    within the same plan_date, so a done-then-undone reads as not-done."""
    try:
        import completion_log
        completion_log.log_uncompletion(task_id)
    except Exception:
        pass
```

In `complete_task_row`, add `_log_recurring_done(task_id)` after the `mark_item_done` line in BOTH the as-needed branch (`server.py:136`) and the recurring branch (`server.py:144`):

```python
    if plan_store.is_as_needed_item(task_id):
        try:
            recurring_active.set_recurring_active(task_id, False)
        except Exception as e:
            return 500, {"error": str(e)}
        plan = plan_store.mark_item_done(task_id)
        _log_recurring_done(task_id)                      # NEW
        return 200, {"completed": {"id": task_id, "done": True, "as_needed": True},
                     "plan": plan or {"empty": True}}
    ...
    if plan_store.is_recurring_item(task_id):
        plan = plan_store.mark_item_done(task_id)
        _log_recurring_done(task_id)                      # NEW
        return 200, {"completed": {"id": task_id, "done": True, "recurring": True},
                     "plan": plan or {"empty": True}}
```

In `uncomplete_task_row`, add `_log_recurring_undone(task_id)` after the `mark_item_undone` line in BOTH the as-needed branch (`server.py:172`) and the recurring branch (`server.py:177`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_recurring_completion_logged.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/server.py tests/test_recurring_completion_logged.py
git commit -m "feat(complete): recurring + as-needed completions write durably to completion_log"
```

---

### Task 3: `Fixed appointment` checkbox on the Recurring type

The per-recurring switch that means "if I miss this, wait for its next cadence — don't carry it forward daily." Default unset = persist. Added to the schema so the surface and the selection logic (Task 5) can read it.

**Files:**
- Modify: `scripts/build_recurring.py`
- Modify: `scripts/verify_model.py` (Recurring expected-property list)
- Test: `tests/test_build_recurring_fixed_appointment.py`

**Interfaces:**
- Produces: a `"Fixed appointment"` checkbox property linked to the Recurring type; read elsewhere by display name `"Fixed appointment"` (mirrors how `recurring_active._active_of` reads `"Active"`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build_recurring_fixed_appointment.py
import build_recurring

def test_fixed_appointment_property_is_ensured(monkeypatch):
    ensured = []
    monkeypatch.setattr(build_recurring.g, "ensure_property",
                        lambda name, kind, *a: ensured.append((name, kind)) or {"key": name})
    linked = {}
    monkeypatch.setattr(build_recurring.g, "ensure_type",
                        lambda k, n, props: linked.setdefault("props", [p["key"] for p in props]) or "gsdo_recurring")
    monkeypatch.setattr(build_recurring.g, "find_property", lambda name: None)
    monkeypatch.setattr(build_recurring.g, "find_type", lambda name: {"id": "t"})
    monkeypatch.setattr(build_recurring.g, "unlink_properties_from_type", lambda *a: None)
    build_recurring.build_recurring()
    assert ("Fixed appointment", "checkbox") in ensured
    assert "Fixed appointment" in linked["props"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_build_recurring_fixed_appointment.py -v`
Expected: FAIL — `"Fixed appointment"` is neither ensured nor linked.

- [ ] **Step 3: Write minimal implementation**

In `scripts/build_recurring.py`, after `p_active` (line 34) add:

```python
    # skip-if-missed (persistence rail): a missed occurrence waits for its next cadence instead of
    # carrying forward daily. Default unset = persist. Read by display name "Fixed appointment".
    p_fixed      = g.ensure_property("Fixed appointment", "checkbox")
```

Add `p_fixed` to the `ensure_type` property list (currently ending `..., p_autonomous, p_docs, p_active])` at line 39):

```python
    key = g.ensure_type("Recurring", "Recurring",
                        [p_freq, p_project, p_context,
                         p_dow, p_dom, p_tod, p_dur, p_iunit, p_icount,
                         p_clarify, p_blocked, p_affective, p_access, p_access_nts,
                         p_autonomous, p_docs, p_active, p_fixed])
```

In `scripts/verify_model.py`, find the Recurring expected-property list and add `"Fixed appointment"` alongside `"Active"` (mirror the entry format the list already uses), so `verify_model` does not fail after the type change.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_build_recurring_fixed_appointment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/build_recurring.py scripts/verify_model.py tests/test_build_recurring_fixed_appointment.py
git commit -m "feat(schema): Fixed appointment checkbox on Recurring (skip-if-missed)"
```

---

### Task 4: Factor `daily_plan.synthetic_recurring_row` — one row-builder, two callers

The persistence re-injection (Task 5) needs to build the same task-shaped row an untimed recurring already rides through the plan on. Extract that row-builder (currently inline at `daily_plan.py:262-279`) so both `load_active_items` and Task 5 share it — no duplicated shape that can silently diverge.

**Files:**
- Modify: `scripts/daily_plan.py` (extract from `load_active_items`, lines ~262-279)
- Test: `tests/test_synthetic_recurring_row.py`

**Interfaces:**
- Produces: `daily_plan.synthetic_recurring_row(obj, proj_id_to_name, duration_min, as_needed) -> dict`
  - `obj`: a raw Anytype Recurring object (has `id`, `name`, `properties`).
  - Returns the row shape: `{id, name, status:"Ready", duration_min, affective:None, access:[], blocked_on:None, context, due_date:None, linked_projects:[names], is_recurring:True, as_needed}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_synthetic_recurring_row.py
import daily_plan

def test_synthetic_recurring_row_shape():
    obj = {"id": "rec-1", "name": "Water plants",
           "properties": [
               {"key": "gsdo_project_link", "objects": [{"id": "p1"}]},
               {"key": "gsdo_context", "text": "kitchen"}]}
    row = daily_plan.synthetic_recurring_row(obj, {"p1": "Household"},
                                             duration_min=15, as_needed=False)
    assert row["id"] == "rec-1"
    assert row["name"] == "Water plants"
    assert row["is_recurring"] is True
    assert row["as_needed"] is False
    assert row["duration_min"] == 15
    assert row["context"] == "kitchen"
    assert row["linked_projects"] == ["Household"]
    assert row["status"] == "Ready" and row["due_date"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_synthetic_recurring_row.py -v`
Expected: FAIL — `AttributeError: module 'daily_plan' has no attribute 'synthetic_recurring_row'`

- [ ] **Step 3: Write minimal implementation**

Add to `scripts/daily_plan.py`:

```python
def synthetic_recurring_row(obj, proj_id_to_name, duration_min, as_needed):
    """Build the task-shaped row an untimed / persisted recurring rides through the plan on — the
    SAME machinery a real task gets (the LLM composes/places it, a ref token resolves it,
    completion routes to the recurring 'done for today'). Shared by load_active_items (due-today
    untimed recurrings) and plan_generate's persistence re-injection (a missed non-appointment
    recurring). `duration_min`/`as_needed` are passed by the caller so each call site keeps its
    own source for them."""
    rprops = {p.get("key"): p for p in obj.get("properties", [])}
    proj_ids = _prop_val(rprops, "gsdo_project_link", "objects") or []
    linked = []
    for x in proj_ids:
        pid = x.get("id") if isinstance(x, dict) else x
        nm = proj_id_to_name.get(pid)
        if nm:
            linked.append(nm)
    return {
        "id": obj.get("id"), "name": obj.get("name"), "status": "Ready",
        "duration_min": duration_min,
        "affective": None, "access": [], "blocked_on": None,
        "context": _prop_val(rprops, "gsdo_context", "text"),
        "due_date": None,
        "linked_projects": linked,
        "is_recurring": True,
        "as_needed": as_needed,
    }
```

Then replace the inline row-append at `daily_plan.py:262-279` with a call to it (behavior-preserving — `proj_id_to_name` here is the existing `proj_id_to_name` map; pass the same `r`-derived values the old code used):

```python
            obj = recurring_obj_by_id.get(r["id"])
            if obj is None:
                continue
            tasks.append(synthetic_recurring_row(
                obj, proj_id_to_name,
                duration_min=r.get("duration_min"),
                as_needed=r.get("as_needed", False)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_synthetic_recurring_row.py -v && pytest tests/ -k "daily_plan or load_active" -v`
Expected: PASS — the new test passes AND the existing daily_plan/load_active tests stay green (behavior-preserving refactor).

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_plan.py tests/test_synthetic_recurring_row.py
git commit -m "refactor(daily_plan): extract synthetic_recurring_row for reuse in persistence re-injection"
```

---

### Task 5: Persist missed non-appointment recurrings; keep Fixed appointments waiting

The heart of the rail. Rollover candidates (`undone_yesterday`, already minus real completions after Task 2) split two ways: task candidates keep the existing active-pool filter (zombie-proof); recurring candidates that are (a) not already surfaced today, (b) not completed today, and (c) not `Fixed appointment` get re-injected as synthetic rows so they keep surfacing until done. A daily chore is left to its own cadence (already in today's pool → skipped). A Fixed appointment is skipped → waits for its next cadence.

**Files:**
- Modify: `scripts/plan_generate.py` (`build_context:628-634`; add `_persisted_recurring_rows`; keep `_filter_rollover_to_active:604-615`)
- Test: `tests/test_persist_missed_recurring.py`

**Interfaces:**
- Consumes: `daily_plan.synthetic_recurring_row` (Task 4); `recurring_active._get_object` (existing, `recurring_active.py:12`); `completion_log.completed_ids_on` (existing).
- Produces: `plan_generate._persisted_recurring_rows(undone_yest, tasks, projects) -> list[row]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_persist_missed_recurring.py
import datetime as dt
import plan_generate, daily_plan, recurring_active, completion_log

def _obj(rid, name, fixed=False):
    props = [{"key": "gsdo_project_link", "objects": []},
             {"name": "Fixed appointment", "checkbox": fixed}]
    return {"id": rid, "name": name, "type": {"key": "gsdo_recurring"}, "properties": props}

def _setup(monkeypatch, objs, done_today=()):
    monkeypatch.setattr(recurring_active, "_get_object", lambda rid: objs[rid])
    monkeypatch.setattr(completion_log, "completed_ids_on",
                        lambda date, path=None: set(done_today))
    # synthetic_recurring_row is real; it only needs obj + a name map
    return

def test_missed_nonappointment_recurring_is_reinjected(monkeypatch):
    objs = {"rec-water": _obj("rec-water", "Water plants", fixed=False)}
    _setup(monkeypatch, objs)
    undone = [{"id": "rec-water", "name": "Water plants"}]
    rows = plan_generate._persisted_recurring_rows(undone, tasks=[], projects=[])
    assert [r["id"] for r in rows] == ["rec-water"]
    assert rows[0]["is_recurring"] is True

def test_fixed_appointment_is_not_reinjected(monkeypatch):
    objs = {"rec-therapy": _obj("rec-therapy", "Therapy", fixed=True)}
    _setup(monkeypatch, objs)
    undone = [{"id": "rec-therapy", "name": "Therapy"}]
    rows = plan_generate._persisted_recurring_rows(undone, tasks=[], projects=[])
    assert rows == []

def test_already_in_todays_pool_is_skipped(monkeypatch):
    objs = {"rec-dishes": _obj("rec-dishes", "Dishes", fixed=False)}
    _setup(monkeypatch, objs)
    undone = [{"id": "rec-dishes", "name": "Dishes"}]
    rows = plan_generate._persisted_recurring_rows(
        undone, tasks=[{"id": "rec-dishes"}], projects=[])
    assert rows == []  # daily chore already re-emitted by cadence — don't double it

def test_completed_today_is_skipped(monkeypatch):
    objs = {"rec-water": _obj("rec-water", "Water plants", fixed=False)}
    _setup(monkeypatch, objs, done_today=["rec-water"])
    undone = [{"id": "rec-water", "name": "Water plants"}]
    rows = plan_generate._persisted_recurring_rows(undone, tasks=[], projects=[])
    assert rows == []  # same-day zombie guard
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_persist_missed_recurring.py -v`
Expected: FAIL — `AttributeError: module 'plan_generate' has no attribute '_persisted_recurring_rows'`

- [ ] **Step 3: Write minimal implementation**

Add to `scripts/plan_generate.py` (near `_filter_rollover_to_active:604`):

```python
def _persisted_recurring_rows(undone_yest, tasks, projects):
    """Rollover candidates that are recurrings whose cadence did NOT re-emit them today — re-inject
    them so a missed non-appointment recurring keeps surfacing until done (the persistence rail).
    SKIP a 'Fixed appointment' recurring (a missed appointment waits for its next cadence, it does
    not nag daily); SKIP any already in today's pool (a daily chore is re-emitted by cadence —
    don't double it); SKIP any completed today (same-day zombie guard, symmetric to
    _filter_rollover_to_active). Returns synthetic task-shaped rows to append to the candidate pool."""
    import daily_plan, recurring_active, completion_log
    present = {t.get("id") for t in tasks}
    done_today = completion_log.completed_ids_on(dt.date.today())
    proj_id_to_name = {p["id"]: p["name"] for p in projects}
    rows = []
    for u in undone_yest:
        rid = u["id"]
        if rid in present or rid in done_today:
            continue
        try:
            obj = recurring_active._get_object(rid)
        except Exception:
            continue
        t = obj.get("type")
        tk = t.get("key") if isinstance(t, dict) else t
        if tk != "gsdo_recurring":
            continue
        by_name = {p.get("name"): p for p in obj.get("properties", [])}
        if (by_name.get("Fixed appointment") or {}).get("checkbox"):
            continue
        rows.append(daily_plan.synthetic_recurring_row(
            obj, proj_id_to_name, duration_min=None, as_needed=False))
    return rows
```

Wire it into `build_context`. Replace lines 632-634:

```python
    undone_yest = plan_snapshot_log.undone_yesterday()   # rollover candidates: yesterday's uncompleted
    undone_yest = _filter_rollover_to_active(undone_yest, tasks)
    rollover_ids = {u["id"] for u in undone_yest}
```

with:

```python
    all_undone = plan_snapshot_log.undone_yesterday()          # rollover candidates: yesterday's uncompleted
    task_roll = _filter_rollover_to_active(all_undone, tasks)  # tasks still active (zombie-proof, unchanged)
    extra_rec = _persisted_recurring_rows(all_undone, tasks, projects)  # missed non-appointment recurrings
    tasks = tasks + extra_rec
    rollover_ids = {u["id"] for u in task_roll} | {r["id"] for r in extra_rec}
    undone_yest = task_roll   # kept for the (about-to-be-removed) narration block; see Task 6
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_persist_missed_recurring.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/plan_generate.py tests/test_persist_missed_recurring.py
git commit -m "feat(plan): persist missed non-appointment recurrings; Fixed appointments wait for cadence"
```

---

### Task 6: Remove the LLM carryover narration — persistence becomes a plain rule

Delete the "## Carried over from yesterday (not marked done) — decide what genuinely carries" block handed to the model. Persisted items now enter the plan as ordinary candidate rows (via `rollover_ids`/`extra_rec` from Task 5), placed like any active item — silently, no "you didn't finish this" framing and no LLM adjudication of what carries.

**Files:**
- Modify: `scripts/plan_generate.py` (remove `759-766`; remove the now-unused `undone_yest` line added in Task 5)
- Test: `tests/test_no_carryover_narration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_no_carryover_narration.py
import pathlib

def test_carryover_narration_text_is_gone():
    src = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "plan_generate.py"
    text = src.read_text()
    assert "Carried over from yesterday" not in text
    assert "not everything should roll forward" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_no_carryover_narration.py -v`
Expected: FAIL — the narration string is still present.

- [ ] **Step 3: Write minimal implementation**

Remove the block at `scripts/plan_generate.py:759-766` in full:

```python
    if undone_yest:
        roll = ("\n\n## Carried over from yesterday (not marked done)\n"
                "These were on yesterday's plan and weren't completed. Decide which GENUINELY should "
                "carry into today — a missed call, an errand that still needs doing — and place those. "
                "Let go the ones that were fine to skip; not everything should roll forward.\n")
        for u in undone_yest:
            roll += f"  - {u['name']}\n"
        context_block += roll
```

Then remove the now-unused `undone_yest = task_roll` line added in Task 5's `build_context` edit (nothing consumes `undone_yest` after this block is gone; `task_roll` still feeds `rollover_ids`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_no_carryover_narration.py tests/test_persist_missed_recurring.py -v`
Expected: PASS — narration gone AND persistence still wired.

- [ ] **Step 5: Commit**

```bash
git add scripts/plan_generate.py tests/test_no_carryover_narration.py
git commit -m "feat(plan): drop LLM carryover narration — persistence is a plain deterministic rule"
```

---

### Task 7: Integration & live-verify (REQUIRED — drive the real runtime, not just tests)

Unit-green is not done. This rail touches the live plan path that produced a real zombie-row bug on 2026-07-17. Prove the feature on real data by regenerating June's actual plan and observing behavior — the repo build-frame guard: reason from how the system functions at runtime.

**Files:**
- No new code. Wiring already lands in Tasks 2 and 5 (`server.complete_task_row` → `completion_log`; `build_context` → `_persisted_recurring_rows`/`rollover_ids`).

**Wiring confirmation (name the real call sites):**
- Recurring/as-needed checkoff → `server.complete_task_row` (`server.py:131-146`) → `_log_recurring_done` → `completion_log.log_completion` (durable).
- Rollover honesty → `plan_snapshot_log.undone_on:62` reads `completion_log.completed_ids_on`, so a logged recurring done drops out of "undone yesterday."
- Persistence → `build_context:632-634` → `_persisted_recurring_rows` appends synthetic rows + `rollover_ids` → `_gate_and_collapse:520` keeps them.

- [ ] **Step 1: Full suite green**

Run: `pytest tests/ -q`
Expected: all pass (no regressions in the existing rollover/daily_plan/completion tests).

- [ ] **Step 2: Rebuild the schema (idempotent) and verify**

Run: `python3 scripts/build_recurring.py && python3 scripts/verify_model.py`
Expected: `[ok] Recurring type ready` and verify passes with `Fixed appointment` present.

- [ ] **Step 3: Restart the server, then drive the four real behaviors** (use the `verify` skill / real overlay against June's live space)

1. **Finished daily chore is not mislabeled.** Complete a due daily recurring in the overlay, then regenerate the plan (next-day simulation via the plan path). Expected: it does NOT appear under any "carried over" framing (there is none) and is not re-injected — `completion_log.completed_ids_on` contains its id for its plan_date.
2. **Missed non-appointment recurring persists.** Leave an untimed weekly recurring (not `Fixed appointment`) uncompleted; regenerate the next day's plan. Expected: it surfaces again as a normal, checkoffable row (real id, resolves, has a checkbox — not a ghost row). Complete it → next regeneration it is gone.
3. **Fixed appointment waits for cadence.** Set `Fixed appointment` on a weekly recurring, leave it missed; regenerate. Expected: it does NOT surface the next day; it returns only on its next scheduled cadence.
4. **Unfinished one-off task persists.** Leave a normal task undone; regenerate. Expected: it surfaces again silently, checkoffable, no "carried over" wording.

- [ ] **Step 4: Confirm zero ghost rows.** For each re-injected recurring in behavior 2, confirm in the real overlay that the row has a working checkbox and resolves to its real id (the 2026-07-14 ghost-row failure mode: a row that renders but can't be checked off). If any re-injected row can't be checked off, STOP — the frame is wrong, not the tests.

- [ ] **Step 5: Commit any wiring fixes the live run surfaces, then hand off for cross-family review**

```bash
git add -A
git commit -m "test(rail): live-verify completion rail + persistence on real plan"
```

Then run the non-Claude cross-family review (`~/.claude/skills/requesting-code-review/github_models_review.py`) on the diff, per repo BUILDING discipline — chunk per file so the ~8k-token cap doesn't false-flag "no tests." Triage findings, apply what's real, before the thread closes.

---

## Self-Review

**Spec coverage:**
- Thread 3 (record recurring completions durably) → Tasks 1–2. ✓
- Thread 2 (unfinished persists silently; no LLM narration) → one-off already works + Task 6 removes narration. ✓
- Thread 2 opt-out (Fixed appointment waits for cadence) → Tasks 3, 5. ✓
- One-rail (completion_log is the single durable record read by rollover) → Tasks 2, 5. ✓
- Daily-cadence exemption (a daily chore is re-emitted by cadence, not double-handled) → Task 5 `present` skip. ✓
- Ghost-row / live-verify guard → Task 7. ✓
- UI gel item — polarity `paused`↔`Active` and shared `plan_generate.py` file — recorded in Global Constraints; the `Active`/`paused` mapping is thread-1's write-back surface (out of this plan's scope), flagged so it is reconciled, not silently mismatched.

**Placeholder scan:** No TBD/TODO/"handle edge cases" — every code step shows real code. `verify_model.py`'s exact list edit (Task 3) references the existing entry format because that list's shape is established in-file; the executor mirrors `"Active"`.

**Type consistency:** `synthetic_recurring_row(obj, proj_id_to_name, duration_min, as_needed)` — same signature in Task 4 (definition), Task 4 call site, and Task 5 call site. `_persisted_recurring_rows(undone_yest, tasks, projects)` — same in Task 5 def, test, and `build_context` wiring. `_log_recurring_done`/`_log_recurring_undone` consistent across Task 2. `completed_ids_on(date, path=None)` matches `completion_log.py:54`.

**Out of scope (documented, not gaps):** §14 `why`-removal (different feature, same file — coordinate); `chunk_log` consolidation into the rail (blocks already reopen tomorrow correctly; folding them into `completion_log` is a follow-up, YAGNI); the `paused`→`Active` write-back polarity (thread-1 surface).

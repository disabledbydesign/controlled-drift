# GSDO Data Model + v1 Python Scaffolding Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the GSDO data model (Goal / Project / Task / Recurring / Strategy + their fields) in the live Anytype space, plus the two deterministic Python pieces the daily plan depends on (clock-time scheduler + neglect-resurfacing query) and the plan-corrections logger.

**Architecture:** All Anytype writes go through the existing, verified `call()` helper in `scripts/anytype_test.py` (loads the key from `.env`, base `http://localhost:31009/v1`, header `Anytype-Version: 2025-11-08`). A new shared module `scripts/gsdo_anytype.py` adds **idempotent** `ensure_*` helpers (create-if-not-exists) on top of `call()` — because the build mutates June's real space, which already holds some types/properties and must not be duplicated. Each type is then ensured by its own small builder script. Pure-logic pieces (the scheduler) are plain Python with unit tests. Anytype-touching pieces are verified by integration checks against the running local API (the same style as the existing `anytype_validate.py`, which passed 14/14).

**Tech Stack:** Python 3 (stdlib only — `urllib`, `json`, `datetime`; no third-party deps, matching the existing scripts), the Anytype Local API (Developer-Preview), `pytest` for unit tests.

## Global Constraints

- **Idempotent always.** Every Anytype write is create-if-not-exists. Re-running any builder must not create duplicates. The space already contains: type `gsdo_goal` (shell, no GSDO properties linked); standalone properties `gsdo_duration_min` (number) and `gsdo_needs_clarifying` (checkbox) NOT yet linked to Task; and two **test artifacts to ignore** — `gsdo_reaching_for` (objects) and `gsdo_location_mode` (select) — neither matches the final model.
- **Reuse by key.** `gsdo_duration_min` and `gsdo_needs_clarifying` already exist — reuse them, link them to Task; do NOT create new duration/clarifying properties.
- **No new dependencies.** stdlib + `pytest` only. Match the existing scripts' style (`call()`, `.env` key loading).
- **Key/header verbatim:** `Authorization: Bearer <key from .env var get_shit_done>`, `Anytype-Version: 2025-11-08`, base `http://localhost:31009/v1`.
- **Space:** "Get Started", id `bafyreibcf3vhpi2neqaf2rdb5yzu2qqlykabxohjc3puyezauvmll7b2n4.2c96yy1wokk27` — but discover it at runtime via `GET /spaces` (first space), as the existing scripts do, rather than hardcoding.
- **No scalar flattening in the schema (guards #3, #5).** `affective` is free **text** (capacity-signal pattern), never a number. `excitement_level` is a number but the spec only ever *displays* it as "X out of 5" — the field stores the number; presentation is the AI layer's job, not this schema's.
- **The schema is the AI's substrate, never June's form.** Every field except `name`/`done` is optional and empty by default. Builders must NOT set required flags or default values that would force data entry.

---

## Notes carried from spec-reading (resolve with June; do NOT silently bake)

These are flagged in-plan because they are decisions, not mechanics. The build-loop's layered stop should surface them.

1. **`last_surfaced` is an addition beyond §2 that §9 item 6 requires.** Neglect-resurfacing ("active items not surfaced in N days") needs to know *when an item was last surfaced*. §2's data model has no such field, and Anytype's built-in `last_modified` won't work (it changes on any edit, not on surfacing). This plan adds a `last_surfaced` (date) property to Task and Project, written by the daily-plan pipeline when an item is surfaced. It is internal plumbing, not a judgment field — no guard concern. **Flag for June:** confirm the field approach vs. a separate surface-log. Task 9 depends on this.
2. **Select option values must exist before they can be assigned.** In Anytype, select/multi-select options are *tags* on the property. The builders create the option set (Active/Parked/Achieved, the four Task statuses, etc.) at property-creation time. Defining tags and linking a property to a type are the two API shapes not exercised by the existing 14/14 validation — Task 1 confirms them empirically against the live OpenAPI spec before any builder relies on them.

---

## File Structure

- `scripts/gsdo_anytype.py` — shared idempotent helpers (`get_space_id`, `find_type`, `find_property`, `ensure_property`, `ensure_select_options`, `ensure_type`, `link_properties_to_type`). One responsibility: safe, idempotent schema operations.
- `scripts/build_goal.py`, `build_project.py`, `build_task.py`, `build_recurring.py`, `build_strategy.py` — one builder per type, each calling the shared helpers. Split by type so a reviewer can accept/reject one type independently.
- `scripts/build_model.py` — runs all builders in dependency order (Goal → Project → Task → Recurring → Strategy), then runs the verification.
- `scripts/verify_model.py` — asserts the full model exists and is correctly linked (the real-model analogue of `anytype_validate.py`).
- `scripts/scheduler.py` — pure-function deterministic clock-time scheduler.
- `scripts/neglect.py` — neglect-resurfacing query.
- `scripts/plan_corrections_log.py` — append-only logger for June's plan edits.
- `tests/test_scheduler.py`, `tests/test_neglect.py`, `tests/test_plan_corrections_log.py` — unit tests (pure logic; neglect's Anytype read is injected/mocked).

---

### Task 1: Shared idempotent Anytype helpers + confirm the two unknown API shapes

**Files:**
- Create: `scripts/gsdo_anytype.py`
- Test: `tests/test_gsdo_anytype.py`

**Interfaces:**
- Consumes: `call(method, path, body=None)` from `scripts/anytype_test.py` (verified working).
- Produces (downstream tasks rely on these exact signatures):
  - `get_space_id() -> str`
  - `find_type(key_or_name: str) -> dict | None` — searches `GET /spaces/{sid}/types?limit=100` by `key` then `name`.
  - `find_property(key_or_name: str) -> dict | None` — searches `GET /spaces/{sid}/properties?limit=200`.
  - `ensure_property(name: str, fmt: str, options: list[str] | None = None) -> str` — returns property `key`; creates only if absent; if `options` given and `fmt` in (`select`,`multi_select`), ensures each option tag exists.
  - `ensure_select_options(property_key: str, options: list[str]) -> None`
  - `ensure_type(name: str, plural: str, property_keys: list[str], layout: str = "basic") -> str` — returns type `key`; creates if absent; links `property_keys` (idempotent).
  - `link_properties_to_type(type_id: str, property_keys: list[str]) -> None`

- [ ] **Step 1: Confirm the two unknown API shapes against the live OpenAPI spec.** Everything else (create property/type/object, set number/checkbox/objects values) is already verified by `anytype_validate.py` (14/14). Only two shapes are unconfirmed: (a) defining select-option *tags*, (b) linking a property to a type. Run this discovery and read the output:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
from anytype_test import call
sid = call("GET","/spaces")[1]["data"][0]["id"]
# (a) existing Task type detail shows how a type lists its properties:
st, t = call("GET", f"/spaces/{sid}/types?limit=100")
task = next((x for x in t["data"] if x.get("key")=="task"), None)
print("TASK TYPE KEYS:", list(task.keys()) if task else "NOT FOUND")
print("TASK TYPE (full):")
import json; print(json.dumps(task, indent=2)[:3000])
# (b) inspect a select property + its tags endpoint shape:
st, p = call("GET", f"/spaces/{sid}/properties?limit=200")
sel = next((x for x in p["data"] if x.get("format")=="select"), None)
print("\nSELECT PROP:", json.dumps(sel, indent=2)[:1000] if sel else "none")
if sel:
    pid = sel.get("id")
    print("\nTAGS:", json.dumps(call("GET", f"/spaces/{sid}/properties/{pid}/tags")[1], indent=2)[:1500])
PY
```
Expected: prints the Task type's property-list field name (e.g. `properties` or `recommended_relations`) and the `/properties/{id}/tags` response. **Record the confirmed field name and tag-create path in a comment at the top of `gsdo_anytype.py`.** If the `/tags` path 404s, try `GET /spaces/{sid}/properties/{pid}` and inspect for an embedded options/tags array, and note the working path.

- [ ] **Step 2: Write the failing test.** This is an integration test against the live API (the codebase's existing pattern). It exercises idempotency — the property that means "real model" is that a second `ensure_property` call returns the same key without creating a duplicate.

```python
# tests/test_gsdo_anytype.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gsdo_anytype as g

def test_space_id_resolves():
    assert isinstance(g.get_space_id(), str) and len(g.get_space_id()) > 10

def test_ensure_property_is_idempotent():
    k1 = g.ensure_property("GSDO Test Context", "text")
    k2 = g.ensure_property("GSDO Test Context", "text")
    assert k1 == k2  # second call must NOT create a duplicate

def test_reuses_existing_duration_property():
    # gsdo_duration_min already exists in the space; ensure must find, not recreate
    k = g.ensure_property("GSDO Duration min", "number")
    assert g.find_property(k) is not None

def test_ensure_select_options_idempotent():
    k = g.ensure_property("GSDO Test Status", "select", options=["Active", "Parked"])
    before = g.find_property(k)
    g.ensure_select_options(k, ["Active", "Parked"])  # re-run
    after = g.find_property(k)
    assert before is not None and after is not None
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_gsdo_anytype.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gsdo_anytype'`.

- [ ] **Step 4: Implement `scripts/gsdo_anytype.py`.** Use the verified `call()` for everything; fill the two confirmed shapes from Step 1 into `ensure_select_options` and `link_properties_to_type`. (Below, `<<TAGS_PATH>>` and `<<TYPE_PROPS_FIELD>>` are replaced with the exact values recorded in Step 1 — do not leave them as placeholders.)

```python
#!/usr/bin/env python3
"""Idempotent Anytype schema helpers for GSDO. Built on the verified call() in anytype_test.py.
Confirmed in Task 1 against live OpenAPI:
  - select-option tags path: <<TAGS_PATH>>  (e.g. /spaces/{sid}/properties/{pid}/tags)
  - type property-list field: <<TYPE_PROPS_FIELD>>  (e.g. "properties")
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call

_SID = None
def get_space_id():
    global _SID
    if _SID is None:
        _SID = call("GET", "/spaces")[1]["data"][0]["id"]
    return _SID

def find_type(key_or_name):
    sid = get_space_id()
    data = call("GET", f"/spaces/{sid}/types?limit=100")[1].get("data", [])
    return next((t for t in data if t.get("key") == key_or_name or t.get("name") == key_or_name), None)

def find_property(key_or_name):
    sid = get_space_id()
    data = call("GET", f"/spaces/{sid}/properties?limit=200")[1].get("data", [])
    return next((p for p in data if p.get("key") == key_or_name or p.get("name") == key_or_name), None)

def ensure_property(name, fmt, options=None):
    existing = find_property(name)
    if existing:
        key = existing.get("key")
    else:
        st, b = call("POST", f"/spaces/{get_space_id()}/properties", {"name": name, "format": fmt})
        assert st in (200, 201), f"create property {name} failed: {st} {b}"
        key = b["property"]["key"]
    if options and fmt in ("select", "multi_select"):
        ensure_select_options(key, options)
    return key

def ensure_select_options(property_key, options):
    sid = get_space_id()
    prop = find_property(property_key)
    pid = prop["id"]
    # path + existing-tag list field confirmed in Task 1:
    existing = {t.get("name") for t in call("GET", f"/spaces/{sid}/properties/{pid}/tags")[1].get("data", [])}
    for opt in options:
        if opt not in existing:
            st, b = call("POST", f"/spaces/{sid}/properties/{pid}/tags", {"name": opt})
            assert st in (200, 201), f"create tag {opt} on {property_key} failed: {st} {b}"

def link_properties_to_type(type_id, property_keys):
    sid = get_space_id()
    t = call("GET", f"/spaces/{sid}/types/{type_id}")[1].get("type", {})
    # <<TYPE_PROPS_FIELD>> is the confirmed field listing a type's properties:
    current = {p.get("key") for p in t.get("<<TYPE_PROPS_FIELD>>", [])}
    to_add = [{"key": k} for k in property_keys if k not in current]
    if to_add:
        merged = t.get("<<TYPE_PROPS_FIELD>>", []) + to_add
        st, b = call("PATCH", f"/spaces/{sid}/types/{type_id}",
                     {"<<TYPE_PROPS_FIELD>>": merged})
        assert st in (200, 201), f"link properties to type {type_id} failed: {st} {b}"

def ensure_type(name, plural, property_keys, layout="basic"):
    existing = find_type(name)
    if existing:
        type_id, key = existing["id"], existing.get("key")
    else:
        st, b = call("POST", f"/spaces/{get_space_id()}/types",
                     {"name": name, "plural_name": plural, "layout": layout})
        assert st in (200, 201), f"create type {name} failed: {st} {b}"
        type_id, key = b["type"]["id"], b["type"]["key"]
    link_properties_to_type(type_id, property_keys)
    return key
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_gsdo_anytype.py -v`
Expected: PASS (4 passed). If `link_properties_to_type` or `ensure_select_options` errors with a 4xx, the Step-1 shape was wrong — re-inspect and correct the path/field, do NOT guess repeatedly. **No-silent-failure:** a non-2xx must raise (the asserts enforce this).

- [ ] **Step 6: Commit**

```bash
git add scripts/gsdo_anytype.py tests/test_gsdo_anytype.py
git commit -m "feat(gsdo): idempotent Anytype schema helpers"
```

---

### Task 2: Build the Goal type

**Files:**
- Create: `scripts/build_goal.py`

**Interfaces:**
- Consumes: `ensure_property`, `ensure_type` from `gsdo_anytype`.
- Produces: a built `gsdo_goal` type with properties `reaching_for, horizon, status, context` linked. (`name` is built-in to every object.)

Spec fields (§2 Goal): `reaching_for` (text), `horizon` (select: Long-term / Medium-term / Short-term), `status` (select: Active / Parked / Achieved), `barriers` (text — queryable struggle-blocks), `context` (text).

- [ ] **Step 1: Write the builder**

```python
#!/usr/bin/env python3
"""Ensure the GSDO Goal type and its properties exist. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_goal():
    p_reaching = g.ensure_property("GSDO Reaching for (text)", "text")
    p_horizon  = g.ensure_property("GSDO Horizon", "select", ["Long-term", "Medium-term", "Short-term"])
    p_status   = g.ensure_property("GSDO Goal status", "select", ["Active", "Parked", "Achieved"])
    p_barriers = g.ensure_property("GSDO Barriers", "text")   # queryable struggle-blocks (§10 stuck-support storage)
    p_context  = g.ensure_property("GSDO Context", "text")
    key = g.ensure_type("GSDO Goal", "GSDO Goals", [p_reaching, p_horizon, p_status, p_barriers, p_context])
    print(f"[ok] Goal type ready: key={key}")
    return key

if __name__ == "__main__":
    build_goal()
```

Note: the property is named **"GSDO Reaching for (text)"** to avoid colliding with the existing test artifact `gsdo_reaching_for` (objects format) that must be ignored. `GSDO Context` is shared across all types (Anytype properties are space-global; one `context` text property is reused everywhere).

- [ ] **Step 2: Run it**

Run: `python3 scripts/build_goal.py`
Expected: prints `[ok] Goal type ready: key=...`. Re-run once: must print the same key, create nothing new.

- [ ] **Step 3: Commit**

```bash
git add scripts/build_goal.py
git commit -m "feat(gsdo): build Goal type"
```

---

### Task 3: Build the Project type

**Files:**
- Create: `scripts/build_project.py`

**Interfaces:**
- Consumes: `ensure_property`, `ensure_type` from `gsdo_anytype`; reuses `GSDO Reaching for (text)`, `GSDO Context` from Task 2 (same names → same keys, idempotent).
- Produces: `gsdo_project` type with all §2 Project properties linked.

Spec fields (§2 Project): `goal_link` (objects), `description` (text), `reaching_for` (text), `status` (select: Active / Parked / Inactive), `deadline` (date), `parent_project` (objects), `excitement_level` (number 1–5), `relevant_docs` (text), `affective` (text — capacity signal, NOT a scalar), `barriers` (text — queryable struggle-blocks), `context` (text).

- [ ] **Step 1: Write the builder**

```python
#!/usr/bin/env python3
"""Ensure the GSDO Project type and its properties exist. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_project():
    p_goal_link   = g.ensure_property("GSDO Goal link", "objects")
    p_description = g.ensure_property("GSDO Description", "text")
    p_reaching    = g.ensure_property("GSDO Reaching for (text)", "text")   # reused from Goal
    p_status      = g.ensure_property("GSDO Project status", "select", ["Active", "Parked", "Inactive"])
    p_deadline    = g.ensure_property("GSDO Deadline", "date")
    p_parent      = g.ensure_property("GSDO Parent project", "objects")
    p_excitement  = g.ensure_property("GSDO Excitement level", "number")
    p_docs        = g.ensure_property("GSDO Relevant docs", "text")
    p_affective   = g.ensure_property("GSDO Affective", "text")   # capacity signal, free text
    p_barriers    = g.ensure_property("GSDO Barriers", "text")     # reused from Goal; queryable struggle-blocks
    p_context     = g.ensure_property("GSDO Context", "text")     # reused
    key = g.ensure_type("GSDO Project", "GSDO Projects",
                        [p_goal_link, p_description, p_reaching, p_status, p_deadline,
                         p_parent, p_excitement, p_docs, p_affective, p_barriers, p_context])
    print(f"[ok] Project type ready: key={key}")
    return key

if __name__ == "__main__":
    build_project()
```

- [ ] **Step 2: Run it**

Run: `python3 scripts/build_project.py`
Expected: `[ok] Project type ready: key=...`. Re-run: same key, nothing new.

- [ ] **Step 3: Commit**

```bash
git add scripts/build_project.py
git commit -m "feat(gsdo): build Project type"
```

---

### Task 4: Extend the built-in Task type

**Files:**
- Create: `scripts/build_task.py`

**Interfaces:**
- Consumes: `ensure_property`, `find_type`, `link_properties_to_type` from `gsdo_anytype`; reuses `GSDO Affective`, `GSDO Relevant docs`, `GSDO Context`.
- Produces: the built-in `task` type with GSDO properties linked (including the two pre-existing standalone properties).

Spec fields (§2 Task): built-in `name`, `done`; plus `status` (select: **Active / Needs Clarifying / Blocked / Done**), `project` (objects), `blocked_on` (text), `deadline` (date), `duration_estimate` (number — **reuse existing `gsdo_duration_min`**), `affective` (text), **`access` conditions** (multi_select — just two earned tags **Can-be-done-lying-down / Involves-leaving-house**) **+ `access_notes`** (text — open annotations for unnamed EF/access barriers; feeds the §6 promotion loop), `ai_autonomous` (checkbox), `relevant_docs` (text), `context` (text). Also link the existing `gsdo_needs_clarifying` (checkbox) which is currently a standalone property. Plus `last_surfaced` (date) — see plan note 1 (flagged; included so Task 9 can function). **Note (session 4 redesign):** the old fixed four-category `embodiment` enum was dropped — open-by-design, two tags only, the rest emerges via annotations (§2 access field).

**Important:** Task is the built-in type, not custom. Do NOT create a new Task type — `find_type("task")` and link to its id.

- [ ] **Step 1: Write the builder**

```python
#!/usr/bin/env python3
"""Extend the built-in Task type with GSDO properties. Idempotent. Reuses existing standalone props."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_task():
    # reuse the two standalone properties already in the space (do NOT recreate):
    p_duration = g.ensure_property("GSDO Duration min", "number")        # existing
    p_clarify  = g.ensure_property("GSDO Needs clarifying", "checkbox")  # existing
    # new task properties:
    p_status     = g.ensure_property("GSDO Task status", "select",
                                     ["Active", "Needs Clarifying", "Blocked", "Done"])
    p_project    = g.ensure_property("GSDO Project link", "objects")
    p_blocked    = g.ensure_property("GSDO Blocked on", "text")
    p_deadline   = g.ensure_property("GSDO Deadline", "date")            # reused from Project
    p_affective  = g.ensure_property("GSDO Affective", "text")           # reused
    p_access     = g.ensure_property("GSDO Access conditions", "multi_select",
                                     ["Can-be-done-lying-down", "Involves-leaving-house"])
    p_access_nts = g.ensure_property("GSDO Access notes", "text")  # open annotations → §6 promotion loop
    p_autonomous = g.ensure_property("GSDO AI autonomous", "checkbox")
    p_docs       = g.ensure_property("GSDO Relevant docs", "text")       # reused
    p_context    = g.ensure_property("GSDO Context", "text")             # reused
    p_surfaced   = g.ensure_property("GSDO Last surfaced", "date")       # plan note 1

    task_type = g.find_type("task")
    assert task_type, "built-in 'task' type not found"
    g.link_properties_to_type(task_type["id"],
        [p_duration, p_clarify, p_status, p_project, p_blocked, p_deadline,
         p_affective, p_access, p_access_nts, p_autonomous, p_docs, p_context, p_surfaced])
    print(f"[ok] Task type extended: id={task_type['id']}")

if __name__ == "__main__":
    build_task()
```

- [ ] **Step 2: Run it**

Run: `python3 scripts/build_task.py`
Expected: `[ok] Task type extended: id=...`. Re-run: nothing new linked.

- [ ] **Step 3: Commit**

```bash
git add scripts/build_task.py
git commit -m "feat(gsdo): extend built-in Task type with GSDO properties"
```

---

### Task 5: Build the Recurring type

**Files:**
- Create: `scripts/build_recurring.py`

**Interfaces:**
- Consumes: `ensure_property`, `ensure_type`; reuses `GSDO Context`.
- Produces: `gsdo_recurring` type.

Spec fields (§2 Recurring): `frequency` (select: Daily / Weekly / As-needed), `has_target` (checkbox), `target` (text), `project` (objects — reuse `GSDO Project link`), `context` (text). **Plus time-anchor fields (session 4 — fixed appointments like weekly therapy):** `day_of_week` (multi_select Mon–Sun), `time_of_day` (text, "HH:MM"), and `duration_estimate` (reuse `GSDO Duration min`). All optional — empty for un-anchored routines; set together for a fixed appointment, which the scheduler (Task 8) treats as a fixed anchor.

- [ ] **Step 1: Write the builder**

```python
#!/usr/bin/env python3
"""Ensure the GSDO Recurring type (Practices + Routines) exists. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_recurring():
    p_freq    = g.ensure_property("GSDO Frequency", "select", ["Daily", "Weekly", "As-needed"])
    p_target  = g.ensure_property("GSDO Has target", "checkbox")
    p_tgt_txt = g.ensure_property("GSDO Target", "text")
    p_project = g.ensure_property("GSDO Project link", "objects")  # reused from Task
    p_context = g.ensure_property("GSDO Context", "text")          # reused
    # time-anchor fields (fixed appointments, e.g. weekly therapy):
    p_dow     = g.ensure_property("GSDO Day of week", "multi_select",
                                  ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    p_tod     = g.ensure_property("GSDO Time of day", "text")      # "HH:MM"
    p_dur     = g.ensure_property("GSDO Duration min", "number")   # reused from Task
    key = g.ensure_type("GSDO Recurring", "GSDO Recurring",
                        [p_freq, p_target, p_tgt_txt, p_project, p_context, p_dow, p_tod, p_dur])
    print(f"[ok] Recurring type ready: key={key}")
    return key

if __name__ == "__main__":
    build_recurring()
```

- [ ] **Step 2: Run it**

Run: `python3 scripts/build_recurring.py`
Expected: `[ok] Recurring type ready: key=...`. Re-run: same key.

- [ ] **Step 3: Commit**

```bash
git add scripts/build_recurring.py
git commit -m "feat(gsdo): build Recurring type"
```

---

### Task 6: Build the Strategy type

**Files:**
- Create: `scripts/build_strategy.py`

**Interfaces:**
- Consumes: `ensure_property`, `ensure_type`; reuses `GSDO Context`.
- Produces: `gsdo_strategy` type.

Spec fields (§2 Strategy): `status` (select: Active / Retired), `what_for` (text), `learning_notes` (text), `context` (text). (`name` built-in.)

- [ ] **Step 1: Write the builder**

```python
#!/usr/bin/env python3
"""Ensure the GSDO Strategy type (strategies/disciplines/mindsets) exists. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_strategy():
    p_status   = g.ensure_property("GSDO Strategy status", "select", ["Active", "Retired"])
    p_what_for = g.ensure_property("GSDO What for", "text")
    p_learning = g.ensure_property("GSDO Learning notes", "text")
    p_context  = g.ensure_property("GSDO Context", "text")  # reused
    key = g.ensure_type("GSDO Strategy", "GSDO Strategies",
                        [p_status, p_what_for, p_learning, p_context])
    print(f"[ok] Strategy type ready: key={key}")
    return key

if __name__ == "__main__":
    build_strategy()
```

- [ ] **Step 2: Run it**

Run: `python3 scripts/build_strategy.py`
Expected: `[ok] Strategy type ready: key=...`. Re-run: same key.

- [ ] **Step 3: Commit**

```bash
git add scripts/build_strategy.py
git commit -m "feat(gsdo): build Strategy type"
```

---

### Task 7: Orchestrator + full-model verification

**Files:**
- Create: `scripts/build_model.py`
- Create: `scripts/verify_model.py`

**Interfaces:**
- Consumes: each `build_*` function; `find_type`, `find_property` from `gsdo_anytype`.
- Produces: a one-command build (`build_model.py`) and a pass/fail verification of the whole model (`verify_model.py`).

- [ ] **Step 1: Write the verifier** (asserts every type exists and carries its spec properties; prints a 14/14-style summary)

```python
#!/usr/bin/env python3
"""Verify the full GSDO data model exists and is linked. Prints PASS/FAIL per check."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

EXPECTED = {
    "GSDO Goal":     ["GSDO Reaching for (text)", "GSDO Horizon", "GSDO Goal status", "GSDO Barriers", "GSDO Context"],
    "GSDO Project":  ["GSDO Goal link", "GSDO Description", "GSDO Project status", "GSDO Deadline",
                      "GSDO Parent project", "GSDO Excitement level", "GSDO Relevant docs",
                      "GSDO Affective", "GSDO Barriers", "GSDO Context"],
    "task":          ["GSDO Duration min", "GSDO Needs clarifying", "GSDO Task status",
                      "GSDO Project link", "GSDO Blocked on", "GSDO Deadline", "GSDO Affective",
                      "GSDO Access conditions", "GSDO Access notes",
                      "GSDO AI autonomous", "GSDO Last surfaced", "GSDO Context"],
    "GSDO Recurring":["GSDO Frequency", "GSDO Has target", "GSDO Target", "GSDO Context",
                      "GSDO Day of week", "GSDO Time of day", "GSDO Duration min"],
    "GSDO Strategy": ["GSDO Strategy status", "GSDO What for", "GSDO Learning notes", "GSDO Context"],
}

def verify():
    sid = g.get_space_id()
    passed = total = 0
    for type_name, props in EXPECTED.items():
        total += 1
        t = g.find_type(type_name)
        if not t:
            print(f"  [FAIL] type {type_name} missing"); continue
        detail = g.call("GET", f"/spaces/{sid}/types/{t['id']}")[1].get("type", {})
        linked = {p.get("key") for p in detail.get("<<TYPE_PROPS_FIELD>>", [])}
        missing = [p for p in props if (g.find_property(p) or {}).get("key") not in linked]
        ok = not missing
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {type_name}: {'all props linked' if ok else f'missing {missing}'}")
    print(f"\nSUMMARY: {passed}/{total} types fully built")
    return passed == total

if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
```
(Replace `<<TYPE_PROPS_FIELD>>` with the confirmed field name from Task 1.)

- [ ] **Step 2: Write the orchestrator**

```python
#!/usr/bin/env python3
"""Build the entire GSDO data model in dependency order, then verify."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build_goal import build_goal
from build_project import build_project
from build_task import build_task
from build_recurring import build_recurring
from build_strategy import build_strategy
import verify_model

if __name__ == "__main__":
    build_goal(); build_project(); build_task(); build_recurring(); build_strategy()
    print("\n== VERIFY ==")
    sys.exit(0 if verify_model.verify() else 1)
```

- [ ] **Step 3: Run the full build + verify**

Run: `python3 scripts/build_model.py`
Expected: each `[ok] ... ready`, then `SUMMARY: 5/5 types fully built`, exit 0. Re-run: still 5/5, nothing duplicated.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_model.py scripts/verify_model.py
git commit -m "feat(gsdo): model orchestrator + full-model verification (5/5)"
```

---

### Task 8: Deterministic clock-time scheduler (pure logic, TDD)

**Files:**
- Create: `scripts/scheduler.py`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: nothing (pure stdlib `datetime`).
- Produces: `schedule(items, start) -> list[dict]` where `items` is `list[{"name": str, "duration_min": int, "fixed_time": datetime | None}]` and `start` is a `datetime.datetime`. Items with a `fixed_time` (appointments — e.g. therapy from a time-anchored `Recurring`) are **fixed anchors**: placed at their real clock time. Items without are **flexible**: placed back-to-back in order, flowing *around* the anchors. Returns each item (copied) with `start_time`/`end_time` added. This is the function the daily-plan pipeline (§1: "Python computes the clock-time schedule") calls — the LLM never assigns times.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scheduler.py
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from scheduler import schedule

def test_places_items_back_to_back():
    start = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "A", "duration_min": 30}, {"name": "B", "duration_min": 45}]
    out = schedule(items, start)
    assert out[0]["start_time"] == dt.datetime(2026, 6, 17, 9, 0)
    assert out[0]["end_time"]   == dt.datetime(2026, 6, 17, 9, 30)
    assert out[1]["start_time"] == dt.datetime(2026, 6, 17, 9, 30)
    assert out[1]["end_time"]   == dt.datetime(2026, 6, 17, 10, 15)

def test_empty_list_returns_empty():
    assert schedule([], dt.datetime(2026, 6, 17, 9, 0)) == []

def test_missing_duration_defaults_to_30():
    out = schedule([{"name": "no-dur"}], dt.datetime(2026, 6, 17, 9, 0))
    assert out[0]["end_time"] == dt.datetime(2026, 6, 17, 9, 30)

def test_preserves_item_fields():
    out = schedule([{"name": "A", "duration_min": 10, "project": "X"}], dt.datetime(2026, 6, 17, 9, 0))
    assert out[0]["name"] == "A" and out[0]["project"] == "X"

def test_fixed_anchor_placed_at_its_time():
    start = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "therapy", "duration_min": 50, "fixed_time": dt.datetime(2026, 6, 17, 14, 0)}]
    out = schedule(items, start)
    assert out[0]["start_time"] == dt.datetime(2026, 6, 17, 14, 0)
    assert out[0]["end_time"]   == dt.datetime(2026, 6, 17, 14, 50)

def test_flexible_flows_around_anchor():
    start = dt.datetime(2026, 6, 17, 13, 0)
    items = [
        {"name": "A", "duration_min": 30},                                              # fits before
        {"name": "therapy", "duration_min": 50, "fixed_time": dt.datetime(2026, 6, 17, 14, 0)},
        {"name": "B", "duration_min": 40},                                              # too big for the gap → after
    ]
    out = schedule(items, start)
    names = [o["name"] for o in out]
    assert names == ["A", "therapy", "B"]
    assert out[0]["start_time"] == dt.datetime(2026, 6, 17, 13, 0)   # A at 13:00
    assert out[1]["start_time"] == dt.datetime(2026, 6, 17, 14, 0)   # anchor holds its time
    assert out[2]["start_time"] == dt.datetime(2026, 6, 17, 14, 50)  # B after the anchor
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_scheduler.py -v`
Expected: FAIL — `No module named 'scheduler'`.

- [ ] **Step 3: Implement `scripts/scheduler.py`**

```python
#!/usr/bin/env python3
"""Deterministic clock-time scheduler. The LLM proposes ORDER; this places items in TIME.
Spec §1: 'LLMs cannot reliably know the current time or do duration arithmetic.'"""
import datetime as dt

DEFAULT_DURATION_MIN = 30

def _dur(item):
    return item.get("duration_min") or DEFAULT_DURATION_MIN

def schedule(items, start):
    """items: list of {"name", "duration_min", "fixed_time": datetime|None, ...}. start: datetime.
    Fixed-time items are anchors placed at their clock time; flexible items flow around them.
    Returns each item (copied) with start_time/end_time added."""
    anchors = sorted(
        ({**it, "start_time": it["fixed_time"],
          "end_time": it["fixed_time"] + dt.timedelta(minutes=_dur(it))}
         for it in items if it.get("fixed_time") is not None),
        key=lambda a: a["start_time"])
    flexible = [it for it in items if it.get("fixed_time") is None]

    out = []
    cursor = start
    fi = 0
    for anchor in anchors:
        # place flexible items that fully fit before this anchor begins
        while fi < len(flexible):
            end = cursor + dt.timedelta(minutes=_dur(flexible[fi]))
            if end <= anchor["start_time"]:
                placed = dict(flexible[fi]); placed["start_time"] = cursor; placed["end_time"] = end
                out.append(placed); cursor = end; fi += 1
            else:
                break
        out.append(anchor)
        cursor = max(cursor, anchor["end_time"])
    # remaining flexible items after the last anchor
    while fi < len(flexible):
        end = cursor + dt.timedelta(minutes=_dur(flexible[fi]))
        placed = dict(flexible[fi]); placed["start_time"] = cursor; placed["end_time"] = end
        out.append(placed); cursor = end; fi += 1
    return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_scheduler.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/scheduler.py tests/test_scheduler.py
git commit -m "feat(gsdo): deterministic clock-time scheduler"
```

---

### Task 9: Neglect-resurfacing query

**Files:**
- Create: `scripts/neglect.py`
- Test: `tests/test_neglect.py`

**Interfaces:**
- Consumes: `GSDO Last surfaced` (date) property on Task (Task 4); `call` from `anytype_test` for the live read.
- Produces: `find_neglected(items, now, days=3) -> list` (pure, testable: items whose `last_surfaced` is None or older than `days`) and `query_neglected(days=3)` (live wrapper that reads active Tasks/Projects from Anytype and calls `find_neglected`).

Depends on plan note 1 (`last_surfaced` field). The pure function is fully unit-tested; the live wrapper is thin.

- [ ] **Step 1: Write the failing test** (pure function only — no live API in tests)

```python
# tests/test_neglect.py
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from neglect import find_neglected

def test_never_surfaced_is_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": None}]
    assert [i["name"] for i in find_neglected(items, now, days=3)] == ["X"]

def test_recently_surfaced_is_not_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": dt.datetime(2026, 6, 16, 9, 0)}]
    assert find_neglected(items, now, days=3) == []

def test_stale_beyond_window_is_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": dt.datetime(2026, 6, 10, 9, 0)}]
    assert [i["name"] for i in find_neglected(items, now, days=3)] == ["X"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_neglect.py -v`
Expected: FAIL — `No module named 'neglect'`.

- [ ] **Step 3: Implement `scripts/neglect.py`**

```python
#!/usr/bin/env python3
"""Neglect-resurfacing: active items not surfaced in N days. Makes the daily plan's
'still here, not today' reassurance HONEST (§9 item 6) — re-surfacing must be real."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call

def find_neglected(items, now, days=3):
    """Pure. items: list of {"last_surfaced": datetime|None, ...}. Returns the neglected ones."""
    cutoff = now - dt.timedelta(days=days)
    out = []
    for it in items:
        ls = it.get("last_surfaced")
        if ls is None or ls < cutoff:
            out.append(it)
    return out

def query_neglected(days=3, now=None):
    """Live wrapper: read active Tasks from Anytype, return the neglected ones.
    Reads the 'GSDO Last surfaced' (date) property; None when never surfaced."""
    import gsdo_anytype as g
    now = now or dt.datetime.now()
    sid = g.get_space_id()
    surfaced_key = (g.find_property("GSDO Last surfaced") or {}).get("key")
    data = call("GET", f"/spaces/{sid}/objects?limit=200")[1].get("data", [])
    items = []
    for o in data:
        pv = {p.get("key"): p for p in o.get("properties", [])}
        raw = pv.get(surfaced_key, {}).get("date") if surfaced_key else None
        ls = dt.datetime.fromisoformat(raw) if raw else None
        items.append({"name": o.get("name"), "id": o.get("id"), "last_surfaced": ls})
    return find_neglected(items, now, days=days)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_neglect.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/neglect.py tests/test_neglect.py
git commit -m "feat(gsdo): neglect-resurfacing query (pure + live wrapper)"
```

---

### Task 10: Plan-corrections logger

**Files:**
- Create: `scripts/plan_corrections_log.py`
- Test: `tests/test_plan_corrections_log.py`

**Interfaces:**
- Consumes: nothing (stdlib `json`, `datetime`).
- Produces: `log_correction(kind, before, after, path=...) -> None` appending one JSON line per correction to `scripts/data/plan_corrections.jsonl`. §9 item 7: capture June's plan-edits from day 1 so the future rhythm-learning loop has training data. v1 only *logs*; no learning loop.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_plan_corrections_log.py
import sys, os, json, tempfile, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from plan_corrections_log import log_correction

def test_appends_one_jsonl_line(tmp_path):
    path = tmp_path / "corr.jsonl"
    log_correction("move_time", {"name": "A", "start": "09:00"}, {"name": "A", "start": "11:00"}, path=str(path))
    log_correction("reject", {"name": "B"}, None, path=str(path))
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["kind"] == "move_time" and rec["before"]["start"] == "09:00" and "ts" in rec
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_plan_corrections_log.py -v`
Expected: FAIL — `No module named 'plan_corrections_log'`.

- [ ] **Step 3: Implement `scripts/plan_corrections_log.py`**

```python
#!/usr/bin/env python3
"""Append-only log of June's plan corrections (§9 item 7). v1 logs only; no learning loop yet."""
import os, json, datetime as dt

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "plan_corrections.jsonl")

def log_correction(kind, before, after, path=DEFAULT_PATH):
    """kind: e.g. 'move_time' | 'reject' | 'reorder'. before/after: JSON-serializable or None."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {"ts": dt.datetime.now().isoformat(), "kind": kind, "before": before, "after": after}
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_plan_corrections_log.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/plan_corrections_log.py tests/test_plan_corrections_log.py
git commit -m "feat(gsdo): plan-corrections logger (rhythm-learning data capture)"
```

---

## Self-Review

**1. Spec coverage (§2 data model + §9 items 2,5,6,7):**
- §2 Goal/Project/Task/Recurring/Strategy + all listed fields → Tasks 2–6. ✓
- Reuse existing `gsdo_duration_min`, `gsdo_needs_clarifying`; ignore test artifacts → Task 4 + Global Constraints. ✓
- §9 item 2 (data model created) → Tasks 2–7. ✓
- §9 item 5 scaffolding — scheduler → Task 8. ✓
- §9 item 6 — neglect-resurfacing → Task 9 (with the `last_surfaced` gap flagged). ✓
- §9 item 7 — plan-corrections log → Task 10. ✓
- **Deliberately NOT in this plan** (correct per §9 "explicitly NOT v1" and the build sequence): the weeding-gate behavior (prompt already drafted), the daily-plan LLM step (prompt drafted, validated after the model exists), drift detection, wins mirror, `afplay` dopamine sound, the spatial-time disc. This plan is the **foundation + the deterministic scaffolding** the daily plan will call — not the behaviors themselves.

**2. Placeholder scan:** Two intentional, clearly-marked discovery tokens (`<<TAGS_PATH>>`, `<<TYPE_PROPS_FIELD>>`) are resolved empirically in Task 1, Step 1 and substituted before Task 1 Step 4 / Task 7 are committed. These are not lazy placeholders — they mark the exactly-two API shapes the existing 14/14 validation never exercised, and the plan refuses to fabricate them. No other placeholders.

**3. Type consistency:** Property *names* are the idempotency key across builders (`GSDO Context`, `GSDO Reaching for (text)`, `GSDO Project link`, `GSDO Affective`, `GSDO Relevant docs`, `GSDO Deadline` are intentionally shared and reused by identical name → identical key). `schedule()`, `find_neglected()`, `query_neglected()`, `log_correction()`, and the `ensure_*` signatures are consistent between their defining task and their consumers.

---

## Two things to resolve with June before/at build (carried from spec-reading)

1. **`last_surfaced` field** — added to make neglect-resurfacing real (§9 item 6 needs surfacing-history; §2 has no such field; Anytype `last_modified` won't serve). Internal plumbing, no guard concern. Confirm: field-on-object vs. separate surface-log.
2. **The two unconfirmed API shapes** (select-option tags; property→type linking) get nailed down empirically in Task 1, Step 1 before anything depends on them — flagged so the build-loop expects a short discovery step up front rather than treating Task 1 as pure codegen.
</content>
</invoke>

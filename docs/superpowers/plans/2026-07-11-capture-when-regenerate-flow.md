# Capture-with-when → verify → regenerate-today Flow — Implementation Plan (rev. 3 — coordination-aligned)

> **For agentic workers:** implement task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (`subagent-driven-development`). Subagents WRITE files but CANNOT run Bash — the main agent runs every test / `build_model.py` / read-back / `verify` gate. Steps use `- [ ]`.

> **⚠️ COORDINATION (read first — this plan touches a multi-thread tree; see `docs/handoff_2026-07-12_orchestration.md`).**
> - **This thread is FIRST on `scripts/capture_generate.py` + the weeding contract.** The `capture-writes` plan (`docs/superpowers/plans/2026-07-12-capture-writes.md`) is explicitly sequenced *after* this one and will re-derive its anchors from the state this leaves. Do not reshape `capture()`/`_creation_props`/`parse_weed`/`_WEED_JSON_INSTRUCTION` beyond what these tasks specify.
> - **`scripts/daily_plan.py` and `scripts/plan_generate.py` are OWNED BY THE SELECTION THREAD — this plan does NOT edit them.** The "future-dated task is held off today" behavior is HANDED OFF (see the **Handoff** section). This thread ships the `Scheduled` field + a pure eligibility helper the selection thread wires in.
> - **`scripts/task_actions.py` is shared (this thread ∧ status-checker), both additive** — re-read the live file before editing (Task 5).

**Goal:** June adds tasks with a *when* (in her words); "today" items land on today's plan after a confirm; "someday" items are parked (off today now, via existing status logic); future-dated items carry an anchored date that the selection thread uses to hold them off today — all in one place, no second input.

**Architecture:** The capture LLM reads a per-item *when*. **Python owns the date** — `when_resolve` anchors the word to a real ISO date *at capture time* (never stores "Thursday"), written to a new `Scheduled` date field on Task. Selection stays deterministic and pre-LLM; `when_resolve` also provides the pure eligibility predicate (*undated or today-or-earlier → eligible; future → held off*) that the **selection thread** calls inside `load_active_items`. The receipt shows each item's *when* as a tappable chip (chip sends resolver **tokens**, Python re-anchors). When the latest capture has any today item, a verify box offers **Regenerate today** → the existing `/api/refresh` (capture's async job has finished, lock free — no chaining). "Not now" changes nothing.

**Tech Stack:** Python 3 stdlib only; `capture_generate`, `datetime_seam`, `gsdo_objects`, `gsdo_anytype`, `build_task`, `verify_model`, `session_store`, `task_actions`, `server`; vanilla JS in `docs/overlay_daily.html`; pytest.

## Global Constraints

- **Python 3 stdlib only.**
- **Date logic is deterministic Python, before the LLM. Store anchored ISO dates, never weekday words.**
- **Delete NO existing functionality** — Log mode (day/Friction tags), weeding, receipts+undo, Ask field, presets, focus authoring keep working.
- **Idempotent Anytype writes; no silent failures — raise, don't `assert`; read-back after every write.**
- **Tests self-clean — NEVER write into June's real Anytype space, session log, or generation log.** Pure-logic tests use no network; capture/task_actions tests mock the network AND the loggers (`session_store.append_entry`, `generation_log.log_generation`), or are integration and run by the main agent against a scratch object they delete. (The repo `conftest.py` sandbox tripwire fails the suite on any write to the real data dir — do not defeat it.)
- **`gsdo_objects.create`/`update` take DISPLAY names** ("Scheduled", "Task status").
- **Coordination invariants** as in the banner above: don't touch `daily_plan.py`/`plan_generate.py`; stay additive on `task_actions.py` (re-read first); this thread owns the capture-file edits and goes first.

---

## File Structure

- `scripts/build_task.py`, `scripts/verify_model.py` — add `Scheduled` date property (T1). [MINE]
- `scripts/when_resolve.py` (NEW) + `tests/test_when_resolve.py` — anchor "when" → ISO date **and** the today-eligibility predicate (T2). [MINE — the predicate is the piece the selection thread imports]
- `scripts/capture_generate.py` — contract gains `when`; capture anchors it, writes `Scheduled`, parks someday, puts `when_label`/`is_today` on the session entry (T3–T4). [MINE — first on this file]
- `scripts/task_actions.py` + `scripts/server.py` — reschedule endpoint (T5). [MINE — additive, re-read first]
- `docs/overlay_daily.html` — when-chips, verify box, wiring (T6). [MINE]
- **NOT edited here:** `scripts/daily_plan.py` / `scripts/plan_generate.py` — see **Handoff**.

---

### Task 1: Add the `Scheduled` date field to Task

**Files:** Modify `scripts/build_task.py` (`build_task()` body), `scripts/verify_model.py` (`EXPECTED["task"]`).
**Interfaces — Produces:** a live Task property, DISPLAY name `"Scheduled"`, format `date`. Distinct from `"Due date"` (a deadline — do NOT reuse it; note the orchestration routes `Due date` to the selection thread as its deadline signal — leave it alone).

- [ ] **Step 1:** In `build_task()`, add `p_scheduled = g.ensure_property("Scheduled", "date")` and include it in the `link_properties_to_type(task_type["id"], [ ... ])` list.
- [ ] **Step 2:** Add `"Scheduled"` to `EXPECTED["task"]` in `verify_model.py`.
- [ ] **Step 3 (main agent, Bash):** `python3 scripts/build_model.py` → completes; verify reports Task has `Scheduled`. Re-run once — idempotent. **Record the resolved property KEY** (may be Anytype-generated, not `gsdo_scheduled`); T4 needs it, and if generated, read the field by DISPLAY name (the "Applies when" pattern in `daily_plan.py`).
- [ ] **Step 4: Commit** `feat(schema): add Scheduled date field to Task`.

---

### Task 2: `when_resolve.py` — anchor the when + the today-eligibility predicate (both pure)

**Files:** Create `scripts/when_resolve.py`; Test `tests/test_when_resolve.py`.
**Interfaces — Produces:**
- `resolve_when(when_text, today) -> (scheduled_iso_or_None, is_today, is_parked)`. Reuses `datetime_seam.DOW_NAME_TO_WEEKDAY`.
- `is_scheduled_for_today_or_earlier(scheduled_iso, today) -> bool` — **the predicate the SELECTION thread imports** (undated/blank → True; parses ≤ today → True; strictly future → False). Tolerant of Anytype's datetime/tz round-trip form.

- [ ] **Step 1: Write the failing tests** (pure, no network):
```python
import datetime as dt
from when_resolve import resolve_when, is_scheduled_for_today_or_earlier as ok
MON = dt.date(2026, 7, 13)
def test_today():        assert resolve_when("today", MON) == (MON.isoformat(), True, False)
def test_tomorrow():     assert resolve_when("tomorrow", MON) == ("2026-07-14", False, False)
def test_next_weekday(): assert resolve_when("thursday", MON) == ("2026-07-16", False, False)
def test_same_weekday_is_next_week(): assert resolve_when("monday", MON) == ("2026-07-20", False, False)
def test_iso_passthrough():  assert resolve_when("2026-08-01", MON) == ("2026-08-01", False, False)
def test_someday_parked(): assert resolve_when("someday", MON) == (None, False, True)
def test_blank_none():   assert resolve_when("", MON) == (None, False, False) and resolve_when(None, MON) == (None, False, False)
def test_unknown_none(): assert resolve_when("whenever the vibe hits", MON) == (None, False, False)
# eligibility predicate (for the selection thread):
def test_undated_eligible():  assert ok(None, MON) is True and ok("", MON) is True
def test_today_eligible():    assert ok("2026-07-13", MON) is True
def test_overdue_eligible():  assert ok("2026-07-01", MON) is True
def test_future_excluded():   assert ok("2026-07-16", MON) is False
def test_datetime_tz_form():  assert ok("2026-07-16T00:00:00Z", MON) is False and ok("2026-07-13T00:00:00Z", MON) is True
```
- [ ] **Step 2:** Run → FAIL (no module).
- [ ] **Step 3: Implement `scripts/when_resolve.py`:**
```python
"""Anchor a free-text 'when' (from the capture LLM) to a concrete date, and answer whether a
scheduled date makes a task eligible for today. Python owns the date so 'Thursday' becomes a real
day and can't drift. The eligibility predicate is imported by the selection thread (it owns where
it's called — load_active_items); this module just provides the pure rule."""
import datetime as dt
from datetime_seam import DOW_NAME_TO_WEEKDAY  # {"Mon":0,...,"Sun":6}

_PARKED = {"someday", "eventually", "later", "whenever", "no rush", "sometime", "no date"}
_DOW = {"monday":"Mon","tuesday":"Tue","wednesday":"Wed","thursday":"Thu",
        "friday":"Fri","saturday":"Sat","sunday":"Sun"}

def _as_date(v):
    if not v: return None
    s = str(v).strip()
    try: return dt.date.fromisoformat(s)
    except ValueError:
        try: return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except ValueError: return None

def resolve_when(when_text, today):
    """(scheduled_iso|None, is_today, is_parked). Blank/unknown -> (None, False, False)."""
    if not when_text: return (None, False, False)
    w = str(when_text).strip().lower()
    if w in _PARKED:                       return (None, False, True)
    if w in ("today", "now", "tonight"):   return (today.isoformat(), True, False)
    if w == "tomorrow":                    return ((today + dt.timedelta(days=1)).isoformat(), False, False)
    d = _as_date(w)
    if d is not None:                      return (d.isoformat(), d == today, False)
    if w in _DOW:
        delta = (DOW_NAME_TO_WEEKDAY[_DOW[w]] - today.weekday()) % 7 or 7
        return ((today + dt.timedelta(days=delta)).isoformat(), False, False)
    return (None, False, False)

def is_scheduled_for_today_or_earlier(scheduled_iso, today=None):
    """True if a task is eligible for today's plan by its Scheduled date: undated or dated
    today-or-earlier. A strictly future date returns False (held off today). Selection-thread import."""
    today = today or dt.date.today()
    d = _as_date(scheduled_iso)
    return True if d is None else d <= today
```
- [ ] **Step 4:** Run → PASS (all).
- [ ] **Step 5: Commit** `feat(capture): when-resolver + today-eligibility predicate (pure)`.

---

### Task 3: Weeding-gate contract reads a per-item `when`

**Files:** Modify `scripts/capture_generate.py` — the per-item JSON contract (`_WEED_JSON_INSTRUCTION`, re-derive anchor ~`:149-171`) and confirm `parse_weed` consumers read `item.get("when","")` safely.
*Note (critic fix): `parse_weed` does NOT iterate items — it `json.loads` + top-level `setdefault`s; items are read raw at use sites. The substantive change is the PROMPT CONTRACT; there is no per-item build loop to edit and no honest failing parse test — coverage of `when` flowing through is in T4. (The later capture-writes thread will add a per-item normalization loop here; leave a clean spot.)*

- [ ] **Step 1:** In `_WEED_JSON_INSTRUCTION`, add to the per-item object:
```
"when": "<when June wants it, IN HER WORDS: 'today', a weekday like 'thursday', 'tomorrow',
         an ISO date, or 'someday'. EMPTY STRING if she didn't say. Never guess a time.>"
```
- [ ] **Step 2:** Confirm downstream reads use `item.get("when","")` (T4 does the reading).
- [ ] **Step 3: Commit** `feat(capture): weeding gate reads a per-item 'when'`.

---

### Task 4: Capture anchors the when, writes `Scheduled`, parks someday, exposes today on the session entry

**Files:** Modify `scripts/capture_generate.py` — `capture` (6-tuple unpack of `_load_weed_context()` ~`:327`), `_create_one` (~`:289`), `_creation_props` (~`:252-273`), the `session_store.append_entry` call (~`:384`). Test: `tests/test_capture_when.py`.
**Interfaces:**
- Consumes: `resolve_when` (T2); each item's `when` (T3).
- Produces: each created Task gets `Scheduled` = resolved ISO date (when non-None) and `Task status="Parked"` when `is_parked`. Each created item on the **session entry** carries `when_label` ("Today"/"Thu Jul 16"/"Parked") and `is_today: bool`. `capture()`'s return dict also has `has_today` (belt-and-suspenders); **the overlay reads the session entry, not the return** (critic fix #1 — the async worker discards `capture()`'s return).

- [ ] **Step 1: Write the failing test** — mock the LLM, network, AND loggers (critic fix #5):
```python
import datetime as dt
def test_capture_writes_scheduled_and_marks_today(monkeypatch):
    from importlib import import_module
    cg = import_module("capture_generate")
    weed = '''{"capacity_read":"","groups":[{"items":[
      {"type":"Task","name":"Email registrar","link":"","status":"Ready","action":"create","dedup_note":"","reasoning":"r","when":"today"},
      {"type":"Task","name":"Clean zotero","link":"","status":"Ready","action":"create","dedup_note":"","reasoning":"r","when":"someday"}]}]}'''
    monkeypatch.setattr(cg.plan_generate, "generate", lambda prompt: weed)
    monkeypatch.setattr(cg, "_load_weed_context", lambda: ("sid", [], [], [], [], []))  # real shape: 6-tuple
    created = {}
    monkeypatch.setattr(cg.gsdo_objects, "create", lambda type_name, name, properties=None: created.__setitem__(name, properties) or "id-"+name)
    monkeypatch.setattr(cg, "_get_object", lambda oid: {"id": oid, "properties": []})
    entries = []
    monkeypatch.setattr(cg.session_store, "append_entry", lambda kind, payload: entries.append(payload))
    monkeypatch.setattr(cg.generation_log, "log_generation", lambda *a, **k: None)
    result = cg.capture("email registrar today, someday clean zotero", today=dt.date(2026,7,13))
    assert created["Email registrar"]["Scheduled"] == "2026-07-13"
    assert created["Clean zotero"].get("Task status") == "Parked"
    assert result["has_today"] is True
    today_items = [c for e in entries for c in e.get("created", []) if c.get("is_today")]
    assert any(c.get("when_label") == "Today" for c in today_items)
```
*Implementer: confirm the real names (`_get_object`, `session_store`, `generation_log`, `create(type_name, name, properties=...)` returning an id STRING) against the file; adjust monkeypatch targets to match — the assertions are the contract.*
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Implement.**
  - `capture(text, today=None)` → default `today = dt.date.today()` (injectable).
  - In capture's per-item loop: `scheduled, is_today, is_parked = when_resolve.resolve_when(item.get("when",""), today)`; pass the tuple into `_create_one(...)` → `_creation_props(...)` (widen BOTH signatures — critic fix #6).
  - `_creation_props` (Task branch): if `scheduled`: `props["Scheduled"]=scheduled`; if `is_parked`: `props["Task status"]="Parked"` (override "Ready"). Nothing else changes.
  - `when_label`: `"Today"` if `is_today`; else `dt.date.fromisoformat(scheduled).strftime("%a %b %-d")` if `scheduled`; else `"Parked"`. Attach `when_label` + `is_today` to the created-item dict `_create_one` returns (flows into `append_entry({"created":[...]})` → `/api/session` → receipt).
  - `has_today = any(is_today ...)` in the return dict.
- [ ] **Step 4:** Run `tests/test_capture_when.py` → PASS; full suite `python3 -m pytest tests/ -q` → no regressions.
- [ ] **Step 5: Commit** `feat(capture): anchor when, write Scheduled, park someday, expose today on receipt`.

---

### Task 5: Reschedule endpoint — tap-a-chip-to-fix

**Files:** Modify `scripts/task_actions.py` (add `reschedule_task` — **re-read the live file first; status-checker also edits it, stay additive**), `scripts/server.py` (add `POST /api/task/reschedule`). Test: `tests/test_reschedule.py`.
**Interfaces — Produces:** `reschedule_task(task_id, when_text, today=None) -> dict`; `POST /api/task/reschedule {id, when}` → 200 `{ok, when_label}`. The chip sends a resolver **token**, never a display label (critic fix #9).
*Design (critic fixes #7/#8): a reschedule only WRITES a date or SETS status Parked — never CLEARS a date (sidesteps `gsdo_objects.update` dropping `None`). "someday" → `Task status=Parked` (excludes from today via status alone). Read-back compares parsed DATES, not strings (tolerates datetime/tz normalization).*

- [ ] **Step 1: Write the failing test** (mock `update` + read-back; no network):
```python
import datetime as dt
def test_reschedule_sets_scheduled(monkeypatch):
    from importlib import import_module
    ta = import_module("task_actions")
    seen = {}
    monkeypatch.setattr(ta.gsdo_objects, "update", lambda oid, props: seen.update({"id":oid, **props}) or {"id":oid})
    monkeypatch.setattr(ta, "_get_object", lambda oid: {"id":oid, "properties":[{"key":ta.SCHEDULED_KEY,"date":"2026-07-16T00:00:00Z"}]})
    out = ta.reschedule_task("abc", "thursday", today=dt.date(2026,7,13))
    assert seen["Scheduled"] == "2026-07-16"
    assert out["when_label"] == "Thu Jul 16"
def test_reschedule_someday_parks(monkeypatch):
    from importlib import import_module
    ta = import_module("task_actions")
    seen = {}
    monkeypatch.setattr(ta.gsdo_objects, "update", lambda oid, props: seen.update(props) or {"id":oid})
    monkeypatch.setattr(ta, "_get_object", lambda oid: {"id":oid, "properties":[]})
    ta.reschedule_task("abc", "someday", today=dt.date(2026,7,13))
    assert seen.get("Task status") == "Parked"
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Implement.** `reschedule_task`: `scheduled, is_today, is_parked = when_resolve.resolve_when(when_text, today or dt.date.today())`. If `is_parked`: `update(id, {"Task status":"Parked"})`. Else if `scheduled`: `update(id, {"Scheduled": scheduled})`. **Read back** via `_get_object`; confirm by comparing persisted date PARSED (`when_resolve._as_date`) to intended (or status=="Parked"); raise `RuntimeError` on genuine mismatch, never on a format difference. Return `{"id":..., "when_label": <T4 formatting>}`. Add `SCHEDULED_KEY` (from T1) or read by display name. In `server.py do_POST`, add `if self.path == "/api/task/reschedule":` mirroring `/api/complete`; return `{ok:True, when_label}`.
- [ ] **Step 4:** Run `tests/test_reschedule.py` → PASS; full suite → no regressions.
- [ ] **Step 5: Commit** `feat(capture): reschedule endpoint (tap-to-fix), status-park sidesteps date-clear`.

---

### Task 6: Overlay — when-chips, verify box, wiring

**Files:** Modify `docs/overlay_daily.html` — CSS (copy `.when-chip*`, `.verify-box*`, `.btn*` from the approved mockup `docs/mockups/flow-add-tab.html`), `renderSession()` (~`:1981-2008`), add `renderVerify()` + handlers.
**Interfaces — Consumes:** `/api/session` entries whose `created` items carry `when_label` + `is_today` (T4); `/api/refresh` (existing); `/api/task/reschedule` (T5).

- [ ] **Step 1:** Copy `.when-chip`, `.when-chip.today`, `.when-chip.parked`, `.verify-box`, `.verify-q`, `.verify-actions`, `.btn`, `.btn.primary` from the mockup into `<style>`. Scoped classes only — do NOT retune shared tokens (Phase 6 rule).
- [ ] **Step 2:** In `renderSession()`, render each created item's `when_label` as `<button class="when-chip [today|parked]">`.
- [ ] **Step 3 (critic fix #9):** Chip tap cycles the intended **token** (`today → tomorrow → someday`) and `POST /api/task/reschedule {id, when:<token>}`; on success set the chip from the returned `when_label`. Never send the rendered date label.
- [ ] **Step 4 (critic fixes #10, #1):** After a capture completes (`pollCapture`→`loadSession`), scope to the **most recent** capture turn only; if any of its created items has `is_today`, render the verify box: "*N of these is for today. Add it to today's plan and rebuild it now?*" → **Regenerate today** = `generate('/api/refresh', {})`; **Not now** = hide, change nothing. No box when none are today.
- [ ] **Step 5:** Confirm Log mode (day/Friction), undo, empty-state, Ask field untouched.
- [ ] **Step 6: Commit** `feat(overlay): when-chips + verify-before-regenerate on the Add tab`.

---

### Task 7: Integration & end-to-end verify (this thread's parts)

**Wiring:** `/api/capture` writes `Scheduled` + puts `when_label`/`is_today` on the session entry → `renderSession` shows chips → verify box (existing `/api/refresh`) → `/api/task/reschedule` for tap-to-fix. **someday→Parked drops off today via existing status logic — this thread verifies that.** The future-date exclusion is verified with the selection thread (see Handoff) — NOT here.

- [ ] **Step 1 (main agent):** restart `python3 scripts/server.py`; load the overlay.
- [ ] **Step 2:** drive the real flow via `verify` with a mixed dump — *"email the registrar today, draft the syllabus thursday, someday clean up my zotero"* — and OBSERVE:
  - receipt shows chips **Today / (dated) / Parked**;
  - verify box says **1** is for today; **Regenerate today** rebuilds today with the today task on it;
  - read back objects: the Thursday task exists, `Scheduled` = the anchored date, status Ready; the someday task is `Parked`;
  - **the someday (Parked) task is NOT on today's plan** (existing status exclusion — verify this holds now);
  - tap the Thursday chip → "someday" → read back status `Parked`;
  - **Not now** on a fresh capture leaves the plan unchanged.
- [ ] **Step 3:** No regressions — Log (day+Friction), receipt undo, Ask field reorder/generate.
- [ ] **Step 4:** Full suite `python3 -m pytest tests/ -q` → green; nothing left in June's real space.
- [ ] **Step 5: Commit** `test(flow): end-to-end verify — when anchored, someday off today, verify-gated regenerate`.

---

## HANDOFF TO THE SELECTION THREAD (not built by this thread)

The selection thread owns `daily_plan.py`/`plan_generate.py`. This thread hands it two finished pieces so "a future-dated task is held off today" lands inside their reconciled model:

1. **The `Scheduled` field** (T1) — populated at capture time with an anchored ISO date (today items = today's date; future = that date; someday = no date + status `Parked`).
2. **The pure predicate** `when_resolve.is_scheduled_for_today_or_earlier(scheduled_iso, today)` (T2) — `True` for undated or today-or-earlier, `False` for strictly future. Tolerant of Anytype's datetime/tz form.

**What the selection thread wires (their file, their call):** in `load_active_items`, read each task's `Scheduled` (by the key/display-name recorded in T1) and skip the task when the predicate returns `False` — so future-dated tasks don't enter today's candidate pool. This is *date-eligibility*; it composes with their engagement sizing (eligibility first, sizing second).

**The one precedence question for their model (NOT decided here):** does a `Scheduled==today` task on a low-engagement (e.g. Backburner) project pin through the engagement cap, or is it still subject to it? This is theirs to settle in the reconciled selection design.

**Joint verify (after they wire it):** capture a "thursday" task and confirm it is absent from today's plan until its date, then appears on/after it. Until then, this thread's Task 7 verifies everything except the future-date exclusion.

---

## Self-Review (rev. 3)

- **Coordination-aligned:** no edits to `daily_plan.py`/`plan_generate.py`; the future-date behavior is a clean handoff (populated field + pure predicate + wiring spec + precedence question). This thread is first on `capture_generate.py`; `task_actions.py` edits are additive with a re-read note.
- **Every critic blocker still addressed:** has_today via session entry (T4) · test mocks 6-tuple + `_get_object` + loggers, self-cleans (T4) · park-via-status sidesteps date-clear (T5) · tolerant date read-back (T2 `_as_date`, T5) · chip sends tokens (T6) · no dead resolver code (T2) · T3 no fake-TDD (T3) · both `_create_one`/`_creation_props` signatures widened (T4) · verify box scoped to latest capture (T6).
- **Decoupled value ships now:** capture vocabulary, anchored `Scheduled`, someday→Parked (real "off today" via existing status), chips, verify, regenerate, reschedule — all verified in T7 without touching the selection thread's files.
- **Executor open flags:** confirm the `Scheduled` property key (T1 Step 3) and the live `session_store` created-item shape against the files before T4.

# Overlay: Tap-to-Place Task Move (times recompute) + Work-Stream Summary Rows — Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking. **Subagents WRITE the code; the main agent RUNS Bash** (subagents in this repo can't run Bash — every `Run:` / pytest / git step is executed by the main agent after the subagent's write lands). Steps that must run in Bash are marked **[main-agent Bash]**.

**Goal:** Add two June-decided features to the Today overlay: (1) **tap-to-place move** — tap a "move" control on a task, tap-targets appear at every later spot in the visible plan (between items, at block starts and ends), tap one and the task lands there with **every clock time recomputed automatically and deterministically** — no LLM, no regeneration; on fragmented (no-time-block) days the same tap-to-place reorders the list. (2) When a work-stream row is expanded, show **what the project is and its next step** first, with a further tap to reveal its individual tasks.

**Architecture:** Both features are surface-only. **Move** mutates the cached plan file (`~/.controlled-drift/current_plan.json`) in place: the item is re-inserted at the tapped position and the affected blocks' clock times **re-flow deterministically from the items' existing durations** (a first-fit walk: each item starts where the previous one ends, from the block's start) — pure arithmetic in `plan_store`, never `plan_generate`/`daily_plan`, never `/api/negotiate`, never Anytype. The API is **positional** (block index + insertion index), which is exactly what a tap-target is. **Summary rows** read each project's plain-language Context (the same `gsdo_context` the map reads), parse it deterministically, and render it above the task list; when the Context doesn't parse, the row falls back to the task list with no invented text. New Python is confined to `plan_store` (the moves + re-flow), a tiny `project_summary` helper (the parse), and two `server` routes; all UI lives in `docs/overlay_daily.html`.

**Tech Stack:** Python 3 stdlib only (no new deps); the existing stdlib `http.server`; vanilla JS in the single-file overlay; pytest with the repo's auto-sandbox (`tests/conftest.py` redirects all data/config to a throwaway dir, so tests self-clean).

**Context that changed since first draft (2026-07-12):**
- **The selection fix has LANDED** (`docs/handoff_selection-fix_2026-07-12.md`): the cached plan this feature mutates is now the gated **~13-next-moves day, not 82 items**. Tap-to-place therefore operates on a short visible plan — a screenful of tap-targets, not a wall.
- **Two real cross-family review findings were just fixed in `overlay_daily.html`** (commit `9896723`): `cycleWhen` (the when-chip) no longer fails silently — on any non-ok result it says plainly "That change didn't save — tap the chip again." via `setAddStatus`. **The move UI must follow the same never-silent pattern.** One deliberate adaptation: `setAddStatus` writes to the Add tab's status line, which is not on screen from the Today tab where the move control lives — so move failures surface through `showError` (the Today tab's existing visible error surface, already used by `toggleItem`). Same honesty rule, the tab's own visible channel.
- **A break-block formatting fix just landed** (commit `945bc87`): interstitial `.item-task` is now 13px/600/text-dim so break/meal names scan as their own block (CSS ~lines 423–450). The move UI renders interstitials through the same `renderFlatItem` path — do not disturb that styling, and interstitials get no move control (they carry no task id).
- The when-chip / verify-box code on the Add tab (commit `c5236a9`) must keep working untouched.

---

## Decisions from June (2026-07-12) — these settle the first draft's open questions

1+2. **Move = tap-to-place, with automatic time recalculation.** Her clarification: "after lunch is imprecise. I meant more that I'll need to be able to navigate the UX and move it with those considerations in mind. Honestly it could even be click and drag." Decided v1: tap a "move" control on the item → tap-targets appear at every later spot in the visible plan (between items, at the start and end of later blocks) → tap where it goes. No language tokens, no block-name pickers, no drag. The cached plan's clock times re-flow deterministically from the existing durations — **no blanked times: every item shows a recomputed time.** Drag-and-drop is a possible later enhancement (desktop), **not v1** — see "Later work". The honesty rule is unchanged: the move is a day-of adjustment; the next generation replaces it; no copy promises otherwise.
3. **Summary-rows scope approved as planned:** multi-task work-stream rows only. A lone task from a project still renders flat.
4. **Silent task-list fallback approved** ("that sounds good") when a project's what-it-is/next-step text doesn't parse (divergence ledger H2) — no placeholder, no invented text. **Terminology ruling: the word "focus" is banned from June-facing copy** — it collides with the global Focus Period. June-facing words are plain: "what this project is / next step." Internals also prefer `project_summary` / `summary` naming so the collision stops propagating.
5. **Reorder on fragmented days too — do not disable.** Her words: "I actually wouldn't mind being able to change the order even when there aren't time blocks." On priority-list days the same tap-to-place moves an item later in the list (pure position change, no times involved). Built as its own task with its own tests.

## Later work (noted, deliberately NOT in v1)

- **Drag-and-drop reordering** (desktop): June said "it could even be click and drag." v1 ships tap-to-place because it works identically on phone and desktop and costs no fine-motor precision; drag can be layered on later as an additional input method for the same positional `/api/task/move` API without changing the backend.

---

## Global Constraints

Copied from the task brief, June's decisions, and repo build discipline; every task inherits these.

- **No LLM, no regeneration, no Anytype write for the move.** Task-move edits the cached plan + rendering only. It must not call `plan_generate`, must not route through `/api/negotiate`, and must not write the plan (or the move) to Anytype. The time re-flow is pure recomputation over the cached plan's blocks inside `plan_store`.
- **The move is a day-of adjustment, not a stored preference.** The next generation rebuilds the plan from Anytype and the move is gone. **June-facing copy must not promise persistence the system doesn't have** — this repo's worst failure mode is words promising machinery that doesn't exist.
- **Do NOT touch** `scripts/daily_plan.py`, `scripts/plan_generate.py`, `scripts/build_project.py`. (Reading them is fine; editing is not. This plan only reads them.)
- **Stdlib only.** No new dependencies.
- **No silent failures.** Raise on failure; the server surfaces the error honestly; the overlay says plainly when a change didn't save (the `cycleWhen` pattern) — via `showError` on the Today tab. Never `assert` for control flow.
- **Access requirements (anything June-facing):** plain language, **no metaphors**, and **the word "focus" never appears in June-facing copy** for these features (reserved for the Focus Period); one thing at a time; **tap-based only — no drag in v1** (drag is a fine-motor and attention cost; possible later desktop enhancement only).
- **Read-back discipline:** any Anytype write proves it persisted by re-fetching before reporting success (the two features here make no Anytype writes; this applies to the final task's closing of the two tracking tasks).
- **Tests self-clean:** the pytest sandbox in `tests/conftest.py` redirects all data/config to a temp dir automatically; never write to June's real space or `~/.controlled-drift/`.
- **Per-task commits.** Small atomic commits at each task boundary.

---

## File Structure

**Modify:**
- `scripts/plan_store.py` — add `move_item_later(task_id, target_block_index, position=None)` (clock-shape move + deterministic time re-flow), `move_priority_item_later(task_id, position)` (fragmented-day reorder), and the small helpers (`_hhmm_to_min`, `_min_to_hhmm`, `_range_bounds`, `_reflow_block`, `_write_plan`). One clear responsibility (cache read/write) it already owns.
- `scripts/server.py` — add `POST /api/task/move` and `GET /api/project-summaries`; add `import project_summary` at the top.
- `docs/overlay_daily.html` — the tap-to-place move (move chip → placement mode with "move here" targets → positional POST) on both plan shapes; the summary-first work-stream row expansion; CSS for both; wire `loadProjectSummaries()` into boot + generation-complete.
- `tests/test_plan_store.py` — unit tests for both move functions and the re-flow arithmetic.
- `tests/test_server.py` — route tests for `/api/task/move` (both shapes) and `/api/project-summaries`.

**Create:**
- `scripts/project_summary.py` — a small helper: given the project dicts, return `{name: {what_it_is, next_step}}` by reusing `orient_map._parse_context`. One parser, not two.
- `tests/test_project_summary.py` — unit tests, including the honest-empty case.

**Read only (do not edit):** `scripts/plan_generate.py` (item/block shape, `_resolve_ids`), `scripts/daily_plan.py` (`load_active_items` project shape), `scripts/orient_map.py` (`_parse_context`).

### Data shapes this plan relies on (verified in the codebase)

- **Cached plan** (`plan_store.load_plan()`): `{woven_frame, blocks: [{label, time, framing, items: [...]}], still_here: [...], generated_at, source}`. A fragmented day instead has `{shape: "priority", header, items: [...]}` with **no `blocks`** and **no clock times on items**.
- **A plan item:** `{time, project, task, why, id?, description?, interstitial?}`. `project` is the project **name** (a string), not an id. `id` is the Anytype task id, present only when resolvable. Times use the en-dash range form `"09:00 – 10:30"`; block times likewise (`"09:00 – 12:00"`).
- **Position contract (this plan's one new convention):** a move destination is `(target_block, position)` where `position` is the item's index in the destination block's item list **after the move** (the "final index"). A tap-target *is* a position, so the client computes it directly. On priority-shape days there is no block — just `position` in the flat list.
- **Project dict** from `daily_plan.load_active_items(sid)` (returns `goals, projects, tasks, ...`): each project carries `{id, name, context, side, engagement, parent_project_id, ...}`. `context` is the raw `gsdo_context` free text.
- **`orient_map._parse_context(ctx)`** → `(what_it_is, the_arc, next_step)`; any missing line is `None`. It splits on the first em-dash of lines beginning `what it is` / `the arc` / `next step`. Silently returns all-`None` on non-conforming text (that's H2 in `docs/divergence_ledger_2026-07-12.md`).

---

## Task 1: `plan_store` — clock-shape positional move with deterministic time re-flow

**Files:**
- Modify: `scripts/plan_store.py` (add helpers + one function after `mark_item_undone`, ~line 169)
- Test: `tests/test_plan_store.py`

**Interfaces:**
- Consumes: `plan_store.load_plan()` (existing), `plan_store._plan_path()` (existing).
- Produces:
  - `move_item_later(task_id: str, target_block_index: int, position: int | None = None) -> dict` — returns the updated plan. `position` is the final index in the destination block (None = append). Raises `LookupError` (no cache / no blocks / task id not scheduled) and `ValueError` (destination not later / index out of range / same-block move without a later position).
  - Module helpers later tasks reuse: `_reflow_block(block) -> None` (in-place), `_write_plan(plan) -> None` (atomic persist).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_plan_store.py`:

```python
# --- tap-to-place move (deterministic, no LLM) — clock shape ------------------

def _clock_plan():
    return {
        "woven_frame": "wf",
        "blocks": [
            {"label": "Morning", "time": "09:00 – 12:00",
             "items": [{"time": "09:00 – 10:30", "project": "Alpha", "task": "draft", "id": "T1"},
                       {"time": "10:30 – 11:15", "project": "Beta", "task": "email", "id": "T2"},
                       {"time": "11:15 – 12:00", "project": "Beta", "task": "forms", "id": "T3"}]},
            {"label": "Afternoon", "time": "13:00 – 17:00",
             "items": [{"time": "13:00 – 14:00", "project": "Gamma", "task": "call", "id": "T4"}]},
        ],
        "still_here": [],
    }


def test_move_append_to_later_block_recomputes_times(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    updated = plan_store.move_item_later("T1", 1)   # position None -> append
    assert "T1" not in [i.get("id") for i in updated["blocks"][0]["items"]]
    # T1 keeps its 90-min duration; T4 ends 14:00 -> T1 is 14:00 – 15:30. Never blanked.
    moved = next(i for i in updated["blocks"][1]["items"] if i.get("id") == "T1")
    assert moved["time"] == "14:00 – 15:30"


def test_move_to_start_of_later_block(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    updated = plan_store.move_item_later("T1", 1, position=0)   # the block-start tap-target
    ids = [i["id"] for i in updated["blocks"][1]["items"]]
    assert ids == ["T1", "T4"]
    times = {i["id"]: i["time"] for i in updated["blocks"][1]["items"]}
    assert times == {"T1": "13:00 – 14:30", "T4": "14:30 – 15:30"}


def test_move_closes_the_gap_in_the_source_block(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    updated = plan_store.move_item_later("T1", 1)
    # The source block re-flows from its start: T2 (45 min) now 09:00–09:45, T3 09:45–10:30.
    t2 = next(i for i in updated["blocks"][0]["items"] if i.get("id") == "T2")
    t3 = next(i for i in updated["blocks"][0]["items"] if i.get("id") == "T3")
    assert t2["time"] == "09:00 – 09:45"
    assert t3["time"] == "09:45 – 10:30"


def test_move_later_within_same_block(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    # Tap-target after T2: T1 lands at final index 1 -> [T2, T1, T3], durations kept.
    updated = plan_store.move_item_later("T1", 0, position=1)
    assert [i["id"] for i in updated["blocks"][0]["items"]] == ["T2", "T1", "T3"]
    times = {i["id"]: i["time"] for i in updated["blocks"][0]["items"]}
    assert times == {"T2": "09:00 – 09:45", "T1": "09:45 – 11:15", "T3": "11:15 – 12:00"}


def test_move_overflow_past_block_end_is_honest_arithmetic(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan = _clock_plan()
    plan["blocks"][1]["items"].append({"time": "14:00 – 16:45", "project": "Gamma",
                                       "task": "long thing", "id": "T5"})
    plan_store.save_plan(plan, source="generate")
    updated = plan_store.move_item_later("T1", 1)   # 90 min appended after 16:45
    moved = next(i for i in updated["blocks"][1]["items"] if i["id"] == "T1")
    # Runs past the block label's 17:00 end — the arithmetic tells the truth; we never
    # squeeze or invent durations to make it fit.
    assert moved["time"] == "16:45 – 18:15"


def test_move_unparseable_item_time_falls_back_to_default_duration(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan = _clock_plan()
    plan["blocks"][0]["items"][1]["time"] = ""   # T2 has no parseable time
    plan_store.save_plan(plan, source="generate")
    updated = plan_store.move_item_later("T1", 1)
    t2 = next(i for i in updated["blocks"][0]["items"] if i["id"] == "T2")
    assert t2["time"] == "09:00 – 09:30"   # default 30 min, anchored to block start


def test_move_preserves_generated_at_and_source(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    saved = plan_store.save_plan(_clock_plan(), source="refresh")
    updated = plan_store.move_item_later("T1", 1)
    # A move is not a regeneration — the timestamp/source must not be re-stamped.
    assert updated["generated_at"] == saved["generated_at"]
    assert updated["source"] == "refresh"


def test_move_persists_to_cache(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    plan_store.move_item_later("T1", 1)
    reloaded = plan_store.load_plan()
    assert "T1" in [i.get("id") for i in reloaded["blocks"][1]["items"]]
    assert not os.path.exists(str(tmp_path / "current_plan.json.tmp"))  # atomic, no leftover


def test_move_rejects_not_later(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    import pytest
    with pytest.raises(ValueError):
        plan_store.move_item_later("T4", 0)                 # earlier block
    with pytest.raises(ValueError):
        plan_store.move_item_later("T1", 0)                 # same block, no position
    with pytest.raises(ValueError):
        plan_store.move_item_later("T2", 0, position=0)     # same block, EARLIER spot
    with pytest.raises(ValueError):
        plan_store.move_item_later("T2", 0, position=1)     # same block, same spot (no-op)


def test_move_rejects_out_of_range_and_missing_id(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    import pytest
    with pytest.raises(ValueError):
        plan_store.move_item_later("T1", 9)                 # block out of range
    with pytest.raises(ValueError):
        plan_store.move_item_later("T1", 1, position=5)     # position out of range
    with pytest.raises(LookupError):
        plan_store.move_item_later("NOPE", 1)


def test_move_raises_when_no_cache_or_no_blocks(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    import pytest
    with pytest.raises(LookupError):
        plan_store.move_item_later("T1", 1)
    plan_store.save_plan({"shape": "priority", "items": [{"task": "x", "id": "T1"}]},
                         source="generate")
    with pytest.raises(LookupError):
        plan_store.move_item_later("T1", 1)   # priority shape has no blocks (see Task 2)
```

- [ ] **Step 2: Run the tests to verify they fail** **[main-agent Bash]**

Run: `python3 -m pytest tests/test_plan_store.py -k move -v`
Expected: FAIL — `AttributeError: module 'plan_store' has no attribute 'move_item_later'`.

- [ ] **Step 3: Write the implementation**

Add to `scripts/plan_store.py` immediately after `mark_item_undone` (after ~line 169):

```python
# --- tap-to-place move (deterministic — no LLM, no regeneration) -------------
# June moves a task by TAPPING WHERE IT GOES: the overlay shows tap-targets at every later
# spot in the visible plan, and the tapped spot arrives here as (target_block, position).
# The clock times then RE-FLOW automatically: pure first-fit arithmetic over the cached
# plan's existing durations. This never touches plan_generate/daily_plan and never writes
# to Anytype. It is a day-of adjustment to what's on screen, NOT a stored preference: the
# next generation rebuilds the plan from Anytype and the move is gone (overlay copy says
# so — nothing here promises persistence).

_DEFAULT_ITEM_MIN = 30  # fallback duration when an item's current time doesn't parse


def _hhmm_to_min(s):
    """'13:30' -> 810, or None if it isn't an HH:MM string."""
    try:
        h, m = str(s).strip().split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _min_to_hhmm(n):
    n %= 24 * 60
    return f"{n // 60:02d}:{n % 60:02d}"


def _range_bounds(s):
    """'09:00 – 10:30' -> (540, 630). A single time or unparseable text -> (start_or_None, None).
    Splits on the en-dash, the separator every generated time range uses."""
    if not s:
        return None, None
    parts = [p.strip() for p in str(s).split("–")]
    start = _hhmm_to_min(parts[0]) if parts else None
    end = _hhmm_to_min(parts[1]) if len(parts) > 1 else None
    return start, end


def _reflow_block(block):
    """Recompute every item's clock time in this block, in order — the automatic time
    recalculation June asked for. Each item KEEPS its existing duration (or 30 min if its
    current time doesn't parse); item N starts where item N-1 ends; the walk starts at the
    block's own start time (or the first item's, if the block has none). If nothing gives a
    start time, the times are left exactly as they are — an honest no-op, never invented.
    If the durations run past the block's labelled end, the times run past it too: the
    arithmetic tells the truth rather than squeezing tasks to fit."""
    items = block.get("items", [])
    if not items:
        return
    cursor, _ = _range_bounds(block.get("time"))
    if cursor is None:
        cursor, _ = _range_bounds(items[0].get("time"))
    if cursor is None:
        return
    for item in items:
        s, e = _range_bounds(item.get("time"))
        dur = (e - s) if (s is not None and e is not None and e > s) else _DEFAULT_ITEM_MIN
        item["time"] = f"{_min_to_hhmm(cursor)} – {_min_to_hhmm(cursor + dur)}"
        cursor += dur


def _write_plan(plan):
    """Atomic persist of an in-place plan mutation (same discipline as save_plan/mark_item_done:
    the overlay never reads a half-written plan). Deliberately does NOT re-stamp
    generated_at/source — a move is not a regeneration."""
    path = _plan_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(plan, f, indent=2)
    os.replace(tmp, path)


def move_item_later(task_id, target_block_index, position=None):
    """Move one scheduled task LATER in the cached clock-shape plan and re-flow the times.

    `position` is the item's FINAL index in the destination block's item list (the tap-target
    the overlay showed); None appends to the end of the destination block. A move within the
    SAME block needs a position strictly greater than the item's current index; any other
    destination must be a strictly later block. Both affected blocks are re-flowed so every
    item shows a real recomputed time.

    Returns the updated plan dict. Raises:
      LookupError — no cached plan; no clock-shape blocks (fragmented days reorder via
                    move_priority_item_later instead); or no scheduled item with task_id.
      ValueError  — block/position out of range, or the destination is not strictly later.
    """
    plan = load_plan()
    if plan is None:
        raise LookupError("no cached plan to move within")
    blocks = plan.get("blocks")
    if not blocks:
        raise LookupError("plan has no time-blocks — use move_priority_item_later for a "
                          "fragmented (priority-shape) day")
    if not (0 <= target_block_index < len(blocks)):
        raise ValueError(f"target block {target_block_index} out of range (0..{len(blocks) - 1})")

    src_index = src_pos = None
    for bi, block in enumerate(blocks):
        for pos, item in enumerate(block.get("items", [])):
            if item.get("id") == task_id:
                src_index, src_pos = bi, pos
                break
        if src_index is not None:
            break
    if src_index is None:
        raise LookupError(f"no scheduled item with id {task_id!r} to move")
    if target_block_index < src_index:
        raise ValueError("can only move a task later")

    # Validate the landing spot BEFORE mutating anything.
    if target_block_index == src_index:
        n = len(blocks[src_index]["items"])
        # Same block: the final index must be strictly later than where it is now.
        if position is None or not (src_pos < position <= n - 1):
            raise ValueError("a move within its own part of the day must land at a later spot")
    else:
        n = len(blocks[target_block_index].get("items", []))
        if position is None:
            position = n                      # append (the block-end tap-target)
        elif not (0 <= position <= n):
            raise ValueError(f"position {position} out of range for that part of the day (0..{n})")

    src_item = blocks[src_index]["items"].pop(src_pos)
    # After the pop, inserting at `position` puts the item at exactly that final index —
    # including the same-block case (everything after src_pos shifted down by one).
    blocks[target_block_index].setdefault("items", []).insert(position, src_item)

    _reflow_block(blocks[src_index])
    if target_block_index != src_index:
        _reflow_block(blocks[target_block_index])

    _write_plan(plan)
    return plan
```

- [ ] **Step 4: Run the tests to verify they pass** **[main-agent Bash]**

Run: `python3 -m pytest tests/test_plan_store.py -v`
Expected: PASS (all move tests + the existing ones).

- [ ] **Step 5: Commit** **[main-agent Bash]**

```bash
git add scripts/plan_store.py tests/test_plan_store.py
git commit -m "feat(overlay): positional move-later in the cached plan with deterministic time re-flow"
```

---

## Task 2: `plan_store.move_priority_item_later` — reorder on fragmented days

June: "I actually wouldn't mind being able to change the order even when there aren't time blocks." On a priority-shape day the plan is a flat ordered list with no clock times — a move is a pure position change, same tap-to-place, nothing to re-flow.

**Files:**
- Modify: `scripts/plan_store.py` (add one function after `move_item_later`)
- Test: `tests/test_plan_store.py`

**Interfaces:**
- Consumes: `load_plan()`, `_write_plan(plan)` (Task 1).
- Produces: `move_priority_item_later(task_id: str, position: int) -> dict` — `position` is the final index in the flat list. Raises `LookupError` (no cache / no priority list / id missing) and `ValueError` (position not later / out of range).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_plan_store.py`:

```python
# --- tap-to-place on a fragmented (priority-shape) day — pure position change --

def _priority_plan():
    return {"shape": "priority", "header": "a short list to pull from",
            "items": [{"project": "Alpha", "task": "draft", "id": "P1"},
                      {"project": "Beta", "task": "email", "id": "P2"},
                      {"project": "Gamma", "task": "call", "id": "P3"}],
            "still_here": []}


def test_priority_move_to_later_position(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_priority_plan(), source="generate")
    updated = plan_store.move_priority_item_later("P1", 2)
    assert [i["id"] for i in updated["items"]] == ["P2", "P3", "P1"]
    # No times involved on a fragmented day — items still carry none.
    assert "time" not in updated["items"][2]


def test_priority_move_one_step(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_priority_plan(), source="generate")
    updated = plan_store.move_priority_item_later("P1", 1)
    assert [i["id"] for i in updated["items"]] == ["P2", "P1", "P3"]


def test_priority_move_persists_and_preserves_stamp(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    saved = plan_store.save_plan(_priority_plan(), source="refresh")
    plan_store.move_priority_item_later("P1", 1)
    reloaded = plan_store.load_plan()
    assert [i["id"] for i in reloaded["items"]] == ["P2", "P1", "P3"]
    assert reloaded["generated_at"] == saved["generated_at"]
    assert reloaded["source"] == "refresh"


def test_priority_move_rejects_not_later_and_out_of_range(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_priority_plan(), source="generate")
    import pytest
    with pytest.raises(ValueError):
        plan_store.move_priority_item_later("P3", 1)   # earlier spot
    with pytest.raises(ValueError):
        plan_store.move_priority_item_later("P2", 1)   # same spot (no-op)
    with pytest.raises(ValueError):
        plan_store.move_priority_item_later("P1", 9)   # out of range


def test_priority_move_raises_on_missing_id_clock_shape_or_no_cache(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    import pytest
    with pytest.raises(LookupError):
        plan_store.move_priority_item_later("P1", 1)   # no cache
    plan_store.save_plan(_priority_plan(), source="generate")
    with pytest.raises(LookupError):
        plan_store.move_priority_item_later("NOPE", 1)
    plan_store.save_plan(_clock_plan(), source="generate")
    with pytest.raises(LookupError):
        plan_store.move_priority_item_later("T1", 1)   # clock plan has no priority list
```

- [ ] **Step 2: Run the tests to verify they fail** **[main-agent Bash]**

Run: `python3 -m pytest tests/test_plan_store.py -k priority_move -v`
Expected: FAIL — `AttributeError: ... no attribute 'move_priority_item_later'`.

- [ ] **Step 3: Write the implementation**

Add to `scripts/plan_store.py` after `move_item_later`:

```python
def move_priority_item_later(task_id, position):
    """Move one item LATER in a fragmented-day (priority-shape) plan. `position` is the item's
    FINAL index in the flat list (the tap-target the overlay showed). Pure position change —
    priority items carry no clock times, so there is nothing to re-flow. Same honesty rule as
    move_item_later: a day-of adjustment to the cache; the next generation replaces it.
    Preserves generated_at/source.

    Raises LookupError (no cached plan / no priority list / id absent) and ValueError
    (position not strictly later, or out of range)."""
    plan = load_plan()
    if plan is None:
        raise LookupError("no cached plan to move within")
    items = plan.get("items")
    if not items:
        raise LookupError("plan has no priority list to reorder (a clock-shape day moves via "
                          "move_item_later)")
    src_pos = next((i for i, it in enumerate(items) if it.get("id") == task_id), None)
    if src_pos is None:
        raise LookupError(f"no item with id {task_id!r} to move")
    if not (src_pos < position <= len(items) - 1):
        raise ValueError("can only move a task to a later spot in the list")
    item = items.pop(src_pos)
    items.insert(position, item)   # after the pop, inserting at `position` = final index
    _write_plan(plan)
    return plan
```

- [ ] **Step 4: Run the tests to verify they pass** **[main-agent Bash]**

Run: `python3 -m pytest tests/test_plan_store.py -v`
Expected: PASS.

- [ ] **Step 5: Commit** **[main-agent Bash]**

```bash
git add scripts/plan_store.py tests/test_plan_store.py
git commit -m "feat(overlay): reorder a fragmented-day priority list by tapped position"
```

---

## Task 3: `project_summary` helper — parse per-project what-it-is / next-step honestly

**Files:**
- Create: `scripts/project_summary.py`
- Test: `tests/test_project_summary.py`

**Interfaces:**
- Consumes: `orient_map._parse_context(ctx) -> (what_it_is, the_arc, next_step)` (existing).
- Produces: `project_summary.summary_map(projects: list[dict]) -> dict[str, dict]` — `{name: {"what_it_is": str?, "next_step": str?}}`, including ONLY projects whose Context yields at least one of the two. A project with neither is omitted (honest empty).

Naming note: this module is deliberately **not** called "focus" anything — "focus" is the Focus Period's word, and June flagged the collision. Internals say `summary`; June-facing copy says "What it is" / "Next step" and never says "focus".

- [ ] **Step 1: Write the failing tests**

Create `tests/test_project_summary.py`:

```python
"""Tests for project_summary.summary_map — the per-project 'what it is / next step' the overlay
shows first when a work-stream row is expanded. Pure function over in-memory dicts; no Anytype,
no files, so nothing to clean up."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_summary


def test_parses_what_it_is_and_next_step():
    projects = [{"name": "Alpha",
                 "context": "what it is — the flagship build\nnext step — wire the overlay"}]
    sm = project_summary.summary_map(projects)
    assert sm["Alpha"]["what_it_is"] == "the flagship build"
    assert sm["Alpha"]["next_step"] == "wire the overlay"


def test_includes_partial_when_only_one_line_present():
    projects = [{"name": "Beta", "context": "what it is — just the what, no next step line"}]
    sm = project_summary.summary_map(projects)
    assert sm["Beta"] == {"what_it_is": "just the what, no next step line"}


def test_omits_projects_with_unparseable_context():
    # H2: the parse is fragile. A project whose Context isn't in the em-dash convention yields
    # NOTHING and is left OUT of the map — the overlay then falls back to the task list. We never
    # fabricate summary text.
    projects = [
        {"name": "Gamma", "context": "just some freeform notes with no structured lines"},
        {"name": "Delta", "context": ""},
        {"name": "Epsilon", "context": None},
    ]
    assert project_summary.summary_map(projects) == {}


def test_skips_nameless_projects():
    projects = [{"name": None, "context": "what it is — orphan"}]
    assert project_summary.summary_map(projects) == {}
```

- [ ] **Step 2: Run the tests to verify they fail** **[main-agent Bash]**

Run: `python3 -m pytest tests/test_project_summary.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'project_summary'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/project_summary.py`:

```python
#!/usr/bin/env python3
"""Per-project summary ('what it is' / 'next step') for the Today overlay's expandable
work-stream rows.

When June opens a work-stream row, she sees what the project is and its next step FIRST, and
can open it a further step to the individual tasks. The summary is parsed from each project's
plain-language Context (the same gsdo_context lines the map reads), reusing
orient_map._parse_context so there is ONE parser, not two.

NAMING: not called "focus" — that word belongs to the global Focus Period and June flagged the
collision. Internals say `summary`; her screen says "What it is" / "Next step".

HONESTY (divergence ledger H2, docs/divergence_ledger_2026-07-12.md): the Context parse is
fragile string-matching — it only yields anything when the Context is written as
`what it is — …` / `next step — …`, and silently yields nothing otherwise. This module does NOT
invent text to fill the gap. A project whose Context doesn't parse is simply OMITTED from the
map; the overlay then falls back to showing the task list directly. Empty is the honest answer.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import orient_map


def summary_map(projects):
    """projects: the project dicts from daily_plan.load_active_items (each with a 'context' free
    text field). Returns {name: {"what_it_is": str?, "next_step": str?}} including ONLY projects
    whose Context yields at least one of the two lines. A project with neither is left out."""
    out = {}
    for p in projects:
        name = p.get("name")
        if not name:
            continue
        what_it_is, _arc, next_step = orient_map._parse_context(p.get("context") or "")
        entry = {}
        if what_it_is:
            entry["what_it_is"] = what_it_is
        if next_step:
            entry["next_step"] = next_step
        if entry:
            out[name] = entry
    return out
```

- [ ] **Step 4: Run the tests to verify they pass** **[main-agent Bash]**

Run: `python3 -m pytest tests/test_project_summary.py -v`
Expected: PASS.

- [ ] **Step 5: Commit** **[main-agent Bash]**

```bash
git add scripts/project_summary.py tests/test_project_summary.py
git commit -m "feat(overlay): project_summary helper — per-project what-it-is/next-step, honest empty on non-conforming Context"
```

---

## Task 4: Server routes — `POST /api/task/move` and `GET /api/project-summaries`

**Files:**
- Modify: `scripts/server.py` (add `import project_summary` in the import block ~line 31–46; add the GET route near `/api/projects` ~line 219; add the POST route near `/api/task/reschedule` ~line 389)
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `plan_store.move_item_later` (Task 1), `plan_store.move_priority_item_later` (Task 2), `project_summary.summary_map` (Task 3), `daily_plan.load_active_items` (existing), `g.get_space_id()` (existing).
- Produces:
  - `POST /api/task/move` body `{id: str, target_block?: int, position?: int}` → clock shape when `target_block` is present (with optional `position`, default append), priority shape when only `position` is present. `200 {ok: true, plan: <updated plan>}`; `400` on bad input / not-later / out-of-range; `404` on no-cache / wrong shape / id-not-found.
  - `GET /api/project-summaries` → `200 {summaries: {name: {what_it_is?, next_step?}}}`; `500` on load failure.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_server.py`. The existing `live_server` fixture already redirects config to `tmp_path` and mocks generation; these tests seed a cache via `plan_store.save_plan` and mock `daily_plan.load_active_items` for the summaries route.

```python
import plan_store
import daily_plan
import project_summary  # noqa: F401  (ensures the module imports cleanly in the server context)


def _seed_clock_plan():
    plan_store.save_plan({
        "woven_frame": "wf",
        "blocks": [
            {"label": "Morning", "time": "09:00 – 12:00",
             "items": [{"time": "09:00 – 10:30", "project": "Alpha", "task": "draft", "id": "T1"}]},
            {"label": "Afternoon", "time": "13:00 – 17:00",
             "items": [{"time": "13:00 – 14:00", "project": "Gamma", "task": "call", "id": "T4"}]},
        ],
        "still_here": [],
    }, source="generate")


def test_move_relocates_and_reflows_in_cache(live_server):
    base, _calls = live_server
    _seed_clock_plan()
    status, body = _post(base, "/api/task/move", {"id": "T1", "target_block": 1, "position": 1})
    data = json.loads(body)
    assert status == 200 and data["ok"] is True
    moved = next(i for i in data["plan"]["blocks"][1]["items"] if i.get("id") == "T1")
    assert moved["time"] == "14:00 – 15:30"   # re-flowed, never blanked
    # And it actually persisted to the cache (not just echoed).
    assert "T1" in [i.get("id") for i in plan_store.load_plan()["blocks"][1]["items"]]


def test_move_priority_shape_reorders(live_server):
    base, _ = live_server
    plan_store.save_plan({"shape": "priority",
                          "items": [{"task": "a", "id": "P1"}, {"task": "b", "id": "P2"}],
                          "still_here": []}, source="generate")
    status, body = _post(base, "/api/task/move", {"id": "P1", "position": 1})
    data = json.loads(body)
    assert status == 200
    assert [i["id"] for i in data["plan"]["items"]] == ["P2", "P1"]


def test_move_bad_body_is_400(live_server):
    base, _ = live_server
    status, _b = _post(base, "/api/task/move", {"id": "", "target_block": 1})
    assert status == 400
    status2, _b2 = _post(base, "/api/task/move", {"id": "T1"})           # no destination at all
    assert status2 == 400
    status3, _b3 = _post(base, "/api/task/move", {"id": "T1", "target_block": "later"})
    assert status3 == 400
    # A JSON boolean must not sneak through as an int (bool is an int subclass in Python).
    status4, _b4 = _post(base, "/api/task/move", {"id": "T1", "target_block": True})
    assert status4 == 400
    status5, _b5 = _post(base, "/api/task/move", {"id": "T1", "position": True})
    assert status5 == 400


def test_move_unknown_id_is_404_and_not_later_is_400(live_server):
    base, _ = live_server
    _seed_clock_plan()
    status, _b = _post(base, "/api/task/move", {"id": "NOPE", "target_block": 1})
    assert status == 404
    status2, _b2 = _post(base, "/api/task/move", {"id": "T4", "target_block": 0})
    assert status2 == 400


def test_project_summaries_route(live_server, monkeypatch):
    base, _ = live_server
    # load_active_items returns (goals, projects, tasks, ...) — mock to a 3-tuple; the route
    # only reads element [1] (projects).
    monkeypatch.setattr(daily_plan, "load_active_items", lambda sid: (
        [],
        [{"name": "Alpha", "context": "what it is — the build\nnext step — ship it"},
         {"name": "Beta", "context": "no structured lines here"}],
        [],
    ))
    status, body = _get(base, "/api/project-summaries")
    data = json.loads(body)
    assert status == 200
    assert data["summaries"]["Alpha"] == {"what_it_is": "the build", "next_step": "ship it"}
    assert "Beta" not in data["summaries"]   # unparseable → omitted, never fabricated
```

- [ ] **Step 2: Run the tests to verify they fail** **[main-agent Bash]**

Run: `python3 -m pytest tests/test_server.py -k "move or summaries" -v`
Expected: FAIL — routes return 404 (`no route ...`).

- [ ] **Step 3: Add the import**

In `scripts/server.py`, in the import block (~line 31–46, alongside `import plan_store`), add:

```python
import project_summary
```

- [ ] **Step 4: Add the GET route**

In `scripts/server.py`, `do_GET`, immediately after the `/api/projects` block (ends ~line 231), add:

```python
        if self.path == "/api/project-summaries":
            # Per-project 'what it is / next step' for the expandable work-stream rows — parsed
            # deterministically from each project's Context (NO LLM), same tier as /api/map +
            # /api/projects. Only projects whose Context actually parses appear here; the overlay
            # falls back to the task list for the rest (honest empty, never fabricated text —
            # divergence ledger H2). Named 'summaries', not 'focus': that word is the Focus
            # Period's, and June flagged the collision.
            try:
                _g, projects, *_ = daily_plan.load_active_items(g.get_space_id())
                self._send(200, {"summaries": project_summary.summary_map(projects)})
            except Exception as e:
                self._send(500, {"error": f"project summaries load failed: {e}"})
            return
```

- [ ] **Step 5: Add the POST route**

In `scripts/server.py`, `do_POST`, immediately after the `/api/task/reschedule` block (ends ~line 406), add:

```python
        if self.path == "/api/task/move":
            # Tap-to-place, deterministic: relocate one task LATER in the CACHED plan at the
            # tapped position, clock times re-flowed automatically from existing durations. No
            # LLM, no reorder call, no Anytype write (contrast /api/negotiate, which regenerates).
            # The move lives ONLY in the cache; the next generation rebuilds from Anytype and
            # it's gone. The overlay copy says so — no false promise of persistence.
            # Shapes: target_block present (int; optional int position, default append) -> clock
            #         move; position only -> fragmented-day (priority-shape) reorder.
            body = self._read_json_body()
            task_id = (body.get("id") or "").strip()
            target = body.get("target_block")
            position = body.get("position")

            def _bad_int(v):
                # bool is an int subclass in Python — a JSON `true` must not pass as an index.
                return v is not None and (not isinstance(v, int) or isinstance(v, bool))

            if not task_id or _bad_int(target) or _bad_int(position):
                self._send(400, {"error": "move needs a task id and integer target_block/position"})
                return
            if target is None and position is None:
                self._send(400, {"error": "move needs a destination (target_block and/or position)"})
                return
            try:
                if target is not None:
                    plan = plan_store.move_item_later(task_id, target, position=position)
                else:
                    plan = plan_store.move_priority_item_later(task_id, position)
            except ValueError as e:      # not later / out of range
                self._send(400, {"error": str(e)})
                return
            except LookupError as e:     # no cache / wrong shape / id not found
                self._send(404, {"error": str(e)})
                return
            self._send(200, {"ok": True, "plan": plan})
            return
```

- [ ] **Step 6: Run the tests to verify they pass** **[main-agent Bash]**

Run: `python3 -m pytest tests/test_server.py -v`
Expected: PASS (new tests + existing routes).

- [ ] **Step 7: Commit** **[main-agent Bash]**

```bash
git add scripts/server.py tests/test_server.py
git commit -m "feat(overlay): /api/task/move (positional, both plan shapes) and /api/project-summaries routes"
```

---

## Task 5: Overlay — tap-to-place move (both plan shapes)

Frontend-only; there is no pytest for the single-file overlay. Its verification is the live end-to-end check in Task 7. The subagent writes the HTML/JS; the main agent commits. **Build alongside the just-fixed when-chip pattern** (commit `9896723`): a change that didn't save is never silent — surfaced via `showError`, the Today tab's visible channel (the Add tab's `setAddStatus` line isn't on screen here). **Do not disturb** the when-chip/verify-box code (~lines 2050–2115) or the interstitial styling from commit `945bc87` (CSS ~lines 423–450).

**The interaction (June-facing, plain words):** every task that can still move later shows a small **"move ›"** control. Tapping it puts the plan into placing mode: the task is highlighted, its control now reads **"cancel"**, and **"move here"** tap-targets appear at every later spot — between items, and at the start and end of each later part of the day. Tapping a spot moves the task there instantly and every time on screen updates. Tapping "cancel" (or the same control again) leaves everything as it was. One decision at a time; no drag.

**Files:**
- Modify: `docs/overlay_daily.html` (CSS after the `.when-chip` rules ~line 866; `renderFlatItem` ~1761; `renderGroup` ~1780; `renderPlan` ~1811; `renderPriorityItem` ~1855; new functions near `cycleWhen` ~2063)

**Interfaces:**
- Consumes: `POST /api/task/move` (Task 4) with `{id, target_block?, position?}`, returns `{ok, plan}`; existing `showError`, `esc`, `fmtTime`, `groupByProject`.
- Produces: module vars `_lastPlan`, `_placing`; JS `startPlacing(id, block)`, `moveChipHtml(id, bi)`, `_placeTargetHtml(targetBlock, position)`, `renderBlockPlacement(block, bi)`, `placeAt(el)`.

- [ ] **Step 1: Add module-level state, the chip, and the tap-target builder**

Just above `renderFlatItem` (~line 1761), add:

```javascript
// ── Tap-to-place move (no drag) ─────────────────────────────────────────────
// June moves a task by tapping WHERE IT GOES: tap "move ›" on the task, tap-targets appear at
// every later spot in the visible plan, tap one. Times recompute server-side (no LLM, instant).
// The move is for TODAY'S view only — the next plan rebuild replaces it (no copy here may
// promise otherwise).
let _lastPlan = null;   // last rendered plan — placement mode re-renders from it
let _placing = null;    // {id, block} while June is choosing a spot; block is null on list days

function startPlacing(id, block) {
  // Tapping the same task's control again cancels; tapping another task switches to it.
  _placing = (_placing && _placing.id === id) ? null
           : { id, block: (block === null || block === undefined) ? null : block };
  if (_lastPlan) renderPlan(_lastPlan);
}

// One "move here" tap-target. data-pos is the FINAL index the item lands at (the position
// contract /api/task/move expects); data-block is absent on fragmented (list) days.
function _placeTargetHtml(targetBlock, position) {
  const tb = targetBlock == null ? '' : ` data-block="${targetBlock}"`;
  return `<button class="place-target"${tb} data-pos="${position}" onclick="placeAt(this)">move here</button>`;
}

// The per-task control. Normal mode: "move ›" on any task with an id and somewhere later to
// go. Placing mode: ONLY the moving task shows a control, reading "cancel" (one thing at a
// time — every other control gives way to the tap-targets).
function moveChipHtml(id, bi) {
  if (!id) return '';
  if (_placing) {
    return _placing.id === id
      ? `<button class="move-chip active" onclick="event.stopPropagation(); startPlacing('${esc(id)}', null)">cancel</button>`
      : '';
  }
  const p = _lastPlan || {};
  let hasLater = false;
  if (p.shape === 'priority') {
    const items = p.items || [];
    const pos = items.findIndex(it => it.id === id);
    hasLater = pos >= 0 && pos < items.length - 1;
  } else {
    const blocks = p.blocks || [];
    const here = (blocks[bi] && blocks[bi].items) || [];
    const pos = here.findIndex(it => it.id === id);
    hasLater = (bi != null && bi < blocks.length - 1) || (pos >= 0 && pos < here.length - 1);
  }
  if (!hasLater) return '';
  const blockArg = (bi === null || bi === undefined) ? 'null' : bi;
  return `<button class="move-chip" title="move this later in the day" onclick="event.stopPropagation(); startPlacing('${esc(id)}', ${blockArg})">move ›</button>`;
}
```

- [ ] **Step 2: Add the placement renderer and the POST**

Add just after `cycleWhen` (~line 2085):

```javascript
// Placement mode for one clock block: items render FLAT (placement happens between individual
// items, and grouped work-stream rows would hide the spots) with a "move here" target at every
// spot LATER than where the task is now — this affordance only moves a task later.
//   same block as the task: a target after each later item (final index = that item's index);
//   later blocks: a target at the start (0), after each item (j+1) — the last one is the end.
//   earlier blocks: no targets.
function renderBlockPlacement(block, bi) {
  const items = block.items || [];
  const src = _placing.block;
  const sameBlock = bi === src;
  const srcIdx = sameBlock ? items.findIndex(it => it.id === _placing.id) : -1;
  const parts = [];
  if (bi > src) parts.push(_placeTargetHtml(bi, 0));
  items.forEach((it, j) => {
    const moving = sameBlock && j === srcIdx;
    parts.push(moving ? `<div class="placing-item">${renderFlatItem(it, true, bi)}</div>`
                      : renderFlatItem(it, true, bi));
    if (bi > src) parts.push(_placeTargetHtml(bi, j + 1));
    else if (sameBlock && j > srcIdx) parts.push(_placeTargetHtml(bi, j));
  });
  return parts.join('');
}

// The tapped spot -> POST -> re-render from the returned plan (times recomputed server-side).
// Never silent on failure (the cycleWhen rule) — surfaced via showError, the Today tab's
// visible channel; placing mode stays on so she can just tap again.
async function placeAt(el) {
  if (!_placing) return;
  const body = { id: _placing.id, position: Number(el.dataset.pos) };
  if (el.dataset.block !== undefined) body.target_block = Number(el.dataset.block);
  el.disabled = true;
  try {
    const res = await fetch('/api/task/move', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || data.ok === false) {
      showError(data.error || "That move didn't save — tap move here again.");
      el.disabled = false;
      return;
    }
    _placing = null;
    if (data.plan) renderPlan(data.plan);
  } catch (_) {
    showError("That move didn't save — tap move here again.");
    el.disabled = false;
  }
}
```

- [ ] **Step 3: Wire placement mode + the chip through the renderers**

In `renderPlan` (~1811), add as the first line of the function body:

```javascript
  _lastPlan = plan;
```

Replace the `else if (plan.blocks)` branch so the block index reaches `renderGroup` and placement mode swaps in the flat renderer:

```javascript
  } else if (plan.blocks) {
    const placingClock = !!(_placing && _placing.block != null);
    container.innerHTML = plan.blocks.map((block, bi) => {
      const itemsHtml = placingClock
        ? renderBlockPlacement(block, bi)
        : groupByProject(block.items || []).map(g => renderGroup(g, bi)).join('');
      return `
      <div class="time-block">
        <div class="block-header" onclick="this.closest('.time-block').classList.toggle('open')">
          <span class="block-name">${esc(block.label)}</span>
          <span class="block-time">${esc(fmtTime(block.time))}</span>
          ${block.framing ? '<span class="block-expand">›</span>' : ''}
        </div>
        ${block.framing ? `<div class="block-framing">${esc(block.framing)}</div>` : ''}
        ${itemsHtml}
      </div>`;
    }).join('');
  }
```

In the priority-shape branch of `renderPlan`, replace the `items` line so placement mode interleaves tap-targets (same later-only rule, pure position):

```javascript
  if (plan.shape === 'priority') {
    let itemsHtml;
    if (_placing && _placing.block === null) {
      const items = plan.items || [];
      const srcIdx = items.findIndex(it => it.id === _placing.id);
      const parts = [];
      items.forEach((it, j) => {
        parts.push(j === srcIdx ? `<div class="placing-item">${renderPriorityItem(it)}</div>`
                                : renderPriorityItem(it));
        if (srcIdx >= 0 && j > srcIdx) parts.push(_placeTargetHtml(null, j));
      });
      itemsHtml = parts.join('');
    } else {
      itemsHtml = (plan.items || []).map(renderPriorityItem).join('');
    }
    container.innerHTML =
      (plan.header ? `<div class="priority-header">${esc(plan.header)}</div>` : '') +
      `<div class="priority-list">${itemsHtml}</div>`;
  } else if (plan.blocks) {
```

Replace `renderFlatItem` (~1761) with a version that accepts `bi` and renders the chip (the click-guard now also ignores the move control; interstitials keep their `945bc87` styling and get no chip — they carry no id):

```javascript
function renderFlatItem(item, showProject, bi) {
  const slim = !!item.interstitial;
  const cls = ['plan-item', item.done ? 'done' : '', slim ? 'interstitial' : ''].filter(Boolean).join(' ');
  const clickAttr = slim ? '' : `onclick="if(!event.target.closest('.item-check,.move-chip'))this.classList.toggle('open')"`;
  const move = slim ? '' : moveChipHtml(item.id, bi);
  return `
    <div class="${cls}" ${clickAttr}>
      <div class="item-top">
        ${item.id ? `<button class="item-check" title="${item.done ? 'undo' : 'mark done'}" onclick="toggleItem('${esc(item.id)}', this)"></button>` : '<span class="check-gap"></span>'}
        <span class="item-time">${esc(fmtTime(item.time))}</span>
        <span class="item-label">
          ${!slim && showProject && item.project ? `<span class="item-project">${esc(item.project)}</span><span class="item-sep"> · </span>` : ''}
          <span class="item-task">${esc(item.task)}</span>
        </span>
        ${move}
      </div>
      ${!slim && item.why ? `<div class="item-why">${esc(item.why)}</div>` : ''}
    </div>`;
}
```

Update `renderGroup`'s head (~1780) — the multi-task body is rewritten in Task 6; here only the signature, delegations, and the sub-task chip change:

```javascript
function renderGroup(g, bi) {
  if (g.atomic) return renderFlatItem(g.item, false, bi);
  if (g.tasks.length === 1) return renderFlatItem(g.tasks[0], true, bi);
```

and in the existing `subHtml` template inside `renderGroup`, add the chip after the label:

```javascript
  const subHtml = g.tasks.map(t => `
    <div class="task-sub${t.done ? ' done' : ''}" onclick="event.stopPropagation()">
      ${t.id ? `<button class="item-check" onclick="toggleItem('${esc(t.id)}', this)"></button>` : '<span class="check-gap"></span>'}
      <span class="task-sub-label">${esc(t.task)}</span>
      ${moveChipHtml(t.id, bi)}
    </div>`).join('');
```

Replace `renderPriorityItem` (~1855) so fragmented days get the same control:

```javascript
function renderPriorityItem(it) {
  const done = it.done ? ' done' : '';
  return `
    <div class="plan-item priority-item${done}" onclick="if(!event.target.closest('.item-check,.move-chip'))this.classList.toggle('open')">
      <div class="item-top">
        ${it.id ? `<button class="item-check" title="${it.done ? 'undo' : 'mark done'}" onclick="toggleItem('${esc(it.id)}', this)"></button>` : '<span class="check-gap"></span>'}
        <span class="item-label">
          ${it.project ? `<span class="item-project">${esc(it.project)}</span><span class="item-sep"> · </span>` : ''}
          <span class="item-task">${esc(it.task)}</span>
        </span>
        ${moveChipHtml(it.id, null)}
      </div>
      ${it.why ? `<div class="item-why">${esc(it.why)}</div>` : ''}
    </div>`;
}
```

- [ ] **Step 4: Add CSS for the move control, tap-targets, and the highlighted item**

After the `.when-chip` rules (~line 866), add:

```css
/* tap-to-place move — chip on the task, "move here" targets while placing */
.move-chip { flex-shrink: 0; margin-left: auto; border-radius: 13px; font-size: 11px;
  padding: 2px 11px; cursor: pointer; font-family: inherit; background: var(--surface);
  border: 1px solid var(--border); color: var(--text-dim); transition: all .12s; }
.move-chip:hover { border-color: var(--gold); color: var(--gold); }
.move-chip.active { border-color: var(--gold); color: var(--gold); }
.place-target { display: block; width: 100%; text-align: center; font-size: 11.5px;
  font-family: inherit; padding: 5px 0; margin: 3px 0; border-radius: 8px; cursor: pointer;
  background: var(--gold-dim); border: 1px dashed var(--gold); color: var(--gold); }
.place-target:disabled { opacity: 0.5; cursor: default; }
.placing-item { outline: 1px solid var(--gold); border-radius: 8px; }
```

- [ ] **Step 5: Sanity-check the file is well-formed** **[main-agent Bash]**

Run: `python3 -c "import pathlib; s=pathlib.Path('docs/overlay_daily.html').read_text(); assert s.count('moveChipHtml(')>=4 and 'startPlacing' in s and 'placeAt' in s and 'renderBlockPlacement' in s and '/api/task/move' in s and 'move here' in s; print('overlay tap-to-place wiring present')"`
Expected: prints `overlay tap-to-place wiring present`. (Full behavioral check is Task 7, live.)

- [ ] **Step 6: Commit** **[main-agent Bash]**

```bash
git add docs/overlay_daily.html
git commit -m "feat(overlay): tap-to-place move — tap a task, tap where it goes, times recompute; both plan shapes"
```

---

## Task 6: Overlay — work-stream summary rows (what it is / next step first, then the tasks)

Frontend-only; verified live in Task 7. June-facing copy in this task must never say "focus" (that's the Focus Period's word).

**Files:**
- Modify: `docs/overlay_daily.html` (CSS after the `.project-row.open .project-tasks` rule ~line 526; `renderGroup` multi-task body ~1783–1806 as left by Task 5; add `loadProjectSummaries` near `loadPlan` ~1372; boot ~2239; `pollGeneration` ~1308)

**Interfaces:**
- Consumes: `GET /api/project-summaries` (Task 4) → `{summaries: {name: {what_it_is?, next_step?}}}`; module var `_lastPlan` (Task 5); `moveChipHtml` (Task 5, already emitted on sub-task rows).
- Produces: module var `_projectSummaries` (name→summary); `loadProjectSummaries()`.

- [ ] **Step 1: Add `_projectSummaries` state + loader**

Just below the `_placing` declaration from Task 5, add:

```javascript
// name -> {what_it_is?, next_step?} for the expandable work-stream rows. Only projects whose
// Context parsed appear here; a row for any other project falls back to its task list, with no
// invented text (divergence ledger H2 — we don't paper over the fragile parse).
let _projectSummaries = {};
```

Add the loader just after `loadPlan` (~line 1372):

```javascript
async function loadProjectSummaries() {
  try {
    const res = await fetch('/api/project-summaries');
    if (!res.ok) return;
    const data = await res.json();
    _projectSummaries = data.summaries || {};
    if (_lastPlan) renderPlan(_lastPlan);   // summaries arrived after the plan — re-render
  } catch (_) { /* static preview / server down — rows just fall back to tasks */ }
}
```

- [ ] **Step 2: Rewrite the multi-task branch of `renderGroup` to be summary-first**

Replace the multi-task remainder of `renderGroup` (from `// Multi-task project row:` through the closing backtick of its return — as left by Task 5) with:

```javascript
  // Multi-task work-stream row: compute the time span from first start → last end.
  const t0 = g.tasks[0].time || '';
  const tN = g.tasks[g.tasks.length - 1].time || '';
  const spanStart = t0.split(' – ')[0] || t0;          // split on en-dash
  const spanEnd   = tN.split(' – ')[1] || tN.split(' – ')[0] || tN;
  const spanTime  = spanStart && spanEnd ? `${spanStart} – ${spanEnd}` : t0;
  const why = g.tasks[0].why || '';

  // Individual task rows (the deepest level) — each keeps its own done-check and move control.
  const subHtml = g.tasks.map(t => `
    <div class="task-sub${t.done ? ' done' : ''}" onclick="event.stopPropagation()">
      ${t.id ? `<button class="item-check" onclick="toggleItem('${esc(t.id)}', this)"></button>` : '<span class="check-gap"></span>'}
      <span class="task-sub-label">${esc(t.task)}</span>
      ${moveChipHtml(t.id, bi)}
    </div>`).join('');

  // What the project is / its next step comes FIRST when this project's Context parsed; a
  // further tap opens the individual tasks. When there's NO parsed summary, show the tasks
  // directly (today's behavior) — never an invented line. (June-facing words are plain:
  // "What it is" / "Next step" — never "focus", which belongs to the Focus Period.)
  const summary = _projectSummaries[g.project];
  let body;
  if (summary && (summary.what_it_is || summary.next_step)) {
    body = `
      <div class="project-summary">
        ${summary.what_it_is ? `<div class="summary-line"><span class="summary-key">What it is:</span> ${esc(summary.what_it_is)}</div>` : ''}
        ${summary.next_step ? `<div class="summary-line"><span class="summary-key">Next step:</span> ${esc(summary.next_step)}</div>` : ''}
      </div>
      <button class="summary-tasks-toggle"
              onclick="event.stopPropagation(); this.closest('.project-row').classList.toggle('tasks-open')">
        see the tasks (${g.tasks.length}) ›
      </button>
      <div class="project-subtasks">${subHtml}</div>`;
  } else {
    body = subHtml;   // no summary written — the task list is the row's expanded content
  }

  return `
    <div class="project-row" onclick="this.classList.toggle('open')">
      <div class="item-top">
        <span class="check-gap"></span>
        <span class="item-time">${esc(fmtTime(spanTime))}</span>
        <span class="project-name">${esc(g.project)}</span>
        <span class="project-count">${g.tasks.length} ›</span>
      </div>
      ${why ? `<div class="project-why">${esc(why)}</div>` : ''}
      <div class="project-tasks">${body}</div>
    </div>`;
```

- [ ] **Step 3: Add CSS for the summary block + nested task reveal**

After the `.project-row.open .project-tasks { display: block; }` rule (~line 526), add:

```css
.project-summary { padding: 2px 0 8px; }
.summary-line { font-size: 12px; line-height: 1.4; color: var(--text); padding: 2px 0; }
.summary-key { color: var(--text-dim); font-weight: 600; }
.summary-tasks-toggle { font-size: 11.5px; font-family: inherit; background: none; border: none;
  color: var(--gold); cursor: pointer; padding: 4px 0; }
.project-subtasks { display: none; margin-top: 4px; }
.project-row.tasks-open .project-subtasks { display: block; }
```

- [ ] **Step 4: Wire the summaries load into boot + generation-complete**

At the boot calls (~lines 2239–2242), add `loadProjectSummaries()` immediately before `loadPlan()`:

```javascript
loadActions();
loadProjectSummaries();
loadPlan();
loadPeriod();
loadMapPointer();
```

In `pollGeneration`, where a new plan lands (~line 1308, `await loadPlan();`), refresh summaries too (a fresh generation may add streams):

```javascript
      await loadProjectSummaries();  // a fresh generation may bring new streams
      await loadPlan();              // a new plan landed — render it
```

- [ ] **Step 5: Sanity-check the file is well-formed and copy is clean** **[main-agent Bash]**

Run: `python3 -c "
import pathlib
s = pathlib.Path('docs/overlay_daily.html').read_text()
assert 'loadProjectSummaries' in s and 'project-summary' in s and 'tasks-open' in s and 'see the tasks' in s
# June-facing copy must not say 'focus' for THIS feature. The pre-existing Focus Period UI may
# use the word; assert the new summary/move code doesn't reintroduce collision names.
for bad in ['focus-line', 'focus-key', 'project-focus', 'focus-tasks']:
    assert bad not in s, bad
print('overlay summary wiring present, no focus-collision names')"`
Expected: prints `overlay summary wiring present, no focus-collision names`.

- [ ] **Step 6: Commit** **[main-agent Bash]**

```bash
git add docs/overlay_daily.html
git commit -m "feat(overlay): work-stream rows show what-it-is/next-step first, tap through to tasks; honest fallback"
```

---

## Task 7: Integration, live verify, cross-family review, and closing the two tracking tasks

This is the required final task: prove both features work in the running overlay, get a non-Claude review of the code, and close the two Anytype tasks the build was opened against.

**How this wires into the running system:**
- Move: the overlay's `moveChipHtml` control (emitted by `renderFlatItem`, the sub-task rows in `renderGroup`, and `renderPriorityItem` — the existing plan render path) → `startPlacing` re-renders with `renderBlockPlacement` tap-targets → `placeAt` POSTs to `/api/task/move` (Task 4) → `plan_store.move_item_later` / `move_priority_item_later` (Tasks 1–2) mutate `~/.controlled-drift/current_plan.json` with re-flowed times → the route returns the updated plan → `renderPlan` re-renders it. The gated selection (landed 2026-07-12) means the day is ~13 next-moves, so placing mode is a screenful, not a scroll.
- Summaries: boot + `pollGeneration` call `loadProjectSummaries` (Task 6) → `GET /api/project-summaries` (Task 4) → `project_summary.summary_map` (Task 3) over `daily_plan.load_active_items` → `renderGroup` (Task 6) reads `_projectSummaries[g.project]` when a row is expanded.

- [ ] **Step 1: Run the full test suite** **[main-agent Bash]**

Run: `python3 -m pytest -q`
Expected: all green (the ~282 existing tests + the new plan_store, project_summary, and server tests). Investigate and fix any regression before continuing — do not proceed on a red suite.

- [ ] **Step 2: Start the server and confirm the new routes answer** **[main-agent Bash]**

Start (background): `python3 scripts/server.py` (the repo notes say the server needs restarting — this is that restart). Then:

```bash
curl -s http://127.0.0.1:5050/api/project-summaries | python3 -m json.tool | head -20
```
Expected: a `{"summaries": {...}}` object. If June's real projects mostly lack the em-dash Context convention, it may be nearly empty — that is the honest H2 state, not a bug. Note in the verify report how many projects yielded a summary.

- [ ] **Step 3: Live end-to-end via the `verify` skill (real overlay, real cache)** **[main-agent Bash + browser]**

Use the `verify` skill (or `agent-browser`/`playwright`) to drive the actual overlay at `http://127.0.0.1:5050`. There must be a cached plan; if none exists, generate one first (`curl -s -X POST http://127.0.0.1:5050/api/refresh -d '{}'` and wait for `/api/status` to go idle). Then observe, and record what you see:

  1. **Move (clock day):** find a task in an early block. Tap **"move ›"** → confirm the plan enters placing mode: the task highlighted, its control reading "cancel", **"move here"** targets at each later spot (between items, at the start and end of later blocks), and no targets at earlier spots. Tap a target → the task lands there **with a real recomputed time** (and the other affected items' times shifted consistently — durations preserved), instantly, with no spinner/regeneration (no ~2-minute wait, no LLM). Also verify cancel: tap "move ›" then "cancel" → the plan returns unchanged. Reload the page and confirm the move survived the reload (it's in the cache). Then trigger a fresh generation and confirm the move is gone (a day-of adjustment, as intended and as the copy says).
  2. **Move (fragmented day):** if today's cached plan is priority-shape, tap "move ›" on a list item → "move here" targets after each later item → tap one → the list reorders instantly, no times involved. If today's plan is clock-shape, this path can't be driven live without fabricating a cache — say so in the report and rely on the Task 2 + Task 4 tests (do not overwrite June's real cached plan just to stage a demo).
  3. **Summary rows:** find a work-stream row (2+ tasks from one project). Tap to expand → confirm **What it is / Next step** shows first *if that project has a parseable Context*; tap **"see the tasks"** → confirm the individual tasks appear below, each with its own done-check and move control. For a project with no parseable Context, confirm the row expands straight to its task list with **no invented text**. Confirm nothing on screen says "focus" for these features.

Write down the observed behavior (and any project name used) in the verify report. If anything doesn't behave as described, fix and re-verify before Step 4.

- [ ] **Step 4: Cross-family code review** **[main-agent Bash]**

This code was generated by a Claude model; per repo discipline it must get a non-Claude review to dodge same-family blind spots (the same pass that caught the two real when-chip findings on 2026-07-12). Run the GitHub Models reviewer over the branch diff:

```bash
git diff main...HEAD > /tmp/overlay-move-subitems.diff
python3 ~/.claude/skills/requesting-code-review/github_models_review.py --diff /tmp/overlay-move-subitems.diff
```
(If the script takes changed files/paths rather than a diff file, follow its `--help`; the point is a non-Claude reviewer over this branch's changes.) **Triage every finding**: fix real bugs (commit each fix), and for anything you judge a non-issue, write one line saying why. Do not close the thread with findings unaddressed.

- [ ] **Step 5: Commit any review fixes** **[main-agent Bash]**

```bash
git add -A && git commit -m "fix(overlay): address cross-family review findings for move + summary rows"
```
(Skip if the review surfaced nothing to change; say so in the report.)

- [ ] **Step 6: Close the two Anytype tracking tasks with read-back** **[main-agent Bash]**

These two features are the two live open tasks on the **"Daily plan pipeline"** stream. Close them now that the build ships:

  1. Use the `drift` skill / Anytype to locate the two open tasks on the "Daily plan pipeline" stream — the move-a-task-later task and the sub-items/work-stream display task. Capture their Anytype ids.
  2. For each id, complete it with read-back:
     ```bash
     python3 -c "import sys; sys.path.insert(0,'scripts'); import task_actions, json; print(json.dumps(task_actions.complete_task('<TASK_ID>'), indent=2))"
     ```
     `complete_task` already re-fetches and proves `Task status == Done` before returning; a non-Done read-back raises. Confirm both return `{"status": "Done", "done": true}`.
  3. Do **not** invent or guess ids — if you can't find exactly two matching open tasks on that stream, stop and report what you found rather than closing the wrong objects.

- [ ] **Step 7: Final report**

Summarize: both features working (with the observed behavior from Step 3, including a before/after of the recomputed times); the summary-parse coverage seen in Step 2 (how many projects yielded a summary — the honest H2 picture); whether the fragmented-day move was verified live or by tests only; the cross-family review outcome (findings + how each was resolved); and confirmation that the two tracking tasks read back as Done.

---

## Self-Review

**Spec coverage (June's decisions):**
- Tap-to-place move, no language tokens / no block-name pickers / no drag → Task 5 (`startPlacing` → `renderBlockPlacement` "move here" targets → `placeAt`); positional API (Tasks 1–2, 4) is exactly a tap-target. Drag noted as later work, not v1. ✓
- Automatic time recalculation, no blanked times, no LLM → Task 1 (`_reflow_block` first-fit arithmetic over existing durations); tested (append, block-start, same-block, gap-close, overflow, fallback-duration). ✓
- Day-of honesty unchanged → Global Constraints; `_write_plan` never re-stamps; code comments forbid persistence promises; Task 7 verifies survives-reload / gone-after-regenerate. ✓
- Summary rows scope: multi-task rows only → Task 6 touches only the multi-task branch of `renderGroup`. ✓
- Silent task-list fallback on unparseable Context; "focus" purged from June-facing copy and internals named `project_summary`/`summaries` → Tasks 3, 4, 6 + the Step 5 copy check in Task 6. ✓
- Reorder on fragmented days, own task + tests → Task 2 (`move_priority_item_later`), covered in the route (Task 4) and UI (Task 5 priority placement). ✓
- Context header current: selection fix landed (~13-move day); when-chip cross-family fix noted with the never-silent pattern adopted (via `showError` on the Today tab — deliberate, explained); break-block formatting fix (`945bc87`) protected; when-chip/verify-box code untouched. ✓
- Hard boundaries: `daily_plan.py`/`plan_generate.py`/`build_project.py` untouched; re-flow is pure recomputation in `plan_store`. stdlib only; sandboxed self-cleaning tests; per-task commits; subagents-write/main-agent-Bash marked; plain language, no metaphors. ✓
- Final task = live verify + cross-family review + close two Anytype tasks with read-back → Task 7. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code; commands have expected output. ✓

**Type consistency:** `move_item_later(task_id, target_block_index, position=None)` identical in Task 1, Task 4 route, Task 7. `move_priority_item_later(task_id, position)` identical in Task 2, Task 4, Task 7. The final-index position contract is stated once (Data shapes) and used consistently: backend insert-after-pop (Tasks 1–2), tap-target `data-pos` computation (`renderBlockPlacement`: same-block after item j → j; later block start → 0, after item j → j+1; priority after item j → j) matches the tested backend semantics (`test_move_later_within_same_block`: T1→position 1 = after T2; `test_move_to_start_of_later_block`: position 0). Route contract `{id, target_block?, position?}` / `{ok, plan}` matches `placeAt` (Task 5) and the Task 4 tests. `summary_map(projects) -> {name: {what_it_is?, next_step?}}` matches the `/api/project-summaries` payload `{summaries: ...}` consumed by `loadProjectSummaries`/`_projectSummaries` (Task 6). `_lastPlan` is set at the top of `renderPlan` (Task 5) before `moveChipHtml`/`renderGroup` read it. `_write_plan`/`_reflow_block` defined in Task 1, reused in Task 2. ✓

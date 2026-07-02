# Current-Focus Configuration Layer — Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking. Route final review through `cross-review` (non-Claude) since this code is Claude-generated.

**Source spec:** `docs/focus_configuration_addendum.md` (addendum to `AI_LAYER_SPEC.md`). Read it first — this plan implements it.

**Goal:** Give the system somewhere to hold *which goals are in front right now, plus current capacity*, so the daily plan aligns to June's actual week instead of the whole task pile.

**Architecture:** A thin new Anytype object (**Focus Period**) holds the short-term time layer + overrides; a new one-word **Side** field on each Project holds obligation-vs-wellbeing; deterministic Python resolves every calendar fact (is-today-off, is-today-in-the-availability-window, which projects are foreground). **The live plan path is `plan_generate.py` (`build_context` → `generate_plan`) — what the overlay and morning push actually call — NOT `daily_plan.run()`, which is the interactive terminal/dev flow.** The two share their building blocks (`load_active_items`, `format_context`, `build_schedule`) but each have their own orchestration on top; the earlier draft wired the feature into the terminal orchestrator, so it would have been invisible on June's phone. This plan routes the new logic through the **shared loading seam (`load_active_items`)** so it reaches every surface at once (Task 3.0). The payload gains the period's facts *plus their free-text meaning*, and foreground actually **drives task selection** (not just a prose hint the model may ignore). A second output shape (a priority-list-to-pull-from) works in the `/drift` chat flow in v1; its **phone-overlay rendering is a new JSON-output contract + a new renderer branch, so it rides with the overlay work in Phase 6** — it is phone-screen work, not a prompt tweak.

**Tech Stack:** Python 3, Anytype local API (`gsdo_anytype` / `gsdo_objects` helpers), stdlib `http.server` overlay, pytest with a `CD_DATA_DIR` / `CD_CONFIG_DIR` sandbox.

---

## Global Constraints

- **No natural-language parsing for any calendar fact.** Python must decide "is today off / in the availability window" from structured fields only — never by reading prose. (Honors the regex-burn lesson; addendum §"deterministic-payload principle".)
- **Facts travel with their meaning.** Every structured fact sent to the LLM is paired with the relevant free text (`intent`, `availability_note`, `engagement_notes`, `reaching_for`). The meaning is never flattened into the fact. (Guard #3: no scalar-flattening of affect/nuance fields.)
- **Idempotent Anytype writes.** Schema builders use `g.ensure_property` / `g.ensure_type`; re-running never duplicates. Verify against the live space by read-back.
- **No silent failures.** Raise, don't `assert`; surface failures honestly (matches `capture_generate` / `generation_log` patterns).
- **Tests self-clean.** Never leave artifacts in June's real space. Pure-logic tests use fixture dicts; path-writing tests use the `CD_DATA_DIR` / `CD_CONFIG_DIR` sandbox already wired in `tests/conftest.py`.
- **Two sides never mix.** Obligation and wellbeing are structurally separate everywhere they surface. The system may surface a neglected *obligation*; it must never nag about a neglected *hobby*.
- **Display names clean, keys stay `gsdo_*` / Anytype-generated.** New-field keys are Anytype-generated and unpredictable — read them back by *display name* (the pattern `daily_plan.load_active_items` already uses for `Engagement`).

---

## Phasing (read this before the tasks)

**v1 — the load-bearing core (Phases 1–5, fully detailed below).** After v1, June authors a Focus Period by voice/chat through the `drift` skill (she speaks it; the system structures it; she confirms — never a blank form, never system-generated content), and the **live** plan (overlay + morning push) will: put foreground goals first by actually selecting them, respect days off, respect an altered-availability window (*more* hours for a sprint as readily as *fewer* for caregiving), and — in the `/drift` chat flow — switch to a priority-list output when the day is fragmented. *And* the system logs the raw materials the future learning loops will need. That is "Job 1 — plan it right up front."

*Correction from the critic-swarm (2026-07-02): the feature must be wired into the **live** path (`plan_generate.build_context` / `generate_plan`), not the terminal `daily_plan.run()`. Phase 3 opens with the structural fix that makes this un-repeatable. There is **no ship deadline** — the caregiving week was June's example of what the system must do, not a date to hit.*

- **Phase 1 — The two new pieces of stored structure.** The Focus Period object + the one-word Side label on each Project.
- **Phase 2 — Deterministic calendar resolution.** Pure Python answers is-today-off / is-today-in-the-window / which-projects-are-foreground, with no prose parsing.
- **Phase 3 — Feeding it to the LIVE plan.** First a shared-seam fix so terminal + overlay + morning push all get the period (Task 3.0); then the live payload gains the period's facts *and* their meaning, foreground **drives selection**, and the workday-end / days-off overrides actually apply.
- **Phase 4 — The plan can change shape.** A sprint period widens the workday; a fragmented period produces a priority-list-to-pull-from (working in the `/drift` chat flow in v1; the phone-overlay rendering of it is Phase 6).
- **Phase 5 — Log the raw materials now (capture, not interpretation).** Build the containers for the qualitative learning signal + full plan snapshots, so nothing is lost between now and when the loops get built. **Capturing is cheap and cannot be done retroactively; interpreting waits for data.** (June's call: log upfront, before the loops exist.)

**Later phases (Phases 6–8, outlined not detailed — planned as we reach them).** These are real and in the addendum, but detailing them now risks specced-then-rescoped waste, and the addendum explicitly makes the *interpretation* loop "its own later design session." Note: their *storage* is built in Phase 5 — these phases only add the sources that write into it.

- **Phase 6 — Authoring + seeing it in the overlay.** Voice-author the period; a composed rendering; the Log Day tab (writes to Phase 5's signal store). *June's named usability keystone — likely its own plan next.*
- **Phase 7 — The check-in pass.** Obligation-only neglect noticing + wellbeing under-rest surfacing; replies stored (in Phase 5's signal store).
- **Phase 8 — Staleness + conflict prompts.** Re-author when a period lapses; surface a day-off-vs-deadline tension.
- **Phase 9 – The interpretation loop itself** — reads Phase 5's accumulated material and lets categories emerge from it. Explicitly *not* scheduled: its own future design session, per the addendum's methodological stance.

---

## Decisions — resolved with June (2026-07-02)

The addendum's "resolve in the plan step" items, now settled.

1. **Storage shape — RESOLVED (June).** One **Focus Period object per stretch** (e.g. "Week of Jun 30"), *not* one-per-day. The handful of individual exception days ("July 3rd off in a work week"; "working this Saturday") live as **a small structured list in a single field on that one object** — not as separate per-day objects (avoids object sprawl, per June's "avoid tons of configs"). Concretely:
   - **Availability window** → two real Anytype **date** fields (`availability_start` / `availability_end`) + a free-text `availability_note`. Deterministically testable; the note carries the nuance. v1 supports **one** structured window; unlimited extra shapes live in the free text (the structured dates are only for Python's "is today affected" test).
   - **Per-day day-off overrides** → two text fields, each a small structured list of ISO dates (`days_off` = force-off, `days_on` = force-on). Exact encoding (comma-separated or a tiny JSON array) is an implementation detail; it is structured (not natural language) so Python parses it deterministically (honors the regex-burn lesson).

2. **Global weekly day-off default — RESOLVED (June): a single JSON settings file, not Anytype, not per-thing.** Lives at `cd_paths.config_file("settings.json")` — **one place for all global set-once defaults** (weekly day off now; `meal_params.json` can migrate in later). Easiest for both the code (one-line read, no network) and agents (plain file tools, no Anytype protocol). Shape: `{"weekly_off": ["Sat", "Sun"]}`. Overridable per-day by the Focus Period. *(Rejected: an Anytype settings object — its only advantage, in-app editing, is weak for a set-once value June changes by voice.)*

3. **Priority-list output — SPLIT (June + critic-swarm).** The output-shape *decision* + the priority list in the `/drift` chat flow are v1 (Phase 4). The **phone-overlay** priority list is a new JSON-output contract (`plan_generate._JSON_INSTRUCTION` currently demands verbatim clock times) + a new overlay renderer branch (`overlay_daily.html` renders time-blocks only), so it moves to **Phase 6** with the overlay work — it's phone-screen work, not a prompt tweak. **No Saturday deadline (June): the caregiving week was her *example* of what the system must do, not a ship date.** The driver is "the system isn't usable yet; this makes it usable."

4. **Authoring stays speak → structure → confirm (June corrected the swarm here).** The June-fit lens proposed "the system drafts the config, June reacts." **Rejected (June): the system can't know her week** — this stretch vs. last is information only she holds, and a confident bad draft is *more* friction, not less. So there is **no auto-generation of config content.** The design's low-friction path is already the right one: she *speaks* the week (her natural brain-dump mode), the system *structures* it into fields, she *confirms or fixes the structuring* — not a blank form, not the system guessing. The real burden is therefore that **the structuring-back must be genuinely good and radically compressed** ("Jobs first, caregiving Sat–Wed, weekends off — right?"), never a twelve-field echo. Burden of proof on the system: prove it structures well, or it backfires. The **only** safe auto-proposal is rolling a *prior* period forward at staleness (Decision 7) — there the system has real content to offer, not a guess.

5. **Side rule for income-generating creative work — RESOLVED (June): income makes it an Obligation.** The axis is survival/income-relevance, not "is it creative." Creative work that earns (leather cuffs) → **Obligation** (and appropriately surfaceable if neglected). Creative work that doesn't → **Wellbeing** (never nagged). This dissolves the binary's one hard case cleanly.

6. **The wrong-entry-point bug gets a structural fix, not a patch — RESOLVED (June: "fold that fix in").** Root cause: two orchestrators (`daily_plan.run()` terminal, `plan_generate.build_context()` live) sit on the shared building blocks, and the terminal one reads as canonical. Fix (Task 3.0): route the new loading through the **one shared seam both already call** (`load_active_items`), and label `build_context` as the live engine / `run()` as the terminal-dev harness — so a field added once reaches every surface and this can't recur.

7. **v1 staleness — RESOLVED (June): the fallback is correct; just nudge.** When no Focus Period is active, falling back to the whole-pile plan is *correct behavior*, not a bug (June's framing — the steward's "silent failure" read is dropped). The only real need is a **gentle v1 nudge** when a period has lapsed ("no active focus period — want to set one for this stretch?"), so June is never left wondering. The richer rollover-and-react prompt is Phase 8.

### Sequencing note — the overlay UI is June's usability keystone

The overlay authoring + composed-view UI (Phase 6) lets June *see and edit* her configuration — she has named this as the thing that makes the system real for her ("what makes the system into something I actually use"). Its dependency is narrow: it needs **Phase 1 (the data model)** but not Phases 2–4. With no ship deadline in play, this plan builds **backend-first** (Phases 1→5, config authored by chat, live plan actually consumes it), with the Phase 6 UI — now *also* carrying the phone-overlay priority-list rendering — as the very next plan. If June would rather see-and-touch it sooner, Phase 1 → Phase 6 → Phases 2–4 is viable; the risk is a config the plan doesn't yet read (the tractable-vs-goal-displacement trap). Her call, not made silently.

---

## File Structure (v1)

- **Create** `scripts/build_focus_period.py` — idempotent builder for the Focus Period type.
- **Modify** `scripts/build_project.py` — add the `Side` select field.
- **Modify** `scripts/build_model.py` — wire `build_focus_period` into the build order.
- **Create** `scripts/focus_period.py` — pure resolution logic (parse a period object; load the active period; day-off / availability / output-shape tests; day-off defaults config). This is the fully-unit-tested heart.
- **Modify** `scripts/daily_plan.py` — extend the shared `load_active_items` to also load the active period + resolved facts (Task 3.0); read each project's Side; add period facts + meaning + foreground-driven selection to `format_context`; wire `Workday end` to the schedule end-time.
- **Modify** `scripts/plan_generate.py` — the **live** engine: consume the period from the shared loader in `build_context`; apply foreground selection + workday-end; the lapse-nudge. (This is where the feature actually reaches June's phone.)
- **Add** the priority-list formatter (pure function) for the `/drift` chat flow; its overlay JSON-contract + renderer version is Phase 6.
- **Create** `scripts/signal_log.py` — append-only qualitative-signal store (Phase 5).
- **Create** `scripts/plan_snapshot_log.py` — durable full-plan snapshots (Phase 5); **Modify** `scripts/plan_generate.py` to call it after `save_plan`.
- **Create** `scripts/focus_period_author.py` — the chat-authoring seam that creates a period + captures signal (Phase 5).
- **Create** `tests/test_focus_period.py` — unit tests for all of `focus_period.py`.
- **Create** `tests/test_priority_list.py` — unit tests for the priority-list formatter.
- **Create** `tests/test_signal_log.py`, `tests/test_plan_snapshot_log.py`, `tests/test_focus_period_author.py` — Phase 5 stores.

*Schema builders (`build_*.py`) have no unit tests in this codebase — they're verified by running the build + `verify_model` read-back against the live space. Phase 1 follows that established pattern; Phases 2–4 are pure functions and get real pytest tests.*

---

## Phase 1 — The two new pieces of stored structure

### Task 1.1: Focus Period type

**Files:**
- Create: `scripts/build_focus_period.py`
- Modify: `scripts/build_model.py:1-15`

**Interfaces:**
- Produces: `build_focus_period() -> str` (the type key). Fields, by display name: `Period start` (date), `Period end` (date), `Intent` (text), `Availability start` (date), `Availability end` (date), `Availability note` (text), `Days off` (text/JSON), `Days on` (text/JSON), `Output format` (select: `Auto` / `Clock schedule` / `Priority list`), `Workday end` (text `HH:MM`), `Foreground projects` (objects), `Paused projects` (objects).

- [ ] **Step 1: Write the builder** (mirrors `scripts/build_recurring.py` exactly)

```python
#!/usr/bin/env python3
"""Ensure the Focus Period type exists. Idempotent.

A Focus Period is the short-term configuration June authors: what this stretch of
time is about (intent), the availability shape (a window + its situated meaning),
day-off overrides, and plan-behavior overrides (output shape, workday end,
foreground/paused projects). The enduring baseline lives on each Project; the
period OVERRIDES it while active. See docs/focus_configuration_addendum.md.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g

def build_focus_period():
    p_start     = g.ensure_property("Period start", "date")
    p_end       = g.ensure_property("Period end", "date")
    p_intent    = g.ensure_property("Intent", "text")
    p_av_start  = g.ensure_property("Availability start", "date")
    p_av_end    = g.ensure_property("Availability end", "date")
    p_av_note   = g.ensure_property("Availability note", "text")
    # Day-off overrides: JSON arrays of ISO dates. JSON is structured (not NL) so
    # Python parses it deterministically. Weekly default lives in a config file.
    p_days_off  = g.ensure_property("Days off", "text")
    p_days_on   = g.ensure_property("Days on", "text")
    # Plan-behavior overrides — each structured + Python-readable:
    p_out_fmt   = g.ensure_property("Output format", "select",
                                    ["Auto", "Clock schedule", "Priority list"])
    p_wk_end    = g.ensure_property("Workday end", "text")   # "HH:MM"
    p_fg        = g.ensure_property("Foreground projects", "objects")
    p_paused    = g.ensure_property("Paused projects", "objects")
    key = g.ensure_type("Focus Period", "Focus Periods",
                        [p_start, p_end, p_intent, p_av_start, p_av_end, p_av_note,
                         p_days_off, p_days_on, p_out_fmt, p_wk_end, p_fg, p_paused])
    print(f"[ok] Focus Period type ready: key={key}")
    return key

if __name__ == "__main__":
    build_focus_period()
```

- [ ] **Step 2: Wire it into `build_model.py`**

```python
from build_focus_period import build_focus_period
# ...
    build_goal(); build_project(); build_task(); build_recurring(); build_strategy()
    build_focus_period()
```

- [ ] **Step 3: Run the builder against the live space and read back**

Run: `python3 scripts/build_focus_period.py`
Expected: `[ok] Focus Period type ready: key=...`
Then confirm the type + all 12 properties exist by re-running (idempotent — no duplicates) and via `python3 scripts/verify_model.py` if it enumerates types, or a direct fetch.

**⚠ Record the real type key (architect's activation-hinge note).** Anytype *generates* the type key from the name; the existing keys aren't uniform (`gsdo_goal`, `gsdo_strategy`, but the Task type's key is bare `task`). The whole feature's activation rides on `focus_period.FOCUS_PERIOD_TYPE_KEY` matching the *real* key — if it's wrong, `load_active_focus_period` filters out every period and the feature silently returns `None` forever, and no unit test catches it. So: read the printed/returned key here, and set the constant in `focus_period.py` to that exact value. Add a one-line read-back assertion (fetch a just-created period, confirm its `type.key` equals the constant) rather than trusting the guessed `gsdo_focus_period`.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_focus_period.py scripts/build_model.py
git commit -m "feat(focus_period): add Focus Period type (idempotent builder)"
```

### Task 1.2: Project `Side` field (obligation vs wellbeing)

**Files:**
- Modify: `scripts/build_project.py:7-39`

**Interfaces:**
- Produces: a `Side` select property on the Project type with options `Obligation` / `Wellbeing`.

**Side rule (Decision 5 — June):** the axis is *income/survival-relevance*, not "is it creative." Creative work that **earns** (leather cuffs) → `Obligation` (appropriately surfaceable if neglected). Creative work that doesn't → `Wellbeing` (never nagged). This is guidance for how June tags projects, captured in the field's description; the field itself is a plain two-option select.

- [ ] **Step 1: Add the property and include it in the type**

In `build_project()`, after `p_eng_notes`:

```python
    # Obligation vs wellbeing — set directly on the Project (June thinks of a project
    # AS obligation or hobby; not derived from the goal). The axis is income/survival-
    # relevance: creative work that EARNS (e.g. leather cuffs) is Obligation; creative
    # work that doesn't is Wellbeing. Structurally separates the two sides everywhere they
    # surface: neglect may be offered on the Obligation side; the Wellbeing side is never
    # nagged (only ever surfaced as under-rest/under-play).
    p_side = g.ensure_property("Side", "select", ["Obligation", "Wellbeing"])
```

And add `p_side` to the `ensure_type("Project", "Projects", [...])` list.

- [ ] **Step 2: Run + read back**

Run: `python3 scripts/build_project.py`
Expected: `[ok] Project type ready: key=...`; confirm `Side` exists on the type (re-run is idempotent).

- [ ] **Step 3: Commit**

```bash
git add scripts/build_project.py
git commit -m "feat(project): add Side field (obligation vs wellbeing)"
```

---

## Phase 2 — Deterministic calendar resolution

All logic here is pure and fully unit-tested. Keeps `daily_plan.py` wiring thin.

### Task 2.1: Parse a Focus Period object into a plain dict

**Files:**
- Create: `scripts/focus_period.py`
- Test: `tests/test_focus_period.py`

**Interfaces:**
- Produces: `parse_focus_period(obj: dict) -> dict` with keys `id, name, start (date|None), end (date|None), intent, availability_start (date|None), availability_end (date|None), availability_note, days_off (list[str]), days_on (list[str]), output_format (str), workday_end (str|None), foreground (list[str]), paused (list[str])`. Reads new fields by **display name** (keys are Anytype-generated). Malformed JSON in `Days off`/`Days on` → `[]` (never raises on bad data; log a warning).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_focus_period.py
import datetime as dt
import focus_period as fp

def _obj(props):
    return {"id": "fp1", "name": "Week of Jun 30",
            "type": {"key": "gsdo_focus_period"},
            "properties": props}

def test_parse_reads_dates_and_json_lists():
    o = _obj([
        {"name": "Period start", "date": "2026-06-30"},
        {"name": "Period end", "date": "2026-07-06"},
        {"name": "Intent", "text": "jobs foreground, survival first"},
        {"name": "Days off", "text": '["2026-07-03"]'},
        {"name": "Days on", "text": ""},
        {"name": "Output format", "select": {"name": "Auto"}},
    ])
    p = fp.parse_focus_period(o)
    assert p["start"] == dt.date(2026, 6, 30)
    assert p["end"] == dt.date(2026, 7, 6)
    assert p["intent"].startswith("jobs foreground")
    assert p["days_off"] == ["2026-07-03"]
    assert p["days_on"] == []
    assert p["output_format"] == "Auto"

def test_parse_bad_json_is_empty_not_error():
    o = _obj([{"name": "Days off", "text": "not json"}])
    assert fp.parse_focus_period(o)["days_off"] == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `CD_DATA_DIR=/tmp/cdtest CD_CONFIG_DIR=/tmp/cdtest pytest tests/test_focus_period.py -v`
Expected: FAIL (`No module named 'focus_period'`).

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Deterministic resolution of a Focus Period. Pure functions — no Anytype writes.

The Focus Period holds the short-term time layer + overrides June authors. Python
resolves every calendar FACT here (is today off, is today in the availability window,
which projects are foreground). The situated MEANING (intent, availability_note) is
carried as free text for the LLM to read — never flattened into a fact. See
docs/focus_configuration_addendum.md.
"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths

_DAY_OFF_DEFAULTS = {"weekly_off": ["Sat", "Sun"]}


def _by_name(obj):
    return {p.get("name"): p for p in obj.get("properties", [])}


def _date(props, name):
    p = props.get(name) or {}
    v = p.get("date")
    if not v:
        return None
    try:
        return dt.date.fromisoformat(v[:10])
    except (ValueError, TypeError):
        return None


def _text(props, name):
    p = props.get(name) or {}
    return p.get("text") or ""


def _json_dates(props, name):
    raw = _text(props, name)
    if not raw.strip():
        return []
    try:
        val = json.loads(raw)
        return [str(d) for d in val] if isinstance(val, list) else []
    except (json.JSONDecodeError, TypeError):
        print(f"[warn] focus_period: {name!r} is not valid JSON — ignoring", file=sys.stderr)
        return []


def _objects_pairs(props, name):
    """Return [(id, name), ...] for an objects relation — KEEP the id (rename-safe linkage).
    The id is the stable link; the name is resolved to the current value later (Task 3.0)."""
    p = props.get(name) or {}
    objs = p.get("objects") or []
    return [(o.get("id"), o.get("name")) for o in objs
            if isinstance(o, dict) and o.get("id")]


def parse_focus_period(obj):
    props = _by_name(obj)
    sel = (props.get("Output format") or {}).get("select") or {}
    return {
        "id": obj.get("id"),
        "name": obj.get("name"),
        "start": _date(props, "Period start"),
        "end": _date(props, "Period end"),
        "intent": _text(props, "Intent"),
        "availability_start": _date(props, "Availability start"),
        "availability_end": _date(props, "Availability end"),
        "availability_note": _text(props, "Availability note"),
        "days_off": _json_dates(props, "Days off"),
        "days_on": _json_dates(props, "Days on"),
        "output_format": (sel.get("name") if isinstance(sel, dict) else sel) or "Auto",
        "workday_end": _text(props, "Workday end") or None,
        # id/name pairs — Task 3.0 resolves ids -> current names against the live projects list
        "foreground_pairs": _objects_pairs(props, "Foreground projects"),
        "paused_pairs": _objects_pairs(props, "Paused projects"),
    }


def parse_hhmm(s):
    """Parse 'HH:MM' -> (hour, minute). Used by build_context for the Workday-end override.
    Returns (18, 0) on anything unparseable (the prior default end-of-day)."""
    try:
        h, m = s.strip().split(":")
        return int(h), int(m)
    except (AttributeError, ValueError):
        return 18, 0
```

- [ ] **Step 4: Run to verify it passes**

Run: `CD_DATA_DIR=/tmp/cdtest CD_CONFIG_DIR=/tmp/cdtest pytest tests/test_focus_period.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/focus_period.py tests/test_focus_period.py
git commit -m "feat(focus_period): parse a Focus Period object into a plain dict"
```

### Task 2.2: Load the active Focus Period for today

**Files:**
- Modify: `scripts/focus_period.py`
- Test: `tests/test_focus_period.py`

**Interfaces:**
- Consumes: `parse_focus_period` (Task 2.1).
- Produces: `load_active_focus_period(objects: list[dict], today: date | None = None) -> dict | None`. Filters raw Anytype objects to Focus Periods whose `[start, end]` contains `today` (inclusive). If several match, the one with the **latest `start`** wins (deterministic tiebreak). Ignores periods missing `start` or `end`.

- [ ] **Step 1: Write the failing test**

```python
def test_load_active_picks_containing_period():
    objs = [
        _obj([{"name": "Period start", "date": "2026-06-01"},
              {"name": "Period end", "date": "2026-06-10"}]),
        _obj([{"name": "Period start", "date": "2026-06-28"},
              {"name": "Period end", "date": "2026-07-06"}]),
    ]
    for o in objs:
        o["type"] = {"key": "gsdo_focus_period"}
    active = fp.load_active_focus_period(objs, today=dt.date(2026, 7, 2))
    assert active is not None
    assert active["start"] == dt.date(2026, 6, 28)

def test_load_active_returns_none_when_no_period_covers_today():
    objs = [_obj([{"name": "Period start", "date": "2026-06-01"},
                  {"name": "Period end", "date": "2026-06-10"}])]
    objs[0]["type"] = {"key": "gsdo_focus_period"}
    assert fp.load_active_focus_period(objs, today=dt.date(2026, 7, 2)) is None
```

- [ ] **Step 2: Run to verify it fails.** Run the file; expect FAIL (`load_active_focus_period` undefined).

- [ ] **Step 3: Implement**

```python
FOCUS_PERIOD_TYPE_KEY = "gsdo_focus_period"

def load_active_focus_period(objects, today=None):
    today = today or dt.date.today()
    candidates = []
    for obj in objects:
        t = obj.get("type")
        tkey = t.get("key") if isinstance(t, dict) else t
        if tkey != FOCUS_PERIOD_TYPE_KEY:
            continue
        p = parse_focus_period(obj)
        if p["start"] and p["end"] and p["start"] <= today <= p["end"]:
            candidates.append(p)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p["start"])
```

*Note for implementer: confirm the real type key by reading it back from the live space after Task 1.1 — Anytype generates it from the type name; `gsdo_focus_period` is the expected form but verify and fix this constant if it differs.*

- [ ] **Step 4: Run to verify it passes.** Expect PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/focus_period.py tests/test_focus_period.py
git commit -m "feat(focus_period): load the active period for today"
```

### Task 2.3: Day-off defaults config + `is_day_off`

**Files:**
- Modify: `scripts/focus_period.py`
- Test: `tests/test_focus_period.py`

**Interfaces:**
- Produces:
  - `load_day_off_defaults() -> list[str]` — reads `cd_paths.config_file("settings.json")` (the single global-defaults file), returns its `weekly_off` list; default `["Sat", "Sun"]` if the file or key is absent/malformed.
  - `is_day_off(period: dict | None, weekly_off: list[str], today: date) -> bool` — precedence: an explicit `days_on` date forces a **work** day (False); an explicit `days_off` date forces **off** (True); otherwise fall back to whether `today`'s weekday abbreviation is in `weekly_off`. A `None` period means "no overrides, weekly default only."

- [ ] **Step 1: Write the failing test**

```python
def test_is_day_off_weekly_default():
    # 2026-07-04 is a Saturday
    assert fp.is_day_off(None, ["Sat", "Sun"], dt.date(2026, 7, 4)) is True
    # 2026-07-02 is a Thursday
    assert fp.is_day_off(None, ["Sat", "Sun"], dt.date(2026, 7, 2)) is False

def test_days_on_overrides_weekend_off():
    period = {"days_off": [], "days_on": ["2026-07-04"]}
    assert fp.is_day_off(period, ["Sat", "Sun"], dt.date(2026, 7, 4)) is False

def test_days_off_overrides_weekday_on():
    period = {"days_off": ["2026-07-02"], "days_on": []}
    assert fp.is_day_off(period, ["Sat", "Sun"], dt.date(2026, 7, 2)) is True

def test_load_day_off_defaults_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    assert fp.load_day_off_defaults() == ["Sat", "Sun"]
```

- [ ] **Step 2: Run to verify it fails.** Expect FAIL.

- [ ] **Step 3: Implement**

```python
def load_day_off_defaults():
    try:
        with open(cd_paths.config_file("settings.json")) as f:
            data = json.load(f)
        wk = data.get("weekly_off")
        return wk if isinstance(wk, list) and wk else list(_DAY_OFF_DEFAULTS["weekly_off"])
    except (FileNotFoundError, json.JSONDecodeError):
        return list(_DAY_OFF_DEFAULTS["weekly_off"])


_WEEKDAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def is_day_off(period, weekly_off, today):
    iso = today.isoformat()
    if period:
        if iso in (period.get("days_on") or []):
            return False   # explicit work day
        if iso in (period.get("days_off") or []):
            return True    # explicit day off
    return _WEEKDAY_ABBR[today.weekday()] in (weekly_off or [])
```

- [ ] **Step 4: Run to verify it passes.** Expect PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/focus_period.py tests/test_focus_period.py
git commit -m "feat(focus_period): day-off defaults config + is_day_off with per-day overrides"
```

### Task 2.4: Availability window + output-shape resolution

**Files:**
- Modify: `scripts/focus_period.py`
- Test: `tests/test_focus_period.py`

**Interfaces:**
- Produces:
  - `in_availability_window(period: dict | None, today: date) -> bool` — True iff the period has both availability dates and `availability_start <= today <= availability_end`.
  - `resolve_output_shape(period: dict | None, in_window: bool) -> str` — returns `"clock"` or `"priority"` from **structured inputs only** (steward's catch: no natural-language scanning). Explicit `Output format` on the period wins (`Clock schedule` → `"clock"`, `Priority list` → `"priority"`). On `Auto` (or no period): `"priority"` if `in_window`, else `"clock"`. **The capacity nuance is NOT scanned here** — it's free text the *model* reads (the prompt tells it "if the day is fragmented, keep the list loose"). If June reliably wants a priority list on a low-but-not-windowed day, she sets `Output format`. (Removed: the `is_off` param — a day off doesn't change output *shape* — and the `_LOW_CAPACITY_MARKERS` keyword-scan, which both parsed prose and hard-coded her example phrase "couple hours" — the design-no-edge-case-specialization guard.)

- [ ] **Step 1: Write the failing test**

```python
def test_in_availability_window():
    period = {"availability_start": dt.date(2026, 7, 4),
              "availability_end": dt.date(2026, 7, 8)}
    assert fp.in_availability_window(period, dt.date(2026, 7, 5)) is True
    assert fp.in_availability_window(period, dt.date(2026, 7, 2)) is False
    assert fp.in_availability_window(None, dt.date(2026, 7, 5)) is False

def test_resolve_output_shape_explicit_wins():
    assert fp.resolve_output_shape({"output_format": "Priority list"}, False) == "priority"
    assert fp.resolve_output_shape({"output_format": "Clock schedule"}, True) == "clock"

def test_resolve_output_shape_auto_from_window_only():
    p = {"output_format": "Auto"}
    assert fp.resolve_output_shape(p, True) == "priority"      # in an availability window
    assert fp.resolve_output_shape(p, False) == "clock"        # normal day
    assert fp.resolve_output_shape(None, False) == "clock"     # no period
```

- [ ] **Step 2: Run to verify it fails.** Expect FAIL.

- [ ] **Step 3: Implement** (structured-only — no prose scanning)

```python
def in_availability_window(period, today):
    if not period:
        return False
    s, e = period.get("availability_start"), period.get("availability_end")
    return bool(s and e and s <= today <= e)


def resolve_output_shape(period, in_window):
    fmt = (period or {}).get("output_format", "Auto")
    if fmt == "Priority list":
        return "priority"
    if fmt == "Clock schedule":
        return "clock"
    return "priority" if in_window else "clock"   # Auto: structured signal only
```

- [ ] **Step 4: Run to verify it passes.** Expect PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/focus_period.py tests/test_focus_period.py
git commit -m "feat(focus_period): availability window + output-shape resolution"
```

---

## Phase 3 — Feeding it to the LIVE plan

**This is the phase the critic-swarm re-pointed.** The value only lands if the feature reaches `plan_generate.build_context` / `generate_plan` (overlay + morning push), not just `daily_plan.run()` (terminal). Task 3.0 makes the *shared* loader carry the period so both paths get it from one place; the rest wires the live engine and makes foreground actually select, not just hint.

*Verify-first (build-agent's catch): before writing any parse code, dump ONE real Focus Period object from the live space and confirm the property shape `parse_focus_period` assumes. Reuse the existing `pvn` display-name accessor in `load_active_items` rather than a parallel accessor.*

### Task 3.0: Load the period through the one shared seam (`load_active_items`)

**Why this task exists:** `daily_plan.run()` and `plan_generate.build_context()` both call `dp.load_active_items(sid)`. If the period loads *there*, both orchestrators get it for free and the wrong-entry-point bug cannot recur (Decision 6).

**Files:**
- Modify: `scripts/daily_plan.py` (`load_active_items` — read Side; also return a `period_ctx`)
- Modify: `scripts/daily_plan.py` module docstring + `plan_generate.py` module docstring (label live vs terminal)
- Test: `tests/test_focus_period.py`

**Interfaces:**
- Produces: `load_active_items(sid)` now returns `(goals, projects, tasks, strategies, today_recurrings, period_ctx)` where `period_ctx = {"period": <dict|None>, "is_off": bool, "in_window": bool}`. Each project dict gains `"side"` (`"Obligation"`/`"Wellbeing"`/`None`). The period's `foreground`/`paused` are resolved from stored **ids** to current project **names** here (rename-safe: the stored link is by id; the name is resolved live from the authoritative projects list).
- Consumes: `focus_period.{load_active_focus_period, load_day_off_defaults, is_day_off, in_availability_window}`. The raw `data` from `g.fetch_all_objects` (already fetched at the top of `load_active_items`) is reused — **no second fetch** (architect's consistency note).

- [ ] **Step 1: Read Side in the `gsdo_project` branch** (alongside `engagement = ...`), and add `"side": side` to the appended project dict:

```python
            side_tag = pvn("Side", "select") or {}
            side = side_tag.get("name") if isinstance(side_tag, dict) else None
```

- [ ] **Step 2: At the end of `load_active_items`, build `period_ctx` from the same `data`:**

```python
    import focus_period as fp
    today = dt.date.today()
    period = fp.load_active_focus_period(data, today)   # data already fetched above — reuse it
    if period:
        # Resolve foreground/paused ids -> current names from the authoritative projects list
        # (rename-safe: the stored link is the id; the display name is resolved live).
        id_to_name = {p["id"]: p["name"] for p in projects}
        period["foreground"] = [id_to_name.get(i, n) for i, n in period.get("foreground_pairs", [])]
        period["paused"] = [id_to_name.get(i, n) for i, n in period.get("paused_pairs", [])]
        period["foreground_ids"] = [i for i, _ in period.get("foreground_pairs", [])]
        period["paused_ids"] = [i for i, _ in period.get("paused_pairs", [])]
    weekly_off = fp.load_day_off_defaults()
    period_ctx = {"period": period,
                  "is_off": fp.is_day_off(period, weekly_off, today),
                  "in_window": fp.in_availability_window(period, today)}
    return goals, projects, tasks, strategies, today_recurrings, period_ctx
```

*(`parse_focus_period` already returns `foreground_pairs` / `paused_pairs` as `[(id, name), ...]` via `_objects_pairs` — Task 2.1. The plain `foreground`/`paused` name lists that `format_context` and `select_and_order_tasks` consume are derived here, resolved against the live projects list so a project rename can't break the link.)*

- [ ] **Step 3: Update BOTH callers of `load_active_items` to accept the 6-tuple.** In `daily_plan.run()` and `plan_generate.build_context()`, change the unpack to include `period_ctx`. Add a one-line docstring marker to each module: `plan_generate.py` = "the LIVE plan engine (overlay + morning push)"; `daily_plan.run()` = "interactive terminal/dev harness — NOT the live path."

- [ ] **Step 4: Test** the resolution logic (`load_active_items` is integration-shaped, so test the id→name resolution helper as a pure function if extracted; otherwise cover via the live read-back in Task 3.3). Commit:

```bash
git add scripts/daily_plan.py scripts/plan_generate.py tests/
git commit -m "feat(load): load Focus Period + Side through the shared seam both paths call"
```

### Task 3.1: `format_context` — the period block + meaning + Side (display)

**Files:**
- Modify: `scripts/daily_plan.py` (`format_context`)
- Test: `tests/test_focus_period.py` (or new `tests/test_daily_plan_context.py`)

**Interfaces:**
- Produces: `format_context(..., period=None, is_off=False, in_window=False)` prepends a `## This period` block (name, intent; `availability_note` **only if `in_window`**; a day-off line if `is_off`; foreground/paused names). Each project line gains `| side: …`. **Note:** display sorting is cosmetic — the *real* reprioritization is task selection (Task 3.2). So this test must assert the period block content, not rely on sort order to prove foreground.

- [ ] **Step 1: Write the failing test** (assert the block content directly — not via index ordering, which the build-agent showed passes trivially from the header):

```python
import daily_plan

def test_context_includes_period_and_meaning():
    period = {"name": "Week of Jun 30", "intent": "jobs foreground, survival first",
              "availability_note": "caregiving — fragmented time, survival-first",
              "foreground": ["Job Search"], "paused": ["Autograder"]}
    projects = [{"id": "p1", "name": "Job Search", "engagement": "Sprint", "side": "Obligation",
                 "reaching_for": "", "context": "", "affective": "", "engagement_notes": "",
                 "parent_project_id": None},
                {"id": "p2", "name": "Autograder", "engagement": "Steady", "side": "Wellbeing",
                 "reaching_for": "", "context": "", "affective": "", "engagement_notes": "",
                 "parent_project_id": None}]
    ctx = daily_plan.format_context([], projects, [], [], [], [], "low",
                                    period=period, is_off=False, in_window=True)
    assert "## This period" in ctx
    assert "survival first" in ctx
    assert "caregiving" in ctx
    assert "side: Obligation" in ctx
    assert "Foreground this period: Job Search" in ctx
    assert "Autograder [paused this period]" in ctx

def test_availability_note_hidden_when_not_in_window():
    period = {"name": "W", "intent": "x", "availability_note": "SECRETNOTE",
              "foreground": [], "paused": []}
    ctx = daily_plan.format_context([], [], [], [], [], [], None,
                                    period=period, is_off=False, in_window=False)
    assert "SECRETNOTE" not in ctx
```

- [ ] **Step 2: Run to verify it fails.** Expect FAIL (`format_context` doesn't accept `period=`).

- [ ] **Step 3: Implement.** New signature `format_context(goals, projects, tasks, strategies, today_recurrings, neglected, capacity, period=None, is_off=False, in_window=False)`. After the time/capacity lines, insert the `## This period` block (as previously drafted). Add `| side: {side}` to `_project_line`; append `" [paused this period]"` when `p["name"]` in the paused set. Keep the foreground-first display sort as a *nicety*, but do NOT let any test depend on it to prove reprioritization.

- [ ] **Step 4: Run to verify it passes.** Expect PASS.

- [ ] **Step 5: Commit** (`feat(daily_plan): period facts+meaning and Side in the LLM context`).

### Task 3.2: Foreground **drives task selection** (the real reprioritization), by id

**Why:** the addendum's whole thesis is that a soft LLM hint *wasn't enough*. Reordering the description (Task 3.1) is a hint. The live selection lives in `plan_generate.build_context`'s `_project_key` (a date-seeded hash over project names, `plan_generate.py:350-358`). Foreground must actually reorder *that*, and paused must drop its tasks.

**Files:**
- Modify: `scripts/plan_generate.py` (`build_context` — the task sort)
- Test: `tests/test_plan_generate_selection.py`

**Interfaces:**
- Produces: in `build_context`, task selection sorts foreground-project tasks first and drops paused-project tasks. Matching is by the period's resolved foreground/paused **names** (from Task 3.0, themselves resolved from stored ids), against each task's `linked_projects`.

- [ ] **Step 1: Write the failing test** (feed a fake `period_ctx` + tasks, assert order + drop). Extract the sort into a pure helper `select_and_order_tasks(tasks, period)` so it's unit-testable without Anytype:

```python
import plan_generate as pg

def test_foreground_tasks_sort_first_paused_dropped():
    tasks = [{"name": "hobby task", "linked_projects": ["Autograder"], "duration_min": 30},
             {"name": "apply Acme", "linked_projects": ["Job Search"], "duration_min": 45}]
    period = {"foreground": ["Job Search"], "paused": ["Autograder"]}
    ordered = pg.select_and_order_tasks(tasks, period)
    assert [t["name"] for t in ordered] == ["apply Acme"]   # foreground kept+first, paused dropped

def test_no_period_preserves_existing_hash_order():
    tasks = [{"name": "a", "linked_projects": ["X"]}, {"name": "b", "linked_projects": ["Y"]}]
    ordered = pg.select_and_order_tasks(tasks, None)
    assert {t["name"] for t in ordered} == {"a", "b"}   # nothing dropped when no period
```

- [ ] **Step 2: Run to verify it fails.** Expect FAIL.

- [ ] **Step 3: Implement** `select_and_order_tasks(tasks, period)` and call it in `build_context` in place of the raw `sorted(tasks, key=_project_key)`:

```python
def select_and_order_tasks(tasks, period):
    """Order tasks foreground-first and drop paused-project tasks (period overrides).
    With no period, preserve the existing date-seeded hash order (unchanged behavior)."""
    fg = set((period or {}).get("foreground") or [])
    paused = set((period or {}).get("paused") or [])
    def _proj(t):
        projs = t.get("linked_projects") or []
        return projs[0] if projs else ""
    kept = [t for t in tasks if _proj(t) not in paused]
    # existing hash order as the base, foreground floated to the front
    import hashlib
    seed = hashlib.md5(dt.date.today().isoformat().encode()).hexdigest()
    def _key(t):
        proj = _proj(t)
        order = int(hashlib.md5((proj + seed).encode()).hexdigest()[:4], 16)
        return (0 if proj in fg else 1, 1 if not proj else 0, order)
    return sorted(kept, key=_key)
```

- [ ] **Step 4: Run to verify it passes.** Expect PASS.

- [ ] **Step 5: Commit** (`feat(plan_generate): foreground drives task selection; paused drops`).

### Task 3.3: Wire the resolved facts into the live engine + terminal; workday-end; lapse-nudge

**Files:**
- Modify: `scripts/plan_generate.py` (`build_context`), `scripts/daily_plan.py` (`run`)
- Test: live read-back (integration)

**Interfaces:**
- Consumes: `period_ctx` from Task 3.0.
- Produces: `build_context` passes `period=period, is_off=is_off, in_window=in_window` into `format_context`; overrides its hardcoded `end_time = 18:00` with the period's `Workday end` when set (steward's cheap fix — `scheduler.schedule`/`build_schedule` already accept `end_time`); and, when `period_ctx["period"] is None`, appends a gentle lapse-nudge line to the context ("No active focus period — want to set one for this stretch?"). `run()` gets the same via its own unpack.

- [ ] **Step 1: In `build_context`**, after unpacking `period_ctx`:

```python
    period = period_ctx["period"]
    # Workday-end override: a sprint period widens the day, a gentle one narrows it.
    if period and period.get("workday_end"):
        wh, wm = fp.parse_hhmm(period["workday_end"])          # add a tiny parser to focus_period
        end_time = now.replace(hour=wh, minute=wm, second=0, microsecond=0)
    ...
    context_block = dp.format_context(goals, projects, tasks, strategies,
                                      today_recurrings, neglected, capacity,
                                      period=period, is_off=period_ctx["is_off"],
                                      in_window=period_ctx["in_window"])
    if period is None:
        context_block += ("\n\n## No active focus period\n"
                          "- There's no configuration for this stretch. If today's plan feels "
                          "off, June may want to set a focus period — offer it, gently, once.")
```

- [ ] **Step 2: Malformed day-off surfaces to June, not just stderr** (steward): when `focus_period` dropped a bad `days_off`/`days_on` list, set a flag on the period dict; if set, `format_context` adds a visible line ("A day-off setting couldn't be read — check it; today was planned as a normal day."). A silently-ignored day off that plans a workday is quietly punitive.

- [ ] **Step 3: Apply the same unpack in `daily_plan.run()`** (terminal), passing the period facts into its `format_context` call.

- [ ] **Step 4: Live read-back.** Author a real Focus Period for the current stretch (see the create-payload recipe in Task 6-prep / below), run BOTH `python3 scripts/plan_generate.py --dry-context` (the live path) and `python3 scripts/daily_plan.py` (terminal), confirm the `## This period` block, foreground-first selection, and workday-end all appear. Self-clean the test period.

- [ ] **Step 5: Commit** (`feat(plan_generate): period facts + workday-end + lapse-nudge reach the live plan`).

### Task 3.4: A documented `create()` recipe for a Focus Period (unblocks every manual check)

**Why (build-agent):** the manual verifications need a real period with **date / select / objects / list** fields populated, but the plan only ever showed a single text field. Without a payload recipe, Phase 3–4 can't be verified at all.

**Files:**
- Create: `scripts/author_period_example.py` (a throwaway/reference helper, git-kept as documentation)

- [ ] **Step 1: Write a reference call** showing every field type through `gsdo_objects.create` — resolving foreground/paused **project names → ids** first (the write side needs ids; `create` formats `objects` as an id list):

```python
import gsdo_objects, gsdo_anytype as g
def find_project_id(name):
    sid = g.get_space_id()
    for o in g.fetch_all_objects(sid):
        t = o.get("type"); tk = t.get("key") if isinstance(t, dict) else t
        if tk == "gsdo_project" and o.get("name") == name:
            return o["id"]
    raise ValueError(f"project {name!r} not found")

gsdo_objects.create("Focus Period", "Week of Jun 30 — jobs foreground", properties={
    "Period start": "2026-06-30", "Period end": "2026-07-06",
    "Intent": "jobs foreground, survival first; caregiving from Saturday",
    "Availability start": "2026-07-05", "Availability end": "2026-07-09",
    "Availability note": "caregiving — fragmented time, survival-first in whatever windows exist",
    "Days off": "", "Days on": "",
    "Output format": "Auto", "Workday end": "22:00",
    "Foreground projects": [find_project_id("Job Search")],
    "Paused projects": [find_project_id("Autograder")],
})
```

- [ ] **Step 2: Note the read/write asymmetry in a comment** (architect): the write side needs project **ids**; the read side (`parse_focus_period`) hands back **{id, name} pairs**. Task 5.3's `author_focus_period` must resolve names→ids before writing — this recipe is the reference for that.

- [ ] **Step 3: Commit** (`docs(focus_period): reference create() recipe for all field types`).

---

## Phase 4 — The plan can change shape

Two shapes: a **sprint** period widens the workday (already wired in Task 3.3 via `Workday end`); a **fragmented** period produces a priority-list-to-pull-from instead of a clock schedule. ADHD-friendly: few items, plain language, no clock pressure.

**v1 scope (critic-swarm split).** The priority-list works in the **`/drift` chat flow** in v1 (the instance reads a Python-ordered skeleton and writes a plain plan). The **phone-overlay** version is a new JSON-output contract + renderer branch → **Phase 6**. Until then the overlay keeps its clock-JSON output; `build_context` still computes the shape so Phase 6 has a clean handoff. **Python owns the order** (foreground-first, from Task 3.2) for *both* shapes — the model narrates, it does not reorder. (Resolves the build-agent's "who orders?" contradiction.)

### Task 4.1: The priority-list formatter (pure)

**Files:**
- Modify: `scripts/daily_plan.py` (add `format_priority_list`)
- Test: `tests/test_priority_list.py`

**Interfaces:**
- Produces: `format_priority_list(ordered_items: list[dict], period: dict | None = None) -> str`. `ordered_items` are **Python-ordered** (foreground-first, from `select_and_order_tasks` — NOT LLM-proposed), each `{"name", "duration_min"?}`. Renders a short ordered list with **no clock times**, an availability line from the period's note if present, and a plain "when you get some time, start at the top" instruction. Caps the visible list (~6) so it stays scannable; notes the remainder count.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_priority_list.py
import daily_plan

def test_priority_list_has_no_clock_times_and_is_ordered():
    items = [{"name": "Submit the Acme application", "duration_min": 45},
             {"name": "Reply to recruiter email", "duration_min": 10}]
    out = daily_plan.format_priority_list(items, period={"availability_note": "couple hours, unknown when"})
    assert "Submit the Acme application" in out
    assert out.index("Submit the Acme application") < out.index("Reply to recruiter email")
    import re
    assert not re.search(r"\d{1,2}:\d{2}", out)   # no HH:MM anywhere — the whole point
    assert "couple hours" in out

def test_priority_list_caps_long_lists():
    items = [{"name": f"Task {i}"} for i in range(10)]
    out = daily_plan.format_priority_list(items)
    assert "Task 0" in out
    assert "more" in out.lower()   # remainder noted
```

- [ ] **Step 2: Run to verify it fails.** Expect FAIL.

- [ ] **Step 3: Implement**

```python
PRIORITY_LIST_CAP = 6

def format_priority_list(ordered_items, period=None):
    """Fragmented-day output: a priority-ordered short list to pull from, no clock times.
    ADHD-friendly: few items, plain language, no clock pressure. (Addendum §"plan changes shape".)"""
    lines = ["## Today — a priority list to pull from (no fixed times)"]
    note = (period or {}).get("availability_note")
    if note:
        lines.append(f"_Availability: {note}_")
    lines.append("When you get a window, start at the top and take the next one that fits:")
    lines.append("")
    shown = ordered_items[:PRIORITY_LIST_CAP]
    for i, it in enumerate(shown, 1):
        dur = it.get("duration_min")
        dur_str = f" (~{dur}min)" if dur else ""
        lines.append(f"{i}. {it['name']}{dur_str}")
    remainder = len(ordered_items) - len(shown)
    if remainder > 0:
        lines.append(f"\n(+{remainder} more held for later — don't worry about them today.)")
    return "\n".join(lines)
```

- [ ] **Step 4: Run to verify it passes.** Expect PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_plan.py tests/test_priority_list.py
git commit -m "feat(daily_plan): priority-list output for fragmented days"
```

### Task 4.2: Choose the shape in the shared assembly

**Files:**
- Modify: `scripts/daily_plan.py` (`run`) and `scripts/plan_generate.py` (`build_context`)

**Interfaces:**
- Consumes: `focus_period.resolve_output_shape(period, in_window)` — **`is_off` and the capacity keyword-scan are removed** (see revised Task 2.4): shape is decided from *structured* inputs only (`Output format` select + `in_window`); the capacity nuance is the model's to read from the free text, not Python's to scan.
- Produces: `shape = fp.resolve_output_shape(period, in_window)`. Terminal/`/drift` path: when `shape == "priority"` the skeleton is `format_priority_list(select_and_order_tasks(tasks, period), period)`. `build_context` (overlay): v1 still emits the clock skeleton but records `shape` for Phase 6 — no phone behavior change yet, clean handoff later.

- [ ] **Step 1: Terminal branch (`daily_plan.run()`)** — Python owns the order for both shapes:

```python
    import plan_generate
    shape = fp.resolve_output_shape(period, in_window)
    if shape == "priority":
        ordered = plan_generate.select_and_order_tasks(tasks, period)
        schedule_block = format_priority_list(ordered, period)
        scheduled = []                                     # keep the confirm block safe
    else:
        start_time = _round_to_5(dt.datetime.now())
        meals = default_meal_anchors(today_recurrings, start_time)
        scheduled = build_schedule(
            [{"name": t["name"], "duration_min": t.get("duration_min")}
             for t in plan_generate.select_and_order_tasks(tasks, period)],
            today_recurrings + meals, start_time)
        schedule_block = format_schedule_blocks(scheduled)
```

*(Guard the later `confirm`/`log_correction` block on `scheduled` being non-empty.)*

- [ ] **Step 2: `build_context` records the shape** (no overlay behavior change in v1): compute `shape` and return/annotate it for Phase 6. Do **not** emit a priority JSON yet — the renderer for it is Phase 6.

- [ ] **Step 3: Manual verification.** Author a period with `Output format = Priority list`, run `python3 scripts/daily_plan.py`, confirm the pull-from list renders with no clock times. Self-clean.

- [ ] **Step 4: Commit** (`feat: choose clock vs priority-list shape from the period (chat flow v1)`).

### Task 4.3: Reflect the shape in the prompt

**Files:**
- Modify: `prompts/daily_list.md`

**Interfaces:**
- Produces: the prompt tells the LLM that the day may come in one of two shapes and to honor whichever the Python skeleton provides — a clock schedule to narrate, OR a priority list to keep as an ordered pull-from list (no invented clock times).

- [ ] **Step 1: Add a short section to `prompts/daily_list.md`** explaining the two output shapes and that Python decides which; the LLM narrates the clock schedule OR keeps the priority list plain and ordered. (Read the current prompt first; match its voice and the existing "Python owns times and order" framing.)

- [ ] **Step 2: Re-validate on real output** (the react-to-real-output method): run `daily_plan.py` for both a normal day and a fragmented day, read what the LLM returns, iterate the prompt wording until both shapes read well. This is a June-in-the-loop step, not a silent lock.

- [ ] **Step 3: Commit**

```bash
git add prompts/daily_list.md
git commit -m "feat(daily_list): teach the prompt the two output shapes"
```

---

## Phase 5 — Log the raw materials now (capture, not interpretation)

Build the *containers* for the qualitative learning signal + full plan snapshots. **This does not build any learning loop** — it makes sure the raw material exists to build one from later. Capturing is cheap and irreversible-if-skipped; interpreting waits for data (the addendum's methodological stance). The containers sit mostly empty in v1 (their richest sources — Log Day, the check-in pass — arrive in Phases 6–7), but the store, the plan-snapshot archive, and config-authoring capture all work from day one.

### Task 5.1: The signal store

**Files:**
- Create: `scripts/signal_log.py`
- Test: `tests/test_signal_log.py`

**Interfaces:**
- Produces:
  - `log_signal(raw_text: str, source: str, reference: dict | None = None, path: str | None = None) -> None` — appends one JSONL record `{ts, source, reference, raw}` to `cd_paths.data_file("signal_log.jsonl")`. `source` ∈ `{"log_day", "checkin_reply", "config_authoring", "config_correction", "plan_renegotiation"}`. `reference` is a small dict like `{"kind": "project", "id": "...", "name": "..."}` or `None`. **Never classifies meaning** — raw text is stored verbatim.
  - `read_signals(path: str | None = None) -> list[dict]` — reads all records (for tests + the future loop).

- [ ] **Step 1: Write the failing test** (mirrors `tests/test_surface_log.py` sandbox style)

```python
# tests/test_signal_log.py
import signal_log

def test_log_signal_appends_verbatim(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    signal_log.log_signal("I skipped the plan, needed to finish the sprint",
                          source="checkin_reply",
                          reference={"kind": "project", "id": "p1", "name": "Job Search"})
    rows = signal_log.read_signals()
    assert len(rows) == 1
    assert rows[0]["raw"] == "I skipped the plan, needed to finish the sprint"
    assert rows[0]["source"] == "checkin_reply"
    assert rows[0]["reference"]["name"] == "Job Search"
    assert "ts" in rows[0]

def test_read_signals_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    assert signal_log.read_signals() == []
```

- [ ] **Step 2: Run to verify it fails.** Expect FAIL (`No module named 'signal_log'`).

- [ ] **Step 3: Implement** (follows `scripts/surface_log.py` exactly)

```python
#!/usr/bin/env python3
"""Append-only store for qualitative learning signal. CAPTURE ONLY — no interpretation.

Stores June's own words about how a day went / what didn't fit / why she diverged,
tagged with a structural source + reference + timestamp. The meaning is deliberately
NOT classified here: a future learning loop reads this accumulated raw material and lets
categories emerge from it (addendum §"persisting signals for a learning loop"). Forcing
categories now is the premature-operationalizing the whole system resists.
"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths

def _path(path=None):
    return path or cd_paths.data_file("signal_log.jsonl")

def log_signal(raw_text, source, reference=None, path=None):
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "source": source, "reference": reference, "raw": raw_text}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")

def read_signals(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
```

- [ ] **Step 4: Run to verify it passes.** Expect PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/signal_log.py tests/test_signal_log.py
git commit -m "feat(signal_log): append-only qualitative-signal store (capture, not interpretation)"
```

### Task 5.2: Durable plan snapshots

The addendum: "persist the day's plan alongside the Log Day entry... without the plan snapshot, 'I did it differently' has nothing to diff against." `surface_log` already records *which items* surfaced per date; this adds the *full generated plan* (order, times, framing) so the diff is high-fidelity.

**Files:**
- Create: `scripts/plan_snapshot_log.py`
- Modify: `scripts/plan_generate.py` (call the snapshot right after `plan_store.save_plan`)
- Test: `tests/test_plan_snapshot_log.py`

**Interfaces:**
- Produces: `log_plan_snapshot(plan: dict, source: str, path: str | None = None) -> None` — appends `{ts, plan_date, source, plan}` to `cd_paths.data_file("plan_snapshots.jsonl")`. `plan_date` = today's ISO date. Stores the full plan dict verbatim.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_plan_snapshot_log.py
import datetime as dt
import plan_snapshot_log

def test_snapshot_stores_full_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    plan = {"items": [{"name": "Apply to Acme", "start": "09:00"}], "frame": "survival first"}
    plan_snapshot_log.log_plan_snapshot(plan, source="morning")
    rows = plan_snapshot_log.read_snapshots()
    assert len(rows) == 1
    assert rows[0]["plan"]["frame"] == "survival first"
    assert rows[0]["source"] == "morning"
    assert rows[0]["plan_date"] == dt.date.today().isoformat()
```

- [ ] **Step 2: Run to verify it fails.** Expect FAIL.

- [ ] **Step 3: Implement** (same JSONL pattern; include a `read_snapshots`)

```python
#!/usr/bin/env python3
"""Durable per-generation plan snapshots — the planned side of planned-vs-actual.
Append-only; the full plan dict is stored verbatim so a future learning loop can diff
what was planned against what June logs she actually did (addendum §Job 2)."""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths

def _path(path=None):
    return path or cd_paths.data_file("plan_snapshots.jsonl")

def log_plan_snapshot(plan, source, path=None):
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "plan_date": dt.date.today().isoformat(), "source": source, "plan": plan}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")

def read_snapshots(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
```

- [ ] **Step 4: Hook it into generation.** In `scripts/plan_generate.py`, inside `generate_plan`, right after `saved = plan_store.save_plan(plan, source=source)`:

```python
    import plan_snapshot_log
    plan_snapshot_log.log_plan_snapshot(saved, source=source)
```

- [ ] **Step 5: Run to verify it passes** (unit test + a manual `generate_plan` run leaving a snapshot in the sandbox). Expect PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/plan_snapshot_log.py scripts/plan_generate.py tests/test_plan_snapshot_log.py
git commit -m "feat(plan_snapshot_log): archive full generated plans for planned-vs-actual"
```

### Task 5.3: Capture config-authoring as signal (the v1 chat-authoring seam)

v1 authoring is **speak → structure → confirm** (Decision 4): June *says* her week, the instance *structures* it into fields, she *confirms or fixes the structuring* — **not** a blank form, and **not** the system generating the content (the system can't know her week; a confident bad draft is more friction). This task gives that path a single entry point that **creates the period AND captures June's raw words as signal** — so authoring/corrections are logged from day one.

**Two things the instance must get right when it structures her words (both are load-bearing, from the swarm):**
1. **Resolve `Foreground projects` / `Paused projects` from names → ids before writing.** The write side of `gsdo_objects.create` formats an `objects` relation as a **list of ids**, but June speaks project *names*. Resolve names→ids first (see the recipe in Task 3.4). The read side hands back id/name pairs — this is the write/read asymmetry the architect flagged.
2. **The structuring-back must be radically compressed** ("Jobs first, caregiving Sat–Wed, weekends off — right?"), never a twelve-field echo (June's overwhelm tell). Burden of proof: if it can't reflect back cleanly, it backfires.

**Files:**
- Create: `scripts/focus_period_author.py`
- Test: `tests/test_focus_period_author.py`

**Interfaces:**
- Consumes: `gsdo_objects.create`, `signal_log.log_signal`.
- Produces: `author_focus_period(raw_text: str, name: str, properties: dict, source: str = "config_authoring") -> str` — creates a `Focus Period` object (caller has already resolved any project names→ids in `properties`), then logs a signal (`raw_text`, `source`, `reference={"kind": "focus_period", "id": <new id>, "name": name}`), and returns the new object id. `source="config_correction"` when editing an existing period's framing.

- [ ] **Step 1: Write the failing test** (monkeypatch the Anytype create so no live write)

```python
# tests/test_focus_period_author.py
import focus_period_author as fpa
import gsdo_objects, signal_log

def test_author_creates_and_logs_signal(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(gsdo_objects, "create", lambda *a, **k: "fp_new_id")
    oid = fpa.author_focus_period(
        raw_text="jobs foreground this week, caregiving from Saturday",
        name="Week of Jun 30", properties={"Intent": "jobs foreground"})
    assert oid == "fp_new_id"
    rows = signal_log.read_signals()
    assert rows[0]["source"] == "config_authoring"
    assert rows[0]["reference"] == {"kind": "focus_period", "id": "fp_new_id", "name": "Week of Jun 30"}
    assert "caregiving" in rows[0]["raw"]
```

- [ ] **Step 2: Run to verify it fails.** Expect FAIL.

- [ ] **Step 3: Implement**

```python
#!/usr/bin/env python3
"""v1 chat-authoring seam for a Focus Period: create the object AND capture June's raw
words as learning signal in one call. So config authoring/corrections are logged from
day one — before the overlay authoring UI (Phase 6) exists."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_objects
import signal_log

def author_focus_period(raw_text, name, properties, source="config_authoring"):
    oid = gsdo_objects.create("Focus Period", name, properties=properties)
    signal_log.log_signal(raw_text, source=source,
                          reference={"kind": "focus_period", "id": oid, "name": name})
    return oid
```

- [ ] **Step 4: Run to verify it passes.** Expect PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/focus_period_author.py tests/test_focus_period_author.py
git commit -m "feat(focus_period_author): create + capture-signal seam for chat authoring"
```

---

## Phase 5 done = v1 shippable

Run the whole suite: `CD_DATA_DIR=/tmp/cdtest CD_CONFIG_DIR=/tmp/cdtest pytest -q`. All green + a live read-back of a real week's Focus Period producing an aligned plan (and a snapshot + authoring signal landing in the data dir) = v1 lands. Then: final whole-branch review via `cross-review` (non-Claude), then merge.

---

## Later phases (outline — plan each as we reach it)

### Phase 6 — Authoring + seeing it in the overlay *(June's usability keystone — likely the next plan)*
- **Voice/chat authoring endpoint** — reuse the capture pattern (`server.py` POST → 202 → background worker → poll `/api/status` → fetch result). New `focus_period_generate.py` mirroring `capture_generate.capture(text)`: June **says** her week → the model **structures** it into the fields (resolving project names→ids, Task 5.3) → **reflects it back radically compressed** ("Jobs first, caregiving Sat–Wed, weekends off — right?"), never a twelve-field echo → she confirms/fixes → `focus_period_author.author_focus_period(...)` (creates + logs signal) + read-back + ding. No auto-generation of content — she supplies what only she can (Decision 4). **Burden of proof: the structuring-back has to be genuinely good, or it backfires into friction.**
- **The phone-overlay priority-list rendering (split out of Phase 4).** This is the second output shape *on the phone*: a new JSON-output contract branch in `plan_generate._JSON_INSTRUCTION` (a no-clock list shape alongside the time-block shape), `parse_plan` handling it, and a new renderer branch in `overlay_daily.html` (which today renders `.time-block` elements only). `build_context` already computes `shape` (Task 4.2) — here it drives which contract + renderer is used. **The spatial-time principle is near-non-negotiable for June — constrain the priority-list rendering with it** (it's a new June-facing surface; also pass the no-metaphors access guard).
- **Composed rendering** — one view = the active Focus Period + every project's engagement + Side, rendered (not a second stored copy — a rendering, so nothing falls out of sync). New `/api/period` GET + a render function; a client tab in `overlay_daily.html` (mirror the Today/Add tab structure at `docs/overlay_daily.html:704-708`, `switchTab`).
- **Log Day tab** — a new tab where June speech-dumps what she actually did; AI structures it after and appends via `signal_log.log_signal(..., source="log_day")` (Task 5.1 store already exists). This is the first rich record of *actual* activity (feeds Phase 7 + the future loop). **June-fit guard:** frame it as *her own brain-dump*, never as "report what you did." The planned-vs-actual diff (against Phase 5's plan snapshots) stays **backend-only** — never surfaced to her as a "you deviated" report, which would reproduce a surveillance dynamic she avoids.
  - **Data dependency for Phase 7 — capture rest *tagged by type*.** When Log Day structures the dump, rest must be recorded by which of the 7 types it was (physical / mental / emotional / social / sensory / creative / spiritual), not as a flat "rested." The check-in pass reads rest-type history across days to find the under-served types — so if Log Day only records "rested," Phase 7's per-type under-rest surfacing has nothing to read. (Also: creative hyperfocus ≠ rest — the addendum's design implication — so Log Day must not silently count hobby/dev time as rest.)

### Phase 7 — The check-in pass (neglect noticing)
- Extend `neglect.py` (already exists). **Obligation side only** for "this matters and has gone quiet"; **Wellbeing side** surfaces *only* as under-rest / under-play, never as "behind on a project."
- **Under-rest surfacing uses the 7-types-of-rest taxonomy** (June's active Strategy "Honor the 7 types of rest"): physical / mental / emotional / social / sensory / creative / spiritual. The wellbeing branch tracks rest *by type*, so it surfaces the specific gap ("physical rest but no sensory or emotional rest lately"), never a flat "you haven't rested." **Why it lives here and not in the daily planner:** it needs cross-day awareness the stateless daily plan doesn't have — it reads rest-type history across days to find under-served types. Depends on Phase 6's Log Day tagging rest by type. June's nuance to honor: the 7 can't all fit one day (rotate across days), and some belong *after* the day's scheduled blocks end.
- Facts, not prose-scanning: Python reads last-surfaced / deadline / completion / rest-type history; the LLM does the soft "is this worth a nudge" judgment. Surface-then-defer; not hard-capped at one item, but never repeated nagging.
- **Per-period "don't chase me about this" override (June-fit).** Survival-loaded obligations (job applications under precarity) are the *highest*-risk surface for reproducing anxiety — noticing "you haven't done job apps in three days" during a caregiving week can land as an anxiety amplifier even when gently worded (the risk is the *content*, not the tone). So the Focus Period carries a per-project "she's chosen to let this sit — don't surface it" list; June stays the author of what matters *including* what she's chosen to leave alone. The check-in pass honors it.
- Every nudge takes a free-text reply → stored via Phase 5's `signal_log` tagged `checkin_reply`.

### Learning loops — deferred to their own session, but two tags to preserve now
The interpretation loop is explicitly a future design session (categories emerge from Phase 5's accumulated data). Two structural hooks the addendum names, recorded here so they aren't lost:
- **Strategy `learning_notes` → strategy-lifespan loop.** Nothing currently reads `learning_notes`, so an active Strategy can silently stop working while the system keeps applying it. The future loop must read this field, detect a drifted/expired strategy, and surface it to June to revise or retire — **never auto-retire.** (ROADMAP §strategy-lifespan; `AI_LAYER_SPEC §2 learning_notes`.)
- **Engagement-level meaning per project** — what Sprint/Steady/Backburner actually implies for each project, learned from June's corrections over time.

### Phase 8 — Staleness + conflict prompts
- **Staleness = rollover-and-react, not re-author-from-blank (June + June-fit).** The v1 minimal lapse-nudge already ships in Phase 3 (Decision 7 — when no period is active, a gentle "want to set one?"; the whole-pile fallback is *correct*, not a bug). Phase 8's richer version: when a period's `Period end` is near, carry the *previous* period forward as a default and ask only **what changed** ("Last stretch was jobs-foreground + caregiving — still true, or what's shifted?"). This is the *only* safe auto-proposal — it offers real prior content, not a guess (Decision 4). Deterministic date test (reuse `focus_period`); inherits the react-in-a-word shape from the conflict prompt below.
- **Conflict:** a day marked off + a hard deadline the same day → surface the tension as a one-line question ("Today's marked off, but the X application is due — work today, or already handled?"), never a silent override. One-word reply resolves it; can open into a fuller chat.
- **History is a free win:** lapsed periods archive (don't delete) → data for the learning loops.

---

## Strategy-coverage audit (session 24, 2026-07-02) — gaps to fold into the phases above

Checked June's active Strategies against this plan. **Most are covered:** the 7 rest types → Phase 6 by-type Log Day + Phase 7 under-rest; obligation-hyperfixation → the Side field (1.2) surfaced in context (3.2); deferred-task surfacing → Phase 7 neglect pass; `learning_notes` → the strategy-lifespan hook above; mix-textures + the *linear* next-item already work at plan time. **Four gaps need placing — none is built or slated as a real task yet:**

1. **Nonlinear → map routing** (Strategy *"next tangible thing for linear work; show the map and let me pick for nonlinear work"*). Currently only a self-review aside ("wire in Phase 6/7") — **not an actual task, and absent from `daily_plan.py` / `daily_list.md`.** Make it real: when a project is nonlinear/creative, the daily plan must **not invent a next item** — it points June to the map (`orient_map.py`) to pick her own thread. Needs a linear/nonlinear signal per project (a Project field, or inferred from engagement/Side) + a daily-plan/prompt branch. Land it as an explicit task in Phase 6 (the map surface); do not leave it as an aside.

2. **Exercise / shorter walks** (Strategy *"encourage regular exercise, including shorter walks"*) — **TODO persisted** ("Give the daily plan recent-exercise awareness + insert exercise as short blocks"). **Correction (June, session 24): a worded nudge is counterproductive — this must be a real short block, not a mention.** Two parts: **(1) design question June named** — how the plan knows her *recent exercise history* (cross-day); this is the same shape as the 7-types-of-rest cross-day problem, so extend Phase 6 Log Day capture + Phase 7 history-reading to record/read movement/exercise, not just rest. **(2)** given recent history, insert exercise as a real short block (a walk) via the same anchor mechanism `default_meal_anchors` uses for Lunch. Healing arc: walks now → running as June recovers.

3. **Break blocks** (Strategy *"regular breaks — every ~2h of focused work"*) — **TODO persisted** ("Insert breaks as real short blocks in the daily schedule (break anchor)"). **Correction (June, session 24): not optional and not a worded nudge — a real scheduled block.** The mechanism already exists: `default_meal_anchors` synthesizes a "Lunch" block (not a real Anytype task — a short block with a duration) and `build_schedule` places it. Breaks need the parallel `default_break_anchors`: a short (<20 min) "Break — stand/stretch" block roughly every 2h of focused work, deterministic. Land it in Phase 4. (Live monitoring of time-at-computer stays parked — could fold into a future cycle-chore timer.)

4. **(minor) Neglect pass — social tasks deferred hardest** (Strategy *"keep surfacing the small tasks and chores I put off"*). Phase 7 reads last-surfaced / deadline / completion, but June defers **social-interaction** tasks hardest — the pass should weight those. A nuance to Phase 7's judgment, not a new mechanism.

*Out of scope by design:* spoon-accounting (the errand-batching Strategy) is its own workstream — see `docs/open_thread_spoon_accounting.md`.

---

## Self-Review (against the spec)

- **Spec coverage (v1):** new object ✓ (1.1); Side on Project ✓ (1.2, income=obligation rule); **feature reaches the LIVE path** ✓ (3.0 shared seam + 3.3 wires `build_context`/`generate_plan`) — the critic-swarm's headline fix; enduring-vs-short-term precedence via foreground/paused + is_day_off ✓ (3.0/3.1); **foreground drives real selection, by id** ✓ (3.2) — not just a prose hint; deterministic calendar facts, no NL ✓ (2.1–2.4, and `resolve_output_shape` de-NL'd); facts+meaning bundle ✓ (3.1); availability window + note ✓ (2.4/3.1); `Workday end` wired so a *sprint* widens the day ✓ (3.3) — the dropped "a period can be MORE" reframe restored; two output shapes — chat-flow in v1, phone-overlay in Phase 6 ✓; malformed day-off surfaces to June ✓ (3.3); type-key activation-hinge read-back ✓ (1.1); v1 lapse-nudge ✓ (3.3/Decision 7); **raw learning-signal store + plan snapshots + config-authoring capture ✓ (Phase 5)**. **Deferred by design (flagged, not dropped):** overlay authoring/rendering + Log Day *UI* + the phone priority-list renderer (Phase 6), check-in/neglect pass + "don't chase me" override (Phase 7), staleness rollover + conflict prompts (Phase 8), the interpretation loop (its own future session), linear-vs-nonlinear map pairing (`orient_map.py`, Phase 6/7). Multi-window availability beyond one structured window → free text in v1.
- **Placeholder scan:** every code step shows real code; every command shows expected output. No TODO/TBD in build steps.
- **Type consistency (re-checked after revision):** `parse_focus_period` now returns `foreground_pairs`/`paused_pairs` (id/name) — Task 3.0 resolves them to `foreground`/`foreground_ids`/`paused`/`paused_ids`, which `format_context` (names) and `select_and_order_tasks` (names) consume. `resolve_output_shape(period, in_window)` — the 2-arg form — is called consistently in Task 4.2 (was 4-arg with dead `is_off` + capacity-scan, now removed). `load_active_items` returns a 6-tuple ending in `period_ctx`; **both** callers (`run`, `build_context`) updated (3.0 Step 3). `parse_hhmm` added (2.1) and consumed by `build_context` (3.3). `focus_period` imported as `fp`; `plan_generate.select_and_order_tasks` referenced from `daily_plan.run` and `build_context`.
- **Swarm findings ledger:** wrong-entry-point → 3.0/3.3 ✓; priority-list under-scoped → split to Phase 6 ✓; "period can be more" dropped → `Workday end` wired + `in_window`-only shape ✓; foreground a hint → 3.2 selection ✓; name-keyed → id-keyed pairs ✓; `is_off` dead / NL-scan → removed ✓; author stub name→id asymmetry → 3.4 recipe + 5.3 note ✓; tests pass regardless → 3.1 asserts content, 4.1 regex-checks no HH:MM ✓; authoring-from-blank → Decision 4 (speak→structure→confirm, no auto-gen) ✓; staleness → Decision 7 v1 nudge + Phase 8 rollover ✓; survival-obligation neglect → Phase 7 "don't chase me" ✓; Log Day surveillance-framing → Phase 6 guard ✓.

---

## Execution Handoff

Plan complete. Two execution options:
1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, final whole-branch `cross-review` (non-Claude, to dodge same-family blind spots). Isolate on the current `feat/overlay-actionable` branch or a fresh worktree.
2. **Inline** — execute here, batched with checkpoints.

Per the addendum's ratified process: **June approves this plan → optional `critic-swarm` on the plan → then build incrementally** (small commits, live read-back, self-cleaning tests).

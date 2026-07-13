"""The composition restore (2026-07-13): the LLM owns selection + order; Python owns the clock.

These pin the behavior the build had drifted from (structural_diagnosis_2026-07-11 /
spec_reconciliation_selection_2026-07-11 / AI_LAYER_SPEC:69): after the model composes, Python
_retime_clock_plan places its order in time — honoring the ORDER the model chose (not a hash),
dropping tasks it deferred, and re-placing fixed anchors at their real times regardless of where
the model put them.
"""
import datetime as dt
import plan_generate as pg
import daily_plan as dp


def _clock_plan(ordered_items):
    """A parsed+resolved clock plan with one Morning block holding `ordered_items` in order."""
    return {"shape": "clock", "woven_frame": "f", "still_here": [],
            "blocks": [{"label": "Morning", "time": "10:00 – 12:00", "framing": "fresh",
                        "items": list(ordered_items)}]}


def _times(plan):
    """Flatten (task, time) in output order across blocks."""
    return [(it.get("task") or it.get("name"), it["time"])
            for b in plan["blocks"] for it in b["items"]]


def test_retime_honors_the_models_order_not_the_input_order():
    # The model composed Beta BEFORE Alpha. Python must schedule in THAT order — not re-sort.
    tasks = [{"id": "a", "name": "Alpha", "duration_min": 30},
             {"id": "b", "name": "Beta", "duration_min": 60}]
    plan = _clock_plan([
        {"time": "x", "task": "Beta", "project": None, "why": "w1", "interstitial": False, "id": "b"},
        {"time": "x", "task": "Alpha", "project": None, "why": "w2", "interstitial": False, "id": "a"},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[],
                          start_time=dt.datetime(2026, 7, 13, 10, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    out = _times(plan)
    assert [t for t, _ in out] == ["Beta", "Alpha"]          # order preserved
    assert out[0][1] == "10:00 – 11:00"                       # Beta 60min from 10:00
    assert out[1][1] == "11:00 – 11:30"                       # Alpha 30min after
    # ids survive (mark-done handshake) and the en-dash HH:MM – HH:MM contract holds
    ids = [it["id"] for b in plan["blocks"] for it in b["items"]]
    assert ids == ["b", "a"]
    assert all(" – " in tm for _, tm in out)


def test_deferred_task_is_not_scheduled():
    # A gentle day: the model put only Alpha in the plan and left Beta for still_here.
    tasks = [{"id": "a", "name": "Alpha", "duration_min": 30},
             {"id": "b", "name": "Beta", "duration_min": 60}]
    plan = _clock_plan([
        {"time": "x", "task": "Alpha", "project": None, "why": "w", "interstitial": False, "id": "a"},
    ])
    plan["still_here"] = [{"label": "Beta", "note": "held for a lower day"}]
    pg._retime_clock_plan(plan, tasks, all_anchors=[],
                          start_time=dt.datetime(2026, 7, 13, 10, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    scheduled_tasks = [t for t, _ in _times(plan)]
    assert scheduled_tasks == ["Alpha"]                       # Beta stays deferred, not force-scheduled


def test_fixed_anchor_placed_at_its_time_and_model_echo_dropped():
    # The model echoed "Lunch" into the morning at a wrong time; Python must drop that echo and
    # place the authoritative Lunch anchor at its real fixed time (12:45), exactly once, id-less.
    tasks = [{"id": "a", "name": "Alpha", "duration_min": 30}]
    lunch = {"name": "Lunch", "fixed_time": dt.datetime(2026, 7, 13, 12, 45),
             "duration_min": 30, "_default_anchor": True}
    plan = _clock_plan([
        {"time": "x", "task": "Alpha", "project": None, "why": "w", "interstitial": False, "id": "a"},
        {"time": "10:30 – 11:00", "task": "Lunch", "project": None, "why": None, "interstitial": False},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[lunch],
                          start_time=dt.datetime(2026, 7, 13, 10, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    rows = _times(plan)
    lunches = [tm for name, tm in rows if name == "Lunch"]
    assert lunches == ["12:45 – 13:15"]                       # exactly one, at the fixed time
    lunch_item = next(it for b in plan["blocks"] for it in b["items"] if it["task"] == "Lunch")
    assert "id" not in lunch_item                             # anchors keep no done-affordance (unchanged behavior)


def test_renamed_anchor_echo_is_deduped():
    # The model renames anchors freely ("Attend SF LGBT…" for "SF LGBT…", "Lunch (~30min)" for
    # "Lunch"). Both echoes must be dropped so Python's authoritative anchor is the ONLY copy —
    # the live 2026-07-13 double-booking bug.
    tasks = [{"id": "a", "name": "Alpha", "duration_min": 30}]
    lunch = {"name": "Lunch", "fixed_time": dt.datetime(2026, 7, 13, 12, 45),
             "duration_min": 30, "_default_anchor": True}
    dropin = {"name": "SF LGBT Center Employment Services Drop-In (virtual)",
              "fixed_time": dt.datetime(2026, 7, 13, 14, 0), "duration_min": 60, "id": "r1"}
    plan = _clock_plan([
        {"time": "x", "task": "Alpha", "project": None, "why": "w", "interstitial": False, "id": "a"},
        {"time": "x", "task": "Lunch (~30min)", "project": None, "why": None, "interstitial": False},
        {"time": "x", "task": "Attend SF LGBT Center Employment Services Drop-In (virtual)",
         "project": None, "why": None, "interstitial": False},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[lunch, dropin],
                          start_time=dt.datetime(2026, 7, 13, 10, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    names = [t for t, _ in _times(plan)]
    assert names.count("Lunch") == 1
    assert sum(1 for n in names if "LGBT" in n) == 1          # exactly one drop-in, not two
    assert "Attend SF LGBT Center Employment Services Drop-In (virtual)" not in names  # the echo is gone


def test_real_task_containing_anchor_word_is_never_dropped():
    # Guard against the substring false-positive (cross-family review, 2026-07-13): a REAL task
    # ("Lunch meeting with the recruiter") resolves to an id, so it must survive even though its
    # name contains the anchor word "Lunch". Only id-less echoes are dropped.
    tasks = [{"id": "m", "name": "Lunch meeting with the recruiter", "duration_min": 60}]
    lunch = {"name": "Lunch", "fixed_time": dt.datetime(2026, 7, 13, 12, 45),
             "duration_min": 30, "_default_anchor": True}
    plan = _clock_plan([
        {"time": "x", "task": "Lunch meeting with the recruiter", "project": None,
         "why": "job", "interstitial": False, "id": "m"},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[lunch],
                          start_time=dt.datetime(2026, 7, 13, 10, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    names = [t for t, _ in _times(plan)]
    assert "Lunch meeting with the recruiter" in names       # the real task survives
    ids = [it.get("id") for b in plan["blocks"] for it in b["items"]]
    assert "m" in ids                                         # mark-done handshake intact


def test_recurring_anchor_is_checkable_meal_and_break_are_not():
    # Chores can be checked off (2026-07-13): a recurring anchor carries a real id, so it gets a
    # checkbox + `recurring` flag (→ local done-for-today). A meal (id None) and a break stay
    # un-checkable.
    scheduled = [
        {"name": "Do the dishes", "id": "r1", "start_time": dt.datetime(2026, 7, 13, 12, 0),
         "end_time": dt.datetime(2026, 7, 13, 12, 20)},                      # recurring: has id
        {"name": "Lunch", "_default_anchor": True, "start_time": dt.datetime(2026, 7, 13, 12, 45),
         "end_time": dt.datetime(2026, 7, 13, 13, 15)},                      # meal: no id
        {"name": "Break — stand, stretch, move", "_break": True, "id": "b1",
         "start_time": dt.datetime(2026, 7, 13, 14, 0),
         "end_time": dt.datetime(2026, 7, 13, 14, 15)},                      # break: excluded even with id
    ]
    blocks = dp.blocks_from_scheduled(scheduled)
    rows = {it["task"]: it for b in blocks for it in b["items"]}
    assert rows["Do the dishes"].get("id") == "r1" and rows["Do the dishes"].get("recurring") is True
    assert "id" not in rows["Lunch"]                                          # meal: no checkbox
    assert "id" not in rows["Break — stand, stretch, move"]                   # break: no checkbox


def test_priority_shape_is_left_untouched():
    plan = {"shape": "priority", "items": [{"task": "x", "id": "a"}], "still_here": []}
    before = dict(plan)
    pg._retime_clock_plan(plan, [{"id": "a", "name": "x"}], all_anchors=[],
                          start_time=dt.datetime(2026, 7, 13, 10, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    assert plan == before                                     # no clock to assign


def test_interstitial_real_task_survives_retime():
    # JSON rule 3 tells the model to mark ≤15-min REAL chores interstitial ("Bring quilt in").
    # An interstitial row that carries a task id is a captured task, not a Python-owned break —
    # it must stay scheduled (the live 2026-07-13 silent-drop: quilt/kitchen/drive-to-SF).
    tasks = [{"id": "q", "name": "Bring quilt in from the yard", "duration_min": 10}]
    plan = _clock_plan([
        {"time": "x", "task": "Bring quilt in from the yard", "project": None, "why": None,
         "interstitial": True, "id": "q"},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[],
                          start_time=dt.datetime(2026, 7, 13, 10, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    names = [t for t, _ in _times(plan)]
    assert "Bring quilt in from the yard" in names            # scheduled, not discarded
    assert plan["still_here"] == []                           # and not parked either


def test_idless_interstitial_break_is_still_dropped_and_not_parked():
    # A model-written break (no id) stays Python's to recompute: dropped from blocks, and NOT
    # force-parked into still_here (it is not a task; the accounting net keys on real tasks).
    tasks = [{"id": "a", "name": "Alpha", "duration_min": 30}]
    plan = _clock_plan([
        {"time": "x", "task": "Alpha", "project": None, "why": "w", "interstitial": False, "id": "a"},
        {"time": "x", "task": "Quick stretch", "project": None, "why": None, "interstitial": True},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[],
                          start_time=dt.datetime(2026, 7, 13, 10, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    names = [t for t, _ in _times(plan)]
    assert "Quick stretch" not in names
    assert all(sh.get("label") != "Quick stretch" for sh in plan["still_here"])


def test_task_that_does_not_fit_before_end_time_is_parked_not_lost():
    # build_schedule stops placing flexible items at end_time. Because the retime runs AFTER the
    # caller's accounting pass, an overflow drop here used to vanish without a trace — it must
    # land in still_here instead.
    tasks = [{"id": "a", "name": "Alpha", "duration_min": 60},
             {"id": "b", "name": "Beta", "duration_min": 60}]
    plan = _clock_plan([
        {"time": "x", "task": "Alpha", "project": None, "why": "w1", "interstitial": False, "id": "a"},
        {"time": "x", "task": "Beta", "project": None, "why": "w2", "interstitial": False, "id": "b"},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[],
                          start_time=dt.datetime(2026, 7, 13, 17, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    names = [t for t, _ in _times(plan)]
    assert names == ["Alpha"]                                 # only Alpha fits before 18:00
    labels = {sh["label"] for sh in plan["still_here"]}
    assert "Beta" in labels                                   # the overflow is visible, not lost


def test_evening_generation_parks_everything_instead_of_emptying_the_plan():
    # A refresh after the workday end (start > end_time): nothing flexible fits at all. The plan
    # must degrade to the honest all-still-here shape — never an empty plan that silently
    # overwrites the morning's cache (deterministic evening failure, found 2026-07-13).
    tasks = [{"id": "a", "name": "Alpha", "duration_min": 30},
             {"id": "b", "name": "Beta", "duration_min": 60}]
    plan = _clock_plan([
        {"time": "x", "task": "Alpha", "project": None, "why": "w1", "interstitial": False, "id": "a"},
        {"time": "x", "task": "Beta", "project": None, "why": "w2", "interstitial": False, "id": "b"},
    ])
    pg._retime_clock_plan(plan, tasks, all_anchors=[],
                          start_time=dt.datetime(2026, 7, 13, 20, 0),
                          end_time=dt.datetime(2026, 7, 13, 18, 0))
    assert _times(plan) == []                                 # nothing schedulable this late
    labels = {sh["label"] for sh in plan["still_here"]}
    assert {"Alpha", "Beta"} <= labels                        # every task visibly parked, none lost


def test_no_project_discrete_task_survives_the_gate():
    # The gate bug: a task with no linked project was hidden as if it were an unset-engagement
    # dormant project. It must survive (discrete standalone action).
    tasks = [{"id": "d", "name": "Call the surgeon", "linked_projects": []}]
    kept = pg._gate_and_collapse(tasks, projects=[], neglected=[], period=None, surface_dates={})
    assert [t["id"] for t in kept] == ["d"]

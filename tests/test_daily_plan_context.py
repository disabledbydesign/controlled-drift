"""Phase 3/4 pure-logic tests: the period block + Side in format_context, and the
priority-list output shape. Fixture dicts — no Anytype, no clock."""
import re
import datetime as dt
import daily_plan


def _proj(name, side=None, eng="Steady"):
    return {"id": name.lower(), "name": name, "engagement": eng, "side": side,
            "reaching_for": "", "context": "", "affective": "", "engagement_notes": "",
            "parent_project_id": None}


def test_context_includes_period_meaning_and_side():
    period = {"name": "Week of Jun 30", "intent": "jobs foreground, survival first",
              "availability_note": "caregiving — fragmented time, survival-first",
              "foreground": ["Job Search"], "paused": ["Autograder"]}
    projects = [_proj("Job Search", side="Obligation", eng="Sprint"),
                _proj("Autograder", side="Wellbeing")]
    ctx = daily_plan.format_context([], projects, [], [], [], [], "low",
                                    period=period, is_off=False, in_window=True)
    assert "## TODAY'S FOCUS PERIOD" in ctx           # authoritative header (was passive "## This period")
    assert "survival first" in ctx                    # intent
    assert "caregiving" in ctx                        # availability_note shown (in_window)
    assert "side: Obligation" in ctx
    assert "Foreground this period: Job Search" in ctx
    assert "[paused this period]" in ctx              # the paused marker appears


def test_availability_note_hidden_when_not_in_window():
    period = {"name": "W", "intent": "x", "availability_note": "SECRETNOTE",
              "foreground": [], "paused": []}
    ctx = daily_plan.format_context([], [], [], [], [], [], None,
                                    period=period, is_off=False, in_window=False)
    assert "SECRETNOTE" not in ctx


def test_day_off_line_present_when_is_off():
    period = {"name": "W", "foreground": [], "paused": []}
    ctx = daily_plan.format_context([], [], [], [], [], [], None,
                                    period=period, is_off=True, in_window=False)
    assert "DAY OFF" in ctx


def test_malformed_day_off_surfaces_to_june():
    period = {"name": "W", "foreground": [], "paused": [], "days_off_error": True}
    ctx = daily_plan.format_context([], [], [], [], [], [], None, period=period)
    assert "couldn't be read" in ctx


def test_context_no_period_is_clean():
    ctx = daily_plan.format_context([], [_proj("X")], [], [], [], [], None)
    assert "## This period" not in ctx


# --- the "gone quiet" (neglect) display path ---------------------------------
# The section was unreachable: query_neglected never set `linked_projects`, so the filter
# fell through to an impossible set-inside-a-list fallback. These pin the fixed path.

OLD = dt.datetime(2026, 6, 1, 9, 0)   # stale enough to be "gone quiet"


def _neg(name, ntype="task", linked=None, last_surfaced=OLD, last_completed=OLD):
    # The active-untouched cohort flags by last COMPLETION now (last_surfaced kept for signature
    # compatibility; format_context no longer filters on it — that guard lives in active_untouched).
    return {"name": name, "type": ntype, "last_surfaced": last_surfaced,
            "last_completed": last_completed,
            "linked_projects": linked if linked is not None else []}


def test_stale_item_in_active_project_reaches_the_not_getting_to_section():
    projects = [_proj("Bar", eng="Steady")]
    neglected = [_neg("Foo", linked=["Bar"])]
    ctx = daily_plan.format_context([], projects, [], [], [], neglected, None)
    assert "not getting to" in ctx
    assert "Foo (last finished something 2026-06-01)" in ctx


def test_backburner_projects_quiet_task_is_not_surfaced_as_a_problem():
    projects = [_proj("Old", eng="Backburner")]
    neglected = [_neg("Zzz", linked=["Old"])]
    ctx = daily_plan.format_context([], projects, [], [], [], neglected, None)
    assert "Zzz" not in ctx                  # a Backburner project is never in the active cohort


def test_never_completed_active_item_renders_plainly():
    # A cohort item with no completion yet (the active_untouched brand-new-project guard already
    # ran upstream) renders honestly rather than being dropped — format_context trusts the cohort.
    projects = [_proj("Bar", eng="Steady")]
    neglected = [_neg("New", linked=["Bar"], last_completed=None)]
    ctx = daily_plan.format_context([], projects, [], [], [], neglected, None)
    assert "New (nothing finished in it yet)" in ctx


def test_project_type_neglected_item_belongs_when_project_is_active():
    projects = [_proj("Baz", eng="Steady")]
    neglected = [_neg("Baz", ntype="project", linked=["Baz"])]
    ctx = daily_plan.format_context([], projects, [], [], [], neglected, None)
    assert "not getting to" in ctx
    assert "Baz (last finished something 2026-06-01)" in ctx


def test_gone_quiet_excludes_todays_recurrings():
    projects = [_proj("Bar", eng="Steady")]
    neglected = [_neg("Take meds", linked=["Bar"])]
    recurrings = [{"name": "Take meds", "fixed_time": dt.datetime(2026, 6, 1, 9, 0)}]
    ctx = daily_plan.format_context([], projects, [], [], recurrings, neglected, None)
    assert "not getting to" not in ctx      # the only item was a recurring, separately listed


# --- the priority-list output shape -----------------------------------------

def test_priority_list_has_no_clock_times_and_is_ordered():
    items = [{"name": "Submit the Acme application", "duration_min": 45},
             {"name": "Reply to recruiter email", "duration_min": 10}]
    out = daily_plan.format_priority_list(items, period={"availability_note": "a couple hours, unknown when"})
    assert out.index("Submit the Acme application") < out.index("Reply to recruiter email")
    assert not re.search(r"\d{1,2}:\d{2}", out)      # no HH:MM anywhere — the whole point
    assert "couple hours" in out


def test_priority_list_caps_long_lists():
    items = [{"name": f"Task {i}"} for i in range(10)]
    out = daily_plan.format_priority_list(items)
    assert "Task 0" in out
    assert "more" in out.lower()                      # remainder noted

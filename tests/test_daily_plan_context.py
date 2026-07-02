"""Phase 3/4 pure-logic tests: the period block + Side in format_context, and the
priority-list output shape. Fixture dicts — no Anytype, no clock."""
import re
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
    assert "## This period" in ctx
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

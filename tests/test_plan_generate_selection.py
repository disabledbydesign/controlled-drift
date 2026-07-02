"""Phase 3.2: foreground drives real task selection (not just a prose hint), paused drops.
Pure logic — no Anytype."""
import plan_generate as pg


def test_foreground_first_paused_dropped():
    tasks = [{"name": "hobby task", "linked_projects": ["Autograder"], "duration_min": 30},
             {"name": "apply Acme", "linked_projects": ["Job Search"], "duration_min": 45}]
    period = {"foreground": ["Job Search"], "paused": ["Autograder"]}
    ordered = pg.select_and_order_tasks(tasks, period)
    assert [t["name"] for t in ordered] == ["apply Acme"]   # foreground kept + first, paused dropped


def test_foreground_floats_up_without_dropping_others():
    tasks = [{"name": "other", "linked_projects": ["Misc"]},
             {"name": "job task", "linked_projects": ["Job Search"]}]
    period = {"foreground": ["Job Search"], "paused": []}
    ordered = pg.select_and_order_tasks(tasks, period)
    assert ordered[0]["name"] == "job task"                 # foreground first
    assert {t["name"] for t in ordered} == {"job task", "other"}  # nothing dropped


def test_no_period_preserves_all_tasks():
    tasks = [{"name": "a", "linked_projects": ["X"]}, {"name": "b", "linked_projects": ["Y"]}]
    ordered = pg.select_and_order_tasks(tasks, None)
    assert {t["name"] for t in ordered} == {"a", "b"}       # nothing dropped when no period

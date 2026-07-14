"""Block selection + Daily-life gating in plan_generate._gate_and_collapse."""
import plan_generate as pg


def _proj(name, eng=None, side=None):
    return {"name": name, "engagement": eng, "side": side,
            "parent_project_id": None, "is_workstream": False}


def _task(tid, name, proj):
    return {"id": tid, "name": name, "linked_projects": [proj]}


def test_daily_life_chores_all_survive_uncollapsed():
    """A Daily-life project with unset engagement surfaces EVERY chore (not one collapsed
    representative) — chores are discrete, and Daily life is exempt from the engagement gate."""
    projects = [_proj("Household", eng=None, side="Daily life")]
    tasks = [_task("t1", "Clean kitchen", "Household"),
             _task("t2", "Do dishes", "Household")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} >= {"t1", "t2"}


def test_non_daily_life_unset_engagement_still_hidden():
    """Contrast: an ordinary unset-engagement project (not Daily life, not neglected) is still
    hidden by the gate — the bypass is specific to Daily life, not a blanket opening."""
    projects = [_proj("Some project", eng=None, side="Wellbeing")]
    tasks = [_task("t1", "A task", "Some project")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} == set()

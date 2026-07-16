"""Rollover (2026-07-13): yesterday's uncompleted items are made eligible so the model can carry
them, and every carry/drop decision is logged under its own tag for observability. Built on the
plan/completion-history foundation. The model DECIDES what carries — these pin the plumbing that
makes that decision possible and observable, not the model's judgment itself."""
import datetime as dt, os, json
import plan_generate as pg
import rollover_log as rl
import cd_paths


def test_rollover_carries_a_dormant_project_task_into_today():
    # "Paper" is dormant (excluded at load -> not in `projects`). Its undone task would be dropped;
    # rollover makes it eligible so "email editor rolls to today" works.
    tasks = [{"id": "t1", "name": "Email the editor", "linked_projects": ["Paper"]}]
    dropped = pg._gate_and_collapse(tasks, [], neglected=[], period=None, surface_dates={})
    assert dropped == []
    carried = pg._gate_and_collapse(tasks, [], neglected=[], period=None,
                                    surface_dates={}, rollover_ids={"t1"})
    assert [t["id"] for t in carried] == ["t1"]


def test_active_project_tasks_all_survive_uncollapsed():
    # No collapse anymore: both tasks of an active project stay (Task 9 groups them into one block
    # at OUTPUT). This gate no longer picks one representative.
    tasks = [{"id": "a", "name": "a", "linked_projects": ["P"]},
             {"id": "b", "name": "b", "linked_projects": ["P"]}]
    projects = [{"name": "P", "engagement": "Steady", "side": "Wellbeing"}]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} == {"a", "b"}


def test_rollover_log_classifies_carried_and_dropped(cd_sandbox):
    # Yesterday's plan held u1 and u2, neither completed → both are carry candidates. The model
    # carried u1 into today and let u2 go; the log must record exactly that split.
    y = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    p = cd_paths.data_file("plan_snapshots.jsonl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    snap = {"ts": "x", "plan_date": y, "source": "test",
            "plan": {"blocks": [{"items": [{"id": "u1", "task": "A"}, {"id": "u2", "task": "B"}]}]}}
    with open(p, "a") as f:
        f.write(json.dumps(snap) + "\n")
    today_plan = {"blocks": [{"items": [{"id": "u1", "task": "A (carried forward)"}]}]}
    rl.log_rollover(today_plan)
    recs = rl.read_rollovers()
    assert len(recs) == 1
    assert {c["id"] for c in recs[0]["carried"]} == {"u1"}
    assert {d["id"] for d in recs[0]["dropped"]} == {"u2"}
    assert recs[0]["considered"] == 2


def test_rollover_log_noop_when_nothing_undone(cd_sandbox):
    # No yesterday snapshot → nothing to carry → no record written (no noise on a clean start).
    rl.log_rollover({"blocks": [{"items": [{"id": "x", "task": "T"}]}]})
    assert rl.read_rollovers() == []

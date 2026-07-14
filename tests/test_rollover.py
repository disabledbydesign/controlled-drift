"""Rollover (2026-07-13): yesterday's uncompleted items are made eligible so the model can carry
them, and every carry/drop decision is logged under its own tag for observability. Built on the
plan/completion-history foundation. The model DECIDES what carries — these pin the plumbing that
makes that decision possible and observable, not the model's judgment itself."""
import datetime as dt, os, json
import plan_generate as pg
import rollover_log as rl
import cd_paths


def test_rollover_id_survives_the_hide_gate():
    # A task under a Backburner project is normally hidden from the plan. If it was undone
    # yesterday, rollover must make it an eligible candidate the model can choose to carry —
    # otherwise "call mom rolls to tomorrow" is impossible for anything under a quiet project.
    tasks = [{"id": "t1", "name": "Email the editor", "linked_projects": ["Paper"]}]
    projects = [{"name": "Paper", "engagement": "Backburner"}]
    hidden = pg._gate_and_collapse(tasks, projects, neglected=[], period=None, surface_dates={})
    assert hidden == []                                    # Backburner, not neglected/foregrounded → hidden
    carried = pg._gate_and_collapse(tasks, projects, neglected=[], period=None,
                                    surface_dates={}, rollover_ids={"t1"})
    assert [t["id"] for t in carried] == ["t1"]            # rollover makes it eligible


def test_rollover_task_does_not_double_surface_its_thread():
    # A carried-over (forced) task and its thread's natural winner must collapse to ONE move — the
    # forced task represents the thread. Regression: when the natural winner was iterated first it
    # slipped through alongside the forced task, showing two moves for one thread.
    tasks = [
        {"id": "a", "name": "Natural winner", "linked_projects": ["P"], "due_date": None},
        {"id": "b", "name": "Carried-over task", "linked_projects": ["P"], "due_date": None},
    ]
    projects = [{"name": "P", "engagement": "Steady", "deadline": None}]
    surface = {"b": dt.datetime(2026, 7, 11)}   # a never surfaced → a is the natural winner
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates=surface, rollover_ids={"b"})
    assert [t["id"] for t in kept] == ["b"]     # exactly one move for thread P — the carried-over task


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

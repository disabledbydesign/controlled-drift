"""Wellbeing-side work collapses into ONE open self-directed block instead of system-picked
hobby tasks (never-pick-her-threads). Pure logic — no Anytype."""
import daily_plan as dp


_PROJECTS = [
    {"name": "Job Search", "side": "Obligation"},
    {"name": "Autograder", "side": "Wellbeing"},
    {"name": "Leather cuffs", "side": "Obligation"},   # income → obligation
    {"name": "Mystery", "side": None},                 # untagged
]


def test_wellbeing_task_partitioned_out():
    tasks = [{"name": "apply Acme", "linked_projects": ["Job Search"]},
             {"name": "hack on autograder", "linked_projects": ["Autograder"]}]
    schedulable, wellbeing = dp.partition_by_side(tasks, _PROJECTS)
    assert [t["name"] for t in schedulable] == ["apply Acme"]
    assert [t["name"] for t in wellbeing] == ["hack on autograder"]


def test_mixed_side_task_stays_schedulable():
    # links to BOTH a wellbeing and an obligation project → schedulable (survival-relevant)
    tasks = [{"name": "dual", "linked_projects": ["Autograder", "Job Search"]}]
    schedulable, wellbeing = dp.partition_by_side(tasks, _PROJECTS)
    assert [t["name"] for t in schedulable] == ["dual"]
    assert wellbeing == []


def test_unlinked_and_unknown_side_stay_schedulable():
    tasks = [{"name": "chore", "linked_projects": []},
             {"name": "untagged", "linked_projects": ["Mystery"]}]
    schedulable, wellbeing = dp.partition_by_side(tasks, _PROJECTS)
    assert {t["name"] for t in schedulable} == {"chore", "untagged"}   # never hidden when unsure
    assert wellbeing == []


def test_open_block_emitted_only_when_wellbeing_work_exists():
    assert dp.open_hobby_block([]) is None
    block = dp.open_hobby_block([{"name": "hack on autograder"}])
    assert block is not None
    assert block["fixed_time"] is None and block["_open_block"] is True
    assert "choice" in block["name"].lower()          # it's HER choice, not a picked task

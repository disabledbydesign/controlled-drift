"""Fun/hobby-side work collapses into ONE open self-directed block instead of system-picked
hobby tasks (never-pick-her-threads). Pure logic — no Anytype.

Updated 2026-07-11 for the three-category Side rework (commit 7ec484f): only "Fun / hobby" is
held out of the plan now; "Wellbeing" (restorative — walks/rest) and "Obligation" both stay IN.
The fixture's held-out project is therefore tagged "Fun / hobby", not "Wellbeing"."""
import daily_plan as dp


_PROJECTS = [
    {"name": "Job Search", "side": "Obligation"},
    {"name": "Autograder", "side": "Fun / hobby"},     # self-directed dev → held out of the plan
    {"name": "Morning walks", "side": "Wellbeing"},    # restorative → now STAYS in the plan
    {"name": "Leather cuffs", "side": "Obligation"},   # income → obligation
    {"name": "Mystery", "side": None},                 # untagged
]


def test_hobby_task_partitioned_out():
    tasks = [{"name": "apply Acme", "linked_projects": ["Job Search"]},
             {"name": "hack on autograder", "linked_projects": ["Autograder"]}]
    schedulable, wellbeing = dp.partition_by_side(tasks, _PROJECTS)
    assert [t["name"] for t in schedulable] == ["apply Acme"]
    assert [t["name"] for t in wellbeing] == ["hack on autograder"]


def test_wellbeing_work_now_stays_in_the_plan():
    # The point of the three-category rework: restorative Wellbeing work is NOT held out anymore.
    tasks = [{"name": "take the morning walk", "linked_projects": ["Morning walks"]}]
    schedulable, wellbeing = dp.partition_by_side(tasks, _PROJECTS)
    assert [t["name"] for t in schedulable] == ["take the morning walk"]
    assert wellbeing == []


def test_mixed_side_task_stays_schedulable():
    # links to BOTH a fun/hobby and an obligation project → schedulable (survival-relevant)
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


def test_rest_item_stays_schedulable_even_if_hobby_linked():
    # June, 2026-07-11: necessary rest (walks/exercise/meals) must never be dropped as "hobby",
    # even when linked to a Fun/hobby project. Rest is recognized by _is_rest_item keywords.
    tasks = [{"name": "Go on a long walk", "linked_projects": ["Autograder"]},
             {"name": "hack on autograder", "linked_projects": ["Autograder"]}]
    schedulable, wellbeing = dp.partition_by_side(tasks, _PROJECTS)
    assert "Go on a long walk" in [t["name"] for t in schedulable]
    assert [t["name"] for t in wellbeing] == ["hack on autograder"]


def test_hobby_block_off_by_default():
    # Fun/hobby is kept out of the plan entirely by default (no settings.json in the sandbox).
    assert dp.include_hobby_block() is False


def test_hobby_block_reads_setting_when_on(tmp_path, monkeypatch):
    # The overlay toggle writes {"include_hobby_block": true} to settings.json; the plan reads it.
    import cd_paths, json, os
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    os.makedirs(cd_paths.config_dir(), exist_ok=True)
    with open(cd_paths.config_file("settings.json"), "w") as f:
        json.dump({"include_hobby_block": True, "backend": "mistral"}, f)
    assert dp.include_hobby_block() is True


def test_open_block_emitted_only_when_wellbeing_work_exists():
    assert dp.open_hobby_block([]) is None
    block = dp.open_hobby_block([{"name": "hack on autograder"}])
    assert block is not None
    assert block["fixed_time"] is None and block["_open_block"] is True
    assert "choice" in block["name"].lower()          # it's HER choice, not a picked task

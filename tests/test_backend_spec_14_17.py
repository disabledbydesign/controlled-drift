"""Backend spec §14 (no per-item "why") and §17 (`workday_start`), plus §4's access wire.

§14 and §17 are both "the field stops/starts existing" changes, so what needs guarding is the
payload contract at the seam, not any one function's internals.
"""
import datetime as dt
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import daily_plan as dp
import focus_period as fp
import plan_generate as pg


# --- §14: the generator stops producing a per-item "why" --------------------

_MODEL_CLOCK_OUTPUT = """```json
{"woven_frame": "Two goals are live: material survival and staying a scholar-builder.",
 "blocks": [{"label": "Morning", "time": "09:00 - 12:00",
             "framing": "Easy wins first, then the harder thing.",
             "why": "a block-level rationale the model composed anyway",
             "items": [{"time": "09:00 - 10:30", "project": "Jobs", "task": "Send the application",
                        "why": "a per-item rationale the model composed anyway", "ref": "T1"}]}],
 "still_here": [{"label": "Reframe paper", "note": "waiting on the portal - nothing to do today"}]}
```"""

_MODEL_PRIORITY_OUTPUT = """```json
{"shape": "priority", "woven_frame": "A fragmented day.",
 "header": "When a window opens, start at the top.",
 "items": [{"project": "Jobs", "task": "Send the application", "why": "unread rationale", "ref": "T1"}],
 "still_here": []}
```"""


def test_why_is_gone_from_the_clock_shape():
    plan = pg.parse_plan(_MODEL_CLOCK_OUTPUT)
    block = plan["blocks"][0]
    assert "why" not in block
    assert "why" not in block["items"][0]


def test_why_is_gone_from_the_priority_shape():
    plan = pg.parse_plan(_MODEL_PRIORITY_OUTPUT)
    assert "why" not in plan["items"][0]


def test_the_woven_frame_and_framings_SURVIVE():
    """§14 removes the per-item rationale and explicitly KEEPS the whole-day narrative. Dropping
    the frame along with the why would silently delete the one narrative the surface still shows."""
    plan = pg.parse_plan(_MODEL_CLOCK_OUTPUT)
    assert plan["woven_frame"].startswith("Two goals are live")
    assert plan["blocks"][0]["framing"] == "Easy wins first, then the harder thing."
    assert plan["still_here"][0]["note"].startswith("waiting on the portal")
    assert plan["blocks"][0]["items"][0]["task"] == "Send the application"


def test_the_prompt_no_longer_asks_for_a_why():
    """Removing it from the output but still paying to compose it would miss half of §14
    ("do not spend tokens composing it")."""
    for prompt in (pg._JSON_INSTRUCTION, pg._JSON_INSTRUCTION_PRIORITY):
        assert '"why"' not in prompt


def test_blocks_from_scheduled_emits_no_why_row():
    """The clock-shape render seam. A composed item carrying a stale `why` must not put one back."""
    start = dt.datetime(2026, 7, 18, 9, 0)
    scheduled = [{"name": "Send the application", "task": "Send the application", "id": "t1",
                  "project": "Jobs", "why": "stale", "_composed": True,
                  "start_time": start, "end_time": start + dt.timedelta(minutes=90)}]
    blocks = dp.blocks_from_scheduled(scheduled)
    assert "why" not in blocks[0]["items"][0]


# --- §17: workday_start bounds the day -------------------------------------

def test_parse_hhmm_start_and_end_fall_back_differently():
    """A start silently defaulting to the END's 18:00 would produce an empty day."""
    assert fp.parse_hhmm("11:30") == (11, 30)
    assert fp.parse_hhmm("garbage") == (18, 0)
    assert fp.parse_hhmm("garbage", default=(10, 0)) == (10, 0)
    assert fp.parse_hhmm("25:00", default=(10, 0)) == (10, 0)


def test_focus_period_reads_workday_start():
    obj = {"id": "fp1", "name": "Slow mornings",
           "properties": [{"name": "Workday start", "text": "11:00"},
                          {"name": "Workday end", "text": "22:00"}]}
    parsed = fp.parse_focus_period(obj)
    assert parsed["workday_start"] == "11:00"
    assert parsed["workday_end"] == "22:00"


def test_workday_start_is_absent_when_unset():
    parsed = fp.parse_focus_period({"id": "fp2", "name": "Plain", "properties": []})
    assert parsed["workday_start"] is None


def test_authoring_round_trips_workday_start():
    """Write path -> Anytype property name, and the reflect-back June confirms before it saves."""
    import focus_period_adapter as fpa
    _, props = fpa.to_write_properties({"name": "Slow mornings", "workday_start": "11:00"},
                                       objects=[])
    assert props["Workday start"] == "11:00"
    reflected = fpa.reflect_back({"name": "Slow mornings", "workday_start": "11:00"})
    shown = {i["key"]: i for i in reflected["items"]}
    assert shown["workday_start"]["display"] == "11:00"
    # and stays out of the reflect-back entirely when she never mentioned a start time
    assert "workday_start" not in {i["key"] for i in fpa.reflect_back({"name": "Plain"})["items"]}


# --- §4: the project-level access profile actually reaches a task ----------

def test_task_inherits_its_projects_access_conditions():
    """The property existed on Project and nothing read it, so tagging a workstream changed
    no plan. A task with none of its own now picks up the resolved project value."""
    projects = {"Metabolism": {"id": "p1", "name": "Metabolism",
                               "access": ["Involves-leaving-house"]}}
    task = {"id": "t1", "access": [], "linked_projects": ["Metabolism"]}
    assert dp.inherited_access(task, projects) == ["Involves-leaving-house"]


def test_a_tasks_own_access_overrides_its_projects():
    """"Override-when-it-differs" — the half that keeps inheritance from flattening real cases."""
    projects = {"Metabolism": {"id": "p1", "name": "Metabolism",
                               "access": ["Involves-leaving-house"]}}
    task = {"id": "t1", "access": ["Can-be-done-lying-down"], "linked_projects": ["Metabolism"]}
    assert dp.inherited_access(task, projects) == ["Can-be-done-lying-down"]


def test_no_project_access_leaves_the_task_empty_not_none():
    projects = {"Metabolism": {"id": "p1", "name": "Metabolism", "access": None}}
    task = {"id": "t1", "access": [], "linked_projects": ["Metabolism", "Missing project"]}
    assert dp.inherited_access(task, projects) == []


def test_access_tags_preserve_absent_versus_empty():
    """The distinction the §4 resolver runs on: None in stays None out."""
    assert dp._access_tags(None) is None
    assert dp._access_tags([]) == []
    assert dp._access_tags([{"name": "Induces-pain"}]) == ["Induces-pain"]

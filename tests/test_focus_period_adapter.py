# tests/test_focus_period_adapter.py — the generate->author adapter + reflect-back template.
# Pure over inputs (name->id resolution takes a fake objects list), so these run offline and
# write nothing to Anytype.
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from focus_period_adapter import (to_write_properties, missing_required, reflect_back,
                                  _fmt_range, _csv)

PROJECTS = [
    {"id": "p1", "name": "Academic positions", "type": {"key": "gsdo_project"}},
    {"id": "p2", "name": "Industry positions", "type": {"key": "gsdo_project"}},
    {"id": "p3", "name": "Reframe paper", "type": {"key": "gsdo_project"}},
    {"id": "g1", "name": "Material survival", "type": {"key": "gsdo_goal"}},  # not a project
]


def _fields(**over):
    f = {
        "name": "Week of Jun 29 — jobs foreground",
        "start_date": "2026-06-29",
        "end_date": "2026-07-06",
        "intent": "Jobs are the survival focus.",
        "availability_start": "2026-07-04",
        "availability_end": "2026-07-06",
        "availability_note": "Caregiving — fragmented time.",
        "days_off": ["2026-07-05"],
        "days_on": [],
        "output_format": "Auto",
        "workday_end": None,
        "foreground_projects": ["Academic positions", "Industry positions"],
        "paused_projects": [],
    }
    f.update(over)
    return f


# --- missing_required (the silent-failure guard) -----------------------------

def test_missing_required_none_when_both_dates_present():
    assert missing_required(_fields()) == []


def test_missing_required_flags_absent_end_date():
    assert missing_required(_fields(end_date=None)) == ["end date"]
    assert missing_required(_fields(start_date="", end_date="")) == ["start date", "end date"]
    assert missing_required({}) == ["start date", "end date"]


# --- to_write_properties (the mapping) ---------------------------------------

def test_to_write_properties_maps_keys_names_and_dates():
    name, props = to_write_properties(_fields(), objects=PROJECTS)
    assert name == "Week of Jun 29 — jobs foreground"
    assert props["Period start"] == "2026-06-29"
    assert props["Period end"] == "2026-07-06"
    assert props["Intent"] == "Jobs are the survival focus."
    assert props["Availability start"] == "2026-07-04"
    assert props["Availability note"].startswith("Caregiving")
    assert props["Days off"] == "2026-07-05"          # ISO list -> CSV
    assert props["Foreground projects"] == ["p1", "p2"]  # names -> ids, order preserved
    assert props["Output format"] == "Auto"


def test_output_format_preserved_exactly_and_garbage_falls_back():
    _, props = to_write_properties(_fields(output_format="Priority list"), objects=PROJECTS)
    assert props["Output format"] == "Priority list"
    _, props2 = to_write_properties(_fields(output_format="nonsense"), objects=PROJECTS)
    assert props2["Output format"] == "Auto"          # never write a garbage select value


def test_absent_optional_fields_are_not_written():
    name, props = to_write_properties(
        _fields(intent=None, availability_start=None, availability_end=None,
                availability_note=None, days_off=[], workday_end=None, paused_projects=[]),
        objects=PROJECTS)
    assert "Intent" not in props
    assert "Availability start" not in props
    assert "Days off" not in props
    assert "Workday end" not in props
    assert "Paused projects" not in props
    # required + shape still present
    assert props["Period start"] and props["Period end"] and props["Output format"] == "Auto"


def test_multi_day_csv_and_paused_ids():
    name, props = to_write_properties(
        _fields(days_off=["2026-07-04", "2026-07-05"], paused_projects=["Reframe paper"]),
        objects=PROJECTS)
    assert props["Days off"] == "2026-07-04, 2026-07-05"
    assert props["Paused projects"] == ["p3"]


def test_unknown_project_name_raises_never_silently_drops():
    with pytest.raises(ValueError):
        to_write_properties(_fields(foreground_projects=["Nonexistent project"]), objects=PROJECTS)


def test_can_build_properties_without_dates_for_a_fix_flow():
    # to_write_properties itself doesn't block (missing_required does) — a fix flow can still
    # assemble props while start/end are being resolved.
    name, props = to_write_properties(_fields(start_date=None, end_date=None), objects=PROJECTS)
    assert "Period start" not in props and "Period end" not in props
    assert props["Foreground projects"] == ["p1", "p2"]


# --- reflect_back (the deterministic confirmation template) ------------------

def test_reflect_back_summary_uses_generated_label_and_lists_fields():
    r = reflect_back(_fields())
    assert r["summary"] == "Week of Jun 29 — jobs foreground"
    assert r["blocking"] == []
    by_key = {i["key"]: i for i in r["items"]}
    assert by_key["foreground"]["display"] == "Academic positions, Industry positions"
    assert by_key["dates"]["display"] == "Mon Jun 29 – Mon Jul 6"
    assert by_key["output_format"]["display"] == "Auto"
    # every item carries an edit hint for the deterministic per-field editor
    assert all("edit" in i for i in r["items"])


def test_reflect_back_defaults_and_empties_read_plainly():
    r = reflect_back(_fields(days_off=[], availability_start=None, availability_end=None,
                             foreground_projects=[]))
    by_key = {i["key"]: i for i in r["items"]}
    assert by_key["days_off"]["display"] == "weekends (default)"
    assert by_key["availability"]["display"] == "none"
    assert by_key["foreground"]["display"] == "—"


def test_reflect_back_surfaces_blocking_missing_dates():
    r = reflect_back(_fields(end_date=None))
    assert r["blocking"] == ["end date"]
    assert {i["key"] for i in r["items"]} >= {"foreground", "dates", "intent"}


def test_paused_and_workday_only_shown_when_present():
    r_plain = reflect_back(_fields())
    assert "paused" not in {i["key"] for i in r_plain["items"]}
    r_full = reflect_back(_fields(paused_projects=["Reframe paper"], workday_end="23:00"))
    keys = {i["key"] for i in r_full["items"]}
    assert "paused" in keys and "workday_end" in keys

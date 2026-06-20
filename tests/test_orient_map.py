"""Tests for orient_map — the deterministic map renderer.

These test the formatting/rendering logic only, with a fake _load() stub.
No live Anytype calls.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import orient_map as om


# ---------------------------------------------------------------------------
# Helpers to build fake Anytype objects
# ---------------------------------------------------------------------------

def _make_obj(name, type_key, oid, props=None):
    prop_list = []
    for key, val in (props or {}).items():
        if isinstance(val, str) and key == "engagement":
            prop_list.append({"key": "engagement",
                               "select": {"name": val}})
        elif isinstance(val, str):
            prop_list.append({"key": key, "text": val})
        elif isinstance(val, list):
            prop_list.append({"key": key, "objects": val})
    return {"id": oid, "name": name, "type": {"key": type_key},
            "properties": prop_list}


def _patch_load(goals, projects, monkeypatch):
    monkeypatch.setattr(om, "_load", lambda: (goals, projects))


# ---------------------------------------------------------------------------
# render_map
# ---------------------------------------------------------------------------

def test_render_map_no_project(monkeypatch):
    _patch_load([], [], monkeypatch)
    out = om.render_map("Nonexistent")
    assert "no project" in out


def test_render_map_no_streams(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    _patch_load([], [proj], monkeypatch)
    out = om.render_map("My Project")
    assert "No work streams yet" in out


def test_render_map_stream_with_context(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    stream = _make_obj("Build the thing", "gsdo_project", "s1",
                       props={"gsdo_parent_project": ["p1"],
                              "gsdo_context": "Working on the core scaffolding."})
    _patch_load([], [proj, stream], monkeypatch)
    out = om.render_map("My Project")
    assert "Build the thing" in out
    assert "Working on the core scaffolding." in out
    # No symbols
    assert "●" not in out
    assert "○" not in out
    assert "✓" not in out


def test_render_map_stream_without_context(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    stream = _make_obj("Vague thread", "gsdo_project", "s1",
                       props={"gsdo_parent_project": ["p1"]})
    _patch_load([], [proj, stream], monkeypatch)
    out = om.render_map("My Project")
    assert "Vague thread" in out
    # No placeholder injected — just the name
    assert "(no description" not in out


def test_render_map_done_stream_in_finished_section(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    active = _make_obj("Active work", "gsdo_project", "s1",
                       props={"gsdo_parent_project": ["p1"],
                              "gsdo_context": "Still in progress."})
    done = _make_obj("Old thing", "gsdo_project", "s2",
                     props={"gsdo_parent_project": ["p1"],
                            "engagement": "Done",
                            "gsdo_context": "Shipped."})
    _patch_load([], [proj, active, done], monkeypatch)
    out = om.render_map("My Project")
    assert "Active work" in out
    assert "Finished:" in out
    assert "Old thing" in out
    # Active stream appears before Finished section
    assert out.index("Active work") < out.index("Finished:")


def test_render_map_goal_header(monkeypatch):
    goal = _make_obj("Material survival", "gsdo_goal", "g1",
                     props={"gsdo_reaching_for_(text)": "Keep the floor: housing, therapy, function."})
    proj = _make_obj("Job Search", "gsdo_project", "p1",
                     props={"gsdo_goal_link": ["g1"]})
    stream = _make_obj("Applications", "gsdo_project", "s1",
                       props={"gsdo_parent_project": ["p1"],
                              "gsdo_context": "Weekly outreach cycle."})
    _patch_load([goal], [proj, stream], monkeypatch)
    out = om.render_map("Job Search")
    assert "Goal: Material survival" in out
    assert "Keep the floor" in out
    assert "Applications" in out


def test_render_map_no_codes_or_labels(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    streams = [
        _make_obj("Stream A", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"],
                         "engagement": "Steady",
                         "gsdo_context": "Chugging along."}),
        _make_obj("Stream B", "gsdo_project", "s2",
                  props={"gsdo_parent_project": ["p1"],
                         "engagement": "Backburner",
                         "gsdo_context": "Parked for now."}),
    ]
    _patch_load([], [proj] + streams, monkeypatch)
    out = om.render_map("My Project")
    # Engagement words must not appear as labels
    assert "Steady" not in out
    assert "Backburner" not in out
    assert "Sprint" not in out
    assert "Hyperfixation" not in out
    # Content does appear
    assert "Stream A" in out
    assert "Stream B" in out
    assert "Chugging along." in out
    assert "Parked for now." in out


# ---------------------------------------------------------------------------
# render_stream
# ---------------------------------------------------------------------------

def test_render_stream_not_found(monkeypatch):
    _patch_load([], [], monkeypatch)
    out = om.render_stream("Ghost")
    assert "no work stream" in out


def test_render_stream_with_context(monkeypatch):
    stream = _make_obj("Build the thing", "gsdo_project", "s1",
                       props={"gsdo_context": "Focused on the map renderer right now."})
    _patch_load([], [stream], monkeypatch)
    out = om.render_stream("Build the thing")
    assert "Build the thing" in out
    assert "Focused on the map renderer right now." in out


def test_render_stream_shows_sub_streams(monkeypatch):
    stream = _make_obj("Parent stream", "gsdo_project", "s1",
                       props={"gsdo_context": "Umbrella."})
    sub = _make_obj("Sub-stream", "gsdo_project", "s2",
                    props={"gsdo_parent_project": ["s1"],
                           "gsdo_context": "The sub-work."})
    _patch_load([], [stream, sub], monkeypatch)
    out = om.render_stream("Parent stream")
    assert "Sub-stream" in out
    assert "The sub-work." in out
    assert "Inside this stream:" in out


def test_render_stream_done_subs_in_finished(monkeypatch):
    stream = _make_obj("Parent stream", "gsdo_project", "s1")
    active_sub = _make_obj("Active sub", "gsdo_project", "s2",
                            props={"gsdo_parent_project": ["s1"]})
    done_sub = _make_obj("Done sub", "gsdo_project", "s3",
                          props={"gsdo_parent_project": ["s1"],
                                 "engagement": "Done"})
    _patch_load([], [stream, active_sub, done_sub], monkeypatch)
    out = om.render_stream("Parent stream")
    assert "Active sub" in out
    assert "Done sub" in out
    assert "Finished:" in out
    assert out.index("Active sub") < out.index("Finished:")


# ---------------------------------------------------------------------------
# missing_descriptions
# ---------------------------------------------------------------------------

def test_missing_descriptions_no_project(monkeypatch):
    _patch_load([], [], monkeypatch)
    assert om.missing_descriptions("Nonexistent") == []


def test_missing_descriptions_all_have_context(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Stream A", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"],
                         "gsdo_context": "Some description."})
    _patch_load([], [proj, s], monkeypatch)
    assert om.missing_descriptions("My Project") == []


def test_missing_descriptions_some_missing(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s1 = _make_obj("Has context", "gsdo_project", "s1",
                   props={"gsdo_parent_project": ["p1"],
                          "gsdo_context": "Described."})
    s2 = _make_obj("No context", "gsdo_project", "s2",
                   props={"gsdo_parent_project": ["p1"]})
    _patch_load([], [proj, s1, s2], monkeypatch)
    missing = om.missing_descriptions("My Project")
    assert missing == ["No context"]


def test_missing_descriptions_excludes_done(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    done = _make_obj("Done stream", "gsdo_project", "s1",
                     props={"gsdo_parent_project": ["p1"],
                            "engagement": "Done"})
    _patch_load([], [proj, done], monkeypatch)
    # Done streams without context are not flagged — they're finished
    assert om.missing_descriptions("My Project") == []

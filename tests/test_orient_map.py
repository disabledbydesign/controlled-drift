"""Tests for orient_map — the deterministic map renderer."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import orient_map as om


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SELECT_KEYS = {"engagement", "gsdo_horizon"}

def _make_obj(name, type_key, oid, props=None):
    prop_list = []
    for key, val in (props or {}).items():
        if key in _SELECT_KEYS and isinstance(val, str):
            prop_list.append({"key": key, "select": {"name": val}})
        elif key in ("gsdo_goal_link", "gsdo_parent_project") and isinstance(val, list):
            prop_list.append({"key": key, "objects": val})
        elif isinstance(val, str):
            prop_list.append({"key": key, "text": val})
    return {"id": oid, "name": name, "type": {"key": type_key},
            "properties": prop_list}

def _patch_load(goals, projects, monkeypatch, tasks=None):
    monkeypatch.setattr(om, "_load", lambda: (goals, projects, tasks or []))

STRUCTURED_CTX = (
    "what it is — takes a messy brain-dump and hands you back a real day\n"
    "next step — build the planning half — pick what matters, fit it to your day"
)


# ---------------------------------------------------------------------------
# _parse_context
# ---------------------------------------------------------------------------

def test_parse_context_structured():
    what_it_is, the_arc, next_step = om._parse_context(STRUCTURED_CTX)
    assert what_it_is == "takes a messy brain-dump and hands you back a real day"
    assert next_step == "build the planning half — pick what matters, fit it to your day"
    assert the_arc is None

def test_parse_context_with_arc():
    ctx = ("what it is — the purpose\n"
           "the arc — where this sits in the bigger picture\n"
           "next step — the move")
    what_it_is, the_arc, next_step = om._parse_context(ctx)
    assert what_it_is == "the purpose"
    assert the_arc == "where this sits in the bigger picture"
    assert next_step == "the move"

def test_parse_context_keeps_internal_dashes():
    """The next-step value contains its own em-dash; only the first split applies."""
    _, _, next_step = om._parse_context(STRUCTURED_CTX)
    assert "—" in next_step

def test_parse_context_empty():
    assert om._parse_context("") == (None, None, None)
    assert om._parse_context(None) == (None, None, None)

def test_parse_context_unstructured():
    assert om._parse_context("just a raw blob") == (None, None, None)

def test_parse_context_partial():
    what_it_is, the_arc, next_step = om._parse_context("what it is — only the purpose")
    assert what_it_is == "only the purpose"
    assert the_arc is None
    assert next_step is None


# ---------------------------------------------------------------------------
# _engagement_label
# ---------------------------------------------------------------------------

def test_label_active():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Steady"})
    assert om._engagement_label(s) == ("●", "ACTIVE")

def test_label_sprint_is_active():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Sprint"})
    assert om._engagement_label(s) == ("●", "ACTIVE")

def test_label_hyperfixation_is_active():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Hyperfixation"})
    assert om._engagement_label(s) == ("●", "ACTIVE")

def test_label_backburner_is_later():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Backburner"})
    assert om._engagement_label(s) == ("○", "later")

def test_label_done():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Done"})
    assert om._engagement_label(s) == ("✓", "done")

def test_label_unset_is_active():
    s = _make_obj("S", "gsdo_project", "1")
    assert om._engagement_label(s) == ("●", "ACTIVE")


# ---------------------------------------------------------------------------
# render_map
# ---------------------------------------------------------------------------

def test_render_map_no_project(monkeypatch):
    _patch_load([], [], monkeypatch)
    assert "no project" in om.render_map("Ghost")

def test_render_map_no_streams(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    _patch_load([], [proj], monkeypatch)
    assert "No work streams yet" in om.render_map("My Project")

def test_render_map_active_stream_full_detail(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Finish the pipeline", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": STRUCTURED_CTX})
    _patch_load([], [proj, s], monkeypatch)
    out = om.render_map("My Project")
    assert "● ACTIVE  Finish the pipeline" in out
    assert "What it is:  takes a messy brain-dump" in out
    assert "Next step:   build the planning half" in out

def test_render_map_active_shows_arc(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    ctx = ("what it is — the purpose\n"
           "the arc — the through-line of where this sits\n"
           "next step — the move")
    s = _make_obj("Stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": ctx})
    _patch_load([], [proj, s], monkeypatch)
    out = om.render_map("My Project")
    assert "The arc:" in out
    assert "the through-line of where this sits" in out
    # order: What it is, then The arc, then Next step
    assert out.index("What it is:") < out.index("The arc:") < out.index("Next step:")

def test_wrap_hanging_indent():
    """A long value wraps with continuation lines aligned under the value column."""
    long_val = "word " * 40
    lines = om._wrap("What it is:", long_val.strip())
    assert len(lines) > 1
    # First line carries the label
    assert lines[0].startswith("   What it is:")
    # Continuation lines are indented to the value column (16 spaces), no label
    assert lines[1].startswith(" " * om._VALUE_COL)
    assert "What it is:" not in lines[1]

def test_render_map_later_stream_what_it_is_only(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Visual layer", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner",
                         "gsdo_context": STRUCTURED_CTX})
    _patch_load([], [proj, s], monkeypatch)
    out = om.render_map("My Project")
    assert "○ later   Visual layer" in out
    assert "What it is:" in out
    # Later streams don't show the next step
    assert "Next step:" not in out

def test_render_map_active_before_later(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    active = _make_obj("Active", "gsdo_project", "s1",
                       props={"gsdo_parent_project": ["p1"]})
    later = _make_obj("Later", "gsdo_project", "s2",
                      props={"gsdo_parent_project": ["p1"], "engagement": "Backburner"})
    _patch_load([], [proj, active, later], monkeypatch)
    out = om.render_map("My Project")
    assert out.index("● ACTIVE") < out.index("○ later")

def test_render_map_done_in_finished_section(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    active = _make_obj("Active", "gsdo_project", "s1",
                       props={"gsdo_parent_project": ["p1"]})
    done = _make_obj("Done thing", "gsdo_project", "s2",
                     props={"gsdo_parent_project": ["p1"], "engagement": "Done"})
    _patch_load([], [proj, active, done], monkeypatch)
    out = om.render_map("My Project")
    assert "Finished:" in out
    assert "Done thing" in out
    assert out.index("● ACTIVE") < out.index("Finished:")

def test_render_map_goal_header(monkeypatch):
    goal = _make_obj("Builder practice", "gsdo_goal", "g1",
                     props={"gsdo_horizon": "Ongoing",
                            "gsdo_reaching_for_(text)": "where building Controlled Drift lives"})
    proj = _make_obj("Build Controlled Drift", "gsdo_project", "p1",
                     props={"gsdo_goal_link": ["g1"]})
    _patch_load([goal], [proj], monkeypatch)
    out = om.render_map("Build Controlled Drift")
    assert "GOAL:  Builder practice  (ongoing)" in out
    assert "where building Controlled Drift lives" in out

def test_render_map_shows_tasks_under_active_stream(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Active stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": STRUCTURED_CTX})
    tasks = [{"id": "t1", "name": "Write the thing", "linked": ["Active stream"], "status": "Active"},
             {"id": "t2", "name": "Review it", "linked": ["Active stream"], "status": "Active"}]
    _patch_load([], [proj, s], monkeypatch, tasks=tasks)
    out = om.render_map("My Project")
    assert "Tasks:" in out
    assert "· Write the thing" in out
    assert "· Review it" in out

def test_render_map_needs_clarifying_flagged(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Active stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": STRUCTURED_CTX})
    tasks = [{"id": "t1", "name": "Fuzzy task", "linked": ["Active stream"], "status": "Needs Clarifying"}]
    _patch_load([], [proj, s], monkeypatch, tasks=tasks)
    out = om.render_map("My Project")
    assert "Fuzzy task  (needs clarifying)" in out

def test_render_map_no_tasks_under_later_stream(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Later stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner"})
    tasks = [{"id": "t1", "name": "Some task", "linked": ["Later stream"], "status": "Active"}]
    _patch_load([], [proj, s], monkeypatch, tasks=tasks)
    out = om.render_map("My Project")
    assert "Some task" not in out

def test_render_map_no_engagement_labels_in_output(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Steady"})
    _patch_load([], [proj, s], monkeypatch)
    out = om.render_map("My Project")
    assert "Steady" not in out
    assert "Sprint" not in out
    assert "Hyperfixation" not in out


# ---------------------------------------------------------------------------
# render_stream
# ---------------------------------------------------------------------------

def test_render_stream_not_found(monkeypatch):
    _patch_load([], [], monkeypatch)
    assert "no work stream" in om.render_stream("Ghost")

def test_render_stream_shows_detail(monkeypatch):
    s = _make_obj("Finish the pipeline", "gsdo_project", "s1",
                  props={"gsdo_context": STRUCTURED_CTX})
    _patch_load([], [s], monkeypatch)
    out = om.render_stream("Finish the pipeline")
    assert "What it is:" in out
    assert "Next step:" in out

def test_render_stream_shows_sub_streams(monkeypatch):
    s = _make_obj("Parent", "gsdo_project", "s1")
    sub = _make_obj("Sub", "gsdo_project", "s2",
                    props={"gsdo_parent_project": ["s1"], "gsdo_context": STRUCTURED_CTX})
    _patch_load([], [s, sub], monkeypatch)
    out = om.render_stream("Parent")
    assert "Inside this stream:" in out
    assert "Sub" in out


# ---------------------------------------------------------------------------
# missing_descriptions
# ---------------------------------------------------------------------------

def test_missing_no_project(monkeypatch):
    _patch_load([], [], monkeypatch)
    assert om.missing_descriptions("Ghost") == []

def test_missing_all_structured(monkeypatch):
    proj = _make_obj("P", "gsdo_project", "p1")
    s = _make_obj("S", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": STRUCTURED_CTX})
    _patch_load([], [proj, s], monkeypatch)
    assert om.missing_descriptions("P") == []

def test_missing_unstructured_context(monkeypatch):
    proj = _make_obj("P", "gsdo_project", "p1")
    s = _make_obj("Needs pass", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": "just a blob"})
    _patch_load([], [proj, s], monkeypatch)
    assert om.missing_descriptions("P") == ["Needs pass"]

def test_missing_no_context(monkeypatch):
    proj = _make_obj("P", "gsdo_project", "p1")
    s = _make_obj("Empty", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"]})
    _patch_load([], [proj, s], monkeypatch)
    assert om.missing_descriptions("P") == ["Empty"]

def test_missing_excludes_done(monkeypatch):
    proj = _make_obj("P", "gsdo_project", "p1")
    done = _make_obj("Done", "gsdo_project", "s1",
                     props={"gsdo_parent_project": ["p1"], "engagement": "Done"})
    _patch_load([], [proj, done], monkeypatch)
    assert om.missing_descriptions("P") == []


# ---------------------------------------------------------------------------
# gap_streams
# ---------------------------------------------------------------------------

def test_gap_streams_returns_ids_and_context(monkeypatch):
    proj = _make_obj("P", "gsdo_project", "p1")
    s = _make_obj("Needs pass", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": "old blob",
                         "engagement": "Steady"})
    _patch_load([], [proj, s], monkeypatch)
    gaps = om.gap_streams("P")
    assert len(gaps) == 1
    assert gaps[0]["id"] == "s1"
    assert gaps[0]["name"] == "Needs pass"
    assert gaps[0]["context"] == "old blob"
    assert gaps[0]["engagement"] == "Steady"

def test_gap_streams_excludes_structured_and_done(monkeypatch):
    proj = _make_obj("P", "gsdo_project", "p1")
    ok = _make_obj("OK", "gsdo_project", "s1",
                   props={"gsdo_parent_project": ["p1"], "gsdo_context": STRUCTURED_CTX})
    done = _make_obj("Done", "gsdo_project", "s2",
                     props={"gsdo_parent_project": ["p1"], "engagement": "Done"})
    _patch_load([], [proj, ok, done], monkeypatch)
    assert om.gap_streams("P") == []

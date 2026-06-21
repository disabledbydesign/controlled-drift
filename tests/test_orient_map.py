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
        elif key == "Stream order":
            prop_list.append({"key": "stream_order", "name": "Stream order", "number": val})
        elif key == "Depends on" and isinstance(val, list):
            prop_list.append({"key": "depends_on", "name": "Depends on", "objects": val})
        elif key == "Arc position rationale" and isinstance(val, str):
            prop_list.append({"key": "arc_rationale", "name": "Arc position rationale", "text": val})
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
    assert om._engagement_label(s) == ("●", "active")

def test_label_sprint_is_active():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Sprint"})
    assert om._engagement_label(s) == ("●", "active")

def test_label_hyperfixation_is_active():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Hyperfixation"})
    assert om._engagement_label(s) == ("●", "active")

def test_label_backburner_is_later():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Backburner"})
    assert om._engagement_label(s) == ("○", "later")

def test_label_done():
    s = _make_obj("S", "gsdo_project", "1", props={"engagement": "Done"})
    assert om._engagement_label(s) == ("✓", "done")

def test_label_unset_is_active():
    s = _make_obj("S", "gsdo_project", "1")
    assert om._engagement_label(s) == ("●", "active")


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

def test_render_map_active_stream_shows_what_it_is(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Finish the pipeline", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": STRUCTURED_CTX})
    _patch_load([], [proj, s], monkeypatch)
    out = om.render_map("My Project")
    assert "● active  Finish the pipeline" in out
    assert "What it is:  takes a messy brain-dump" in out
    # No separate Next step line — the arc's → carries that
    assert "Next step:" not in out

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

def test_streams_ordered_by_stream_order(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    # names are alphabetically reversed vs. desired order, so only Stream order can drive it
    a = _make_obj("Zebra", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "Stream order": 1,
                         "engagement": "Backburner"})
    b = _make_obj("Apple", "gsdo_project", "s2",
                  props={"gsdo_parent_project": ["p1"], "Stream order": 2,
                         "engagement": "Backburner"})
    _patch_load([], [proj, a, b], monkeypatch)
    out = om.render_map("My Project")
    assert out.index("Zebra") < out.index("Apple")   # order 1 before order 2

def test_parallel_streams_get_running_alongside_note(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    a = _make_obj("Stream A", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "Stream order": 3,
                         "engagement": "Backburner"})
    b = _make_obj("Stream B", "gsdo_project", "s2",
                  props={"gsdo_parent_project": ["p1"], "Stream order": 3,
                         "engagement": "Backburner"})
    _patch_load([], [proj, a, b], monkeypatch)
    out = om.render_map("My Project")
    assert "running alongside" in out

def test_sequential_streams_no_alongside_note(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    a = _make_obj("Stream A", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "Stream order": 1,
                         "engagement": "Backburner"})
    b = _make_obj("Stream B", "gsdo_project", "s2",
                  props={"gsdo_parent_project": ["p1"], "Stream order": 2,
                         "engagement": "Backburner"})
    _patch_load([], [proj, a, b], monkeypatch)
    out = om.render_map("My Project")
    assert "running alongside" not in out


# ---------------------------------------------------------------------------
# Dependency ordering (parallel-default)
# ---------------------------------------------------------------------------

def test_dep_ids_empty_when_no_field():
    s = _make_obj("S", "gsdo_project", "1")
    assert om._dep_ids(s) == []

def test_dep_ids_reads_list():
    s = _make_obj("S", "gsdo_project", "1", props={"Depends on": ["a", "b"]})
    assert om._dep_ids(s) == ["a", "b"]

def test_arc_rationale_none_when_absent():
    s = _make_obj("S", "gsdo_project", "1")
    assert om._arc_rationale(s) is None

def test_arc_rationale_reads_text():
    s = _make_obj("S", "gsdo_project", "1",
                  props={"Arc position rationale": "because it unlocks everything else"})
    assert om._arc_rationale(s) == "because it unlocks everything else"

def test_dependency_enforces_order(monkeypatch):
    """Stream B depends on A — A must render before B regardless of name order."""
    proj = _make_obj("My Project", "gsdo_project", "p1")
    a = _make_obj("Zzz First", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner"})
    b = _make_obj("Aaa Second", "gsdo_project", "s2",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner",
                         "Depends on": ["s1"]})
    _patch_load([], [proj, a, b], monkeypatch)
    out = om.render_map("My Project")
    assert out.index("Zzz First") < out.index("Aaa Second")

def test_dependency_two_groups_no_alongside_for_singletons(monkeypatch):
    """With a dep, we get two groups of 1 — no running alongside (groups of 1 don't get it)."""
    proj = _make_obj("My Project", "gsdo_project", "p1")
    a = _make_obj("Stream A", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner"})
    b = _make_obj("Stream B", "gsdo_project", "s2",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner",
                         "Depends on": ["s1"]})
    _patch_load([], [proj, a, b], monkeypatch)
    out = om.render_map("My Project")
    assert out.index("Stream A") < out.index("Stream B")
    assert "running alongside" not in out

def test_parallel_default_no_separator_when_all_parallel(monkeypatch):
    """No deps, no Stream order set — everything parallel by default; no separator needed."""
    proj = _make_obj("My Project", "gsdo_project", "p1")
    a = _make_obj("Alpha", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner"})
    b = _make_obj("Beta", "gsdo_project", "s2",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner"})
    _patch_load([], [proj, a, b], monkeypatch)
    out = om.render_map("My Project")
    assert "Alpha" in out
    assert "Beta" in out
    assert "running alongside" not in out

def test_dep_cycle_doesnt_crash(monkeypatch):
    """Cyclic dependencies are broken gracefully — both streams still render."""
    proj = _make_obj("My Project", "gsdo_project", "p1")
    a = _make_obj("Stream A", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "Depends on": ["s2"],
                         "engagement": "Backburner"})
    b = _make_obj("Stream B", "gsdo_project", "s2",
                  props={"gsdo_parent_project": ["p1"], "Depends on": ["s1"],
                         "engagement": "Backburner"})
    _patch_load([], [proj, a, b], monkeypatch)
    out = om.render_map("My Project")
    assert "Stream A" in out
    assert "Stream B" in out


# ---------------------------------------------------------------------------
# Arc position rationale in render_stream
# ---------------------------------------------------------------------------

def test_render_stream_shows_arc_rationale(monkeypatch):
    s = _make_obj("My Stream", "gsdo_project", "s1",
                  props={"Arc position rationale": "this one must come first because it builds the foundation"})
    _patch_load([], [s], monkeypatch)
    out = om.render_stream("My Stream")
    assert "Why here:" in out
    assert "must come first" in out   # text wraps — check a phrase within one line

def test_render_stream_no_rationale_section_when_absent(monkeypatch):
    s = _make_obj("My Stream", "gsdo_project", "s1")
    _patch_load([], [s], monkeypatch)
    out = om.render_stream("My Stream")
    assert "Why here:" not in out

def test_done_stream_not_shown_on_map(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    active = _make_obj("Active thing", "gsdo_project", "s1",
                       props={"gsdo_parent_project": ["p1"]})
    done = _make_obj("Done thing", "gsdo_project", "s2",
                     props={"gsdo_parent_project": ["p1"], "engagement": "Done"})
    _patch_load([], [proj, active, done], monkeypatch)
    out = om.render_map("My Project")
    assert "Active thing" in out
    assert "Done thing" not in out      # finished work is off the map
    assert "Finished" not in out

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

def _step(tid, name, stream_id, order, done=False):
    return {"id": tid, "name": name, "linked_ids": [stream_id], "status": "Done" if done else "Active",
            "done": done, "order": order}

def test_render_map_arc_under_active_stream(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Active stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "gsdo_context": STRUCTURED_CTX})
    tasks = [_step("t1", "first step", "s1", 1, done=True),
             _step("t2", "second step", "s1", 2, done=False),
             _step("t3", "third step", "s1", 3, done=False)]
    _patch_load([], [proj, s], monkeypatch, tasks=tasks)
    out = om.render_map("My Project")
    assert "The arc:" in out
    assert "✓ first step" in out      # done
    assert "→ second step" in out     # first not-done = where we are
    assert "☐ third step" in out      # future

def test_arc_orders_by_step_order(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Active stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"]})
    # supplied out of order; should render 1,2,3
    tasks = [_step("t3", "third", "s1", 3), _step("t1", "first", "s1", 1), _step("t2", "second", "s1", 2)]
    _patch_load([], [proj, s], monkeypatch, tasks=tasks)
    out = om.render_map("My Project")
    assert out.index("first") < out.index("second") < out.index("third")

def test_arc_only_one_here_marker(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Active stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"]})
    tasks = [_step("t1", "a", "s1", 1, done=False), _step("t2", "b", "s1", 2, done=False)]
    _patch_load([], [proj, s], monkeypatch, tasks=tasks)
    out = om.render_map("My Project")
    assert out.count("→") == 1   # only the first not-done step gets the pointer
    assert "→ a" in out
    assert "☐ b" in out

def test_render_map_no_arc_under_later_stream(monkeypatch):
    proj = _make_obj("My Project", "gsdo_project", "p1")
    s = _make_obj("Later stream", "gsdo_project", "s1",
                  props={"gsdo_parent_project": ["p1"], "engagement": "Backburner"})
    tasks = [_step("t1", "some step", "s1", 1)]
    _patch_load([], [proj, s], monkeypatch, tasks=tasks)
    out = om.render_map("My Project")
    assert "some step" not in out
    assert "The arc:" not in out

def test_id_list_normalizes_strings_and_dicts():
    assert om._id_list(["a", {"id": "b"}, {"no": "id"}, None]) == ["a", "b"]
    assert om._id_list(None) == []

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

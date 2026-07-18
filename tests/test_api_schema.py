"""Unit tests for the `GET /api/schema` payload builder.

Anytype is faked at the `call()` seam, so these test the MERGE — live vocabularies against
UI-authored ordering — rather than the network. The live-space read itself is exercised by
driving the real server (see the live-verify record in the task report).
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import api_schema
import gsdo_anytype as g


# A fake space whose vocabularies deliberately DISAGREE with the UI's preferred order in three
# ways: an option listed but not live (Sprint), an option live but not listed (Surprise), and a
# live order that is not the display order.
FAKE_TAGS = {
    "Goal engagement": ["Steady", "Backburner", "Open", "Sprint"],
    "Goal status": ["Active", "Parked", "Achieved"],
    "Horizon": ["Ongoing", "Chapter", "Milestone", "Short-term", "Medium-term", "Long-term"],
    "Engagement": ["Done", "Backburner", "Open", "Steady", "Needs Clarifying", "Surprise"],
    "Project status": ["Active", "Parked", "Inactive"],
    "Side": ["Work", "Daily life", "Fun / hobby", "Wellbeing"],
    "Task status": ["Ready", "Active", "Blocked", "In Design", "Parked", "Needs Clarifying", "Done"],
    "Access conditions": ["Induces-pain", "Requires-talking-to-a-person", "Can-be-done-lying-down",
                          "Involves-leaving-house", "Requires-deep-thinking", "Involves-bureaucracy"],
    "Interval unit": ["day", "as_needed", "month", "week"],
    "Day of week": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    "Applies when": ["Low energy", "Always"],
    "Strategy status": ["Retired", "Active"],
}


def _fake_call_factory(tags=None, drop=()):
    tags = FAKE_TAGS if tags is None else tags
    names = [n for n in tags if n not in drop]
    ids = {n: f"prop-{i}" for i, n in enumerate(names)}

    def fake_call(method, path, body=None):
        if path.startswith("/spaces/sid/properties?"):
            return 200, {"data": [{"id": ids[n], "name": n, "format": "select"} for n in names]}
        if "/tags" in path:
            pid = path.split("/properties/")[1].split("/tags")[0]
            name = next(n for n, i in ids.items() if i == pid)
            return 200, {"data": [{"name": t} for t in tags[name]]}
        raise AssertionError(f"unexpected call {method} {path}")
    return fake_call


@pytest.fixture
def fake_space(monkeypatch):
    monkeypatch.setattr(g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(api_schema.g, "call", _fake_call_factory())


def test_options_come_from_live_tags_not_a_hardcoded_list(fake_space):
    rel = api_schema.build_schema()["relations"]
    # `Sprint` and `Hyperfixation` are in the UI's preferred order but not live -> dropped.
    assert "Sprint" not in rel["proj"]["options"]
    assert "Hyperfixation" not in rel["proj"]["options"]
    # A live option nobody anticipated is still surfaced, appended after the known ones.
    assert rel["proj"]["options"] == ["Backburner", "Open", "Steady", "Needs Clarifying",
                                      "Done", "Surprise"]


def test_preferred_order_wins_over_anytype_ordering(fake_space):
    rel = api_schema.build_schema()["relations"]
    assert rel["dow"]["options"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    assert rel["unit"]["options"] == ["day", "week", "month", "as_needed"]
    assert rel["strategyStatus"]["options"] == ["Active", "Retired"]


def test_every_relation_key_the_contract_names_is_present(fake_space):
    rel = api_schema.build_schema()["relations"]
    assert set(rel) == {"goalEng", "goalStatus", "horizon", "proj", "projStatus", "side",
                        "taskStatus", "access", "unit", "dow", "strategyState", "strategyStatus"}
    for key, spec in rel.items():
        assert spec["label"] and isinstance(spec["options"], list) and spec["options"]


def test_control_tuples_keep_their_positional_shape(fake_space):
    ctrl = api_schema.build_schema()["controls"]
    # The UI destructures by index; arity and slot meaning are load-bearing.
    assert ctrl["PROJECT"][0] == ["select", "Engagement", "engagement", "proj"]
    assert ctrl["PROJECT"][4] == ["number", "Typical block (min)", "blockMin", None, None]
    assert ctrl["TASK"][3] == ["number", "Duration (min)", "duration"]
    assert ctrl["RECURRING"][0] == ["recur", "Repeats", "count", "unit"]
    assert ctrl["RECURRING"][3] == ["time", "Time of day", "tod"]


def test_every_control_relkey_resolves_to_a_declared_relation(fake_space):
    schema = api_schema.build_schema()
    for level, controls in schema["controls"].items():
        for c in controls:
            if c[0] in ("select", "multi"):
                assert c[3] in schema["relations"], f"{level} {c} has an unknown relation key"


def test_field_semantics_ride_alongside_not_inside_the_tuples(fake_space):
    schema = api_schema.build_schema()
    due = schema["fields"]["TASK"]["due"]
    assert due["property"] == "Due date"
    assert due["hint"] and len(due["hint"].splitlines()) == 1
    assert "deadline" in due["means"].lower()
    # The tuple itself is unchanged — its hint is the UI-authored copy, not the semantics line.
    assert schema["controls"]["TASK"][1][4].startswith("Deadline — drives urgency")


def test_strategy_directive_maps_to_the_live_what_for_property(fake_space):
    # June decided 2026-07-18: no new `Directive` field; the mockup drifted, the data model wins.
    fields = api_schema.build_schema()["fields"]["STRATEGY"]
    assert fields["directive"]["property"] == "What for"


def test_subproject_and_workstream_resolve_project_semantics(fake_space):
    fields = api_schema.build_schema()["fields"]
    assert fields["SUBPROJECT"]["blockMin"]["property"] == "Block chunk min"
    assert fields["WORKSTREAM"]["access"]["property"] == "Access conditions"


def test_a_missing_live_property_raises_rather_than_serving_a_partial_vocabulary(monkeypatch):
    monkeypatch.setattr(g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(api_schema.g, "call", _fake_call_factory(drop=("Side",)))
    with pytest.raises(RuntimeError, match="Side"):
        api_schema.build_schema()

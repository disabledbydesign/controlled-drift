"""Unit tests for the `GET /api/tree` payload builder.

These drive `build_tree_from()` against a hand-built fake space, so what is under test is the
GRAPH ASSEMBLY — levels, link-following, tri-state `vals`, and above all the guarantee that no
object is dropped — not the network. The live-space read is exercised by driving the real server
(see the live-verify record in the task report).

The fake space deliberately contains the shapes that have caused real bugs here: a task whose
project link is dangling, a workstream that inherits its flag from a grandparent, a project
pointing at a goal that no longer exists, and a text property that came back as `""`.
"""
import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import api_tree


def obj(oid, type_name, name, props=()):
    return {"id": oid, "name": name, "type": {"name": type_name, "properties": []},
            "properties": list(props)}


def sel(key, name, value):
    return {"key": key, "name": name, "format": "select",
            "select": {"name": value}}


def text(key, name, value):
    return {"key": key, "name": name, "format": "text", "text": value}


def num(key, name, value):
    return {"key": key, "name": name, "format": "number", "number": value}


def check(key, name, value):
    return {"key": key, "name": name, "format": "checkbox", "checkbox": value}


def multi(key, name, values):
    return {"key": key, "name": name, "format": "multi_select",
            "multi_select": [{"name": v} for v in values]}


def link(key, ids):
    return {"key": key, "name": key, "format": "objects", "objects": list(ids)}


@pytest.fixture
def space():
    return [
        obj("g1", "Goal", "Material survival", [sel("gsdo_goal_status", "Goal status", "Active")]),
        obj("p1", "Project", "Publishing papers", [
            link("gsdo_goal_link", ["g1"]),
            sel("gsdo_engagement", "Engagement", "Open"),
            sel("gsdo_side", "Side", "Work"),
            num("gsdo_block_chunk_min", "Block chunk min", 60),
        ]),
        obj("p2", "Project", "Autograder bias paper", [link("gsdo_parent_project", ["p1"])]),
        obj("ws1", "Project", "Daily plan pipeline", [
            link("gsdo_parent_project", ["p1"]),
            {"key": "is_workstream", "name": "is_workstream", "format": "checkbox",
             "checkbox": True},
        ]),
        # inherits workstream-ness from ws1 without its own checkbox
        obj("ws2", "Project", "Nested thread", [link("gsdo_parent_project", ["ws1"])]),
        obj("t1", "Task", "Consolidate research data", [
            link("linked_projects", ["p2"]),
            sel("gsdo_task_status", "Task status", "Active"),
            multi("gsdo_access_conditions", "Access conditions", ["Requires-deep-thinking"]),
            text("gsdo_context", "Context", ""),
        ]),
        obj("t2", "Task", "Unfiled thing", []),                        # no link at all
        obj("t3", "Task", "Dangling link", [link("linked_projects", ["gone"])]),
        obj("r1", "Recurring", "Do the dishes", [
            link("gsdo_project_link", ["p1"]),
            check("gsdo_active", "Active", False),
        ]),
        obj("r2", "Recurring", "Unfiled routine", []),
        obj("pg", "Project", "No goal here", []),
        obj("pgone", "Project", "Goal was deleted", [link("gsdo_goal_link", ["deleted-goal"])]),
        obj("s1", "Strategy", "When low energy, pick one small win", [
            sel("gsdo_strategy_status", "Strategy status", "Active"),
            text("gsdo_what_for", "What for", "Surface a single small task."),
        ]),
        obj("page1", "Page", "Some note", []),                          # not a GSDO type
    ]


def find(nodes, node_id):
    for n in nodes:
        if n["id"] == node_id:
            return n
        hit = find(n["children"], node_id)
        if hit:
            return hit
    return None


# --- the anti-vanishing guarantee -------------------------------------------------------------

def test_every_gsdo_object_appears_exactly_once(space):
    r = api_tree.build_tree_from(space)
    seen = []

    def walk(nodes):
        for n in nodes:
            seen.append(n["id"])
            walk(n["children"])
    walk(r["nodes"])
    for bucket in r["orphans"].values():
        walk(bucket["nodes"])
    seen += [s["id"] for s in r["strategies"]]
    expected = {o["id"] for o in space if o["type"]["name"] in api_tree.GSDO_TYPES}
    assert sorted(seen) == sorted(expected), "an object was dropped or duplicated"


def test_a_dropped_object_raises_rather_than_silently_shrinking_the_tree(space):
    """The guard is the point: a graph that lost objects must fail loudly, not render short."""
    with pytest.raises(RuntimeError, match="would be dropped"):
        api_tree._check_no_omission(space, {"g1"})


def test_counts_reconcile_with_the_fetched_objects(space):
    c = api_tree.build_tree_from(space)["counts"]
    assert c["objects_fetched"] == len(space)
    assert c["excluded"] == 1                       # the Page
    total = c["in_tree"] + sum(c["in_orphans"].values()) + c["strategies"]
    assert total == sum(c["by_type"].values())


# --- orphan buckets ----------------------------------------------------------------------------

def test_orphan_tasks_include_both_unlinked_and_dangling_links(space):
    o = api_tree.build_tree_from(space)["orphans"]["orphan_tasks"]
    assert {n["id"] for n in o["nodes"]} == {"t2", "t3"}
    assert o["label"] == "⚠ NO PROJECT — orphan tasks"


def test_orphan_recurring_bucket(space):
    o = api_tree.build_tree_from(space)["orphans"]["orphan_recurring"]
    assert [n["id"] for n in o["nodes"]] == ["r2"]


def test_project_whose_goal_no_longer_exists_lands_in_the_goalless_bucket(space):
    """review_surface renders such a project NOWHERE — it has a goal id that matches no goal."""
    ids = {n["id"] for n in api_tree.build_tree_from(space)["orphans"]
           ["projects_without_goal"]["nodes"]}
    assert ids == {"pg", "pgone"}


def test_a_parentless_workstream_gets_its_own_bucket(space):
    space.append(obj("wsX", "Project", "Loose stream", [
        {"key": "is_workstream", "name": "is_workstream", "format": "checkbox", "checkbox": True}]))
    b = api_tree.build_tree_from(space)["orphans"]["parentless_workstreams"]
    assert [n["id"] for n in b["nodes"]] == ["wsX"]


# --- levels ------------------------------------------------------------------------------------

def test_levels_distinguish_project_subproject_and_workstream(space):
    nodes = api_tree.build_tree_from(space)["nodes"]
    assert find(nodes, "p1")["level"] == "PROJECT"
    assert find(nodes, "p2")["level"] == "SUBPROJECT"
    assert find(nodes, "ws1")["level"] == "WORKSTREAM"
    # all three are the Anytype type `Project` — level is the finer UI concept (spec §5)
    assert {find(nodes, i)["type"] for i in ("p1", "p2", "ws1")} == {"Project"}


def test_workstream_flag_is_inherited_down_the_parent_chain(space):
    nodes = api_tree.build_tree_from(space)["nodes"]
    assert find(nodes, "ws2")["level"] == "WORKSTREAM"


def test_workstreams_are_children_not_a_separate_key(space):
    """The fixture nests WORKSTREAM nodes in `children` (app/src/fixtures/tree.ts, 'Build
    Controlled Drift'), unlike review_surface's separate `workstreams` key."""
    p1 = find(api_tree.build_tree_from(space)["nodes"], "p1")
    assert "ws1" in {c["id"] for c in p1["children"]}
    assert "workstreams" not in p1


# --- vals --------------------------------------------------------------------------------------

def test_unset_fields_are_absent_so_inheritance_still_works(space):
    """Tri-state, spec §4: absent = inherit. A default-filled bag destroys inheritance."""
    p2 = find(api_tree.build_tree_from(space)["nodes"], "p2")
    assert "side" not in p2["vals"] and "engagement" not in p2["vals"]


def test_an_explicitly_empty_text_field_is_present_as_empty_string(space):
    t1 = find(api_tree.build_tree_from(space)["nodes"], "t1")
    assert t1["vals"]["context"] == ""


def test_values_keep_their_types(space):
    nodes = api_tree.build_tree_from(space)["nodes"]
    assert find(nodes, "p1")["vals"]["blockMin"] == 60          # number, not "60"
    assert find(nodes, "t1")["vals"]["access"] == ["Requires-deep-thinking"]   # array, not a string
    assert find(nodes, "t1")["vals"]["status"] == "Active"


def test_recurring_active_is_inverted_into_the_ui_paused_key(space):
    r1 = find(api_tree.build_tree_from(space)["nodes"], "r1")
    assert r1["vals"]["paused"] is True and "active" not in r1["vals"]


def test_an_untouched_recurring_reports_no_paused_key_at_all(space):
    r2 = api_tree.build_tree_from(space)["orphans"]["orphan_recurring"]["nodes"][0]
    assert "paused" not in r2["vals"]


def test_strategies_are_flat_and_directive_reads_what_for(space):
    s = api_tree.build_tree_from(space)["strategies"]
    assert [n["level"] for n in s] == ["STRATEGY"] and s[0]["children"] == []
    assert s[0]["vals"]["directive"] == "Surface a single small task."
    assert s[0]["vals"]["status"] == "Active"


def test_node_shape_matches_the_frontend_fixture_contract(space):
    r = api_tree.build_tree_from(space)
    assert set(r["nodes"][0]) == {"id", "level", "type", "title", "vals", "children"}

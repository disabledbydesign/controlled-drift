"""The shared Parent-project inheritance resolver (backend spec §4).

The tri-state is the part worth guarding: a node inherits when it has NO value, but an ancestor
holding an explicit empty is a deliberate "none" that stops the walk — and that answer has to
stay distinguishable from "nothing up this chain had a value at all". Both look like a falsey
value at the call site, so only `Resolved.source` tells them apart.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import resolve


def _chain():
    """workstream -> project -> task-bearing subproject, linked by parent_project_id."""
    return [
        {"id": "ws", "name": "GRA", "parent_project_id": None},
        {"id": "proj", "name": "Metabolism", "parent_project_id": "ws"},
        {"id": "sub", "name": "Session 12", "parent_project_id": "proj"},
    ]


def _hier(nodes):
    return resolve.Hierarchy(nodes), {n["id"]: n for n in nodes}


# --- the tri-state ----------------------------------------------------------

def test_own_value_wins_over_any_ancestor():
    nodes = _chain()
    nodes[0]["side"] = "Work"
    nodes[2]["side"] = "Fun / hobby"
    h, by_id = _hier(nodes)
    r = h.effective(by_id["sub"], "side")
    assert r.value == "Fun / hobby"
    assert r.inherited is False
    assert r.source is by_id["sub"]


def test_absent_value_inherits_from_nearest_ancestor():
    nodes = _chain()
    nodes[0]["side"] = "Work"          # the workstream at the top
    nodes[1]["side"] = "Daily life"    # the nearer ancestor should win
    h, by_id = _hier(nodes)
    r = h.effective(by_id["sub"], "side")
    assert r.value == "Daily life"
    assert r.inherited is True
    assert r.source is by_id["proj"]


def test_ancestor_with_an_EMPTY_value_stops_the_walk():
    """The tri-state's whole point. `proj` says "intentionally none" by holding an empty value;
    the walk must stop there and NOT reach `ws`'s "Work"."""
    nodes = _chain()
    nodes[0]["side"] = "Work"
    nodes[1]["side"] = ""              # present, empty = a deliberate "none"
    h, by_id = _hier(nodes)
    r = h.effective(by_id["sub"], "side")
    assert r.value == ""
    assert r.source is by_id["proj"]   # <- the deliberate "none" is attributable
    assert r.inherited is True


def test_deliberate_none_is_distinguishable_from_nothing_to_inherit():
    """Both resolve to a falsey value, so a caller reading only `.value` cannot tell them apart.
    `.source` is what carries the difference — an ancestor, versus None."""
    stopped_nodes = _chain()
    stopped_nodes[1]["side"] = ""
    h_stopped, by_id_stopped = _hier(stopped_nodes)
    stopped = h_stopped.effective(by_id_stopped["sub"], "side")

    h_empty, by_id_empty = _hier(_chain())        # nobody in the chain has a `side` at all
    nothing = h_empty.effective(by_id_empty["sub"], "side")

    assert not stopped.value and not nothing.value          # indistinguishable by value alone
    assert stopped.source is by_id_stopped["proj"]          # "none, deliberately"
    assert nothing.source is None                           # "nothing to inherit"
    assert stopped != nothing


def test_none_means_absent_and_keeps_walking():
    """Python's stand-in for the TS port's `undefined`: an explicit None is NOT a custom empty."""
    nodes = _chain()
    nodes[0]["side"] = "Work"
    nodes[1]["side"] = None
    h, by_id = _hier(nodes)
    assert h.effective(by_id["sub"], "side").value == "Work"


# --- the include_self distinction ------------------------------------------

def test_include_self_false_answers_what_would_i_inherit():
    """Matches the TS `effective()`, which starts at the parent because its caller renders an
    inheritance hint beside a field the user is editing."""
    nodes = _chain()
    nodes[1]["side"] = "Work"
    nodes[2]["side"] = "Fun / hobby"
    h, by_id = _hier(nodes)
    assert h.effective(by_id["sub"], "side", include_self=False).value == "Work"
    assert h.effective(by_id["sub"], "side").value == "Fun / hobby"


# --- the checkbox rule ------------------------------------------------------

def test_falsey_rule_lets_an_unticked_checkbox_defer_upward():
    """A checkbox cannot store "unset" — Anytype returns False — so False has to mean inherit.
    Under the DEFAULT rule the same data would stop at the first ancestor and answer False."""
    nodes = _chain()
    nodes[0]["is_workstream"] = True
    nodes[1]["is_workstream"] = False
    nodes[2]["is_workstream"] = False
    h, by_id = _hier(nodes)
    assert h.effective(by_id["sub"], "is_workstream",
                       is_absent=resolve.absent_if_falsey).value is True
    assert h.effective(by_id["sub"], "is_workstream").value is False


# --- robustness -------------------------------------------------------------

def test_parent_cycle_terminates():
    """Anytype does not stop June from making two projects each other's parent."""
    nodes = [{"id": "a", "parent_project_id": "b"}, {"id": "b", "parent_project_id": "a"}]
    h, by_id = _hier(nodes)
    assert h.effective(by_id["a"], "side").value is None


def test_parent_outside_the_index_ends_the_walk():
    """A real case: the parent project was filtered out of the active set."""
    nodes = [{"id": "a", "parent_project_id": "gone"}]
    h, by_id = _hier(nodes)
    assert h.effective(by_id["a"], "side").source is None


def test_injected_accessors_walk_a_different_node_shape():
    """orient_map walks raw Anytype objects, not daily_plan's flat dicts."""
    nodes = [{"oid": "top", "up": None, "flag": True},
             {"oid": "kid", "up": "top", "flag": False}]
    h = resolve.Hierarchy(nodes, id_of=lambda n: n["oid"], parent_id_of=lambda n: n["up"],
                          get=lambda n, field: n["flag"])
    kid = nodes[1]
    assert h.effective(kid, "flag", is_absent=resolve.absent_if_falsey).value is True

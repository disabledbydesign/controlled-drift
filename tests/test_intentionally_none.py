"""Spec §4's third state — "set here, and deliberately none" — for fields whose storage cannot
hold an explicit empty.

These are unit tests over the marker logic and the `vals` projection. The live round-trip (write
empty, reload, confirm it did not revert to inheriting) was verified against June's real space on
2026-07-19 with a self-cleaning scratch pair; that is the proof that matters, and these are the
regression net under it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import api_tree
import intentionally_none as inone


# ── the marker vocabulary ────────────────────────────────────────────────────


def test_absent_marker_marks_nothing():
    assert inone.marked_keys(None) == set()
    assert inone.marked_keys([]) == set()


def test_marker_maps_display_names_back_to_val_keys():
    assert inone.marked_keys(["Access conditions"]) == {"access"}
    assert inone.marked_keys(["Access conditions", "Affective"]) == {"access", "affective"}


def test_an_unknown_option_is_ignored_not_raised():
    """A stray value must not take down a whole tree read."""
    assert inone.marked_keys(["Access conditions", "Something else entirely"]) == {"access"}


def test_with_key_adds_and_removes_in_a_stable_order():
    m = inone.with_key(None, "access", True)
    assert m == ["Access conditions"]
    m = inone.with_key(m, "affective", True)
    # Stable order (the spec's, not insertion order) so rewriting the same set does not churn
    # the stored value and log a correction that changed nothing.
    assert m == ["Access conditions", "Affective"]
    assert inone.with_key(m, "access", False) == ["Affective"]
    assert inone.with_key(["Affective"], "affective", False) == []


def test_removing_a_key_that_was_never_marked_is_a_no_op():
    assert inone.with_key(None, "access", False) == []


# ── what counts as "none" ────────────────────────────────────────────────────


def test_empty_values_of_every_shape_count_as_none():
    for v in (None, "", "   ", [], (), set()):
        assert inone.is_empty_value(v) is True, v


def test_real_values_do_not():
    for v in (["Induces-pain"], "some text", 45):
        assert inone.is_empty_value(v) is False, v


def test_zero_is_a_real_number_not_an_absence():
    """`blockMin` 0 is odd but real. Treating it as "none" would silently discard what she set."""
    assert inone.is_empty_value(0) is False


# ── the vals projection: where the tri-state is reassembled ──────────────────


def _obj(props):
    """An Anytype object shaped the way `api_tree._vals` reads it."""
    return {"properties": props}


def _multi(name, values):
    return {"name": name, "format": "multi_select",
            "multi_select": [{"name": v} for v in values]}


def test_a_marked_field_reads_back_as_PRESENT_and_empty():
    """The whole point. Key PRESENT means "set here"; the resolver stops walking at it."""
    o = _obj([_multi(inone.PROPERTY, ["Access conditions"])])
    vals = api_tree._vals(o, "TASK")
    assert "access" in vals, "a marked field must be PRESENT, or it silently inherits again"
    assert vals["access"] == []


def test_an_unmarked_field_stays_absent():
    vals = api_tree._vals(_obj([]), "TASK")
    assert "access" not in vals


def test_a_real_value_wins_over_a_stale_marker():
    """Both set is a contradiction; the real value is the safer answer and must not be hidden."""
    o = _obj([
        _multi("Access conditions", ["Induces-pain"]),
        _multi(inone.PROPERTY, ["Access conditions"]),
    ])
    assert api_tree._vals(o, "TASK")["access"] == ["Induces-pain"]


def test_the_marker_is_never_itself_a_vals_key():
    """It is plumbing. If it leaked into `vals` it would render as a field in the UI."""
    o = _obj([_multi(inone.PROPERTY, ["Access conditions"])])
    assert inone.PROPERTY not in api_tree._vals(o, "TASK")
    assert "intentionallyNone" not in api_tree._vals(o, "TASK")


def test_marking_a_field_the_level_does_not_have_is_ignored():
    """`blockMin` is not on TASK. A marker naming it must not invent the key."""
    o = _obj([_multi(inone.PROPERTY, ["Block chunk min"])])
    assert "blockMin" not in api_tree._vals(o, "TASK")

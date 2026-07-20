"""The Review & Reorganize write layer — backend spec §1, contract §4.

Fully offline: `tests/fake_space.py` stands in at the TRANSPORT seam, so `gsdo_objects`,
`api_write`, `api_tree` and `task_actions` all run their real code — the dedup guard, the
link-kind guard, guard #3 and every read-back are exercised, not stubbed.

The load-bearing tests here are the read-back ones. `test_*_reads_back_*` assert that the GET
happens AFTER the write (following `tests/test_archive_readback.py`'s precedent), and the
`swallow_writes` tests assert that a write Anytype ACCEPTS but does not persist is reported as a
failure — which is the entire point of the discipline and the thing a 200-means-success layer
gets wrong.
"""
import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import fake_space
import api_write
import corrections_log


def _seed():
    return [
        fake_space.obj("goal-1", "Goal", "Get through the move"),
        fake_space.obj("goal-2", "Goal", "Stay well"),
        fake_space.obj("proj-1", "Project", "Household", **{"Goal link": ["goal-1"]}),
        fake_space.obj("proj-2", "Project", "Job search", **{"Goal link": ["goal-1"]}),
        fake_space.obj("ws-1", "Project", "Writing stream",
                       **{"Parent project": ["proj-1"], "Is workstream": True}),
        fake_space.obj("task-1", "Task", "Call the surgeon",
                       **{"Linked Projects": ["proj-1"], "Task status": "Ready"}),
        fake_space.obj("task-2", "Task", "Update the CV", **{"Linked Projects": ["proj-2"]}),
        fake_space.obj("rec-1", "Recurring", "Water the plants",
                       **{"Project link": ["proj-1"], "Interval unit": "as_needed",
                          "Active": True}),
        fake_space.obj("strat-1", "Strategy", "One small win when low energy"),
    ]


@pytest.fixture
def space(monkeypatch, tmp_path):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    return fake_space.install(fake_space.FakeSpace(_seed()), monkeypatch.setattr)


# --- rename -----------------------------------------------------------------

def test_rename_returns_the_refetched_object(space):
    out = api_write.set_title("task-1", "Call the surgeon's office")
    assert out["ok"] is True
    # The contract's point: the client renders "Saved" from `object`, not from `ok`.
    assert out["object"]["title"] == "Call the surgeon's office"
    assert out["object"]["id"] == "task-1"
    assert out["object"]["level"] == "TASK"


def test_rename_reads_back_after_writing(space):
    api_write.set_title("task-1", "Renamed")
    methods = [m for m, _ in space.calls]
    assert "PATCH" in methods
    assert "GET" in methods[methods.index("PATCH"):], "no re-fetch after the write"


def test_rename_fails_when_the_write_does_not_persist(space):
    """Anytype accepts the PATCH and stores nothing. A layer that trusted the 200 would say
    'Saved'; this must raise."""
    space.swallow_writes = True
    with pytest.raises(RuntimeError, match="title did not persist"):
        api_write.set_title("task-1", "Renamed")


def test_rename_refuses_an_empty_title(space):
    with pytest.raises(api_write.WriteRefused):
        api_write.set_title("task-1", "   ")


# --- set a field ------------------------------------------------------------

def test_set_field_returns_the_persisted_value(space):
    out = api_write.set_vals("task-1", {"status": "Done"})
    assert out["object"]["vals"]["status"] == "Done"


def test_set_field_handles_multi_select_as_a_list_and_as_a_joined_string(space):
    api_write.set_vals("task-1", {"access": ["Involves-leaving-house", "Induces-pain"]})
    out = api_write.set_vals("task-2", {"access": "Involves-leaving-house, Induces-pain"})
    assert set(out["object"]["vals"]["access"]) == {"Involves-leaving-house", "Induces-pain"}


def test_set_field_fails_when_the_value_does_not_persist(space):
    space.swallow_writes = True
    with pytest.raises(RuntimeError, match="did not persist"):
        api_write.set_vals("task-1", {"status": "Done"})


def test_set_field_fails_when_the_value_comes_back_absent(space):
    """An ABSENT field is a failure, not a pass — the `if persisted is not None` hole contract §4
    records in `reschedule_task`."""
    space.swallow_writes = True
    with pytest.raises(RuntimeError, match="read back: absent"):
        api_write.set_vals("task-1", {"due": "2026-08-01"})


def test_set_field_compares_dates_parsed_not_as_strings(space):
    """Anytype normalizes a date to an ISO datetime; that is not a mismatch."""
    api_write.set_vals("task-1", {"due": "2026-08-01"})
    space.objects["task-1"]["properties"] = [
        {**p, "date": "2026-08-01T00:00:00Z"} if p["key"] == "due_date" else p
        for p in space.objects["task-1"]["properties"]]
    api_write._verify("task-1", "TASK", {"due": "2026-08-01"})   # must not raise


def test_set_field_refuses_a_key_that_is_not_writable_on_this_level(space):
    with pytest.raises(api_write.WriteRefused, match="not a writable field"):
        api_write.set_vals("goal-1", {"due": "2026-08-01"})


def test_set_field_enforces_guard_3_no_scalar_affect(space):
    """The one mechanical content rule, inherited from `gsdo_objects` — an affect field is free
    text, never a 1-5 number. Nothing here adds a semantic validator beyond it."""
    with pytest.raises(ValueError):
        api_write.set_vals("proj-1", {"affective": 3})


def test_set_field_logs_a_correction_with_who_authored_the_old_value(space, tmp_path):
    corrections_log.log_authorship("task-1", "Task status", "Ready", object_type="Task",
                                   authored_by="llm", surface="capture")
    api_write.set_vals("task-1", {"status": "Done"})
    recs = [r for r in corrections_log.read_records()
            if r.get("object_id") == "task-1" and r.get("kind") == "surface_edit"]
    assert len(recs) == 1
    assert recs[0]["field"] == "Task status"
    assert recs[0]["before"] == "Ready" and recs[0]["after"] == "Done"
    # The load-bearing field: she overwrote a value the MODEL wrote. That is the correction signal.
    assert recs[0]["authored_by"] == "llm"
    assert recs[0]["surface"] == "review_reorganize"


def test_correction_authorship_is_unknown_when_nothing_recorded_it(space):
    """'unknown' is a real, honest value — guessing 'user' would poison the loop."""
    api_write.set_vals("task-1", {"status": "Done"})
    rec = [r for r in corrections_log.read_records() if r.get("kind") == "surface_edit"][0]
    assert rec["authored_by"] == "unknown"


# --- move -------------------------------------------------------------------

def test_move_reparents_and_returns_the_refetched_object(space):
    out = api_write.move_object("task-1", "proj-2")
    assert out["object"]["id"] == "task-1"
    assert space.objects["task-1"]["properties"]
    tree_parent = [p for p in space.objects["task-1"]["properties"]
                   if p["key"] == "linked_projects"][0]
    assert tree_parent["objects"] == ["proj-2"]


def test_move_clears_the_link_it_moved_off_of(space):
    """A Project under a Goal that moves under a Project must lose its Goal link, or the tree
    reads it two ways."""
    api_write.move_object("proj-2", "proj-1")
    props = {p["key"]: p for p in space.objects["proj-2"]["properties"]}
    assert props["gsdo_parent_project"]["objects"] == ["proj-1"]
    assert props["gsdo_goal_link"]["objects"] == []


def test_move_refuses_an_illegal_parent_kind(space):
    with pytest.raises(api_write.WriteRefused, match="cannot sit under"):
        api_write.move_object("task-1", "goal-1")


def test_move_refuses_a_cycle(space):
    with pytest.raises(api_write.WriteRefused, match="own subtree"):
        api_write.move_object("proj-1", "ws-1")


def test_move_refuses_self_parenting(space):
    with pytest.raises(api_write.WriteRefused):
        api_write.move_object("proj-1", "proj-1")


def test_move_fails_when_the_relink_does_not_persist(space):
    space.swallow_writes = True
    with pytest.raises(RuntimeError, match="did not persist"):
        api_write.move_object("task-1", "proj-2")


def test_move_logs_the_parent_change(space):
    api_write.move_object("task-1", "proj-2")
    rec = [r for r in corrections_log.read_records() if r.get("kind") == "surface_move"][0]
    assert rec["field"] == api_write.PARENT_FIELD
    assert rec["before"] == ["proj-1"] and rec["after"] == ["proj-2"]


# --- create -----------------------------------------------------------------

def test_create_returns_the_new_object_with_its_real_id(space):
    out = api_write.create_child("TASK", "Book the movers", parent_id="proj-1")
    assert out["object"]["title"] == "Book the movers"
    assert out["object"]["id"] in space.objects
    assert out["object"]["level"] == "TASK"


def test_create_links_the_new_object_under_its_parent(space):
    out = api_write.create_child("TASK", "Book the movers", parent_id="proj-1")
    props = {p["key"]: p for p in space.objects[out["object"]["id"]]["properties"]}
    assert props["linked_projects"]["objects"] == ["proj-1"]


def test_create_workstream_sets_the_workstream_flag(space):
    out = api_write.create_child("WORKSTREAM", "Grant stream", parent_id="proj-1")
    assert out["object"]["level"] == "WORKSTREAM"


def test_create_refuses_a_duplicate_name_instead_of_silently_no_oping(space):
    """⚠ THE HAZARD (BUILD_DOC §6): `gsdo_objects.create` dedups by name and returns an existing
    id WITHOUT writing properties. Left alone, June would appear to create a task and silently
    edit nothing. It must fail loudly, naming the object that already holds the name."""
    with pytest.raises(api_write.DuplicateName) as e:
        api_write.create_child("TASK", "call the surgeon", parent_id="proj-2")
    assert e.value.existing_id == "task-1"
    assert "already exists" in str(e.value)
    # and nothing was written
    props = {p["key"]: p for p in space.objects["task-1"]["properties"]}
    assert props["linked_projects"]["objects"] == ["proj-1"]


def test_create_refuses_an_empty_title(space):
    """An empty name matches every other empty-named object in the dedup check — the hazard at
    its worst. Contract §4 has the UI posting `title: ''`; that flow has to send a title."""
    with pytest.raises(api_write.WriteRefused, match="needs a title"):
        api_write.create_child("TASK", "", parent_id="proj-1")


def test_create_verification_catches_a_deduped_no_op(space, monkeypatch):
    """The second guard, for the race the name check cannot close: even if `create` returned an
    existing id, the parent link it was asked for would not be there — and read-back raises."""
    monkeypatch.setattr(api_write.gsdo_objects, "create",
                        lambda t, n, body=None, properties=None: "task-2")
    with pytest.raises(RuntimeError, match="did not persist"):
        api_write.create_child("TASK", "Book the movers", parent_id="proj-1")


def test_create_stamps_the_title_as_june_authored(space):
    out = api_write.create_child("TASK", "Book the movers", parent_id="proj-1")
    assert corrections_log.resolve_authored_by(out["object"]["id"],
                                               corrections_log.TITLE_FIELD) == "user"


def test_create_refuses_an_unknown_level(space):
    with pytest.raises(api_write.WriteRefused):
        api_write.create_child("WIDGET", "Nope")


# --- delete -----------------------------------------------------------------

def test_delete_archives_and_confirms_it(space):
    out = api_write.delete_object("task-2")
    assert out == {"ok": True, "id": "task-2", "archived": True}
    assert space.objects["task-2"]["archived"] is True


def test_delete_reads_back_after_the_delete(space):
    api_write.delete_object("task-2")
    methods = [m for m, _ in space.calls]
    assert "GET" in methods[methods.index("DELETE"):], "no re-fetch after the DELETE"


def test_delete_logs_the_removal(space):
    api_write.delete_object("task-2")
    rec = [r for r in corrections_log.read_records() if r.get("kind") == "surface_delete"][0]
    assert rec["before"] == "Update the CV" and rec["after"] is None


# --- recurring active toggle ------------------------------------------------

def test_toggle_recurring_paused_writes_the_inverse_active_flag(space):
    out = api_write.set_recurring_paused("rec-1", True)
    assert out["object"]["vals"]["paused"] is True
    props = {p["key"]: p for p in space.objects["rec-1"]["properties"]}
    assert props["gsdo_active"]["checkbox"] is False


def test_toggle_recurring_paused_fails_when_it_does_not_persist(space):
    space.swallow_writes = True
    with pytest.raises(RuntimeError, match="read-back mismatch"):
        api_write.set_recurring_paused("rec-1", True)


def test_setting_paused_through_the_generic_field_path_routes_to_the_single_writer(space):
    """`Active` has exactly one writer (`recurring_active`), which reads back and logs. A generic
    field write would bypass both."""
    out = api_write.set_vals("rec-1", {"paused": True})
    assert out["object"]["vals"]["paused"] is True
    import reactivation_log
    assert reactivation_log.read_changes()


def test_paused_cannot_be_bundled_with_other_fields(space):
    with pytest.raises(api_write.WriteRefused):
        api_write.set_vals("rec-1", {"paused": True, "context": "x"})


def test_toggle_refuses_a_non_recurring(space):
    with pytest.raises(api_write.WriteRefused):
        api_write.set_recurring_paused("task-1", True)


# --- type conversion (spec §5) ----------------------------------------------

def test_convert_task_to_recurring_keeps_the_same_id(space):
    """The whole reason the in-place path was worth probing for: a new object would have a new
    id, and every inbound reference to the old one would break."""
    out = api_write.convert_type("task-1", "Recurring")
    assert out["ok"] is True
    assert out["object"]["id"] == "task-1"
    assert out["object"]["type"] == "Recurring"


def test_convert_preserves_every_field_including_ones_the_new_type_does_not_show(space):
    """Spec §5: fields not applicable to the new type stay STORED, just unshown. `Task status` is
    not a Recurring field — it must still be on the object afterwards, or converting back would
    silently lose what June entered.

    This is the test that fails if a conversion drops a field.
    """
    api_write.set_vals("task-1", {"context": "spoke to the receptionist", "duration": 25})
    before = api_write._stored_values(api_write._get_object("task-1"))
    assert before["Task status"] == "Ready"

    api_write.convert_type("task-1", "Recurring")

    after = api_write._stored_values(api_write._get_object("task-1"))
    for name, was in before.items():
        if name in ("Linked Projects", "Project link"):
            continue           # the parent relink, the one thing a conversion rewrites
        assert name in after, f"conversion dropped {name!r}"
        assert after[name] == was, f"conversion changed {name!r}"
    assert after["Task status"] == "Ready"
    assert after["Context"] == "spoke to the receptionist"
    assert after["Duration min"] == 25


def test_convert_relinks_the_parent_onto_the_property_the_new_type_uses(space):
    """A Task holds its parent in `Linked Projects`, a Recurring in `Project link`. If the old
    link were left set, the tree would reach the object two ways."""
    api_write.convert_type("task-1", "Recurring")
    obj = api_write._get_object("task-1")
    assert api_write._link_ids(obj, "Project link") == ["proj-1"]
    assert api_write._link_ids(obj, "Linked Projects") == []


def test_convert_round_trip_brings_the_unshown_field_back(space):
    """Spec §5's "reappear if converted back", driven rather than assumed."""
    api_write.convert_type("task-1", "Recurring")
    out = api_write.convert_type("task-1", "Task")
    assert out["object"]["vals"]["status"] == "Ready"
    assert api_write._link_ids(api_write._get_object("task-1"), "Linked Projects") == ["proj-1"]


def test_convert_refuses_a_parent_that_still_has_children(space):
    """The leaf guard. This is the test that fails if a parent is let through."""
    with pytest.raises(api_write.WriteRefused) as e:
        api_write.convert_type("proj-1", "Task")
    assert "Call the surgeon" in str(e.value), "the refusal must name what to move first"
    # and nothing was written — the guard runs before any PATCH
    assert api_write._type_name(api_write._get_object("proj-1")) == "Project"


def test_convert_a_leaf_project_to_a_task_is_allowed(space):
    """The same guard must not refuse a childless project — that is the miscategorised case."""
    out = api_write.convert_type("ws-1", "Task")
    assert out["object"]["type"] == "Task"
    assert out["object"]["level"] == "TASK"


def test_convert_project_to_workstream_sets_the_flag(space):
    out = api_write.convert_type("proj-2", "Workstream")
    assert out["object"]["level"] == "WORKSTREAM"
    assert api_write._checkbox(api_write._get_object("proj-2"), "Is workstream") is True


def test_convert_workstream_back_to_project_clears_the_flag(space):
    api_write.convert_type("ws-1", "Subproject")
    assert api_write._checkbox(api_write._get_object("ws-1"), "Is workstream") is False


def test_convert_refuses_a_parent_that_cannot_host_the_new_type(space):
    """A Project under a Goal cannot become a Recurring — no link expresses it, so converting
    would silently orphan the object. Refuse, naming the fix."""
    # A CHILDLESS project under a goal, so the leaf guard is not what refuses this.
    new_id = api_write.create_child("PROJECT", "Sort out insurance", parent_id="goal-1")["object"]["id"]
    with pytest.raises(api_write.WriteRefused) as e:
        api_write.convert_type(new_id, "Recurring")
    assert "Goal" in str(e.value) and "Move it under a project" in str(e.value)


def test_convert_refuses_subproject_to_project_as_a_move_not_a_conversion(space):
    with pytest.raises(api_write.WriteRefused) as e:
        api_write.convert_type("proj-1", "Subproject")
    assert "sits under another project" in str(e.value)


def test_convert_refuses_an_unknown_target(space):
    with pytest.raises(api_write.WriteRefused):
        api_write.convert_type("task-1", "Sandwich")


def test_convert_fails_when_the_type_write_does_not_persist(space):
    space.swallow_writes = True
    with pytest.raises(RuntimeError, match="type did not persist"):
        api_write.convert_type("task-1", "Recurring")


def test_convert_reads_back_after_writing(space):
    api_write.convert_type("task-1", "Recurring")
    methods = [m for m, _ in space.calls]
    assert "GET" in methods[methods.index("PATCH"):], "no re-fetch after the write"


def test_convert_logs_the_type_change_to_the_corrections_log(space):
    api_write.convert_type("task-1", "Recurring")
    recs = [r for r in corrections_log.read_records() if r.get("kind") == "surface_convert"]
    type_rec = next(r for r in recs if r.get("field") == api_write.TYPE_FIELD)
    assert type_rec["before"] == "Task" and type_rec["after"] == "Recurring"
    assert type_rec["object_id"] == "task-1"
    assert type_rec["surface"] == "review_reorganize"


# --- envelope shape ---------------------------------------------------------

def test_every_mutation_returns_the_same_envelope(space):
    outs = [api_write.set_title("task-1", "A"),
            api_write.set_vals("task-1", {"status": "Done"}),
            api_write.move_object("task-1", "proj-2"),
            api_write.create_child("TASK", "Brand new", parent_id="proj-1"),
            api_write.set_recurring_paused("rec-1", True)]
    for out in outs:
        assert out["ok"] is True
        assert set(out["object"]) == {"id", "level", "type", "title", "vals", "children"}


def test_a_missing_object_is_a_lookup_error_not_a_silent_success(space):
    with pytest.raises(LookupError):
        api_write.set_title("nope-1", "X")


def test_converting_a_task_to_recurring_defaults_the_cadence_to_as_needed(space):
    """A converted Recurring must NOT be able to vanish from her plan.

    `datetime_seam.py` draws a hard line: `as_needed` surfaces when Active is on, but a MISSING
    interval unit returns False unconditionally — "never configured stays off", i.e. permanently
    invisible with nothing on screen to explain why. A Task carries no interval, so a straight
    conversion lands in that second branch.

    June's use case is exactly why it matters: she converts BECAUSE the type was miscategorised.
    Producing a recurring that can never surface is the one outcome the feature must not have.
    `as_needed` is the honest default — a recurring with no schedule, entering the plan when she
    asks for it rather than on a clock.
    """
    api_write.convert_type("task-1", "Recurring")
    stored = api_write._stored_values(api_write._get_object("task-1"))
    assert stored.get(api_write.INTERVAL_UNIT_PROP) == api_write.AS_NEEDED, (
        "a converted recurring with no cadence would be permanently invisible"
    )
    # And it does NOT switch itself on — a conversion must not push work into today's plan.
    assert not stored.get("Active")


def test_conversion_does_not_overwrite_a_cadence_that_is_already_set(space):
    """The default only fills a GAP. An interval already on the object is hers and must survive."""
    # Seeded on the Task directly. A Task cannot be GIVEN an interval through `set_vals` —
    # the property is not valid at that level — but it can CARRY one, which is exactly the
    # state a Recurring→Task conversion leaves behind (spec §5: unshown, still stored).
    fake_space._set_prop(space.objects["task-1"], api_write.INTERVAL_UNIT_PROP, "month")
    api_write.convert_type("task-1", "Recurring")
    after = api_write._stored_values(api_write._get_object("task-1")).get(api_write.INTERVAL_UNIT_PROP)
    assert after == "month"


def test_converting_a_recurring_away_and_back_keeps_her_cadence_not_the_default(space):
    """The round-trip case. Spec §5 keeps unshown fields stored, so a Recurring→Task→Recurring
    trip must come back with what she set, not be flattened by the gap-filler. `rec-1` is
    seeded `as_needed` already, so this pins the mechanism rather than the value: the filler
    must not fire when the round trip carried a unit home."""
    fake_space._set_prop(space.objects["rec-1"], api_write.INTERVAL_UNIT_PROP, "month")
    api_write.convert_type("rec-1", "Task")
    api_write.convert_type("rec-1", "Recurring")
    stored = api_write._stored_values(api_write._get_object("rec-1"))
    assert stored.get(api_write.INTERVAL_UNIT_PROP) == "month"


def test_a_cadence_default_that_does_not_persist_is_reported_not_reported_as_success(space):
    """Cross-family review gate, 2026-07-18. The `as_needed` gap-filler was written and never
    proven. It cannot be covered by the no-field-was-dropped loop, because that loop walks the
    fields the object held BEFORE and the whole point of the default is that this one was absent.

    So a silently-swallowed interval write left `convert_type` returning `{"ok": True}` for a
    Recurring that `datetime_seam` will never surface — the exact outcome the default exists to
    prevent, now arriving with a success message on it. Here Anytype accepts the write and drops
    that one property; the conversion must fail loudly rather than report success.
    """
    real_apply = space._apply

    def drop_the_interval(oid, props):
        real_apply(oid, [p for p in props
                         if p.get("key") != fake_space.prop_meta(
                             api_write.INTERVAL_UNIT_PROP)["key"]])

    space._apply = drop_the_interval
    with pytest.raises(RuntimeError, match="Interval unit"):
        api_write.convert_type("task-1", "Recurring")


# --- the duration cap holds on THIS path too (2026-07-20) --------------------
#
# /api/duration caps a duration at a day, but the object editor writes the SAME 'Duration min'
# field through set_vals, and that path had no range check — so 3045 minutes (the value the
# pre-filled duration box produced live) could reach her real object by the other door. The cap
# is one shared constant now, enforced on both writers.

def test_a_duration_over_a_day_is_refused_on_the_object_path(space):
    with pytest.raises(api_write.WriteRefused, match="24 hours"):
        api_write.set_vals("task-1", {"duration": 3045})


def test_a_refused_duration_does_not_reach_the_object(space):
    try:
        api_write.set_vals("task-1", {"duration": 3045})
    except api_write.WriteRefused:
        pass
    out = api_write.set_vals("task-1", {"duration": 60})   # a normal write still lands
    assert out["object"]["vals"]["duration"] == 60


def test_a_full_day_duration_is_accepted_on_the_object_path(space):
    out = api_write.set_vals("task-1", {"duration": 1440})
    assert out["object"]["vals"]["duration"] == 1440


def test_the_block_length_field_is_capped_too(space):
    # blockMin -> 'Block chunk min' is a duration in minutes as well, and reaches Anytype by the
    # same path; the cap is keyed on the field's meaning, not on which route wrote it.
    with pytest.raises(api_write.WriteRefused, match="24 hours"):
        api_write.set_vals("proj-1", {"blockMin": 3045})

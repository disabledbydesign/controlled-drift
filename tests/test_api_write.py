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

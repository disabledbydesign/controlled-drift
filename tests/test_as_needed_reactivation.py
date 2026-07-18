import datetime as dt, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import datetime_seam as ds


def test_active_as_needed_is_due_every_day():
    item = {"interval_unit": "as_needed", "active": True}
    for d in (dt.date(2026, 7, 17), dt.date(2026, 7, 18), dt.date(2026, 8, 1)):
        due, _ = ds.today_fixed_time(item, d)
        assert due is True


def test_inactive_as_needed_is_never_due():
    due, _ = ds.today_fixed_time({"interval_unit": "as_needed", "active": False}, dt.date(2026, 7, 17))
    assert due is False
    due2, _ = ds.today_fixed_time({"interval_unit": "as_needed"}, dt.date(2026, 7, 17))  # absent = off
    assert due2 is False


def test_scheduled_recurring_ignores_active():
    # a daily task is due regardless of active; active must not perturb scheduled units
    due, _ = ds.today_fixed_time({"interval_unit": "day", "active": False}, dt.date(2026, 7, 17))
    assert due is True


def test_unset_interval_stays_off_even_if_active():
    # never-configured (no unit) is the surface-list's concern, not this feature
    due, _ = ds.today_fixed_time({"interval_unit": None, "active": True}, dt.date(2026, 7, 17))
    assert due is False


def test_set_recurring_active_writes_reads_logs(monkeypatch):
    import recurring_active as ra
    updates, logged = {}, {}
    # the primitive fetches TWICE: BEFORE (off) then AFTER (on) the write
    states = iter([{"name": "Clean the fridge", "properties": [{"name": "Active", "checkbox": False}]},
                   {"name": "Clean the fridge", "properties": [{"name": "Active", "checkbox": True}]}])
    monkeypatch.setattr(ra, "_get_object", lambda rid: next(states))
    monkeypatch.setattr(ra.gsdo_objects, "update",
                        lambda rid, properties: updates.update({rid: properties}))
    monkeypatch.setattr(ra.reactivation_log, "log_change",
                        lambda rid, name, old, new: logged.update({"c": (rid, old, new)}))
    out = ra.set_recurring_active("rid1", True)
    assert updates["rid1"]["Active"] is True
    assert out is True and logged["c"] == ("rid1", False, True)   # old read from pre-state, not None


def test_set_recurring_active_noops_log_on_retap(monkeypatch):
    # re-activating an ALREADY-active task: pre-state == new, so the log no-op fires (a real re-tap)
    import recurring_active as ra
    logged = {}
    on = {"name": "X", "properties": [{"name": "Active", "checkbox": True}]}
    monkeypatch.setattr(ra, "_get_object", lambda rid: on)          # pre == post == on
    monkeypatch.setattr(ra.gsdo_objects, "update", lambda rid, properties: None)
    monkeypatch.setattr(ra.reactivation_log, "log_change",
                        lambda rid, name, old, new: logged.update({"c": True}) if old != new else None)
    ra.set_recurring_active("rid1", True)
    assert logged == {}   # old(True) == new(True): nothing logged — the guard is now REACHABLE


def test_set_recurring_active_raises_on_readback_mismatch(monkeypatch):
    import recurring_active as ra, pytest
    off = {"name": "X", "properties": [{"name": "Active", "checkbox": False}]}
    monkeypatch.setattr(ra, "_get_object", lambda rid: off)         # write True, but read-back stays False
    monkeypatch.setattr(ra.gsdo_objects, "update", lambda rid, properties: None)
    with pytest.raises(RuntimeError):
        ra.set_recurring_active("rid1", True)


def test_is_as_needed_item_reads_the_row_flag(monkeypatch):
    import plan_store
    monkeypatch.setattr(plan_store, "load_plan",
                        lambda: {"items": [{"id": "r1", "recurring": True, "as_needed": True},
                                           {"id": "r2", "recurring": True}]})
    assert plan_store.is_as_needed_item("r1") is True
    assert plan_store.is_as_needed_item("r2") is False   # scheduled recurring, not as-needed


def test_complete_active_as_needed_deactivates_and_checks(monkeypatch):
    import server
    calls = {}
    monkeypatch.setattr(server.plan_store, "is_as_needed_item", lambda tid: tid == "r1")
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.update({"deact": (rid, active)}) or active)
    monkeypatch.setattr(server.plan_store, "mark_item_done",
                        lambda tid: calls.update({"cache_done": tid}) or {"items": []})
    code, body = server.complete_task_row("r1")
    assert code == 200
    assert calls["deact"] == ("r1", False)      # real deactivation
    assert calls["cache_done"] == "r1"          # still shows checked today
    assert body["completed"]["as_needed"] is True


def test_complete_doubly_flagged_row_routes_as_needed_not_recurring(monkeypatch):
    # An active as-needed row IS a Recurring object, so it's flagged both `recurring` and
    # `as_needed` in the cached plan. as_needed must win the routing (real deactivation), never
    # falling through to the recurring branch's cache-only "done for today" flip — that would
    # leave Active untouched and the task would resurface forever despite being "completed".
    import server
    calls = {}
    monkeypatch.setattr(server.plan_store, "is_as_needed_item", lambda tid: True)
    monkeypatch.setattr(server.plan_store, "is_recurring_item", lambda tid: True)  # BOTH True
    monkeypatch.setattr(server.recurring_active, "set_recurring_active",
                        lambda rid, active: calls.update({"deact": (rid, active)}) or active)
    monkeypatch.setattr(server.plan_store, "mark_item_done",
                        lambda tid: calls.update({"cache_done": tid}) or {"items": []})
    code, body = server.complete_task_row("r1")
    assert code == 200
    assert "deact" in calls                     # took the real-deactivation path
    assert body["completed"].get("as_needed") is True
    assert body["completed"].get("recurring") is not True  # did NOT take the cache-only branch


# --- recurring_active.as_needed_objects (shared filter, review fix 2026-07-17) --------------
# Task 6's review found the Focus-Period grounding gap: two independent, drifted copies of this
# filter (one per entry point) let one path silently diverge from another. This is now the single
# shared source both entry points (and the fixed authoring grounding) read from.

def test_as_needed_objects_includes_inactive_ones():
    # The whole point: an OFF as-needed task must still be found (it's the reactivation target).
    import recurring_active as ra
    off = {"id": "r1", "name": "Clean the fridge", "type": {"key": "gsdo_recurring"},
           "properties": [{"key": "interval_unit", "select": {"name": "as_needed"}},
                          {"key": "active", "checkbox": False}]}
    assert ra.as_needed_objects([off]) == [off]


def test_as_needed_objects_excludes_scheduled_recurring_and_other_types():
    import recurring_active as ra
    scheduled = {"id": "r2", "name": "Take meds", "type": {"key": "gsdo_recurring"},
                 "properties": [{"key": "interval_unit", "select": {"name": "day"}}]}
    project = {"id": "p1", "name": "Take meds", "type": {"key": "gsdo_project"}}  # name collision
    assert ra.as_needed_objects([scheduled, project]) == []

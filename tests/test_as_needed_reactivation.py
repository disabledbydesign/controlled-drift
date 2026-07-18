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

import datetime as dt
import plan_generate, daily_plan, recurring_active, completion_log

def _obj(rid, name, fixed=False):
    props = [{"key": "gsdo_project_link", "objects": []},
             {"name": "Fixed appointment", "checkbox": fixed}]
    return {"id": rid, "name": name, "type": {"key": "gsdo_recurring"}, "properties": props}

def _setup(monkeypatch, objs, done_today=()):
    monkeypatch.setattr(recurring_active, "_get_object", lambda rid: objs[rid])
    monkeypatch.setattr(completion_log, "completed_ids_on",
                        lambda date, path=None: set(done_today))
    # synthetic_recurring_row is real; it only needs obj + a name map
    return

def test_missed_nonappointment_recurring_is_reinjected(monkeypatch):
    objs = {"rec-water": _obj("rec-water", "Water plants", fixed=False)}
    _setup(monkeypatch, objs)
    undone = [{"id": "rec-water", "name": "Water plants"}]
    rows = plan_generate._persisted_recurring_rows(undone, tasks=[], projects=[])
    assert [r["id"] for r in rows] == ["rec-water"]
    assert rows[0]["is_recurring"] is True

def test_fixed_appointment_is_not_reinjected(monkeypatch):
    objs = {"rec-therapy": _obj("rec-therapy", "Therapy", fixed=True)}
    _setup(monkeypatch, objs)
    undone = [{"id": "rec-therapy", "name": "Therapy"}]
    rows = plan_generate._persisted_recurring_rows(undone, tasks=[], projects=[])
    assert rows == []

def test_already_in_todays_pool_is_skipped(monkeypatch):
    objs = {"rec-dishes": _obj("rec-dishes", "Dishes", fixed=False)}
    _setup(monkeypatch, objs)
    undone = [{"id": "rec-dishes", "name": "Dishes"}]
    rows = plan_generate._persisted_recurring_rows(
        undone, tasks=[{"id": "rec-dishes"}], projects=[])
    assert rows == []  # daily chore already re-emitted by cadence — don't double it

def test_completed_today_is_skipped(monkeypatch):
    objs = {"rec-water": _obj("rec-water", "Water plants", fixed=False)}
    _setup(monkeypatch, objs, done_today=["rec-water"])
    undone = [{"id": "rec-water", "name": "Water plants"}]
    rows = plan_generate._persisted_recurring_rows(undone, tasks=[], projects=[])
    assert rows == []  # same-day zombie guard

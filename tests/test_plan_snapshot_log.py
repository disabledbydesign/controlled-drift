"""plan_snapshot_log — durable full-plan snapshots for planned-vs-actual."""
import datetime as dt
import plan_snapshot_log


def test_snapshot_stores_full_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    plan = {"blocks": [{"items": [{"task": "Apply to Acme", "time": "09:00 – 10:00"}]}],
            "woven_frame": "survival first"}
    plan_snapshot_log.log_plan_snapshot(plan, source="morning")
    rows = plan_snapshot_log.read_snapshots()
    assert len(rows) == 1
    assert rows[0]["plan"]["woven_frame"] == "survival first"
    assert rows[0]["source"] == "morning"
    assert rows[0]["plan_date"] == dt.date.today().isoformat()


def test_read_snapshots_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    assert plan_snapshot_log.read_snapshots() == []

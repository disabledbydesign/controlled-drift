import os, json, datetime
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def _make_bound_dir(tmp):
    gsdot = {"system": "Controlled Drift", "binds_to": {"projects": [{"id": "x", "name": "X"}]}}
    with open(os.path.join(tmp, ".gsdot"), "w") as f:
        json.dump(gsdot, f)


def test_update_last_sweep_writes_date(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep import update_last_sweep
    update_last_sweep(str(tmp_path))
    with open(os.path.join(str(tmp_path), ".gsdot")) as f:
        data = json.load(f)
    assert data["last_sweep"] == datetime.date.today().isoformat()


def test_update_last_sweep_preserves_binds_to(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep import update_last_sweep
    update_last_sweep(str(tmp_path))
    with open(os.path.join(str(tmp_path), ".gsdot")) as f:
        data = json.load(f)
    assert "binds_to" in data


def test_update_last_sweep_with_items(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep import update_last_sweep
    update_last_sweep(str(tmp_path), items_surfaced=["Task A", "Task B"])
    with open(os.path.join(str(tmp_path), ".gsdot")) as f:
        data = json.load(f)
    assert data["items_surfaced"] == ["Task A", "Task B"]


def test_update_last_sweep_no_binding_raises(tmp_path):
    from sweep import update_last_sweep
    import pytest
    with pytest.raises(FileNotFoundError):
        update_last_sweep(str(tmp_path))


def test_write_log_entry_creates_file(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep_log import write_log_entry, read_log
    write_log_entry(str(tmp_path), "Something went well: CLAUDE.md check caught 2 items.")
    log = read_log(str(tmp_path))
    assert "Something went well" in log
    assert datetime.date.today().isoformat() in log


def test_write_log_entry_appends(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep_log import write_log_entry, read_log
    write_log_entry(str(tmp_path), "First entry.")
    write_log_entry(str(tmp_path), "Second entry.")
    log = read_log(str(tmp_path))
    assert "First entry" in log
    assert "Second entry" in log


def test_read_log_absent_returns_empty(tmp_path):
    from sweep_log import read_log
    assert read_log(str(tmp_path)) == ""

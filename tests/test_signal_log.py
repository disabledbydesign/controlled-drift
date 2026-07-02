"""signal_log — append-only qualitative-signal store. Sandbox-redirected via CD_DATA_DIR."""
import signal_log


def test_log_signal_appends_verbatim(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    signal_log.log_signal("I skipped the plan, needed to finish the sprint",
                          source="checkin_reply",
                          reference={"kind": "project", "id": "p1", "name": "Job Search"})
    rows = signal_log.read_signals()
    assert len(rows) == 1
    assert rows[0]["raw"] == "I skipped the plan, needed to finish the sprint"
    assert rows[0]["source"] == "checkin_reply"
    assert rows[0]["reference"]["name"] == "Job Search"
    assert "ts" in rows[0]


def test_log_signal_appends_multiple(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    signal_log.log_signal("first", source="log_day")
    signal_log.log_signal("second", source="config_correction", reference=None)
    rows = signal_log.read_signals()
    assert [r["raw"] for r in rows] == ["first", "second"]
    assert rows[1]["reference"] is None


def test_read_signals_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    assert signal_log.read_signals() == []

"""focus_period_author — the create + capture-signal seam. gsdo_objects.create is
monkeypatched so no live Anytype write happens."""
import focus_period_author as fpa
import gsdo_objects
import signal_log


def test_author_creates_and_logs_signal(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(gsdo_objects, "create", lambda *a, **k: "fp_new_id")
    oid = fpa.author_focus_period(
        raw_text="jobs foreground this week, caregiving from Saturday",
        name="Week of Jun 30", properties={"Intent": "jobs foreground"})
    assert oid == "fp_new_id"
    rows = signal_log.read_signals()
    assert rows[0]["source"] == "config_authoring"
    assert rows[0]["reference"] == {"kind": "focus_period", "id": "fp_new_id", "name": "Week of Jun 30"}
    assert "caregiving" in rows[0]["raw"]


def test_author_correction_uses_correction_source(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(gsdo_objects, "create", lambda *a, **k: "fp2")
    fpa.author_focus_period("actually paused cuffs this week", "Week of Jun 30",
                            {"Intent": "x"}, source="config_correction")
    assert signal_log.read_signals()[0]["source"] == "config_correction"

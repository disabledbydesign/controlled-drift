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


def test_update_with_no_words_of_hers_writes_no_signal(tmp_path, monkeypatch):
    """signal_log.jsonl holds JUNE'S OWN TYPED WORDS. The per-field editor changes one field with
    no sentence typed at all, so the update arrives with an empty raw_text — and an empty record
    stamped 'config_correction' is a claim she said something when she said nothing. The object
    update itself still happens; only the fabricated signal is withheld. Same rule as commit
    1522ad5, which moved machine-recorded deferrals out of this log."""
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    seen = {}
    monkeypatch.setattr(gsdo_objects, "update",
                        lambda oid, **k: seen.update({"id": oid, "kw": k}))
    fpa.update_focus_period("fp-1", "   ", "Week of Jun 30", {"Workday end": "19:00"})
    assert seen["id"] == "fp-1"          # the field change itself still landed
    assert signal_log.read_signals() == []


def test_update_with_her_words_still_logs_them(tmp_path, monkeypatch):
    """The guard is narrow: a real sentence of hers still reaches the log, verbatim."""
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(gsdo_objects, "update", lambda oid, **k: None)
    fpa.update_focus_period("fp-1", "actually paused cuffs this week", "Week of Jun 30", {})
    rows = signal_log.read_signals()
    assert len(rows) == 1
    assert rows[0]["raw"] == "actually paused cuffs this week"
    assert rows[0]["source"] == "config_correction"


def test_create_with_no_words_of_hers_writes_no_signal(tmp_path, monkeypatch):
    """Same rule on the create route, so the two write paths cannot drift apart."""
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(gsdo_objects, "create", lambda *a, **k: "fp_new_id")
    oid = fpa.author_focus_period("", "Week of Jun 30", {"Intent": "x"})
    assert oid == "fp_new_id"
    assert signal_log.read_signals() == []


def test_authorship_stamps_llm_but_intent_stays_june(tmp_path, monkeypatch):
    """A Focus Period legitimately carries both authorships at once: the model structures the
    period, but `Intent` is June's own words and is never reworded (backend spec §17). Stamping
    Intent 'llm' would record a correction of the model every time she edits her own sentence."""
    import corrections_log
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(gsdo_objects, "create", lambda *a, **k: "fp3")
    fpa.author_focus_period("my week", "Week of Jul 20",
                            {"Intent": "recovery, gentle", "Workday end": "18:00",
                             "Output format": "Auto"})

    stamps = {r["field"]: r for r in corrections_log.read_records()
              if r.get("kind") == "authorship" and r.get("object_id") == "fp3"}
    assert stamps["Intent"]["authored_by"] == "user"
    assert stamps["Workday end"]["authored_by"] == "llm"
    assert stamps["Output format"]["authored_by"] == "llm"
    assert stamps["__title__"]["authored_by"] == "llm"

    assert corrections_log.resolve_authored_by("fp3", "Intent") == "user"
    assert corrections_log.resolve_authored_by("fp3", "Workday end") == "llm"


_FAKE_OBJS = [
    {"type": {"key": "gsdo_project"}, "id": "id-job", "name": "Job Search"},
    {"type": {"key": "gsdo_project"}, "id": "id-cuffs", "name": "Leather cuffs"},
    {"type": {"key": "gsdo_goal"}, "id": "id-goal", "name": "Job Search"},  # a goal named the same — ignored
]


def test_resolve_project_names_to_ids():
    assert fpa.resolve_project_names_to_ids(["Job Search"], objects=_FAKE_OBJS) == ["id-job"]
    assert fpa.resolve_project_names_to_ids(["Leather cuffs", "Job Search"], objects=_FAKE_OBJS) \
        == ["id-cuffs", "id-job"]


def test_resolve_raises_on_unknown_project():
    import pytest
    with pytest.raises(ValueError):
        fpa.resolve_project_names_to_ids(["Nonexistent"], objects=_FAKE_OBJS)

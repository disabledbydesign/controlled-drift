"""Pure-logic tests for focus_period.py — no Anytype, no clock.

Deterministic resolution of a Focus Period: parse, load-active, is-day-off,
availability window, output-shape. Fixture dicts mimic the Anytype object shape
(properties = list of {"name", <value-by-format>}).
"""
import datetime as dt
import focus_period as fp


def _obj(props, oid="fp1", name="Week of Jun 30", tkey="focus_period"):
    return {"id": oid, "name": name, "type": {"key": tkey}, "properties": props}


# --- parse ------------------------------------------------------------------

def test_parse_reads_dates_intent_and_select():
    o = _obj([
        {"name": "Period start", "date": "2026-06-30"},
        {"name": "Period end", "date": "2026-07-06"},
        {"name": "Intent", "text": "jobs foreground, survival first"},
        {"name": "Availability start", "date": "2026-07-05"},
        {"name": "Availability end", "date": "2026-07-09"},
        {"name": "Availability note", "text": "caregiving — fragmented"},
        {"name": "Output format", "select": {"name": "Priority list"}},
        {"name": "Workday end", "text": "22:00"},
    ])
    p = fp.parse_focus_period(o)
    assert p["start"] == dt.date(2026, 6, 30)
    assert p["end"] == dt.date(2026, 7, 6)
    assert p["intent"].startswith("jobs foreground")
    assert p["availability_start"] == dt.date(2026, 7, 5)
    assert p["availability_note"] == "caregiving — fragmented"
    assert p["output_format"] == "Priority list"
    assert p["workday_end"] == "22:00"


def test_parse_defaults_output_format_to_auto():
    assert fp.parse_focus_period(_obj([]))["output_format"] == "Auto"


def test_parse_date_list_accepts_json_and_csv():
    p_json = fp.parse_focus_period(_obj([{"name": "Days off", "text": '["2026-07-03"]'}]))
    assert p_json["days_off"] == ["2026-07-03"]
    assert p_json["days_off_error"] is False
    p_csv = fp.parse_focus_period(_obj([{"name": "Days on", "text": "2026-07-04, 2026-07-05"}]))
    assert p_csv["days_on"] == ["2026-07-04", "2026-07-05"]


def test_parse_date_list_flags_malformed_not_silent():
    p = fp.parse_focus_period(_obj([{"name": "Days off", "text": "not-a-date"}]))
    assert p["days_off"] == []
    assert p["days_off_error"] is True   # surfaced to June, never a silent drop


def test_parse_keeps_object_id_name_pairs():
    o = _obj([{"name": "Foreground projects",
               "objects": [{"id": "p1", "name": "Job Search"}]}])
    assert fp.parse_focus_period(o)["foreground_pairs"] == [("p1", "Job Search")]


def test_parse_hhmm():
    assert fp.parse_hhmm("22:00") == (22, 0)
    assert fp.parse_hhmm("9:30") == (9, 30)
    assert fp.parse_hhmm("nonsense") == (18, 0)   # safe default end-of-day
    assert fp.parse_hhmm("25:00") == (18, 0)


# --- load active period -----------------------------------------------------

def test_load_active_picks_containing_period():
    objs = [_obj([{"name": "Period start", "date": "2026-06-01"},
                  {"name": "Period end", "date": "2026-06-10"}], oid="old"),
            _obj([{"name": "Period start", "date": "2026-06-28"},
                  {"name": "Period end", "date": "2026-07-06"}], oid="cur")]
    active = fp.load_active_focus_period(objs, today=dt.date(2026, 7, 2))
    assert active is not None and active["id"] == "cur"


def test_load_active_latest_start_wins_on_overlap():
    objs = [_obj([{"name": "Period start", "date": "2026-06-28"},
                  {"name": "Period end", "date": "2026-07-10"}], oid="a"),
            _obj([{"name": "Period start", "date": "2026-07-01"},
                  {"name": "Period end", "date": "2026-07-10"}], oid="b")]
    assert fp.load_active_focus_period(objs, today=dt.date(2026, 7, 2))["id"] == "b"


def test_load_active_none_when_no_period_covers_today():
    objs = [_obj([{"name": "Period start", "date": "2026-06-01"},
                  {"name": "Period end", "date": "2026-06-10"}])]
    assert fp.load_active_focus_period(objs, today=dt.date(2026, 7, 2)) is None


def test_load_active_ignores_non_focus_period_objects():
    objs = [_obj([{"name": "Period start", "date": "2026-06-28"},
                  {"name": "Period end", "date": "2026-07-06"}], tkey="gsdo_project")]
    assert fp.load_active_focus_period(objs, today=dt.date(2026, 7, 2)) is None


# --- day-off ----------------------------------------------------------------

def test_is_day_off_weekly_default():
    # 2026-07-04 is a Saturday; 2026-07-02 is a Thursday
    assert fp.is_day_off(None, ["Sat", "Sun"], dt.date(2026, 7, 4)) is True
    assert fp.is_day_off(None, ["Sat", "Sun"], dt.date(2026, 7, 2)) is False


def test_days_on_overrides_weekend_off():
    period = {"days_off": [], "days_on": ["2026-07-04"]}
    assert fp.is_day_off(period, ["Sat", "Sun"], dt.date(2026, 7, 4)) is False


def test_days_off_overrides_weekday_on():
    period = {"days_off": ["2026-07-02"], "days_on": []}
    assert fp.is_day_off(period, ["Sat", "Sun"], dt.date(2026, 7, 2)) is True


def test_load_day_off_defaults_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    assert fp.load_day_off_defaults() == ["Sat", "Sun"]


def test_load_day_off_defaults_reads_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text('{"weekly_off": ["Sun"]}')
    assert fp.load_day_off_defaults() == ["Sun"]


# --- availability + output shape --------------------------------------------

def test_in_availability_window():
    period = {"availability_start": dt.date(2026, 7, 4),
              "availability_end": dt.date(2026, 7, 8)}
    assert fp.in_availability_window(period, dt.date(2026, 7, 5)) is True
    assert fp.in_availability_window(period, dt.date(2026, 7, 2)) is False
    assert fp.in_availability_window(None, dt.date(2026, 7, 5)) is False


def test_resolve_output_shape_explicit_wins():
    assert fp.resolve_output_shape({"output_format": "Priority list"}, False) == "priority"
    assert fp.resolve_output_shape({"output_format": "Clock schedule"}, True) == "clock"


def test_resolve_output_shape_auto_from_window_only():
    p = {"output_format": "Auto"}
    assert fp.resolve_output_shape(p, True) == "priority"
    assert fp.resolve_output_shape(p, False) == "clock"
    assert fp.resolve_output_shape(None, False) == "clock"

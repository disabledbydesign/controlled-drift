# tests/test_scheduler.py
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from scheduler import schedule

def test_places_items_back_to_back():
    start = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "A", "duration_min": 30}, {"name": "B", "duration_min": 45}]
    out = schedule(items, start)
    assert out[0]["start_time"] == dt.datetime(2026, 6, 17, 9, 0)
    assert out[0]["end_time"]   == dt.datetime(2026, 6, 17, 9, 30)
    assert out[1]["start_time"] == dt.datetime(2026, 6, 17, 9, 30)
    assert out[1]["end_time"]   == dt.datetime(2026, 6, 17, 10, 15)

def test_empty_list_returns_empty():
    assert schedule([], dt.datetime(2026, 6, 17, 9, 0)) == []

def test_missing_duration_defaults_to_30():
    out = schedule([{"name": "no-dur"}], dt.datetime(2026, 6, 17, 9, 0))
    assert out[0]["end_time"] == dt.datetime(2026, 6, 17, 9, 30)

def test_preserves_item_fields():
    out = schedule([{"name": "A", "duration_min": 10, "project": "X"}], dt.datetime(2026, 6, 17, 9, 0))
    assert out[0]["name"] == "A" and out[0]["project"] == "X"

def test_fixed_anchor_placed_at_its_time():
    start = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "therapy", "duration_min": 50, "fixed_time": dt.datetime(2026, 6, 17, 14, 0)}]
    out = schedule(items, start)
    assert out[0]["start_time"] == dt.datetime(2026, 6, 17, 14, 0)
    assert out[0]["end_time"]   == dt.datetime(2026, 6, 17, 14, 50)

def test_flexible_flows_around_anchor():
    start = dt.datetime(2026, 6, 17, 13, 0)
    items = [
        {"name": "A", "duration_min": 30},                                              # fits before
        {"name": "therapy", "duration_min": 50, "fixed_time": dt.datetime(2026, 6, 17, 14, 0)},
        {"name": "B", "duration_min": 40},                                              # too big for the gap → after
    ]
    out = schedule(items, start)
    names = [o["name"] for o in out]
    assert names == ["A", "therapy", "B"]
    assert out[0]["start_time"] == dt.datetime(2026, 6, 17, 13, 0)   # A at 13:00
    assert out[1]["start_time"] == dt.datetime(2026, 6, 17, 14, 0)   # anchor holds its time
    assert out[2]["start_time"] == dt.datetime(2026, 6, 17, 14, 50)  # B after the anchor

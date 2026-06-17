# tests/test_neglect.py
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from neglect import find_neglected

def test_never_surfaced_is_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": None}]
    assert [i["name"] for i in find_neglected(items, now, days=3)] == ["X"]

def test_recently_surfaced_is_not_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": dt.datetime(2026, 6, 16, 9, 0)}]
    assert find_neglected(items, now, days=3) == []

def test_stale_beyond_window_is_neglected():
    now = dt.datetime(2026, 6, 17, 9, 0)
    items = [{"name": "X", "last_surfaced": dt.datetime(2026, 6, 10, 9, 0)}]
    assert [i["name"] for i in find_neglected(items, now, days=3)] == ["X"]

"""Tests for session_store — the working-memory log beneath capture/weed + negotiate.

All paths redirect into tmp_path via the deterministic CD_CONFIG_DIR env mechanism, so tests
never touch June's real ~/.controlled-drift/ data (the conftest tripwire enforces this too).
"""
import sys, os, json, threading, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest
import session_store as ss


def _redirect(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))


# --- basics -----------------------------------------------------------------

def test_load_log_empty_when_absent(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    log = ss.load_log()
    assert log["entries"] == []


def test_append_stamps_ts_and_stream(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    rec = ss.append_entry("capture", {"intent": "capture", "raw_input": "call the bank"})
    assert rec["stream"] == "capture" and "ts" in rec
    assert ss.recent_entries("capture")[0]["raw_input"] == "call the bank"


def test_append_is_atomic_no_tmp_left(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    ss.append_entry("capture", {"intent": "capture", "raw_input": "a"})
    ss.append_entry("capture", {"intent": "capture", "raw_input": "b"})
    assert not os.path.exists(str(tmp_path / "session_log.json.tmp"))
    assert len(ss.load_log()["entries"]) == 2


def test_load_survives_corrupt_json(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    with open(str(tmp_path / "session_log.json"), "w") as f:
        f.write("{not json")
    assert ss.load_log()["entries"] == []


def test_unknown_stream_rejected(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        ss.append_entry("nope", {"intent": "capture"})
    with pytest.raises(ValueError):
        ss.recent_entries("nope")


# --- the two streams stay separate (June's call) ----------------------------

def test_streams_do_not_mix(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    ss.append_entry("capture", {"intent": "capture", "raw_input": "cap"})
    ss.append_entry("negotiate", {"intent": "negotiate", "raw_input": "neg"})
    cap = ss.recent_entries("capture")
    neg = ss.recent_entries("negotiate")
    assert [e["raw_input"] for e in cap] == ["cap"]
    assert [e["raw_input"] for e in neg] == ["neg"]


# --- the 8h window drops a prior day ----------------------------------------

def test_window_drops_old_entries(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    old = (dt.datetime.now() - dt.timedelta(hours=30)).isoformat()
    ss.append_entry("capture", {"intent": "capture", "raw_input": "yesterday", "ts": old})
    ss.append_entry("capture", {"intent": "capture", "raw_input": "today"})
    recent = ss.recent_entries("capture", hours=8)
    assert [e["raw_input"] for e in recent] == ["today"]


def test_unparseable_ts_is_kept(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    ss.append_entry("capture", {"intent": "capture", "raw_input": "weird", "ts": "not-a-date"})
    # Better to keep a stray entry than silently lose data.
    assert any(e["raw_input"] == "weird" for e in ss.recent_entries("capture"))


# --- token budget truncates oldest, chronological order preserved -----------

def test_token_budget_truncates_oldest(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    for i in range(20):
        ss.append_entry("capture", {"intent": "capture", "raw_input": f"entry number {i} " * 10})
    kept = ss.recent_entries("capture", token_budget=200)
    # Something dropped, and what's kept is the NEWEST, in chronological order.
    assert 0 < len(kept) < 20
    nums = [e["raw_input"] for e in kept]
    assert nums == sorted(nums, key=lambda s: int(s.split()[2]))  # chronological
    assert "19" in kept[-1]["raw_input"]                          # newest retained


def test_budget_keeps_at_least_one_oversized_entry(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    ss.append_entry("capture", {"intent": "capture", "raw_input": "x" * 4000})
    # Even a single entry over the whole budget is kept — never return empty when data exists.
    assert len(ss.recent_entries("capture", token_budget=100)) == 1


# --- undo is conversational; failure is health data -------------------------

def test_mark_undo_appends_and_is_visible(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    ss.mark_undo("capture", "task-123", detail="removed Call bank")
    recent = ss.recent_entries("capture")
    assert recent[-1]["intent"] == "undo" and recent[-1]["target_id"] == "task-123"


def test_log_failure_excluded_from_conversation_but_readable(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    ss.append_entry("capture", {"intent": "capture", "raw_input": "real turn"})
    ss.log_failure("capture", "context_window_exceeded", {"prompt_chars": 99999})
    # Conversation history excludes failures by default...
    conv = ss.recent_entries("capture")
    assert all(e.get("intent") != "failure" for e in conv)
    assert any(e["raw_input"] == "real turn" for e in conv)
    # ...but include_failures surfaces them, and failures() is the health view.
    assert any(e.get("intent") == "failure" for e in ss.recent_entries("capture", include_failures=True))
    fails = ss.failures("capture")
    assert len(fails) == 1 and fails[0]["kind"] == "context_window_exceeded"


def test_concurrent_appends_lose_nothing(tmp_path, monkeypatch):
    # REGRESSION (cross-review catch): the server is multi-threaded and append is a
    # read-modify-write. Without the write lock, concurrent appends silently drop entries.
    _redirect(tmp_path, monkeypatch)

    def worker(n):
        ss.append_entry("capture", {"intent": "capture", "raw_input": f"turn {n}"})

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    inputs = {e["raw_input"] for e in ss.load_log()["entries"]}
    assert inputs == {f"turn {i}" for i in range(40)}    # every append survived


def test_failures_across_streams_and_window(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    old = (dt.datetime.now() - dt.timedelta(hours=50)).isoformat()
    ss.log_failure("capture", "create_failed", {"err": "x"})
    ss.append_entry("negotiate", {"intent": "failure", "kind": "parse_failed",
                                  "detail": {}, "ts": old})
    assert len(ss.failures()) == 2            # both streams, all time
    assert len(ss.failures(hours=8)) == 1     # window drops the old one
    assert len(ss.failures("negotiate")) == 1

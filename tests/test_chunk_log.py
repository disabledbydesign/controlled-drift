"""Tests for the daily, resetting chunk log — "worked on this project today".

The session sandbox in conftest.py redirects CD_DATA_DIR away from real data, so the
default-path calls here are safe. Several tests also pass an explicit `path=` for clarity
and to guarantee a pristine file per case.
"""
import datetime as dt

import chunk_log


def test_log_two_unlog_one_nets_to_remaining(tmp_path):
    """The plan's named acceptance test: chunk a + b, un-chunk a → only b remains."""
    p = tmp_path / "chunk_log.jsonl"
    chunk_log.log_chunk("a", path=str(p))
    chunk_log.log_chunk("b", path=str(p))
    chunk_log.unlog_chunk("a", path=str(p))
    assert chunk_log.chunked_today_ids(path=str(p)) == {"b"}


def test_unchunk_then_rechunk_nets_back_to_present(tmp_path):
    p = tmp_path / "chunk_log.jsonl"
    chunk_log.log_chunk("a", path=str(p))
    chunk_log.unlog_chunk("a", path=str(p))
    chunk_log.log_chunk("a", path=str(p))
    assert chunk_log.chunked_today_ids(path=str(p)) == {"a"}


def test_chunk_for_a_different_date_is_not_in_todays_set(tmp_path):
    p = tmp_path / "chunk_log.jsonl"
    yesterday = dt.date.today() - dt.timedelta(days=1)
    chunk_log.log_chunk("a", date=yesterday, path=str(p))
    chunk_log.log_chunk("b", path=str(p))  # today
    assert chunk_log.chunked_today_ids(path=str(p)) == {"b"}
    # And querying that other date returns only its own chunk.
    assert chunk_log.chunked_today_ids(date=yesterday, path=str(p)) == {"a"}


def test_missing_log_file_returns_empty_set(tmp_path):
    p = tmp_path / "does_not_exist.jsonl"
    assert chunk_log.chunked_today_ids(path=str(p)) == set()
    assert chunk_log.read_events(path=str(p)) == []


def test_default_path_uses_sandbox_and_records_full_ts(cd_sandbox):
    """Default-path (no explicit path) resolves through cd_paths into the test sandbox.
    Also asserts the record shape: full ts, date, event, project_id."""
    chunk_log.log_chunk("proj-1")
    assert chunk_log.chunked_today_ids() == {"proj-1"}
    events = chunk_log.read_events()
    assert len(events) == 1
    rec = events[0]
    assert rec["event"] == "chunked"
    assert rec["project_id"] == "proj-1"
    assert rec["date"] == dt.date.today().isoformat()
    # Full timestamp kept (mirrors completion_log): starts with the date, has a T + time.
    assert rec["ts"].startswith(dt.date.today().isoformat())
    assert "T" in rec["ts"]


def test_iso_string_date_is_accepted(tmp_path):
    """A date passed as an ISO string normalizes the same as a date object."""
    p = tmp_path / "chunk_log.jsonl"
    d = dt.date.today() - dt.timedelta(days=2)
    chunk_log.log_chunk("a", date=d.isoformat(), path=str(p))
    assert chunk_log.chunked_today_ids(date=d, path=str(p)) == {"a"}
    assert chunk_log.chunked_today_ids(date=d.isoformat(), path=str(p)) == {"a"}

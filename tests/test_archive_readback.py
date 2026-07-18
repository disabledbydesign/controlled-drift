# tests/test_archive_readback.py — archive_object must PROVE the removal, not trust the DELETE.
#
# The undo of a capture is the one write that used to report success on an HTTP status code
# alone ("could not archive... : {st}" and then a hardcoded archived: True). These tests fail if
# the helper ever stops re-fetching: the fake transport records every call, and the success cases
# assert the GET happened after the DELETE.
#
# Fully offline — the Anytype transport (`call`) and the space-id lookup are both stubbed.
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import task_actions as ta


def _transport(monkeypatch, get_response):
    """Stub task_actions' Anytype transport. DELETE always succeeds; GET returns get_response
    (a (status, body) tuple). Returns the recorded call log."""
    calls = []
    monkeypatch.setattr(ta.g, "get_space_id", lambda: "space-test")

    def fake_call(method, path, body=None):
        calls.append((method, path))
        if method == "DELETE":
            return 204, ""
        if method == "GET":
            return get_response
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(ta, "call", fake_call)
    return calls


def test_archive_confirmed_when_object_is_gone(monkeypatch):
    """Hard-removed / no longer readable — a 404 on read-back IS the proof."""
    calls = _transport(monkeypatch, (404, {"error": "not found"}))
    out = ta.archive_object("obj-1")
    assert out == {"id": "obj-1", "archived": True}
    assert [m for m, _ in calls] == ["DELETE", "GET"]      # it re-fetched — this is the point


def test_archive_confirmed_by_archived_marker(monkeypatch):
    """DELETE archives rather than hard-deletes, so the object may still read back — then the
    proof is its own archived marker, not the API's acknowledgment."""
    calls = _transport(monkeypatch, (200, {"object": {"id": "obj-1", "name": "Call surgeon",
                                                      "archived": True}}))
    out = ta.archive_object("obj-1")
    assert out == {"id": "obj-1", "archived": True}
    assert calls[1][1] == "/spaces/space-test/objects/obj-1"


def test_archive_raises_when_object_reads_back_live(monkeypatch):
    """The failure the discipline exists to catch: DELETE accepted, object still there."""
    _transport(monkeypatch, (200, {"object": {"id": "obj-1", "name": "Call surgeon",
                                              "archived": False}}))
    with pytest.raises(RuntimeError) as e:
        ta.archive_object("obj-1")
    assert "unarchived" in str(e.value)


def test_archive_raises_when_no_archived_marker_at_all(monkeypatch):
    """An object with no archived marker is UNDETERMINED, not confirmed — never report success
    on state we could not read."""
    _transport(monkeypatch, (200, {"object": {"id": "obj-1", "name": "Call surgeon"}}))
    with pytest.raises(RuntimeError):
        ta.archive_object("obj-1")


def test_archive_raises_when_readback_unreadable(monkeypatch):
    """A read-back that errors is not a pass."""
    _transport(monkeypatch, (500, "boom"))
    with pytest.raises(RuntimeError) as e:
        ta.archive_object("obj-1")
    assert "could not confirm archive" in str(e.value)


def test_archive_raises_when_delete_rejected(monkeypatch):
    """Pre-existing behavior preserved: a rejected DELETE still raises, and never re-fetches."""
    calls = []
    monkeypatch.setattr(ta.g, "get_space_id", lambda: "space-test")
    monkeypatch.setattr(ta, "call",
                        lambda m, p, b=None: (calls.append(m), (403, "nope"))[1])
    with pytest.raises(RuntimeError):
        ta.archive_object("obj-1")
    assert calls == ["DELETE"]


def test_archive_polls_through_an_async_lag(monkeypatch):
    """Anytype archives ASYNCHRONOUSLY — the first re-fetch can still read `archived: False`.

    Confirmed live 2026-07-18 by the type-conversion probe: the first read immediately after a
    successful DELETE returned False, a moment later True. A single immediate read-back reported
    FAILURE for an archive that had succeeded. This pins the polling so that regression cannot
    come back.
    """
    import task_actions

    calls = []
    state = {"reads": 0}

    def fake_call(method, path, body=None):
        calls.append((method, path))
        if method == "DELETE":
            return 204, {}
        state["reads"] += 1
        # Archived only becomes visible on the third read — the race.
        archived = state["reads"] >= 3
        return 200, {"object": {"id": "obj-1", "archived": archived}}

    monkeypatch.setattr(task_actions, "call", fake_call)
    monkeypatch.setattr(task_actions.g, "get_space_id", lambda: "space-1")
    monkeypatch.setattr(task_actions.time, "sleep", lambda _s: None)

    out = task_actions.archive_object("obj-1")
    assert out == {"id": "obj-1", "archived": True}
    assert state["reads"] == 3, "should have polled, not read once"
    assert calls[0][0] == "DELETE" and calls[1][0] == "GET"


def test_archive_still_raises_when_it_never_archives(monkeypatch):
    """Polling must not swallow a REAL failure — only the timing assumption changed."""
    import task_actions

    def fake_call(method, path, body=None):
        if method == "DELETE":
            return 204, {}
        return 200, {"object": {"id": "obj-1", "archived": False}}

    monkeypatch.setattr(task_actions, "call", fake_call)
    monkeypatch.setattr(task_actions.g, "get_space_id", lambda: "space-1")
    monkeypatch.setattr(task_actions.time, "sleep", lambda _s: None)

    import pytest
    with pytest.raises(RuntimeError, match="still reads back unarchived"):
        task_actions.archive_object("obj-1")

# tests/test_api_periods.py — GET /api/periods, the route the Focus tab lists + seeds its editor
# from. Before this endpoint existed the tab rendered INVENTED sample periods that looked real, so
# what is pinned here is exactly the contract that keeps the frontend off fabricated data:
# every period comes back (not just the active one), the active flag is computed from today, ids
# resolve to CURRENT project names, and a fetch failure is a 500 — never an empty success that the
# client would read as "she has no periods".
#
# HTTP-level on the real ThreadingHTTPServer, with Anytype replaced at `server.g` (the same seam
# tests/test_focus_commit_reactivation.py uses). Nothing touches the real space.
import sys, os, json, threading, urllib.request, urllib.error, datetime as dt
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from http.server import ThreadingHTTPServer
import server

TODAY = dt.date.today()


def _d(offset):
    return (TODAY + dt.timedelta(days=offset)).isoformat()


def _period_obj(oid, name, start, end, **props):
    """An Anytype focus_period object as it reads back. `start`/`end` are day offsets from today
    (None = the half-authored, no-start case the sort has to survive)."""
    p = []
    if start is not None:
        p.append({"name": "Period start", "date": _d(start) + "T00:00:00Z"})
    if end is not None:
        p.append({"name": "Period end", "date": _d(end) + "T00:00:00Z"})
    p.extend(props.pop("extra", []))
    return {"id": oid, "name": name, "type": {"key": "focus_period"}, "properties": p}


# Every value below is DISTINCT and distinguishable — no two fields share a value, so a test that
# asserts on one field cannot accidentally pass while reading another.
def _rich_active_period():
    return _period_obj(
        "period-active", "Active week — jobs and caregiving", -2, 4,
        extra=[
            {"name": "Intent", "text": "Jobs are the survival focus this stretch."},
            {"name": "Availability start", "date": _d(1) + "T00:00:00Z"},
            {"name": "Availability end", "date": _d(3) + "T00:00:00Z"},
            {"name": "Availability note", "text": "Caregiving Sat-Mon, fragmented time."},
            {"name": "Days off", "text": "2026-01-02"},
            {"name": "Days on", "text": "2026-01-03"},
            {"name": "Output format", "select": {"name": "Priority list"}},
            {"name": "Workday start", "text": "09:15"},
            {"name": "Workday end", "text": "17:45"},
            # dict form carrying a STALE name — the handler must prefer the live project's
            # CURRENT name over the name embedded in the link.
            {"name": "Foreground projects", "objects": [{"id": "proj-fg", "name": "Stale foreground name"}]},
            # bare id-string form (what Anytype actually returns on read-back)
            {"name": "Paused projects", "objects": ["proj-paused"]},
        ])


def _seed_objects():
    return [
        # projects, under their CURRENT (renamed) names
        {"id": "proj-fg", "name": "Academic positions", "type": {"key": "gsdo_project"}, "properties": []},
        {"id": "proj-paused", "name": "Dissertation revisions", "type": {"key": "gsdo_project"}, "properties": []},
        # a non-period object: must be filtered out by type key
        {"id": "task-1", "name": "Call the surgeon", "type": {"key": "task"}, "properties": []},
        # deliberately NOT in start order, so the sort has to do real work
        _period_obj("period-future", "Future week", 10, 17),
        _rich_active_period(),
        _period_obj("period-nostart", "Half-authored, no start", None, 40),
        _period_obj("period-past", "Past week", -30, -24),
    ]


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))

    # A mutable holder so a test can swap the space contents (or make the fetch raise) without
    # rebuilding the server.
    state = {"objects": _seed_objects(), "raise": None}

    def fake_fetch(sid):
        if state["raise"] is not None:
            raise state["raise"]
        return state["objects"]

    monkeypatch.setattr(server.g, "fetch_all_objects", fake_fetch)
    monkeypatch.setattr(server.g, "get_space_id", lambda: "sid")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}", state
    srv.shutdown()
    srv.server_close()


def _get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _periods(live_server):
    base, _ = live_server
    status, body = _get(base, "/api/periods")
    assert status == 200
    return body["periods"]


# --- it returns ALL periods, not just the active one ------------------------

def test_returns_every_period_not_only_the_active_one(live_server):
    """The whole reason this route exists: /api/period (singular) already returned the active one
    and could not seed an editor over the others."""
    out = _periods(live_server)
    assert [p["id"] for p in out] == [
        "period-past", "period-active", "period-future", "period-nostart"]
    assert len(out) == 4, "all four periods, including the past and future ones"


def test_non_period_objects_are_filtered_out(live_server):
    ids = {p["id"] for p in _periods(live_server)}
    assert "task-1" not in ids and "proj-fg" not in ids


# --- exactly one active, computed from today --------------------------------

def test_exactly_the_period_containing_today_is_active(live_server):
    out = _periods(live_server)
    active = [p["id"] for p in out if p["active"] is True]
    assert active == ["period-active"]
    inactive = {p["id"] for p in out if p["active"] is False}
    assert inactive == {"period-past", "period-future", "period-nostart"}


def test_no_period_contains_today_means_none_is_active(live_server):
    base, state = live_server
    state["objects"] = [
        {"id": "proj-fg", "name": "Academic positions", "type": {"key": "gsdo_project"}, "properties": []},
        _period_obj("period-past", "Past week", -30, -24),
        _period_obj("period-future", "Future week", 10, 17),
    ]
    status, body = _get(base, "/api/periods")
    assert status == 200
    assert [p["id"] for p in body["periods"]] == ["period-past", "period-future"]
    assert all(p["active"] is False for p in body["periods"]), \
        "no period covers today — nothing may be flagged active"


# --- sorting -----------------------------------------------------------------

def test_sorted_earliest_start_first(live_server):
    out = _periods(live_server)
    starts = [p["start_date"] for p in out if p["start_date"]]
    assert starts == sorted(starts)
    assert starts[0] == _d(-30), "the past period sorts first"
    assert starts[-1] == _d(10), "the future period sorts last among the dated ones"


def test_period_with_no_start_sorts_last_and_does_not_crash(live_server):
    """A half-authored period should cost its own position, not the whole list."""
    out = _periods(live_server)
    assert out[-1]["id"] == "period-nostart"
    assert out[-1]["start_date"] is None


def test_all_periods_missing_a_start_still_returns_them_all(live_server):
    base, state = live_server
    state["objects"] = [
        _period_obj("p-a", "No start A", None, 3),
        _period_obj("p-b", "No start B", None, 9),
    ]
    status, body = _get(base, "/api/periods")
    assert status == 200
    assert {p["id"] for p in body["periods"]} == {"p-a", "p-b"}


# --- each entry carries id + the period_to_fields keys ----------------------

def test_every_entry_carries_an_id(live_server):
    out = _periods(live_server)
    assert all(p.get("id") for p in out), "an edit needs the id to name what it is changing"
    assert len({p["id"] for p in out}) == len(out)


def test_entry_carries_the_full_period_to_fields_shape_with_distinct_values(live_server):
    """Every asserted value is distinct, so a swapped mapping cannot pass by coincidence."""
    out = _periods(live_server)
    p = next(x for x in out if x["id"] == "period-active")
    assert p["name"] == "Active week — jobs and caregiving"
    assert p["start_date"] == _d(-2)
    assert p["end_date"] == _d(4)
    assert p["intent"] == "Jobs are the survival focus this stretch."
    assert p["availability_start"] == _d(1)
    assert p["availability_end"] == _d(3)
    assert p["availability_note"] == "Caregiving Sat-Mon, fragmented time."
    assert p["days_off"] == ["2026-01-02"]
    assert p["days_on"] == ["2026-01-03"]
    assert p["output_format"] == "Priority list"
    assert p["workday_start"] == "09:15"
    assert p["workday_end"] == "17:45"
    assert p["foreground_projects"] == ["Academic positions"]
    assert p["paused_projects"] == ["Dissertation revisions"]


def test_every_period_to_fields_key_is_present_on_every_entry(live_server):
    """The key list is spelled out literally, NOT derived from period_to_fields — deriving it
    would make the assertion tautological (drop a key from the adapter and both sides shrink
    together, so the test would still pass while the editor lost a field)."""
    expected = {
        "name", "start_date", "end_date", "intent",
        "availability_start", "availability_end", "availability_note",
        "days_off", "days_on", "output_format", "workday_start", "workday_end",
        "foreground_projects", "paused_projects",
        "id", "active",
    }
    for p in _periods(live_server):
        assert set(p.keys()) == expected, f"{p['id']} does not carry the edit shape"


# --- project ids resolve to CURRENT names -----------------------------------

def test_foreground_and_paused_resolve_to_current_names_not_stale_ones(live_server):
    p = next(x for x in _periods(live_server) if x["id"] == "period-active")
    assert p["foreground_projects"] == ["Academic positions"]
    assert "Stale foreground name" not in p["foreground_projects"], \
        "the link carried an old name; the live project name must win"
    assert p["paused_projects"] == ["Dissertation revisions"], \
        "a bare id string carries no name at all — it must be resolved from the space"


def test_a_renamed_project_comes_back_under_its_new_name(live_server):
    base, state = live_server
    for o in state["objects"]:
        if o["id"] == "proj-fg":
            o["name"] = "Job search (renamed)"
    status, body = _get(base, "/api/periods")
    assert status == 200
    p = next(x for x in body["periods"] if x["id"] == "period-active")
    assert p["foreground_projects"] == ["Job search (renamed)"]


# --- failure vs empty: the distinction that keeps fake data out -------------

def test_fetch_failure_is_a_500_with_an_error_body(live_server):
    base, state = live_server
    state["raise"] = RuntimeError("anytype unreachable")
    status, body = _get(base, "/api/periods")
    assert status == 500
    assert "error" in body and "anytype unreachable" in body["error"]
    assert "periods" not in body, "a failure must not also look like a (partial) success"


def test_empty_space_is_an_empty_list_not_an_error(live_server):
    """A real state — she may not have authored a period yet."""
    base, state = live_server
    state["objects"] = [
        {"id": "task-1", "name": "Call the surgeon", "type": {"key": "task"}, "properties": []},
    ]
    status, body = _get(base, "/api/periods")
    assert status == 200
    assert body == {"periods": []}


def test_failure_and_empty_are_distinguishable_to_the_client(live_server):
    """The frontend decides between 'show the empty state' and 'show an error' on this alone —
    if they ever converge, the fabricated-sample-data bug can come back."""
    base, state = live_server
    state["objects"] = []
    empty_status, empty_body = _get(base, "/api/periods")
    state["raise"] = RuntimeError("boom")
    fail_status, fail_body = _get(base, "/api/periods")
    assert (empty_status, empty_body) == (200, {"periods": []})
    assert fail_status == 500
    assert empty_status != fail_status and empty_body != fail_body

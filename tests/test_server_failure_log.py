"""`POST /api/log/correction` — the route that makes a failed write in the APP survive a reload.

June, 2026-07-18: *"what matters more is error logging if something fails."* Before this route
existed, a failure reached `console.error` and a 50-entry in-memory array that died with the tab,
so the durable half of what she asked for was the half that did not exist.

Driven over the REAL `ThreadingHTTPServer` on an ephemeral port, following
`tests/test_server_write_routes.py` — what the HTTP boundary returns is its own claim, and a
route can validate correctly in a helper and still answer the wrong status code.

Isolation: `tests/conftest.py` redirects `CD_DATA_DIR`/`CD_CONFIG_DIR` to a session sandbox for
every test, and the `live` fixture additionally gives each test its own `tmp_path`, so the
records asserted on here are only ever this test's. `corrections_log` resolves its path through
`cd_paths` at call time, which is what makes that redirect bite.
"""
import sys, os, json, threading, urllib.request, urllib.error
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from http.server import ThreadingHTTPServer
import server
import corrections_log


@pytest.fixture
def live(monkeypatch, tmp_path):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _post(base, body):
    data = json.dumps(body).encode()
    r = urllib.request.Request(base + "/api/log/correction", data=data, method="POST",
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


# --- it records, durably ----------------------------------------------------

def test_a_failure_is_appended_to_the_corrections_log(live):
    """The whole point: after the request, the record is ON DISK and readable back."""
    st, b = _post(live, {"msg": "Not moved. The server did not answer.",
                         "objectId": "task-1", "before": {"move": "task-1"}})
    assert st == 200 and b["ok"] is True

    recs = corrections_log.read_records()
    assert len(recs) == 1, "the failure did not reach the durable log"
    rec = recs[0]
    assert rec["kind"] == "write_failed"
    assert rec["before"]["msg"] == "Not moved. The server did not answer."
    assert rec["before"]["intended"] == {"move": "task-1"}
    assert rec["after"] is None, "nothing persisted, so `after` must say so"
    assert rec["object_id"] == "task-1"
    assert rec["surface"] == "app"
    assert "ts" in rec


def test_the_client_kind_is_carried_through(live):
    """`fail()` passes a `kind` for some failures; the log must keep it, not flatten it."""
    _post(live, {"msg": "Move refused.", "kind": "move_refused"})
    assert corrections_log.read_records()[0]["kind"] == "move_refused"


def test_a_record_with_no_object_omits_the_id_rather_than_inventing_one(live):
    """Not every failure is about an object. `log_correction` writes optional keys only when
    given, and a blank id must take that path rather than landing as an empty string."""
    _post(live, {"msg": "Could not reach the server."})
    rec = corrections_log.read_records()[0]
    assert "object_id" not in rec


def test_two_failures_append_rather_than_overwrite(live):
    _post(live, {"msg": "first"})
    _post(live, {"msg": "second"})
    assert [r["before"]["msg"] for r in corrections_log.read_records()] == ["first", "second"]


# --- ⚠ the authorship fold must not see these -------------------------------

def test_a_failed_write_does_not_claim_June_authored_the_value(live):
    """LOAD-BEARING. `resolve_authored_by` reads any non-'authorship' record for an
    (object_id, field) pair as June having overwritten that field. A write that FAILED changed
    nothing, so if these records carried a `field` the learning loop would be told she authored
    a value she never managed to save. They must leave the resolution exactly as they found it."""
    corrections_log.log_authorship("task-1", "Context", "a value the model wrote")
    assert corrections_log.resolve_authored_by("task-1", "Context") == "llm"

    _post(live, {"msg": "Not saved.", "objectId": "task-1",
                 "before": {"field": "Context", "value": "her edit"}})

    assert corrections_log.resolve_authored_by("task-1", "Context") == "llm", \
        "a FAILED write was folded in as an authorship change"


# --- malformed input is refused, readably -----------------------------------

def test_a_record_with_no_message_is_refused(live):
    """A record saying a write failed without saying WHICH one is not worth keeping, and
    accepting it silently would be the exact failure mode this route exists to end."""
    st, b = _post(live, {"objectId": "task-1"})
    assert st == 400
    assert "message" in b["error"], f"unreadable refusal: {b['error']!r}"
    assert corrections_log.read_records() == []


def test_a_blank_message_is_refused_like_a_missing_one(live):
    st, b = _post(live, {"msg": "   "})
    assert st == 400 and "message" in b["error"]
    assert corrections_log.read_records() == []


def test_a_non_string_message_is_refused(live):
    st, b = _post(live, {"msg": {"nested": "object"}})
    assert st == 400 and "message" in b["error"]
    assert corrections_log.read_records() == []


def test_a_blank_kind_is_refused_rather_than_logged_as_empty(live):
    st, b = _post(live, {"msg": "boom", "kind": "  "})
    assert st == 400 and "kind" in b["error"]
    assert corrections_log.read_records() == []


def test_a_non_string_object_id_is_refused(live):
    st, b = _post(live, {"msg": "boom", "objectId": 17})
    assert st == 400 and "objectId" in b["error"]
    assert corrections_log.read_records() == []

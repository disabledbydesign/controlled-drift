"""`POST /api/duration` refuses a number of minutes that cannot be a real duration.

WHY THIS EXISTS. The overlay's duration box is PRE-FILLED with the stored value, and tapping
into it places a cursor rather than selecting — so typing "45" over a pre-filled "30" produced
`3045`, live, 2026-07-20. The server's only guard was `minutes <= 0`, so 3045 minutes — fifty
hours — would have been written to her real Anytype object without complaint.

WHY 24 HOURS AND NOT SOMETHING TIGHTER. June asked "24 hours? 14 hours?" and the answer is the
looser one on purpose. A 14-hour cap encodes an OPINION about how long her work should take;
this repo has already been bitten by exactly that move — `BLOCK_DEFAULT_MIN = 90` was traced to
an ILLUSTRATION in a design doc ("work on GRA for 90 min") that became a hardcoded rule nobody
had decided. A 24-hour cap encodes a fact about days instead, and still catches the typo this
guard exists for.

The real protection is that the control now reverts to the stored value when a write is
refused (June: "if a change can't be made, the UI content needs to show what's really in the
data — that's essential"). This cap is the second line, not the first.

Same harness as test_server_priority_order.py: the real ThreadingHTTPServer on an ephemeral
port, Anytype replaced at the transport seam, every path redirected into tmp_path.
"""
import sys, os, json, threading, urllib.request, urllib.error

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from http.server import ThreadingHTTPServer
import fake_space
import server
import plan_store
from test_api_write import _seed


TASK = "task-1"          # a real id in test_api_write._seed(); a fake one 404s on write


def _plan():
    return {
        "shape": "priority",
        "items": [{"id": TASK, "task": "Call the surgeon", "duration_min": 30}],
    }


@pytest.fixture
def live(monkeypatch, tmp_path):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    fake_space.install(fake_space.FakeSpace(_seed()), monkeypatch.setattr)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _post(base, path, body):
    r = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_the_real_typo_is_refused(live):
    """3045 is the exact value the pre-filled box produced when "45" was typed over "30"."""
    plan_store.save_plan(_plan())

    st, b = _post(live, "/api/duration", {"id": TASK, "minutes": 3045})

    assert st == 400
    assert "24 hours" in b["error"]


def test_a_refused_duration_leaves_the_stored_value_alone(live):
    """The point of the guard: her real stored duration is untouched by a rejected write."""
    plan_store.save_plan(_plan())

    _post(live, "/api/duration", {"id": TASK, "minutes": 3045})

    # A priority-shape plan keeps its rows under `items`; only a clock-shape day has `blocks`.
    assert plan_store.load_plan()["items"][0]["duration_min"] == 30


def test_a_full_day_is_still_allowed(live):
    """1440 is the boundary and is ACCEPTED — the cap is a fact about days, not a view about
    how long her work should take. Asserted positively: this must not produce the cap error."""
    plan_store.save_plan(_plan())

    st, b = _post(live, "/api/duration", {"id": TASK, "minutes": 1440})

    assert st == 200
    assert b["duration_min"] == 1440


def test_just_over_a_day_is_refused(live):
    """One minute past the boundary, so the test pins the boundary itself rather than a range."""
    plan_store.save_plan(_plan())

    st, b = _post(live, "/api/duration", {"id": TASK, "minutes": 1441})

    assert st == 400
    assert "24 hours" in b["error"]


def test_zero_is_still_refused_with_its_own_words(live):
    """The pre-existing lower guard keeps its own message — a cap error would misdescribe it."""
    plan_store.save_plan(_plan())

    st, b = _post(live, "/api/duration", {"id": TASK, "minutes": 0})

    assert st == 400
    assert "positive" in b["error"]

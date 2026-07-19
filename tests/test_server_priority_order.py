"""`POST /api/plan/priority-order` over real HTTP — the route that was missing entirely.

Before this, `PriorityList.tsx` wrote her reordering to `ctx.up({priOrder})` and there was no
server reference anywhere: `GET /api/plan/priority-order` answered 404 and every manual
reordering died with the tab. June's decision, 2026-07-19: "Yes, should persist."

The route answers with the REWRITTEN PLAN, matching the other per-row plan routes
(`/api/task/move`, `/api/duration`, `/api/task/not-today`) — the plan is the only proof the
write landed, and `api/planRow.ts` is built around taking it.

Same harness as `test_server_write_routes.py`: the real ThreadingHTTPServer on an ephemeral
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


A, B, C = "bafyA", "bafyB", "bafyC"


def _plan():
    return {
        "shape": "priority",
        "items": [
            {"id": A, "task": "Call the pharmacy"},
            {"id": B, "task": "Rent portal"},
            {"id": C, "task": "Water the plants"},
        ],
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


def test_it_saves_the_order_and_answers_with_the_rewritten_plan(live):
    plan_store.save_plan(_plan())

    st, b = _post(live, "/api/plan/priority-order", {"order": [C, A, B]})

    assert st == 200
    assert b["ok"] is True
    assert b["plan"]["priority_order"] == [C, A, B]


def test_the_saved_order_survives_a_fresh_read_of_the_plan(live):
    """The point of the whole part: it is on disk, not in a response."""
    plan_store.save_plan(_plan())

    _post(live, "/api/plan/priority-order", {"order": [B, C, A]})

    assert plan_store.load_plan()["priority_order"] == [B, C, A]


def test_the_order_rides_back_on_GET_api_plan(live):
    """The surface reads its saved ranking off the ordinary plan payload — no second fetch of a
    dedicated read route, and no adapter change needed to carry it."""
    plan_store.save_plan(_plan())
    _post(live, "/api/plan/priority-order", {"order": [C, B, A]})

    with urllib.request.urlopen(live + "/api/plan", timeout=5) as resp:
        got = json.loads(resp.read().decode())

    assert got["priority_order"] == [C, B, A]


def test_a_missing_order_is_a_400(live):
    plan_store.save_plan(_plan())

    st, b = _post(live, "/api/plan/priority-order", {})

    assert st == 400
    assert "order" in b["error"]


def test_an_order_that_is_not_a_list_of_ids_is_a_400(live):
    """⚠ Asserts the SENTENCE, not just the status. Without the route's type check the store
    still refuses this — it stringifies `7` and then fails set-equality — so a bare `st == 400`
    passed with the guard deleted. What the guard actually buys is the honest message: it says
    the entry is not an id, instead of reporting `'7'` back to the caller as though it were an
    id the plan was asked for. Found by mutation."""
    plan_store.save_plan(_plan())

    st, b = _post(live, "/api/plan/priority-order", {"order": [A, 7, B]})

    assert st == 400
    assert "must be a task id" in b["error"]


def test_an_id_the_plan_does_not_have_is_a_400_naming_it(live):
    """A ranking that addresses a row this plan does not hold is refused, and the sentence says
    which id — never a quiet filter that stores a subtly wrong order."""
    plan_store.save_plan(_plan())

    st, b = _post(live, "/api/plan/priority-order", {"order": [A, B, "bafyGHOST"]})

    assert st == 400
    assert "bafyGHOST" in b["error"]


def test_no_cached_plan_is_a_404(live):
    """⚠ Both this and the clock-shape test below assert the STORE'S OWN sentence, not merely
    the status. An unrouted path also answers 404, so a bare `st == 404` passed against a server
    that had no such route at all — which is exactly the state this file was written in. The
    message is what distinguishes a real refusal from a missing endpoint."""
    st, b = _post(live, "/api/plan/priority-order", {"order": [A]})

    assert st == 404
    assert "no cached plan to rank" in b["error"]


def test_a_clock_shape_plan_is_a_404(live):
    """A clock day orders its rows under blocks[] and moves through /api/task/move."""
    plan_store.save_plan({"shape": "clock", "blocks": [{"label": "Morning", "items": []}]})

    st, b = _post(live, "/api/plan/priority-order", {"order": [A]})

    assert st == 404
    assert "priority list to rank" in b["error"]


def test_a_refused_order_leaves_the_previous_one_standing(live):
    """A rejected write must not clear what she had. Asserted positively: the earlier ranking is
    still the one on disk."""
    plan_store.save_plan(_plan())
    _post(live, "/api/plan/priority-order", {"order": [C, A, B]})

    _post(live, "/api/plan/priority-order", {"order": [A, B, "bafyGHOST"]})

    assert plan_store.load_plan()["priority_order"] == [C, A, B]

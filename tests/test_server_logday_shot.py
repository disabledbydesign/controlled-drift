"""Endpoint tests for the snapshot half of /api/logday, and GET /api/shot/<name>.

These drive the REAL handler over the REAL HTTP stack on an ephemeral port, which is how the
if-chain in scripts/server.py is actually reachable — nothing here mocks the route.

The most important test in this file is `test_logday_without_a_shot_is_unchanged`: 45 friction
entries already exist, and an entry with no snapshot must keep producing exactly the record the
pre-2026-07-19 code produced.
"""
import base64, json, os, sys, threading, urllib.request, urllib.error
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    """The real handler on an ephemeral port, with both data roots redirected to tmp_path.

    No importlib.reload here: cd_paths resolves every path at CALL time (cd_paths.py docstring),
    so monkeypatching the env is enough and reloading server would re-execute a large import
    graph for no benefit.
    """
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path / "config"))
    import server
    from http.server import ThreadingHTTPServer
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}", tmp_path
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(timeout=5)


def _post(base, path, body):
    req = urllib.request.Request(
        base + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _signals(tmp_path):
    # Absent file means no entry was written at all — the refusal tests assert exactly that, so
    # this has to read as an empty log rather than raising.
    p = tmp_path / "signal_log.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def test_logday_without_a_shot_is_unchanged(live_server):
    base, tmp_path = live_server
    status, body = _post(base, "/api/logday", {"text": "plain text", "tags": ["issue"]})
    assert status == 200 and body["ok"] is True and body["tags"] == ["issue"]
    rec = _signals(tmp_path)[-1]
    assert rec["raw"] == "plain text"
    assert rec["reference"] == {"kind": "log_day", "tags": ["issue"]}
    assert "shot" not in rec["reference"]


def test_logday_with_a_shot_stores_the_png_and_points_at_it(live_server):
    base, tmp_path = live_server
    status, body = _post(base, "/api/logday", {
        "text": "this row is wrong", "tags": ["issue"], "shot": DATA_URL,
        "view": {"tab": "today", "detailId": None},
        "target": {"tag": "button", "label": "Not today", "text": "Not today", "data": {}},
    })
    assert status == 200
    name = body["shot"]
    assert name and name.endswith(".png")
    assert (tmp_path / "shots" / name).read_bytes() == PNG_1PX
    ref = _signals(tmp_path)[-1]["reference"]
    assert ref["shot"] == name
    assert ref["view"] == {"tab": "today", "detailId": None}
    assert ref["target"]["label"] == "Not today"


def test_logday_records_which_entry_point_was_used(live_server):
    base, tmp_path = live_server
    _post(base, "/api/logday", {"text": "x", "tags": ["issue"], "via": "longpress"})
    assert _signals(tmp_path)[-1]["reference"]["via"] == "longpress"


def test_logday_drops_an_unknown_via_rather_than_storing_junk(live_server):
    base, tmp_path = live_server
    _post(base, "/api/logday", {"text": "x", "tags": ["issue"], "via": "telepathy"})
    assert "via" not in _signals(tmp_path)[-1]["reference"]


def test_logday_stores_mark_geometry_with_the_image_size(live_server):
    base, tmp_path = live_server
    marks = [{"points": [[10, 10], [20, 20]], "box": [10, 10, 10, 10], "closed": False}]
    _post(base, "/api/logday", {"text": "x", "tags": ["issue"], "shot": DATA_URL,
                                "marks": marks, "size": {"w": 392, "h": 860}})
    ref = _signals(tmp_path)[-1]["reference"]
    assert ref["marks"] == marks
    assert ref["size"] == {"w": 392, "h": 860}


def test_logday_omits_marks_when_nothing_was_drawn(live_server):
    base, tmp_path = live_server
    _post(base, "/api/logday", {"text": "x", "tags": ["issue"], "shot": DATA_URL, "marks": []})
    assert "marks" not in _signals(tmp_path)[-1]["reference"]


def test_a_bad_shot_fails_the_whole_write_rather_than_logging_text_alone(live_server):
    """June was told the image saved; it must not silently become a text-only entry."""
    base, tmp_path = live_server
    status, body = _post(base, "/api/logday", {
        "text": "has an image", "tags": ["issue"], "shot": "data:image/png;base64,!!!not base64",
    })
    assert status == 400
    assert "snapshot" in body["error"].lower()
    assert _signals(tmp_path) == []


def test_a_shot_with_no_text_is_still_refused(live_server):
    base, tmp_path = live_server
    status, body = _post(base, "/api/logday", {"text": "  ", "tags": ["issue"], "shot": DATA_URL})
    assert status == 400
    assert _signals(tmp_path) == []


def test_get_shot_serves_the_png_back(live_server):
    base, tmp_path = live_server
    _, body = _post(base, "/api/logday", {"text": "x", "tags": ["issue"], "shot": DATA_URL})
    with urllib.request.urlopen(base + "/api/shot/" + body["shot"]) as r:
        assert r.status == 200
        assert r.headers["Content-Type"] == "image/png"
        assert r.read() == PNG_1PX


def test_get_shot_refuses_a_traversal_name(live_server):
    base, _ = live_server
    req = urllib.request.Request(base + "/api/shot/..%2F..%2Fsignal_log.jsonl")
    try:
        with urllib.request.urlopen(req) as r:
            raise AssertionError("traversal should not have succeeded, got %s" % r.status)
    except urllib.error.HTTPError as e:
        assert e.code in (400, 404)

# Snapshot-and-Annotate Friction Capture — Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let June capture friction *in place* on any screen — a snapshot of what she is looking at, freehand marks on it, and a multi-line comment — appended to the existing friction log without leaving the screen that frustrated her.

**Architecture:** A capture overlay mounted once in `app/src/shell/Surface.tsx`, above the phone/desktop fork, so it exists on every screen in both shells. It snapshots the live DOM to a PNG **in the browser** (`modern-screenshot`), never via the macOS screenshot API — so it needs no Screen Recording permission, cannot silently return a black rectangle, and works identically on June's phone over the LAN. The PNG rides as base64 in the JSON body of the **existing** `/api/logday` endpoint; the server decodes it to `scripts/data/shots/` and hangs a pointer on the signal record's already-polymorphic `reference` field. No new log is invented (BUILD_DOC.md §1: "Never invent a new log").

**Tech Stack:** React 19 + TypeScript + Vite 8 (`app/`), vitest + jsdom for frontend tests. Python 3 stdlib `ThreadingHTTPServer` (`scripts/server.py`), pytest. One new runtime dependency: `modern-screenshot` v4.7.0.

## Global Constraints

- **No new log module.** Friction entries continue to go through `scripts/signal_log.py::log_signal` with `source="log_day"`. The attachment pointer goes in `reference`, which is already polymorphic across sources (`{"kind": "log_day", "tags": [...]}` today).
- **No new HTTP endpoint for the write.** Extend the existing `POST /api/logday` (`scripts/server.py:1243`). One new **read** endpoint (`GET /api/shot/<name>`) is required so the triage pass can see the images.
- **No multipart.** Base64 in the JSON body only. `_read_json_body` (`scripts/server.py:549`) stays JSON-only.
- **No macOS `screencapture`, no PyObjC, no Quartz.** `scripts/desktop_app.py:156` records that `screencapture` returns black without Screen Recording permission and the `.app` bundle is unsigned. The capture happens inside the web page.
- **Storage root:** `scripts/data/shots/`, resolved through `cd_paths.data_file` so `CD_DATA_DIR` redirects it and the test suite never writes to June's real directory.
- **Privacy:** `scripts/data/` is already gitignored (`.gitignore:16`). Task 1 adds an explicit `scripts/data/shots/` line anyway so the reason is written down — these PNGs contain her real health and financial detail, the same reason the review-surface HTML is ignored.
- **Tags unchanged:** only `"day"` and `"issue"` survive the server filter. A snapshot capture sends `["issue"]`.
- **Every entry records which way in was used** (`reference.via`: `"longpress" | "shortcut" | "rightclick" | "button"`). June asked for this so an unused entry point can be found and retired rather than accumulating. **Retirement is surfaced to her, never automatic** — the report says what the numbers are and asks; nothing is removed without her word.
- **Drawn marks are stored as geometry as well as pixels** (`reference.marks`). They already exist as point arrays in the overlay, so this is nearly free, and it tells a later reader *where* a mark is and how big — the part a picture alone leaves ambiguous.
- **Never a silent success.** The toast is raised only after the server confirms, and the overlay stays open on failure with her text and drawing intact. This matches the existing `logDay` contract at `app/src/shell/useAppState.ts:1381`.
- **No metaphors in any June-facing copy** (global access guard). Button and error text must be literal.
- **Python:** raise, never `assert`. No silent failures.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/shot_store.py` | **Create.** Decode one base64 PNG, validate it, write it under `scripts/data/shots/`, return its filename. Read one back by name with path containment. |
| `tests/test_shot_store.py` | **Create.** Unit tests for the above. |
| `scripts/server.py` | **Modify.** `/api/logday` accepts optional `shot` / `view` / `target`; new `GET /api/shot/<name>`. |
| `tests/test_server_logday_shot.py` | **Create.** Endpoint-level tests. |
| `app/src/friction/capture.ts` | **Create.** Snapshot the DOM to a PNG data URL; build a descriptor of the element under the pointer. |
| `app/src/friction/__tests__/capture.test.ts` | **Create.** |
| `app/src/friction/AnnotateOverlay.tsx` | **Create.** The full-screen editor: snapshot + draw canvas + multi-line comment + Send/Cancel. |
| `app/src/friction/__tests__/AnnotateOverlay.test.tsx` | **Create.** |
| `app/src/friction/useFrictionCapture.ts` | **Create.** Trigger detection (long-press, keyboard shortcut) and capture lifecycle state. |
| `app/src/friction/__tests__/useFrictionCapture.test.ts` | **Create.** |
| `app/src/shell/useAppState.ts` | **Modify.** `logDay` gains optional `shot` / `view` / `target`. |
| `app/src/shell/Surface.tsx` | **Modify.** Mount the overlay + the quiet persistent button once, above the shell fork. |
| `app/package.json` | **Modify.** Add `modern-screenshot`. |
| `.gitignore` | **Modify.** Explicit `scripts/data/shots/` line with the reason. |
| `scripts/friction_report.py` | **Create.** Summarise the friction log: how many entries, which way in was used, which entry points have gone unused — and say plainly that retirement is June's call. |
| `tests/test_friction_report.py` | **Create.** |
| `docs/friction_triage.md` | **Create.** The first written triage instruction. There has never been one. |
| `tests/test_signal_record_shape.py` | **Create.** Pins the record shape the triage doc reads, so a change to the writer fails a test that names the reader. |

---

### Task 1: The shot store

**Files:**
- Create: `scripts/shot_store.py`
- Create: `tests/test_shot_store.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `cd_paths.data_file` (`scripts/cd_paths.py:33`).
- Produces:
  - `shots_dir() -> str`
  - `save_png(data_url: str) -> str` — returns a bare filename like `2026-07-19T14-22-05-a3f9c1.png`. Raises `ValueError` on anything that is not a PNG data URL, or on a payload above `MAX_BYTES`.
  - `read_png(name: str) -> bytes` — raises `ValueError` on a name that is not a plain filename, `FileNotFoundError` if absent.
  - `MAX_BYTES = 8 * 1024 * 1024`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_shot_store.py`:

```python
import base64, os, pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import shot_store

# A 1x1 transparent PNG — the smallest real PNG, so the magic-number check is exercised.
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()


def test_save_png_writes_the_file_and_returns_a_bare_name(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    name = shot_store.save_png(DATA_URL)
    assert os.sep not in name and name.endswith(".png")
    on_disk = os.path.join(str(tmp_path), "shots", name)
    assert os.path.exists(on_disk)
    with open(on_disk, "rb") as f:
        assert f.read() == PNG_1PX


def test_save_png_names_are_unique(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    names = {shot_store.save_png(DATA_URL) for _ in range(20)}
    assert len(names) == 20


def test_save_png_rejects_a_non_png_data_url(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        shot_store.save_png("data:image/jpeg;base64," + base64.b64encode(PNG_1PX).decode())


def test_save_png_rejects_bytes_that_are_not_actually_a_png(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    bad = "data:image/png;base64," + base64.b64encode(b"not a png at all").decode()
    with pytest.raises(ValueError):
        shot_store.save_png(bad)


def test_save_png_rejects_an_oversized_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    huge = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * (shot_store.MAX_BYTES + 1)).decode()
    with pytest.raises(ValueError):
        shot_store.save_png(huge)


def test_read_png_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    name = shot_store.save_png(DATA_URL)
    assert shot_store.read_png(name) == PNG_1PX


@pytest.mark.parametrize("name", ["../secrets.png", "a/b.png", "", ".", "..", "shot.txt"])
def test_read_png_refuses_a_name_that_is_not_a_plain_png_filename(tmp_path, monkeypatch, name):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        shot_store.read_png(name)


def test_read_png_missing_file_raises_filenotfound(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    # ⚠ TWELVE hex characters. `save_png` uses `secrets.token_hex(6)`, which returns 12 chars, and
    # `_NAME_RE` requires 12 — so a 6-char name is one this module could never have generated and
    # is rejected as malformed before the file is ever opened. Any later task that hand-writes a
    # snapshot filename needs 12. (Plan error, caught building Task 1.)
    with pytest.raises(FileNotFoundError):
        shot_store.read_png("2026-01-01T00-00-00-abcdef123456.png")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/june/Documents/GitHub/cyborg-memory/controlled-drift && python3 -m pytest tests/test_shot_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shot_store'`

- [ ] **Step 3: Write the implementation**

Create `scripts/shot_store.py`:

```python
#!/usr/bin/env python3
"""Binary store for friction snapshots — the PNGs that ride along with a Log entry.

CAPTURE ONLY, exactly like signal_log: the image is stored verbatim and never inspected,
resized, or classified. The signal record in signal_log.jsonl holds only the FILENAME; the
bytes live here, out of the JSONL so the log stays greppable and diffable.

⚠ These images are June's real screen — task names, medical and financial detail, the same
content that keeps scripts/data/ out of git. The directory is gitignored. Nothing here ever
leaves the machine.
"""
import sys, os, re, base64, datetime as dt, secrets
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths

# A phone screenshot is well under a megabyte; 8MB is a generous ceiling that still refuses a
# runaway or hostile body outright rather than writing it to disk and finding out later.
MAX_BYTES = 8 * 1024 * 1024

_PREFIX = "data:image/png;base64,"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Exactly the shape save_png() generates: an ISO-ish timestamp, a hex suffix, .png. Anything
# else is refused, which is what makes read_png's path containment total.
_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-[0-9a-f]{12}\.png$")


def shots_dir():
    return cd_paths.data_file("shots")


def save_png(data_url):
    """Write one base64 PNG data URL to the shots dir; return its bare filename.

    Raises ValueError on anything that is not a PNG, or is over MAX_BYTES. We check the magic
    number rather than trusting the data-URL's own claim about its type: the prefix is written
    by the client and a mislabelled body would otherwise be stored as a .png that is not one.
    """
    if not isinstance(data_url, str) or not data_url.startswith(_PREFIX):
        raise ValueError("a snapshot must be a data:image/png;base64 URL")
    try:
        raw = base64.b64decode(data_url[len(_PREFIX):], validate=True)
    except Exception as e:
        raise ValueError("that snapshot was not valid base64: %s" % e)
    if len(raw) > MAX_BYTES:
        raise ValueError("that snapshot is larger than the %d byte limit" % MAX_BYTES)
    if not raw.startswith(_PNG_MAGIC):
        raise ValueError("that snapshot's bytes are not a PNG")

    name = "%s-%s.png" % (dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S"), secrets.token_hex(6))
    d = shots_dir()
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(raw)
    return name


def read_png(name):
    """Bytes of one stored snapshot. Raises ValueError on a name this module did not generate."""
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ValueError("not a snapshot name")
    with open(os.path.join(shots_dir(), name), "rb") as f:
        return f.read()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_shot_store.py -v`
Expected: all PASS

- [ ] **Step 5: Mutation-test the containment check**

Per the standing rule (`feedback-mutation-test-before-trusting`): a test written to catch a bug must be seen failing against broken code.

Temporarily change `_NAME_RE.match(name)` to `True` in `read_png`. Run `python3 -m pytest tests/test_shot_store.py -v`.
Expected: `test_read_png_refuses_a_name_that_is_not_a_plain_png_filename` FAILS for the `../secrets.png` case. Then restore the line and confirm green again.

- [ ] **Step 6: Add the explicit gitignore line**

In `.gitignore`, immediately after the existing `scripts/data/` block (line 16), add:

```
# Friction snapshots — PNGs of June's real screen (task names, medical/financial detail).
# Already covered by scripts/data/ above; named explicitly so the reason is on the record and
# a later narrowing of that rule cannot silently start committing her screenshots. (2026-07-19)
scripts/data/shots/
```

- [ ] **Step 7: Commit**

```bash
git add scripts/shot_store.py tests/test_shot_store.py .gitignore
git commit -m "feat(friction): store a snapshot PNG alongside a log entry

The friction log has only ever held text, so June had to reconstruct in words
whatever she was looking at. This is the binary half: capture-only, verbatim,
gitignored for the same reason the rest of scripts/data/ is."
```

---

### Task 2: `/api/logday` accepts a snapshot

**Files:**
- Modify: `scripts/server.py:1243-1266`
- Create: `tests/test_server_logday_shot.py`

**Interfaces:**
- Consumes: `shot_store.save_png` (Task 1).
- Produces: the request body `/api/logday` now accepts, and the `reference` shape written to `signal_log.jsonl`:

```
request  {"text": str, "tags": ["issue"], "shot": "data:image/png;base64,…"|null,
          "view": {"tab": str, "detailId": str|null}|null,
          "target": {"tag": str, "label": str, "text": str, "data": {…},
                     "chain": [{"tag": str, "label": str}, …]}|null,
          "via": "longpress"|"shortcut"|"rightclick"|"button"|null,
          "marks": [{"points": [[x,y],…], "box": [x,y,w,h], "closed": bool}, …]|null,
          "size": {"w": int, "h": int}|null}
reference {"kind": "log_day", "tags": [...], "shot": name|absent,
           "view": {...}|absent, "target": {...}|absent,
           "via": str|absent, "marks": [...]|absent, "size": {...}|absent}
response {"ok": true, "tags": [...], "shot": name|null}
```

`marks` and `size` travel together: mark coordinates are in image pixels, so they are meaningless
without the image dimensions they were drawn against.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_server_logday_shot.py`. This drives the handler through the real HTTP stack on an ephemeral port, which is how the other server tests in this repo reach the if-chain.

```python
import base64, json, os, sys, threading, urllib.request, urllib.error
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    """The real handler on an ephemeral port, with both data roots redirected to tmp_path."""
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path / "config"))
    import importlib
    import cd_paths, signal_log, shot_store, server
    for m in (cd_paths, signal_log, shot_store, server):
        importlib.reload(m)
    from http.server import ThreadingHTTPServer
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", tmp_path
    httpd.shutdown()


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
    p = tmp_path / "signal_log.jsonl"
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
            assert False, "traversal should not have succeeded, got %s" % r.status
    except urllib.error.HTTPError as e:
        assert e.code in (400, 404)
```

> **Note for the implementer:** the fixture assumes the handler class in `scripts/server.py` is named `Handler`. Confirm the actual class name with `grep -n "class .*BaseHTTPRequestHandler" scripts/server.py` and use it. If the repo already has a live-server fixture in `tests/conftest.py`, reuse that instead of redefining one.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_server_logday_shot.py -v`
Expected: FAIL — the shot tests fail because `body["shot"]` is missing (`KeyError`), and `/api/shot/...` 404s.

- [ ] **Step 3: Add the import**

In `scripts/server.py`, next to the existing `import signal_log`, add:

```python
import shot_store
```

- [ ] **Step 4: Replace the `/api/logday` handler**

Replace `scripts/server.py:1243-1266` in full with:

```python
        if self.path == "/api/logday":
            # Log (Task 5/6C, extended): June's own faithful record — how the day went AND/OR an
            # issue she hits in real time to come back to later. She picks which via `tags` (multi-
            # select: "day", "issue", or both) — a light label, NOT a classifier. Stored verbatim +
            # uncategorized via signal_log (source="log_day"); the tags ride in reference so a later
            # "review my issues" pass can find them, and Phase 7 still extracts from the raw text.
            # Sync, no LLM. We never narrate a classification back — only a plain acknowledgment.
            #
            # 2026-07-19: an entry may now carry a SNAPSHOT of what she was looking at, plus which
            # view she was on and which element she pressed. The reason is that the text-only path
            # made her translate the friction into words at the exact moment she had least capacity
            # to do it — she had to leave the screen to describe the screen. All three are optional
            # and additive: an entry without them is byte-identical to what this wrote before.
            body = self._read_json_body()
            text = (body.get("text") or "").strip()
            if not text:
                self._send(400, {"error": "log needs text"})
                return
            # keep only known tags; tolerate a malformed (non-list) value; default to the day if
            # none came through (never lose the entry over a tag)
            raw_tags = body.get("tags")
            tags = ([t for t in raw_tags if t in ("day", "issue")]
                    if isinstance(raw_tags, list) else []) or ["day"]

            reference = {"kind": "log_day", "tags": tags}

            # ⚠ The snapshot is written BEFORE the signal record, and a failure here fails the
            # WHOLE request. The alternative — log the text and drop the image — would tell her
            # the capture landed while quietly discarding the half that carried the context. A
            # refused write she can retry beats a silent partial one. (No silent failures.)
            shot = body.get("shot")
            if shot:
                try:
                    reference["shot"] = shot_store.save_png(shot)
                except ValueError as e:
                    self._send(400, {"error": str(e)})
                    return
                except Exception as e:
                    self._send(500, {"error": str(e)})
                    return

            # Where she was and what she pressed. Stored verbatim and NOT interpreted — same
            # discipline as the raw text. `target` is best-effort from the DOM and may be absent
            # or coarse; that is fine, it is a hint for triage, never a claim.
            view = body.get("view")
            if isinstance(view, dict):
                reference["view"] = view
            target = body.get("target")
            if isinstance(target, dict):
                reference["target"] = target

            # Which way in she used. Recorded so an entry point that turns out to go unused can be
            # FOUND and retired instead of quietly accumulating — June's ask, 2026-07-19. It is a
            # record of a mechanism, not of her, and it is never used to prompt or nudge her.
            via = body.get("via")
            if via in ("longpress", "shortcut", "rightclick", "button"):
                reference["via"] = via

            # The drawn marks as GEOMETRY, next to the pixels. A circle in the image tells a later
            # reader something is wrong there; the geometry tells it where and how big, which is
            # the part a picture alone leaves ambiguous. Stored verbatim, never interpreted here.
            marks = body.get("marks")
            if isinstance(marks, list) and marks:
                reference["marks"] = marks
            size = body.get("size")
            if isinstance(size, dict):
                reference["size"] = size          # mark coords are meaningless without this

            try:
                signal_log.log_signal(text, source="log_day", reference=reference)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            self._send(200, {"ok": True, "tags": tags, "shot": reference.get("shot")})
            return
```

- [ ] **Step 5: Add the `GET /api/shot/<name>` route**

In `do_GET` (`scripts/server.py:600`), alongside the other literal-path matches, add:

```python
        # The one path-parameter GET outside _object_route. A snapshot has to be readable to be
        # worth storing: this is what the triage pass (and June) open to see what she was looking
        # at. Containment is total — shot_store.read_png only accepts names it generated itself.
        if self.path.startswith("/api/shot/"):
            name = unquote(self.path[len("/api/shot/"):])
            try:
                data = shot_store.read_png(name)
            except ValueError:
                self._send(400, {"error": "not a snapshot name"})
                return
            except FileNotFoundError:
                self._send(404, {"error": "no such snapshot"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            # Names are unique and content never changes, so this is safe to cache hard.
            self.send_header("Cache-Control", "private, max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(data)
            return
```

> `unquote` is already imported at the top of `scripts/server.py` (used by `_object_route`).

- [ ] **Step 6: Add the route to the module docstring inventory**

`scripts/server.py:11-46` lists every route. Add `GET  /api/shot/{name}` to that list, and note the extended body on `POST /api/logday`.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_server_logday_shot.py -v`
Expected: all PASS

- [ ] **Step 8: Run the whole Python suite for regressions**

Run: `python3 -m pytest tests/ -q`
Expected: no new failures. The unchanged-path test in Step 1 is the guard that existing `logDay` callers still write a byte-identical record.

- [ ] **Step 9: Commit**

```bash
git add scripts/server.py tests/test_server_logday_shot.py
git commit -m "feat(friction): accept a snapshot, view and press-target on /api/logday

Extends the existing endpoint rather than inventing a second friction path —
reference was already polymorphic, so the attachment pointer hangs off it with
no schema break. A bad image fails the whole write: a partial save that drops
the image would tell her the capture landed when the useful half did not."
```

---

### Task 3: The browser-side capture utility

**Files:**
- Create: `app/src/friction/capture.ts`
- Create: `app/src/friction/__tests__/capture.test.ts`
- Modify: `app/package.json`

**Interfaces:**
- Consumes: `modern-screenshot`'s `domToPng`.
- Produces:

```ts
export interface PressTarget {
  tag: string; label: string; text: string;
  data: Record<string, string>;
  chain: Array<{ tag: string; label: string }>;   // innermost first, outward, capped at 5
}
export function describeTarget(el: Element | null): PressTarget | null;
export function snapshot(node?: HTMLElement | null): Promise<string | null>;
```

`snapshot` resolves to a PNG data URL, or `null` if capture failed (never throws — a failed snapshot must still let her file a text-only entry).

- [ ] **Step 1: Add the dependency**

```bash
cd /Users/june/Documents/GitHub/cyborg-memory/controlled-drift/app && npm install modern-screenshot@^4.7.0
```

This is the app's first runtime dependency beyond React. It has zero transitive dependencies — verify with `npm ls modern-screenshot`.

- [ ] **Step 2: Write the failing tests**

Create `app/src/friction/__tests__/capture.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

const domToPng = vi.fn();
// jsdom cannot rasterise anything, so the library is mocked. What we test here is OUR logic:
// the descriptor walk, and that a capture failure degrades to null instead of throwing.
vi.mock('modern-screenshot', () => ({ domToPng: (...a: unknown[]) => domToPng(...a) }));

import { describeTarget, snapshot } from '../capture.ts';

beforeEach(() => {
  domToPng.mockReset();
  document.body.innerHTML = '';
});

describe('describeTarget', () => {
  it('is null for no element', () => {
    expect(describeTarget(null)).toBeNull();
  });

  it('reads the tag, the accessible label and a text snippet', () => {
    document.body.innerHTML = `<button aria-label="Move this back">Not today</button>`;
    const t = describeTarget(document.querySelector('button'));
    expect(t).toMatchObject({ tag: 'button', label: 'Move this back', text: 'Not today' });
  });

  it('falls back to the text when there is no aria-label', () => {
    document.body.innerHTML = `<div>Cancel food stamps</div>`;
    expect(describeTarget(document.querySelector('div'))!.label).toBe('Cancel food stamps');
  });

  it('truncates a long text snippet', () => {
    document.body.innerHTML = `<div>${'x'.repeat(400)}</div>`;
    expect(describeTarget(document.querySelector('div'))!.text.length).toBeLessThanOrEqual(200);
  });

  it('collects data-* attributes from the element and its ancestors', () => {
    document.body.innerHTML =
      `<section data-desk-col="map"><span data-signal="row"><em>hi</em></span></section>`;
    const t = describeTarget(document.querySelector('em'));
    expect(t!.data).toEqual({ 'desk-col': 'map', signal: 'row' });
  });

  it('records the element chain outward, so a mis-hit still lands somewhere useful', () => {
    document.body.innerHTML = `<li aria-label="Cancel food stamps"><span><i></i></span></li>`;
    const chain = describeTarget(document.querySelector('i'))!.chain;
    expect(chain[0].tag).toBe('i');
    expect(chain.map((c) => c.tag)).toContain('li');
    expect(chain.find((c) => c.tag === 'li')!.label).toBe('Cancel food stamps');
  });

  it('caps the chain rather than walking the whole document', () => {
    document.body.innerHTML = '<a><b><i><u><s><em><q>x</q></em></s></u></i></b></a>';
    expect(describeTarget(document.querySelector('q'))!.chain.length).toBeLessThanOrEqual(5);
  });

  it('lets a nearer data attribute win over an ancestor with the same name', () => {
    document.body.innerHTML = `<section data-signal="outer"><span data-signal="inner"><em>hi</em></span></section>`;
    expect(describeTarget(document.querySelector('em'))!.data.signal).toBe('inner');
  });
});

describe('snapshot', () => {
  it('returns the data URL the renderer produced', async () => {
    domToPng.mockResolvedValue('data:image/png;base64,AAAA');
    expect(await snapshot(document.body)).toBe('data:image/png;base64,AAAA');
  });

  it('resolves null rather than throwing when the renderer fails', async () => {
    domToPng.mockRejectedValue(new Error('tainted canvas'));
    expect(await snapshot(document.body)).toBeNull();
  });

  it('resolves null when the renderer returns something that is not a png data URL', async () => {
    domToPng.mockResolvedValue('');
    expect(await snapshot(document.body)).toBeNull();
  });

  it('skips nodes marked as capture chrome', async () => {
    domToPng.mockResolvedValue('data:image/png;base64,AAAA');
    await snapshot(document.body);
    const opts = domToPng.mock.calls[0][1] as { filter: (n: Node) => boolean };
    const chrome = document.createElement('div');
    chrome.setAttribute('data-cd-capture-chrome', '');
    expect(opts.filter(chrome)).toBe(false);
    expect(opts.filter(document.createElement('p'))).toBe(true);
  });
});
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd app && npx vitest run src/friction/__tests__/capture.test.ts`
Expected: FAIL — cannot resolve `../capture.ts`

- [ ] **Step 4: Write the implementation**

Create `app/src/friction/capture.ts`:

```ts
import { domToPng } from 'modern-screenshot';

/**
 * What June was pressing when she summoned the capture.
 *
 * Deliberately coarse and best-effort. The app is not instrumented with per-row ids (only five
 * data-* attributes exist across the whole tree), so rather than requiring an instrumentation
 * pass first, this reads whatever the DOM already says: the element kind, its accessible label,
 * a text snippet, and any data-* attributes on the way up. That is a HINT for the triage pass —
 * "she was on the Not today button" — never a claim about which object she meant.
 */
export interface PressTarget {
  tag: string;
  label: string;
  text: string;
  data: Record<string, string>;
  /**
   * The innermost element and its ancestors, outward. Recorded because June's own worry about
   * this is the right one: elements overlap, and a finger lands slightly off. The innermost hit
   * may be a padding div or the wrong sibling. The chain means a near-miss still lands somewhere
   * useful — a reader that cannot make sense of `label` can look one step out.
   */
  chain: Array<{ tag: string; label: string }>;
}

const MAX_TEXT = 200;
/** Far enough out to escape a mis-hit, short enough not to be the whole document. */
const MAX_CHAIN = 5;
/** Elements carrying this attribute are the capture UI itself and must not appear in the shot. */
export const CHROME_ATTR = 'data-cd-capture-chrome';

function snip(s: string | null | undefined): string {
  const t = (s || '').replace(/\s+/g, ' ').trim();
  return t.length > MAX_TEXT ? t.slice(0, MAX_TEXT) : t;
}

export function describeTarget(el: Element | null): PressTarget | null {
  if (!el) return null;
  const text = snip(el.textContent);
  const aria = el.getAttribute('aria-label');

  // Walk to the document root collecting data-* attributes. NEAREST WINS: the loop only fills a
  // key it has not already seen, so an inner data-signal is not overwritten by an outer one.
  const data: Record<string, string> = {};
  const chain: Array<{ tag: string; label: string }> = [];
  for (let n: Element | null = el; n; n = n.parentElement) {
    for (const a of Array.from(n.attributes)) {
      if (!a.name.startsWith('data-')) continue;
      const key = a.name.slice('data-'.length);
      if (!(key in data)) data[key] = a.value;
    }
    if (chain.length < MAX_CHAIN) {
      chain.push({
        tag: n.tagName.toLowerCase(),
        label: snip(n.getAttribute('aria-label')) || snip(n.textContent),
      });
    }
  }

  return { tag: el.tagName.toLowerCase(), label: snip(aria) || text, text, data, chain };
}

/**
 * The live screen as a PNG data URL, rendered from the DOM inside the page.
 *
 * ── why not the macOS screenshot ────────────────────────────────────────────
 * `screencapture` needs Screen Recording permission, and `desktop_app.py:156` records that it
 * returns a BLACK image without it — a failure mode that looks like a working capture. The
 * bundle is also unsigned, so the permission prompt has no stable identity to attach to. Doing
 * it in the page needs no permission at all, cannot go black, and works unchanged on June's
 * phone over the LAN, which the OS path could never have done.
 *
 * ── the honest tradeoff ─────────────────────────────────────────────────────
 * This RE-RENDERS the DOM rather than copying real pixels, so unusual CSS can come out slightly
 * wrong. If the friction being logged IS a rendering bug, the image may not show it faithfully.
 * That is why the entry also carries the view and the press target: the record stays useful even
 * when the picture is imperfect.
 *
 * NEVER throws. A failed snapshot must still leave her able to file a text-only entry — losing
 * the whole capture because the image did not render would be strictly worse than the old path.
 */
export async function snapshot(node?: HTMLElement | null): Promise<string | null> {
  const root = node || document.body;
  if (!root) return null;
  try {
    const url = await domToPng(root, {
      // The overlay is drawn before the async render finishes in some orderings; excluding it by
      // attribute is cheaper and more reliable than trying to sequence around it.
      filter: (n: Node) =>
        !(n instanceof Element && n.hasAttribute(CHROME_ATTR)),
      // 1 rather than devicePixelRatio: a 3x phone screen would produce a multi-megabyte PNG for
      // no legibility gain at the size she will actually look at it.
      scale: 1,
    });
    return typeof url === 'string' && url.startsWith('data:image/png') ? url : null;
  } catch {
    return null;
  }
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd app && npx vitest run src/friction/__tests__/capture.test.ts`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/src/friction/capture.ts app/src/friction/__tests__/capture.test.ts app/package.json app/package-lock.json
git commit -m "feat(friction): snapshot the DOM in-page, and describe the pressed element

In-page rather than the macOS screenshot: no Screen Recording permission, no
silent black frame, and it works identically on her phone. A failed render
returns null so a text-only entry is still possible."
```

---

### Task 4: `logDay` carries the snapshot

**Files:**
- Modify: `app/src/shell/useAppState.ts:501-504` (the interface) and `:1381-1401` (the implementation)
- Modify: `app/src/screens/__tests__/addSettings.test.tsx` if the existing assertion at line 309 breaks

**Interfaces:**
- Consumes: `PressTarget` from `app/src/friction/capture.ts`.
- Produces:

```ts
export interface Mark { points: Array<[number, number]>; box: [number, number, number, number]; closed: boolean; }
export type CaptureVia = 'longpress' | 'shortcut' | 'rightclick' | 'button';
export interface LogExtras {
  shot?: string | null;
  view?: { tab: string; detailId: string | null } | null;
  target?: PressTarget | null;
  via?: CaptureVia | null;
  marks?: Mark[] | null;
  size?: { w: number; h: number } | null;
}
logDay(text: string, tags: string[], extras?: LogExtras): Promise<boolean>
```

- [ ] **Step 1: Write the failing test**

Add to `app/src/screens/__tests__/addSettings.test.tsx` (or a new `app/src/shell/__tests__/logDayExtras.test.ts` if the harness there is simpler — use whichever matches the existing pattern for testing `useAppState` network calls):

```ts
it('sends the snapshot, view and target through to /api/logday', async () => {
  const send = vi.fn().mockResolvedValue({ ok: true, tags: ['issue'], shot: 'a.png' });
  // …mount via the harness this file already uses, then:
  await result.current.logDay('this row is wrong', ['issue'], {
    shot: 'data:image/png;base64,AAAA',
    view: { tab: 'today', detailId: null },
    target: { tag: 'button', label: 'Not today', text: 'Not today', data: {} },
  });
  expect(send).toHaveBeenCalledWith('POST', '/api/logday', {
    text: 'this row is wrong',
    tags: ['issue'],
    shot: 'data:image/png;base64,AAAA',
    view: { tab: 'today', detailId: null },
    target: { tag: 'button', label: 'Not today', text: 'Not today', data: {} },
  });
});

it('omits the extra keys entirely when there are none', async () => {
  const send = vi.fn().mockResolvedValue({ ok: true, tags: ['issue'] });
  await result.current.logDay('plain', ['issue']);
  expect(send).toHaveBeenCalledWith('POST', '/api/logday', { text: 'plain', tags: ['issue'] });
});
```

The second test is the regression guard: the existing assertion at `addSettings.test.tsx:309` (`expect(logDay).toHaveBeenCalledWith('a friction', ['issue'])`) must keep passing, so the extras argument has to be genuinely optional and absent keys must not appear in the body.

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/screens/__tests__/addSettings.test.tsx`
Expected: FAIL — the extras are dropped, so the body lacks `shot`.

- [ ] **Step 3: Extend the interface declaration**

At `app/src/shell/useAppState.ts:501-504`, replace the `logDay` declaration with:

```ts
  /**
   * Log one entry. `extras` carries an optional snapshot of what she was looking at, which view
   * she was on, and which element she pressed — see `app/src/friction/`. All optional: the Add
   * tab's Log button still calls this with two arguments and sends a byte-identical body.
   */
  logDay: (text: string, tags: string[], extras?: LogExtras) => Promise<boolean>;
```

and add near the other exported types in that file:

```ts
import type { PressTarget } from '../friction/capture.ts';

/** The optional context a snapshot capture attaches to a log entry. */
export interface LogExtras {
  shot?: string | null;
  view?: { tab: string; detailId: string | null } | null;
  target?: PressTarget | null;
}
```

- [ ] **Step 4: Extend the implementation**

At `app/src/shell/useAppState.ts:1381`, replace the `apiSend` call with:

```ts
      // Only present keys are sent. An entry with no snapshot must produce exactly the body the
      // Add tab's Log button has always sent, so the unchanged path stays provably unchanged.
      const payload: Record<string, unknown> = { text: body, tags };
      if (extras?.shot) payload.shot = extras.shot;
      if (extras?.view) payload.view = extras.view;
      if (extras?.target) payload.target = extras.target;
      if (extras?.via) payload.via = extras.via;
      if (extras?.marks?.length) payload.marks = extras.marks;
      if (extras?.size) payload.size = extras.size;

      const res = await apiSend<{ ok?: boolean; tags?: string[]; shot?: string | null }>(
        'POST', '/api/logday', payload,
      );
      if (!res.ok) {
        fail(`That was NOT logged, so nothing was saved. ${res.error}`);
        return false;
      }
      succeed('Logged', null);
      return true;
```

and add `extras` to the `useCallback` signature and its dependency array as appropriate.

- [ ] **Step 5: Run the tests**

Run: `cd app && npx vitest run && npx tsc --noEmit`
Expected: all PASS, no type errors.

- [ ] **Step 6: Commit**

```bash
git add app/src/shell/useAppState.ts app/src/screens/__tests__/addSettings.test.tsx
git commit -m "feat(friction): logDay carries an optional snapshot, view and target

Optional and additive — an entry with no snapshot sends the same body the Add
tab's Log button always sent, which the second test pins."
```

---

### Task 5: The annotate overlay

**Files:**
- Create: `app/src/friction/AnnotateOverlay.tsx`
- Create: `app/src/friction/__tests__/AnnotateOverlay.test.tsx`

**Interfaces:**
- Consumes: nothing from earlier tasks at runtime — it receives the snapshot as a prop so it is testable in isolation.
- Produces:

```tsx
export interface AnnotateOverlayProps {
  T: Theme;
  shot: string | null;          // null when the render failed — text-only mode
  target: PressTarget | null;
  onCancel: () => void;
  onSend: (
    text: string,
    shot: string | null,
    marks: Mark[],
    size: { w: number; h: number } | null,
  ) => Promise<boolean>;
}
export function AnnotateOverlay(props: AnnotateOverlayProps): JSX.Element;
```

**Why the marks go out as geometry too.** June asked whether an arrow tool or a shape palette
would read more clearly to a model interpreting the image than her hand-drawn circles. The
dichotomy is avoidable: a hand-drawn loop in a high-contrast colour is legible in the image, and
what a picture leaves genuinely ambiguous is *where the mark is and how far it extends*. The
strokes are already point arrays in this component, so emitting their bounding boxes costs
almost nothing and answers that directly — better than a shape palette would, and without
putting a tool-selection step between June and writing down what is wrong. `closed` is a cheap
hint (did the stroke end near where it began) that separates "circled this" from "pointed at
this" without asking her to declare which she meant.

**Drawing scope (v1):** freehand strokes only, one colour, undo-last and clear. No arrow tool, no shapes, no colour picker, no text-on-image — a tool palette is a different feature and June named drawing as nice-to-have, not required. Strokes are held as point arrays and re-rendered on every change, so undo is a `pop` rather than a pixel operation; they are composited onto the image only at send time.

- [ ] **Step 1: Write the failing tests**

Create `app/src/friction/__tests__/AnnotateOverlay.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnnotateOverlay } from '../AnnotateOverlay.tsx';
import { THEMES } from '@tokens';

const T = THEMES.celestial;
const SHOT = 'data:image/png;base64,AAAA';

function setup(over: Partial<React.ComponentProps<typeof AnnotateOverlay>> = {}) {
  const onCancel = vi.fn();
  const onSend = vi.fn().mockResolvedValue(true);
  render(
    <AnnotateOverlay T={T} shot={SHOT} target={null} onCancel={onCancel} onSend={onSend} {...over} />,
  );
  return { onCancel, onSend };
}

beforeEach(() => vi.clearAllMocks());

it('shows the snapshot it was given', () => {
  setup();
  expect(screen.getByAltText(/what you were looking at/i)).toHaveAttribute('src', SHOT);
});

it('offers a multi-line comment box, not a single line', () => {
  setup();
  expect(screen.getByRole('textbox').tagName).toBe('TEXTAREA');
});

it('will not send an empty comment', () => {
  const { onSend } = setup();
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
  expect(onSend).not.toHaveBeenCalled();
});

it('sends the typed comment', async () => {
  const { onSend } = setup();
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'this row is wrong' } });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
  await waitFor(() =>
    expect(onSend).toHaveBeenCalledWith('this row is wrong', expect.any(String), [], expect.anything()),
  );
});

it('sends a drawn mark as geometry, not only as pixels', async () => {
  const { onSend } = setup();
  const canvas = document.querySelector('canvas')!;
  // jsdom gives a zero-size rect, so at() maps every point to 0 — what this pins is that a
  // stroke produces ONE mark with a box and a `closed` flag, not the coordinate arithmetic
  // (which only Task 10's live check on the real app actually proves).
  canvas.setPointerCapture = vi.fn();
  fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 });
  fireEvent.pointerMove(canvas, { clientX: 40, clientY: 40, pointerId: 1 });
  fireEvent.pointerUp(canvas, { pointerId: 1 });
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'here' } });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
  await waitFor(() => expect(onSend).toHaveBeenCalled());
  const marks = onSend.mock.calls[0][2];
  expect(marks).toHaveLength(1);
  expect(marks[0].box).toHaveLength(4);
  expect(typeof marks[0].closed).toBe('boolean');
});

it('cancels without sending', () => {
  const { onCancel, onSend } = setup();
  fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
  expect(onCancel).toHaveBeenCalled();
  expect(onSend).not.toHaveBeenCalled();
});

it('closes on Escape', () => {
  const { onCancel } = setup();
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(onCancel).toHaveBeenCalled();
});

it('stays open with the text intact when the send fails', async () => {
  const onSend = vi.fn().mockResolvedValue(false);
  setup({ onSend });
  const box = screen.getByRole('textbox');
  fireEvent.change(box, { target: { value: 'keep me' } });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
  await waitFor(() => expect(onSend).toHaveBeenCalled());
  expect(screen.getByRole('textbox')).toHaveValue('keep me');
});

it('falls back to text only when there is no snapshot', async () => {
  const { onSend } = setup({ shot: null });
  expect(screen.queryByAltText(/what you were looking at/i)).toBeNull();
  expect(screen.getByText(/could not take a picture/i)).toBeInTheDocument();
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'still works' } });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));
  await waitFor(() => expect(onSend).toHaveBeenCalledWith('still works', null, [], null));
});

it('names what she pressed when a target is known', () => {
  setup({ target: { tag: 'button', label: 'Not today', text: 'Not today', data: {} } });
  expect(screen.getByText(/Not today/)).toBeInTheDocument();
});

it('hides the drawing controls until something has been drawn', () => {
  setup();
  expect(screen.queryByRole('button', { name: /undo/i })).toBeNull();
});
```

> `@tokens` is the existing alias used across `app/src`; confirm the theme export name with `grep -n "export const THEMES" design/tokens/tokens.ts` and match it.

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/friction/__tests__/AnnotateOverlay.test.tsx`
Expected: FAIL — cannot resolve `../AnnotateOverlay.tsx`

- [ ] **Step 3: Write the implementation**

Create `app/src/friction/AnnotateOverlay.tsx`:

```tsx
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Theme } from '@tokens';
import { CHROME_ATTR, type PressTarget } from './capture.ts';
import type { Mark } from '../shell/useAppState.ts';

/** One freehand stroke, as the points it passed through in image coordinates. */
type Stroke = Array<[number, number]>;

const STROKE_WIDTH = 4;

export interface AnnotateOverlayProps {
  T: Theme;
  /** The snapshot, or null when the render failed — then this is a text-only entry. */
  shot: string | null;
  target: PressTarget | null;
  onCancel: () => void;
  /** Returns whether it landed. False keeps the overlay open with everything intact. */
  onSend: (text: string, shot: string | null) => Promise<boolean>;
}

/**
 * The capture editor: what she was looking at, whatever she draws on it, and what she wants to
 * say about it.
 *
 * ── why the marks are held as points, not painted ───────────────────────────
 * Strokes live in state as arrays of points and the canvas is re-rendered from them on every
 * change, so undo is a `pop`. Painting straight onto a single canvas would be less code and make
 * undo impossible without a pixel-history buffer.
 *
 * ── why the image is composited only at send ────────────────────────────────
 * The snapshot stays an untouched <img> underneath and the strokes sit on a canvas above it.
 * They are flattened into one PNG once, in `composite()`, when she sends. Until then the
 * original is intact, so Clear genuinely restores it.
 */
export function AnnotateOverlay({ T, shot, target, onCancel, onSend }: AnnotateOverlayProps) {
  const [text, setText] = useState('');
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [sending, setSending] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawing = useRef(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);

  /** Re-render every stroke. Runs on any change to `strokes`, including an undo. */
  useEffect(() => {
    const c = canvasRef.current;
    const ctx = c?.getContext('2d');
    if (!c || !ctx) return;
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.strokeStyle = T.warn || '#ff5470';
    ctx.lineWidth = STROKE_WIDTH;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (const s of strokes) {
      if (s.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(s[0][0], s[0][1]);
      for (const [x, y] of s.slice(1)) ctx.lineTo(x, y);
      ctx.stroke();
    }
  }, [strokes, T]);

  /** Pointer position in CANVAS coordinates — the canvas is displayed scaled to fit. */
  const at = useCallback((e: React.PointerEvent<HTMLCanvasElement>): [number, number] => {
    const c = canvasRef.current!;
    const r = c.getBoundingClientRect();
    return [
      ((e.clientX - r.left) / (r.width || 1)) * c.width,
      ((e.clientY - r.top) / (r.height || 1)) * c.height,
    ];
  }, []);

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    drawing.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    const p = at(e);
    setStrokes((prev) => [...prev, [p]]);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return;
    const p = at(e);
    setStrokes((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      return [...prev.slice(0, -1), [...last, p]];
    });
  };

  const onPointerUp = () => {
    drawing.current = false;
  };

  /** Flatten the snapshot and the strokes into one PNG. Null when there was no snapshot. */
  const composite = useCallback((): string | null => {
    const img = imgRef.current;
    const marks = canvasRef.current;
    if (!img || !marks) return null;
    const out = document.createElement('canvas');
    out.width = marks.width;
    out.height = marks.height;
    const ctx = out.getContext('2d');
    if (!ctx) return shot;
    try {
      ctx.drawImage(img, 0, 0, out.width, out.height);
      ctx.drawImage(marks, 0, 0);
      return out.toDataURL('image/png');
    } catch {
      // jsdom, and any future canvas restriction: fall back to the unannotated original rather
      // than losing the image. Her comment is the part that must never be lost.
      return shot;
    }
  }, [shot]);

  /**
   * The strokes as data: each one's bounding box, and whether it closed back on itself.
   *
   * This is the answer to "would an arrow tool read more clearly than a hand-drawn circle" —
   * the shape is not what a later reader is missing, the COORDINATES are. Emitting these lets a
   * hand-drawn loop say "the trouble is in this rectangle" as precisely as any shape tool could,
   * with no tool palette standing between June and writing the entry.
   */
  const geometry = useCallback((): Mark[] => {
    return strokes
      .filter((s) => s.length >= 2)
      .map((s) => {
        const xs = s.map((p) => p[0]);
        const ys = s.map((p) => p[1]);
        const x = Math.min(...xs);
        const y = Math.min(...ys);
        const w = Math.max(...xs) - x;
        const h = Math.max(...ys) - y;
        const [sx, sy] = s[0];
        const [ex, ey] = s[s.length - 1];
        // "Closed" = it ended near where it began, relative to its own size. A loop reads as
        // circling something; an open stroke reads as pointing at something.
        const span = Math.max(w, h, 1);
        const closed = Math.hypot(ex - sx, ey - sy) < span * 0.35;
        return { points: s, box: [x, y, w, h] as [number, number, number, number], closed };
      });
  }, [strokes]);

  const send = async () => {
    if (!text.trim() || sending) return;
    setSending(true);
    const c = canvasRef.current;
    const size = c && c.width ? { w: c.width, h: c.height } : null;
    const ok = await onSend(text.trim(), shot ? composite() : null, geometry(), size);
    setSending(false);
    // On failure we deliberately do NOT clear: `useAppState.fail` has already told her nothing
    // was saved, and throwing away her comment at that moment would be the worst possible move.
    if (ok) onCancel();
  };

  const btn = (extra: React.CSSProperties = {}): React.CSSProperties => ({
    padding: '10px 16px',
    borderRadius: 10,
    border: `1px solid ${T.line}`,
    background: T.card,
    color: T.text,
    font: 'inherit',
    cursor: 'pointer',
    ...extra,
  });

  return (
    <div
      {...{ [CHROME_ATTR]: '' }}
      role="dialog"
      aria-label="Log what is wrong here"
      style={{
        position: 'fixed', inset: 0, zIndex: 9999, background: T.bg,
        display: 'flex', flexDirection: 'column', gap: 12, padding: 16, overflow: 'auto',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <strong style={{ color: T.text }}>Log what is wrong here</strong>
        {target?.label ? (
          <span style={{ color: T.dim, fontSize: 13 }}>You pressed: {target.label}</span>
        ) : null}
      </div>

      {shot ? (
        <div style={{ position: 'relative', maxHeight: '45vh', overflow: 'hidden', borderRadius: 12, border: `1px solid ${T.line}` }}>
          <img
            ref={imgRef}
            src={shot}
            alt="What you were looking at"
            onLoad={(e) => {
              const c = canvasRef.current;
              if (!c) return;
              c.width = e.currentTarget.naturalWidth || e.currentTarget.width;
              c.height = e.currentTarget.naturalHeight || e.currentTarget.height;
            }}
            style={{ display: 'block', width: '100%', height: 'auto' }}
          />
          <canvas
            ref={canvasRef}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', touchAction: 'none', cursor: 'crosshair' }}
          />
        </div>
      ) : (
        <p style={{ color: T.dim, margin: 0 }}>
          Could not take a picture of this screen. You can still write down what is wrong.
        </p>
      )}

      {shot && strokes.length > 0 ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" style={btn()} onClick={() => setStrokes((p) => p.slice(0, -1))}>
            Undo mark
          </button>
          <button type="button" style={btn()} onClick={() => setStrokes([])}>
            Clear marks
          </button>
        </div>
      ) : shot ? (
        <p style={{ color: T.dim, margin: 0, fontSize: 13 }}>You can draw on the picture to point at something.</p>
      ) : null}

      <textarea
        aria-label="What is wrong here"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="What is wrong here?"
        style={{
          width: '100%', minHeight: 150, resize: 'vertical', padding: 12,
          borderRadius: 12, border: `1px solid ${T.line}`, background: T.card,
          color: T.text, font: 'inherit',
        }}
      />

      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button type="button" style={btn()} onClick={onCancel}>Cancel</button>
        <button
          type="button"
          style={btn({ background: T.accent, color: T.bg, borderColor: T.accent, opacity: text.trim() && !sending ? 1 : 0.5 })}
          onClick={send}
        >
          {sending ? 'Saving…' : 'Send'}
        </button>
      </div>
    </div>
  );
}
```

> **Implementer note on theme keys:** `T.warn`, `T.dim`, `T.card`, `T.line`, `T.accent`, `T.bg`, `T.text` are assumed from the token set. Run `grep -n "export interface Theme" -A 40 design/tokens/tokens.ts` and substitute the real key names. Do not invent tokens — use what exists.

- [ ] **Step 4: Run the tests**

Run: `cd app && npx vitest run src/friction/__tests__/AnnotateOverlay.test.tsx`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/src/friction/AnnotateOverlay.tsx app/src/friction/__tests__/AnnotateOverlay.test.tsx
git commit -m "feat(friction): the annotate overlay — snapshot, freehand marks, comment

Marks are point arrays re-rendered each change so undo is a pop, and are
flattened into the PNG only at send. A failed send keeps the overlay open with
her comment intact."
```

---

### Task 6: Triggers — long-press, keyboard shortcut, and the quiet button

**Files:**
- Create: `app/src/friction/useFrictionCapture.ts`
- Create: `app/src/friction/__tests__/useFrictionCapture.test.ts`

**Interfaces:**
- Consumes: `snapshot`, `describeTarget` from `./capture.ts`.
- Produces:

```ts
export const LONG_PRESS_MS = 550;
export interface CaptureState {
  open: boolean; busy: boolean; shot: string | null;
  target: PressTarget | null; via: CaptureVia | null;
}
export function useFrictionCapture(): {
  state: CaptureState;
  begin: (target?: Element | null, via?: CaptureVia) => void;   // the quiet button's entry point
  close: () => void;
};
```

**Entry points — one flow, four ways in, split by what each is good for:**

| Way in | Where | What it is for |
|---|---|---|
| Long press | Touch only | "*This row* is wrong," on the phone. |
| Right click | The desktop app only | "*This control* is wrong," with exact targeting and no gesture ambiguity. |
| `Cmd/Ctrl+Shift+F` | Anywhere with a keyboard | Same, for the browser, where the right-click menu belongs to the browser. |
| The quiet button | Everywhere | "*This whole screen* is wrong" — and the guaranteed way in if a gesture misfires. |

**Why right-click is confined to the desktop app.** June proposed it and it is better than the
gesture on desktop: exact targeting, discoverable, no collision with drag-to-reparent. Its one
real cost is that claiming `contextmenu` removes the browser's own menu — inspect, copy, open in
new tab. In the native window there is no browser menu to lose, so the cost is zero there and
real in a browser tab. Hence the split, rather than choosing one and paying for it everywhere.

**Every open records which way was used** (`state.via`), which is what makes the retirement
question in Task 8 answerable with numbers instead of a guess.

- [ ] **Step 1: Write the failing tests**

Create `app/src/friction/__tests__/useFrictionCapture.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

const snapshot = vi.fn();
vi.mock('../capture.ts', async (orig) => ({
  ...(await orig<typeof import('../capture.ts')>()),
  snapshot: (...a: unknown[]) => snapshot(...a),
}));
const isNative = vi.fn();
vi.mock('../../shell/native.ts', () => ({ isNative: () => isNative() }));

import { useFrictionCapture, LONG_PRESS_MS } from '../useFrictionCapture.ts';

beforeEach(() => {
  vi.useFakeTimers();
  snapshot.mockReset().mockResolvedValue('data:image/png;base64,AAAA');
  isNative.mockReset().mockReturnValue(false);
  document.body.innerHTML = '<button id="t">Not today</button>';
});
afterEach(() => vi.useRealTimers());

it('starts closed', () => {
  const { result } = renderHook(() => useFrictionCapture());
  expect(result.current.state.open).toBe(false);
});

it('opens with a snapshot when begin is called', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  await act(async () => {
    result.current.begin(null);
    await vi.runAllTimersAsync();
  });
  expect(result.current.state.open).toBe(true);
  expect(result.current.state.shot).toBe('data:image/png;base64,AAAA');
});

it('records what was pressed', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  await act(async () => {
    result.current.begin(document.getElementById('t'));
    await vi.runAllTimersAsync();
  });
  expect(result.current.state.target?.label).toBe('Not today');
});

it('opens after a long press and not before', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  const el = document.getElementById('t')!;
  act(() => {
    el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: 5, clientY: 5, pointerType: 'touch' }));
  });
  act(() => { vi.advanceTimersByTime(LONG_PRESS_MS - 50); });
  expect(result.current.state.open).toBe(false);
  await act(async () => { await vi.runAllTimersAsync(); });
  expect(result.current.state.open).toBe(true);
});

it('cancels the long press when the finger moves — a scroll must not open it', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  const el = document.getElementById('t')!;
  act(() => {
    el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: 5, clientY: 5, pointerType: 'touch' }));
    window.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, clientX: 5, clientY: 60 }));
  });
  await act(async () => { await vi.runAllTimersAsync(); });
  expect(result.current.state.open).toBe(false);
});

it('cancels the long press when the finger lifts early', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  const el = document.getElementById('t')!;
  act(() => {
    el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: 5, clientY: 5, pointerType: 'touch' }));
    window.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
  });
  await act(async () => { await vi.runAllTimersAsync(); });
  expect(result.current.state.open).toBe(false);
});

it('does not long-press on a mouse — that would break click-and-hold', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  const el = document.getElementById('t')!;
  act(() => {
    el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: 5, clientY: 5, pointerType: 'mouse' }));
  });
  await act(async () => { await vi.runAllTimersAsync(); });
  expect(result.current.state.open).toBe(false);
});

it('opens on the keyboard shortcut', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  await act(async () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'F', shiftKey: true, metaKey: true, bubbles: true }));
    await vi.runAllTimersAsync();
  });
  expect(result.current.state.open).toBe(true);
});

it('records which way in was used', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  await act(async () => { result.current.begin(null, 'button'); await vi.runAllTimersAsync(); });
  expect(result.current.state.via).toBe('button');
});

it('records a long press as a long press, not as the button', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  act(() => {
    document.getElementById('t')!.dispatchEvent(
      new PointerEvent('pointerdown', { bubbles: true, clientX: 5, clientY: 5, pointerType: 'touch' }));
  });
  await act(async () => { await vi.runAllTimersAsync(); });
  expect(result.current.state.via).toBe('longpress');
});

it('opens on right click in the native app', async () => {
  isNative.mockReturnValue(true);
  const { result } = renderHook(() => useFrictionCapture());
  const ev = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
  await act(async () => {
    document.getElementById('t')!.dispatchEvent(ev);
    await vi.runAllTimersAsync();
  });
  expect(result.current.state.open).toBe(true);
  expect(result.current.state.via).toBe('rightclick');
  expect(ev.defaultPrevented).toBe(true);
});

it('leaves the browser context menu alone when not native', async () => {
  isNative.mockReturnValue(false);
  const { result } = renderHook(() => useFrictionCapture());
  const ev = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
  await act(async () => {
    document.getElementById('t')!.dispatchEvent(ev);
    await vi.runAllTimersAsync();
  });
  expect(result.current.state.open).toBe(false);
  expect(ev.defaultPrevented).toBe(false);
});

it('opens with a null shot when the render failed, rather than not opening', async () => {
  snapshot.mockResolvedValue(null);
  const { result } = renderHook(() => useFrictionCapture());
  await act(async () => {
    result.current.begin(null);
    await vi.runAllTimersAsync();
  });
  expect(result.current.state.open).toBe(true);
  expect(result.current.state.shot).toBeNull();
});

it('ignores a second begin while one capture is already in flight', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  await act(async () => {
    result.current.begin(null);
    result.current.begin(null);
    await vi.runAllTimersAsync();
  });
  expect(snapshot).toHaveBeenCalledTimes(1);
});

it('closes', async () => {
  const { result } = renderHook(() => useFrictionCapture());
  await act(async () => { result.current.begin(null); await vi.runAllTimersAsync(); });
  act(() => result.current.close());
  expect(result.current.state.open).toBe(false);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/friction/__tests__/useFrictionCapture.test.ts`
Expected: FAIL — cannot resolve `../useFrictionCapture.ts`

- [ ] **Step 3: Write the implementation**

Create `app/src/friction/useFrictionCapture.ts`:

```ts
import { useCallback, useEffect, useRef, useState } from 'react';
import { describeTarget, snapshot, type PressTarget } from './capture.ts';
import { isNative } from '../shell/native.ts';
import type { CaptureVia } from '../shell/useAppState.ts';

/**
 * Long enough not to fire on a tap or the start of a scroll, short enough that she is not holding
 * her thumb down wondering whether it registered. Matches the platform's own press-and-hold feel.
 */
export const LONG_PRESS_MS = 550;
/** Past this much movement it was a scroll, not a press. */
const MOVE_TOLERANCE_PX = 10;

export interface CaptureState {
  open: boolean;
  /** A capture is being rendered. Guards against a second trigger mid-flight. */
  busy: boolean;
  shot: string | null;
  target: PressTarget | null;
  /** Which way in was used. Recorded so an unused entry point can be found and retired. */
  via: CaptureVia | null;
}

const CLOSED: CaptureState = { open: false, busy: false, shot: null, target: null, via: null };

/**
 * When and how June summons the capture.
 *
 * ── two entry points, one flow ──────────────────────────────────────────────
 * They answer two different kinds of friction. Long-press / shortcut says "THIS THING is wrong"
 * and carries what she pressed, which is what turns a vague report into one pointing at a
 * specific row or control. The quiet always-present button says "this whole screen is wrong"
 * and needs no target. The button is also the guaranteed path: a gesture can misfire or be
 * swallowed by the platform, and there must always be a way in that cannot.
 *
 * ── why touch only for the long press ───────────────────────────────────────
 * A mouse press-and-hold is already meaningful in this app (the desktop shell has drag-to-
 * reparent and the pane dividers are mousedown/mousemove — `Surface.tsx`). Claiming hold on a
 * mouse would break both. Desktop gets the keyboard shortcut instead, reading the last pointer
 * position so it still knows what she was looking at.
 *
 * ⚠ RISK, to check on the real phone: iOS Safari raises its own callout and text selection on a
 * long press. The overlay opening over the top should make that moot, but if the callout wins,
 * the fix is `-webkit-touch-callout: none` plus preventDefault on `contextmenu` in the app
 * shell. The quiet button is unaffected either way, which is the point of having it.
 */
export function useFrictionCapture() {
  const [state, setState] = useState<CaptureState>(CLOSED);
  const busyRef = useRef(false);
  const timer = useRef<number | null>(null);
  const origin = useRef<{ x: number; y: number; el: Element | null } | null>(null);
  const lastPointer = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const begin = useCallback((el?: Element | null, via: CaptureVia = 'button') => {
    // A second trigger while one is rendering would race two snapshots into one state slot.
    if (busyRef.current) return;
    busyRef.current = true;
    const target = describeTarget(el ?? null);
    setState({ open: false, busy: true, shot: null, target, via });
    void snapshot(document.body).then((shot) => {
      busyRef.current = false;
      // Opens even when `shot` is null. A failed render must not swallow the whole capture —
      // the overlay says so plainly and she can still write the entry.
      setState({ open: true, busy: false, shot, target, via });
    });
  }, []);

  const close = useCallback(() => {
    busyRef.current = false;
    setState(CLOSED);
  }, []);

  const cancelPress = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    origin.current = null;
  }, []);

  useEffect(() => {
    const onDown = (e: PointerEvent) => {
      lastPointer.current = { x: e.clientX, y: e.clientY };
      if (e.pointerType !== 'touch') return;
      cancelPress();
      const el = e.target instanceof Element ? e.target : null;
      origin.current = { x: e.clientX, y: e.clientY, el };
      timer.current = window.setTimeout(() => {
        timer.current = null;
        const o = origin.current;
        origin.current = null;
        if (o) begin(o.el, 'longpress');
      }, LONG_PRESS_MS);
    };

    // Right click, in the native window only. `isNative()` is a synchronous URL read, so this is
    // settled on the first render — in a browser the listener is never attached at all and the
    // browser's own menu is untouched.
    const onContextMenu = (e: MouseEvent) => {
      if (!isNative()) return;
      e.preventDefault();
      begin(e.target instanceof Element ? e.target : null, 'rightclick');
    };

    const onMove = (e: PointerEvent) => {
      lastPointer.current = { x: e.clientX, y: e.clientY };
      const o = origin.current;
      if (!o) return;
      if (Math.abs(e.clientX - o.x) > MOVE_TOLERANCE_PX || Math.abs(e.clientY - o.y) > MOVE_TOLERANCE_PX) {
        cancelPress();
      }
    };

    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        const { x, y } = lastPointer.current;
        begin(document.elementFromPoint(x, y), 'shortcut');
      }
    };

    window.addEventListener('pointerdown', onDown, true);
    window.addEventListener('pointermove', onMove, true);
    window.addEventListener('pointerup', cancelPress, true);
    window.addEventListener('pointercancel', cancelPress, true);
    window.addEventListener('keydown', onKey);
    window.addEventListener('contextmenu', onContextMenu);
    return () => {
      cancelPress();
      window.removeEventListener('pointerdown', onDown, true);
      window.removeEventListener('pointermove', onMove, true);
      window.removeEventListener('pointerup', cancelPress, true);
      window.removeEventListener('pointercancel', cancelPress, true);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('contextmenu', onContextMenu);
    };
  }, [begin, cancelPress]);

  return { state, begin, close };
}
```

- [ ] **Step 4: Run the tests**

Run: `cd app && npx vitest run src/friction/__tests__/useFrictionCapture.test.ts`
Expected: all PASS

- [ ] **Step 5: Mutation-test the scroll guard**

The scroll-cancel test is the one most likely to be written wrong and pass anyway. Temporarily delete the `cancelPress()` call inside `onMove`, re-run, and confirm `cancels the long press when the finger moves` FAILS. Restore and confirm green.

- [ ] **Step 6: Commit**

```bash
git add app/src/friction/useFrictionCapture.ts app/src/friction/__tests__/useFrictionCapture.test.ts
git commit -m "feat(friction): long-press, keyboard shortcut and quiet-button triggers

Touch-only long press, because mouse press-and-hold already means drag-to-
reparent and the pane dividers in the desktop shell. A moved finger is a
scroll and cancels."
```

---

### Task 7: Mount it on every screen

**Files:**
- Modify: `app/src/shell/Surface.tsx:96-105`
- Create: `app/src/shell/__tests__/surfaceCapture.test.tsx`

**Interfaces:**
- Consumes: `useFrictionCapture` (Task 6), `AnnotateOverlay` (Task 5), `surface.logDay` (Task 4).
- Produces: nothing downstream. This is the wiring task.

`Surface.tsx` is the mount point because it is the **single** place above the phone/desktop fork (`Surface.tsx:104-105`). Mounting here — not in `AppShell` and `DeskShell` separately — is what makes the feature exist on every screen in both shells with one implementation, and it means an in-progress capture survives a window resize across the 900px breakpoint for the same reason the rest of the session state does.

- [ ] **Step 1: Write the failing test**

Create `app/src/shell/__tests__/surfaceCapture.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Surface } from '../Surface.tsx';
import { THEMES } from '@tokens';

// Follow whatever fixture/source stubbing the other Surface tests in this directory use.
function renderSurface() {
  return render(<Surface T={THEMES.celestial} name="celestial" setTheme={vi.fn()} source={/* test fixture */ undefined} />);
}

it('offers the capture button on the phone shell', () => {
  renderSurface();
  expect(screen.getByRole('button', { name: /log what is wrong/i })).toBeInTheDocument();
});

it('opens the capture overlay from the button', async () => {
  renderSurface();
  fireEvent.click(screen.getByRole('button', { name: /log what is wrong/i }));
  await waitFor(() =>
    expect(screen.getByRole('dialog', { name: /log what is wrong here/i })).toBeInTheDocument(),
  );
});

it('does not appear in the snapshot it takes', () => {
  renderSurface();
  const btn = screen.getByRole('button', { name: /log what is wrong/i });
  expect(btn.closest('[data-cd-capture-chrome]')).not.toBeNull();
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd app && npx vitest run src/shell/__tests__/surfaceCapture.test.tsx`
Expected: FAIL — no such button.

- [ ] **Step 3: Wire it in**

In `app/src/shell/Surface.tsx`, add the imports:

```tsx
import { AnnotateOverlay } from '../friction/AnnotateOverlay.tsx';
import { useFrictionCapture } from '../friction/useFrictionCapture.ts';
import { CHROME_ATTR } from '../friction/capture.ts';
```

and replace the body of `Surface` (lines 96-105) with:

```tsx
  const wideByViewport = useIsDesktop();
  const wide = isNative() || wideByViewport;
  const surface = useSurface({ T, name, setTheme, wide, source });

  // ── the friction capture, mounted ONCE above the fork ──────────────────────
  // Same reason `useSurface` is called here: this is the only place that is on every screen in
  // BOTH shells. Mounted inside AppShell and DeskShell separately it would be two
  // implementations drifting apart, and an in-progress capture would be thrown away by a window
  // resize across 900px — exactly the bug the state placement above exists to prevent.
  const capture = useFrictionCapture();

  return (
    <>
      {wide ? <DeskShell T={T} surface={surface} /> : <AppShell T={T} surface={surface} />}

      {/* The quiet always-there way in. Marked as capture chrome so it is excluded from the
          snapshot — otherwise every image would have this button burned into the corner. */}
      {!capture.state.open && !capture.state.busy ? (
        <button
          type="button"
          {...{ [CHROME_ATTR]: '' }}
          aria-label="Log what is wrong here"
          title="Log what is wrong here (hold, or Cmd-Shift-F)"
          onClick={() => capture.begin(null, 'button')}
          style={{
            position: 'fixed', right: 12, bottom: 12, zIndex: 9998,
            width: 34, height: 34, borderRadius: 17,
            border: `1px solid ${T.line}`, background: T.card, color: T.dim,
            font: 'inherit', fontSize: 15, lineHeight: '1', cursor: 'pointer', opacity: 0.55,
          }}
        >
          !
        </button>
      ) : null}

      {capture.state.open ? (
        <AnnotateOverlay
          T={T}
          shot={capture.state.shot}
          target={capture.state.target}
          onCancel={capture.close}
          onSend={(text, shot, marks, size) =>
            surface.logDay(text, ['issue'], {
              shot,
              view: { tab: surface.ui.tab, detailId: surface.ui.detail?.id ?? null },
              target: capture.state.target,
              via: capture.state.via,
              marks,
              size,
            })
          }
        />
      ) : null}
    </>
  );
```

> **Implementer note:** `surface.ui.tab` and `surface.ui.detail?.id` are the assumed shapes for the current view. Confirm against `useSurface`'s return type and `AppState['ui']` in `useAppState.ts` — `DeskShell.tsx:166-168` already reads `tab` and `ui.detail`, so match exactly what it uses. If `logDay` is not on the `surface` object, find where `AddScreen` reaches it (`ctx.logDay`) and use the same path.

- [ ] **Step 4: Run the tests**

Run: `cd app && npx vitest run && npx tsc --noEmit`
Expected: all PASS, no type errors.

- [ ] **Step 5: Check the button against the desktop app's narrow window**

The native Today window is 392px wide (`native.ts`). A fixed bottom-right control must not sit on top of the phone shell's tab bar or the desktop shell's content. Run the existing screenshot tool and look:

```bash
cd app && node scripts/shot.mjs "today,map" celestial
```

Open the PNGs in `/tmp/cd-shots`. If the button overlaps the tab bar, raise `bottom` above it rather than moving it — bottom-right is the reachable corner on a phone held one-handed.

- [ ] **Step 6: Commit**

```bash
git add app/src/shell/Surface.tsx app/src/shell/__tests__/surfaceCapture.test.tsx
git commit -m "feat(friction): mount the capture on every screen, both shells

Surface is the single place above the phone/desktop fork, so this is one
implementation rather than two, and an in-progress capture survives a resize
across the 900px breakpoint like the rest of the session state."
```

---

### Task 8: Which way in she actually uses — and the retirement question

**Files:**
- Create: `scripts/friction_report.py`
- Create: `tests/test_friction_report.py`

**Interfaces:**
- Consumes: `signal_log.read_signals` (`scripts/signal_log.py:36`).
- Produces: `summarise(signals) -> dict` and a `__main__` that prints it. Shape:

```python
{"total": int, "with_shot": int, "with_marks": int,
 "by_via": {"longpress": int, "shortcut": int, "rightclick": int, "button": int},
 "unused": [str],        # entry points with zero uses
 "rarely_used": [str],   # under 10% of captures, and at least one other way in is doing better
 "since": str|None, "until": str|None}
```

> ⚠ **A BROKEN ENTRY POINT AND AN UNUSED ONE LOOK IDENTICAL HERE — and the report would blame
> June.** Found while building Task 6: `document.elementFromPoint` does not exist in jsdom, and
> the keyboard shortcut would have shipped throwing on every keypress. It would have recorded
> zero uses, and this report would then have said "never used: shortcut" — reading as *she does
> not reach for it* when the truth was *it never worked*. That is a false finding about a person,
> produced by a tool that only sees counts.
>
> Two consequences, both required:
> 1. **Task 10 must exercise all four entry points on the real app before any report is trusted.**
>    Zero uses is only evidence if the thing demonstrably works.
> 2. **The report must say this out loud in its own output**, not just here — whoever reads it
>    months from now will not have this plan open.

**Why this exists, and the line it must not cross.** June asked to be able to see whether she
uses both ways in or only one, so an unused one can be retired rather than sitting there forever.
The measurement is of the *mechanism*, not of her. So: this reports on entry points and never on
her rate of logging, her productivity, or her habits, and it **never decides anything**. It prints
what the numbers are and states that retiring one is her call. Nothing is removed automatically,
and this must not become something that prompts or nudges her.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_friction_report.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import friction_report


def sig(via=None, shot=None, marks=None, ts="2026-07-19T10:00:00", source="log_day"):
    ref = {"kind": "log_day", "tags": ["issue"]}
    if via: ref["via"] = via
    if shot: ref["shot"] = shot
    if marks: ref["marks"] = marks
    return {"ts": ts, "source": source, "reference": ref, "raw": "x"}


def test_counts_only_friction_entries():
    out = friction_report.summarise([sig(via="button"), sig(source="config_authoring")])
    assert out["total"] == 1


def test_counts_each_way_in():
    out = friction_report.summarise([sig(via="button"), sig(via="button"), sig(via="longpress")])
    assert out["by_via"]["button"] == 2
    assert out["by_via"]["longpress"] == 1


def test_names_an_entry_point_that_has_never_been_used():
    out = friction_report.summarise([sig(via="button") for _ in range(5)])
    assert "longpress" in out["unused"]
    assert "button" not in out["unused"]


def test_a_rarely_used_way_in_is_reported_but_not_called_unused():
    signals = [sig(via="button") for _ in range(19)] + [sig(via="longpress")]
    out = friction_report.summarise(signals)
    assert out["unused"] == [] or "longpress" not in out["unused"]
    assert "longpress" in out["rarely_used"]


def test_nothing_is_called_unused_before_there_is_enough_to_go_on():
    """Two entries is not evidence. Calling a way in unused on that basis would be a made-up finding."""
    out = friction_report.summarise([sig(via="button"), sig(via="button")])
    assert out["unused"] == []
    assert out["rarely_used"] == []


def test_counts_snapshots_and_marks():
    out = friction_report.summarise([
        sig(via="button", shot="a.png", marks=[{"box": [0, 0, 1, 1]}]),
        sig(via="button", shot="b.png"),
        sig(via="button"),
    ])
    assert out["total"] == 3 and out["with_shot"] == 2 and out["with_marks"] == 1


def test_empty_log_does_not_crash():
    out = friction_report.summarise([])
    assert out["total"] == 0 and out["unused"] == [] and out["since"] is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_friction_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'friction_report'`

- [ ] **Step 3: Write the implementation**

Create `scripts/friction_report.py`:

```python
#!/usr/bin/env python3
"""What the friction log holds, and which way in June actually uses.

⚠ WHAT THIS IS NOT. This does not measure June. It measures MECHANISMS — whether an entry point
the system offers is one she reaches for. It reports no rate of logging, no streak, no trend in
her behaviour, and it never prompts or nudges. She asked for it so an unused way in could be
found and retired instead of sitting there forever; that is the whole scope.

⚠ IT DECIDES NOTHING. Retiring an entry point is June's call, always. This prints the numbers and
says so. (Her instruction, 2026-07-19: "run it by me first though, of course.")
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import signal_log

WAYS_IN = ("longpress", "shortcut", "rightclick", "button")

# Below this, the log has not seen enough use to say anything about an entry point. Calling one
# "unused" after three captures would be inventing a finding out of noise.
MIN_FOR_A_VERDICT = 15
RARE_SHARE = 0.10


def summarise(signals):
    friction = [s for s in signals if s.get("source") == "log_day"]
    refs = [s.get("reference") or {} for s in friction]
    total = len(friction)

    by_via = {w: 0 for w in WAYS_IN}
    for r in refs:
        v = r.get("via")
        if v in by_via:
            by_via[v] += 1

    unused, rarely = [], []
    # Only entry points that EXISTED for these entries can be judged. Entries written before the
    # capture shipped carry no `via` at all, so they are excluded from the denominator rather than
    # counted as evidence against every way in.
    attributed = sum(by_via.values())
    if attributed >= MIN_FOR_A_VERDICT:
        best = max(by_via.values())
        for w in WAYS_IN:
            if by_via[w] == 0:
                unused.append(w)
            elif by_via[w] < attributed * RARE_SHARE and by_via[w] < best:
                rarely.append(w)

    stamps = sorted(s.get("ts") for s in friction if s.get("ts"))
    return {
        "total": total,
        "with_shot": sum(1 for r in refs if r.get("shot")),
        "with_marks": sum(1 for r in refs if r.get("marks")),
        "by_via": by_via,
        "unused": unused,
        "rarely_used": rarely,
        "since": stamps[0] if stamps else None,
        "until": stamps[-1] if stamps else None,
    }


def _print(out):
    print("Friction log — %d entries%s" % (
        out["total"],
        (", %s to %s" % (out["since"], out["until"])) if out["since"] else ""))
    print("  with a picture: %d    with marks drawn on it: %d" % (out["with_shot"], out["with_marks"]))
    print("  how they were started:")
    for w in WAYS_IN:
        print("    %-11s %d" % (w, out["by_via"][w]))
    if out["unused"] or out["rarely_used"]:
        for w in out["unused"]:
            print("  Never used: %s" % w)
        for w in out["rarely_used"]:
            print("  Rarely used: %s" % w)
        # ⚠ Say this every time, not once in a doc. A way in that is BROKEN records zero uses and
        # looks exactly like one she does not want — and the difference is the difference between
        # fixing a bug and removing something she needs. This nearly happened: the keyboard
        # shortcut shipped-ready with a crash on every keypress (caught building Task 6, 2026-07-19).
        print("  ⚠ Check it still WORKS before reading zero as 'not wanted' — a broken way in")
        print("    counts zero too, and that is a bug to fix, not a feature to remove.")
        print("  Whether to remove any of these is your call — nothing has been changed.")
    else:
        print("  Nothing to flag: every way in is getting used, or there is not enough yet to tell.")


if __name__ == "__main__":
    _print(summarise(signal_log.read_signals()))
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_friction_report.py -v`
Expected: all PASS

- [ ] **Step 5: Run it against the real log**

Run: `python3 scripts/friction_report.py`
Expected: it reads June's real `signal_log.jsonl` (79 entries at time of writing, 45 of them `log_day`) without crashing. Every `via` count will be zero and nothing will be flagged, because no entry predates this build — which is the correct output, not a bug.

- [ ] **Step 6: Commit**

```bash
git add scripts/friction_report.py tests/test_friction_report.py
git commit -m "feat(friction): report which way in gets used, so an unused one can be retired

Measures the mechanism, never June — no rate, no streak, no nudge. And it
decides nothing: retirement is her call, which the output says out loud."
```

---

### Task 9: Teach the triage to read a snapshot — and pin the shape it reads

**Files:**
- Create: `docs/friction_triage.md`
- Create: `tests/test_signal_record_shape.py`

**The framing correction this task rests on.** June asked to protect against drift between the
friction signal and "the log instructions," then said she was not sure what instructions exist —
that the triage has only ever been done by hand, and the handoff is a record of one pass rather
than a spec. That is right, and it means **there are no instructions to drift from yet.** So the
work is not a drift guard over an absent document; it is writing the first instruction, and then
making the connection between writer and reader something a test can break. The guard against
drift is not vigilance — it is that `signal_log.py` is the single source of truth for the record
shape, the triage doc quotes it, and a test fails loudly if the writer changes underneath.

- [ ] **Step 1: Write the failing test**

Create `tests/test_signal_record_shape.py`:

```python
"""The contract between what writes a friction entry and what reads one.

⚠ IF THIS TEST FAILS, docs/friction_triage.md IS NOW WRONG. That is the entire point of it: the
triage instructions describe a record shape, and nothing else would notice if the shape moved out
from under them. Fix the doc in the same commit as the schema change, or the next triage pass
reads fields that are not there any more. (June asked for exactly this guard, 2026-07-19.)
"""
import base64, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import signal_log, shot_store

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

# Every key docs/friction_triage.md tells a reader to look at. Adding one here is cheap; removing
# one means the doc has to change too.
DOCUMENTED_REFERENCE_KEYS = {"kind", "tags", "shot", "view", "target", "via", "marks", "size"}
DOCUMENTED_RECORD_KEYS = {"ts", "source", "reference", "raw"}


def test_a_full_capture_record_has_exactly_the_documented_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    name = shot_store.save_png("data:image/png;base64," + base64.b64encode(PNG_1PX).decode())
    signal_log.log_signal("something is wrong here", source="log_day", reference={
        "kind": "log_day", "tags": ["issue"], "shot": name,
        "view": {"tab": "today", "detailId": None},
        "target": {"tag": "button", "label": "Not today", "text": "Not today",
                   "data": {}, "chain": [{"tag": "button", "label": "Not today"}]},
        "via": "longpress",
        "marks": [{"points": [[1, 1], [2, 2]], "box": [1, 1, 1, 1], "closed": False}],
        "size": {"w": 392, "h": 860},
    })
    rec = signal_log.read_signals()[-1]
    assert set(rec) == DOCUMENTED_RECORD_KEYS
    assert set(rec["reference"]) <= DOCUMENTED_REFERENCE_KEYS
    assert rec["reference"]["shot"] == name


def test_the_triage_doc_names_every_key_a_reader_is_told_to_use():
    """A key that exists but is undocumented is invisible to the next triage pass."""
    doc = open(os.path.join(os.path.dirname(__file__), "..", "docs", "friction_triage.md")).read()
    for key in DOCUMENTED_REFERENCE_KEYS:
        assert key in doc, "docs/friction_triage.md never mentions reference.%s" % key


def test_the_triage_doc_names_the_read_route():
    doc = open(os.path.join(os.path.dirname(__file__), "..", "docs", "friction_triage.md")).read()
    assert "/api/shot/" in doc


def test_a_text_only_entry_is_still_valid(tmp_path, monkeypatch):
    """The old shape must keep working — most of the existing 45 entries have no capture at all."""
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    signal_log.log_signal("plain", source="log_day", reference={"kind": "log_day", "tags": ["issue"]})
    rec = signal_log.read_signals()[-1]
    assert set(rec) == DOCUMENTED_RECORD_KEYS
    assert set(rec["reference"]) <= DOCUMENTED_REFERENCE_KEYS
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_signal_record_shape.py -v`
Expected: the two doc tests FAIL — `docs/friction_triage.md` does not exist.

- [ ] **Step 3: Write the triage instructions**

Create `docs/friction_triage.md`:

```markdown
# Reading the friction log

**Status:** first written version, 2026-07-19. Before this, triage was done by hand once and the
only record was `docs/handoff_2026-07-16_friction-log-triage.md` — a record of that one pass, not
instructions. This is the instruction. Revise it as passes teach us more.

⚠ **`tests/test_signal_record_shape.py` pins this document to the code.** If the record shape
changes, that test fails and names this file. Fix both in the same commit.

## Where it is

`scripts/data/signal_log.jsonl` — one JSON object per line, append-only, never rewritten.
Written by `scripts/signal_log.py::log_signal`. Gitignored: it carries June's real medical and
financial detail and does not go to a remote.

## What one entry looks like

Every record: `ts`, `source`, `reference`, `raw`.

Friction entries are the ones with `source == "log_day"`. Other sources
(`checkin_reply`, `config_authoring`, `config_correction`) live in the same file and are **not**
friction — filter first.

`raw` is June's own words, stored verbatim and never classified at write time. `reference` for a
friction entry:

| key | meaning |
|---|---|
| `kind` | always `"log_day"` |
| `tags` | `["issue"]` for friction, `["day"]` for how-the-day-went. Both may appear. |
| `shot` | filename of a PNG of what she was looking at. Absent on a text-only entry. |
| `view` | `{"tab": …, "detailId": …}` — which screen she was on. |
| `target` | what she pressed: `tag`, `label`, `text`, `data`, and `chain` (that element and its ancestors outward). |
| `via` | how she opened the capture: `longpress` / `shortcut` / `rightclick` / `button`. |
| `marks` | what she drew, as geometry: `points`, `box` `[x,y,w,h]`, and `closed`. |
| `size` | the image's pixel dimensions. **`marks` coordinates are in these pixels and mean nothing without it.** |

`resolved` appears on some entries. **No code writes it** — it is added by hand during a triage
pass to record what became of an item. Keep doing that; it is how a pass leaves a trace.

## How to read one

1. **Read `raw` first, and take it at face value.** It is her account of what went wrong. It is
   not a bug report to be corrected into one.
2. **Open the picture if there is one:** `http://localhost:5050/api/shot/<reference.shot>`, or
   directly at `scripts/data/shots/<name>`.
3. **Use `marks` to find where she was pointing.** `box` is the region. `closed: true` reads as
   circling something; `closed: false` reads as pointing at it. This is what the geometry is for
   — a picture alone leaves the extent of a hand-drawn mark ambiguous.
4. **Treat `target` as a hint, never a claim.** Elements overlap and a finger lands slightly off.
   If `label` does not make sense, look outward along `chain`. If it still does not, ignore it —
   `raw` and the picture are the evidence, `target` is a convenience.
5. **`view` tells you which screen to go look at yourself.** Reproduce before concluding.

## What NOT to do

- **Do not classify at read time and write the classification back into the log.** The log is
  capture-only by design; categories are meant to emerge across a pass, not be stamped per entry.
- **Do not treat absence as evidence.** A missing `shot` means the render failed or she used a
  build without it, not that the friction was minor.
- **Do not aggregate her.** Counting entry-point use is fine (`scripts/friction_report.py`).
  Counting *her* — how often she logs, streaks, trends in her behaviour — is not what this is for.
- **Do not send these images anywhere.** They are pictures of her real screen.

## Related

- `scripts/friction_report.py` — what the log holds and which way in gets used.
- `docs/handoff_2026-07-16_friction-log-triage.md` — the first pass, as a worked example.
- `docs/superpowers/plans/2026-07-19-snapshot-friction-capture.md` — why the capture works this way.
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_signal_record_shape.py -v`
Expected: all PASS

- [ ] **Step 5: Mutation-test the drift guard**

This is the test most worth proving, because its whole value is failing at the right moment.
Temporarily remove the `| `via` |` row from `docs/friction_triage.md`, run the suite, and confirm
`test_the_triage_doc_names_every_key_a_reader_is_told_to_use` FAILS naming `via`. Restore it and
confirm green.

- [ ] **Step 6: Commit**

```bash
git add docs/friction_triage.md tests/test_signal_record_shape.py
git commit -m "docs(friction): the first written triage instructions, pinned by a test

There were none — the handoff was a record of one pass, not a spec. So this
writes the instruction and makes the writer/reader connection breakable: change
the record shape and a test fails naming the doc that is now wrong."
```

---

### Task 10: Integration and live verification — REQUIRED

**Files:** none created. This task proves the feature works by driving the real running system on real data.

**Why this task exists and cannot be skipped.** Every piece above can pass its own tests and the feature can still be dead or wrong. This repo has been bitten twice by exactly that: once by a build that matched the design doc and 599 green tests while producing uncheckoffable ghost rows, and once by live-verifying against a server still holding the old code. Unit tests plus a clean diff is not evidence.

**The wiring this connects to, named explicitly:** `app/src/shell/Surface.tsx`'s `Surface()` now renders `AnnotateOverlay` and calls `surface.logDay`, which POSTs to `scripts/server.py`'s `/api/logday` handler, which calls `shot_store.save_png` and `signal_log.log_signal`. That is the full path, and every link is exercised below.

- [ ] **Step 1: Build the frontend**

```bash
cd /Users/june/Documents/GitHub/cyborg-memory/controlled-drift/app && npx vite build
```
Expected: a clean build into `app/dist`. The server serves `/` from there (`server.py:601-612`), so an unbuilt change is invisible no matter how green the tests are.

- [ ] **Step 2: Restart the server by the SAFE protocol**

The running process holds the old Python. Never hand-start it — `server.py` defaults to loopback and hand-starting silently drops June's phone access.

```bash
OLD=$(lsof -ti :5050); echo "old pid: $OLD"
launchctl kickstart -k gui/$(id -u)/com.june.controlled-drift.server
sleep 4; NEW=$(lsof -ti :5050); echo "new pid: $NEW"
lsof -nP -iTCP:5050 -sTCP:LISTEN
tail -20 ~/.controlled-drift/server.log
```
Expected: `NEW` differs from `OLD`, the bind reads `*:5050` and **not** `127.0.0.1:5050`, and the log has no traceback. If the PID did not change you are still testing the old code — stop and fix that first.

- [ ] **Step 3: Prove the backend end-to-end against the running server**

```bash
cd /Users/june/Documents/GitHub/cyborg-memory/controlled-drift
python3 - <<'PY'
import base64, json, urllib.request
png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
body = {"text": "LIVE VERIFY 2026-07-19 — delete me",
        "tags": ["issue"],
        "shot": "data:image/png;base64," + base64.b64encode(png).decode(),
        "view": {"tab": "today", "detailId": None},
        "target": {"tag": "button", "label": "Not today", "text": "Not today", "data": {}}}
req = urllib.request.Request("http://127.0.0.1:5050/api/logday", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
print(json.load(urllib.request.urlopen(req)))
PY
tail -1 scripts/data/signal_log.jsonl
```
Expected: the response carries a real `shot` filename; the last log line has `reference.shot` set to that name, plus `view` and `target`. Then confirm the file and the read route:

```bash
NAME=$(python3 -c "import json;print(json.loads(open('scripts/data/signal_log.jsonl').read().splitlines()[-1])['reference']['shot'])")
ls -l "scripts/data/shots/$NAME"
curl -sS -o /tmp/verify-shot.png -w "%{http_code} %{content_type}\n" "http://127.0.0.1:5050/api/shot/$NAME"
file /tmp/verify-shot.png
```
Expected: the file exists, the curl reports `200 image/png`, and `file` says `PNG image data`.

- [ ] **Step 4: Remove the verification entry**

It is a test artifact in June's real log. Delete that one line from `scripts/data/signal_log.jsonl` and its PNG from `scripts/data/shots/`, then confirm the file's last line is a real entry again. Tests self-clean; so does this.

- [ ] **Step 5: Drive the REAL app — the part that cannot be substituted**

Open the desktop app (double-click `Controlled Drift.app`) **and** `http://127.0.0.1:5050/` in a browser window under 900px wide. On each:

1. Go to Today, on a day with a real plan. Press and hold a real task row (or `Cmd-Shift-F` with the pointer over it).
2. Confirm the overlay opens showing **an actual picture of the screen you were just on** — not a blank, not a black rectangle, not a picture with the capture button in it.
3. Confirm it names what you pressed.
4. Draw two marks. Undo one. Confirm only one remains.
5. Type a multi-line comment.
6. Send. Confirm the "Logged" toast, and that the overlay closes.
7. `tail -1 scripts/data/signal_log.jsonl` and open the referenced PNG. **The drawn mark must be in the image** — this is the check that the composite step actually runs rather than silently falling back to the unannotated original.
8. In that same line, check `reference.marks`: there must be one entry, its `box` must sit roughly where you actually drew (compare against `reference.size`), and `via` must say how you opened it. Coordinate arithmetic cannot be tested in jsdom — a zero-size rect makes every point collapse to the origin — so **this is the only place the mark geometry is genuinely verified.** If the boxes are all `[0,0,0,0]`, the scaling in `at()` is wrong.
9. **Exercise ALL FOUR ways in, and confirm each one actually opens the capture** — long press (phone), right click (native app), `Cmd/Ctrl+Shift+F` (browser), the quiet button (everywhere). This is not thoroughness for its own sake: Task 8 reports an entry point with zero uses as unused, and a BROKEN one records zero too. Shipping a dead trigger would produce a report saying June does not use something that never worked. Zero is only evidence once each one is known to work.
10. **In the desktop app only:** right-click a row. The capture must open with `via: "rightclick"` and no macOS context menu. Then open `http://127.0.0.1:5050/` in a browser and right-click — the **browser's own menu must still appear** and no capture should open. That split is the whole point of confining it to native.
11. Delete every verification entry and its PNG.

**This step is the whole point.** Steps 1-4 prove the pieces are connected. Only this proves the feature does what it is for: that the picture shows what she was actually looking at, that her marks survive, and that the record can be read back later. If the image is blank, black, wrong-looking, or missing the marks, the feature does not work no matter what the suite says.

- [ ] **Step 6: Check the phone**

From June's phone on the LAN (`http://100.86.195.93:5050/`), repeat steps 1-6 above. This is where the long-press is most likely to fight the platform: watch for iOS Safari's own callout or text selection appearing instead of, or on top of, the overlay. If it does, apply the `-webkit-touch-callout: none` / `contextmenu` `preventDefault` fix noted in `useFrictionCapture.ts`, rebuild, and re-check. Confirm the quiet button works regardless.

- [ ] **Step 7: Full suites**

```bash
cd /Users/june/Documents/GitHub/cyborg-memory/controlled-drift && python3 -m pytest tests/ -q
cd app && npx vitest run && npx tsc --noEmit && npx vite build
```
Expected: all green, no new failures.

- [ ] **Step 8: Cross-family review — required before this thread closes**

Per repo CLAUDE.md, every landed build gets a non-Claude review, because a same-family reviewer shares the blind spots of the model that wrote the code.

```bash
python3 ~/.claude/skills/requesting-code-review/github_models_review.py
```
That API caps requests at roughly 8k tokens, so **chunk the diff per file, and send each file together with its tests** — a file sent without its tests gets false-flagged as untested. Triage the findings and apply what is real; record what was rejected and why.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "test(friction): live-verified the snapshot capture end to end

Drove the real app in both shells and on the phone: the image shows the screen
she was on, the drawn marks survive into the stored PNG, and the entry reads
back. Verification entries removed from her real log."
```

---

## Self-Review

**Spec coverage.** Every element of the agreed design maps to a task: in-place capture on every screen (Task 7), DOM-to-PNG rather than the OS screenshot (Task 3), multi-line comment (Task 5), drawing (Task 5), the press-target data June asked about (Tasks 3 and 6), both entry points (Task 6), the view/target mitigation for imperfect rendering (Tasks 2-4), privacy (Task 1), and reuse of the existing friction path rather than a new log (Task 2).

**Placeholder scan.** Three places name a lookup the implementer must do rather than a value I could verify: the server handler class name (Task 2 Step 1), the theme token key names (Task 5 Step 3), and the `surface.ui` shape (Task 7 Step 3). Each is flagged inline with the exact command to resolve it. These are honest unknowns from files I did not read in full, not deferred decisions — and guessing them would have produced code that looks right and does not compile.

**Type consistency.** `PressTarget` is defined once in `capture.ts` (Task 3) and imported by `useAppState.ts` (Task 4), `AnnotateOverlay.tsx` (Task 5) and `useFrictionCapture.ts` (Task 6). `CHROME_ATTR` is defined in `capture.ts` and used in `AnnotateOverlay.tsx` and `Surface.tsx`. `snapshot` and `describeTarget` keep the same signatures across Tasks 3, 6 and their tests. The server's `reference` shape written in Task 2 is exactly what Task 4 sends and Task 8 Step 3 asserts.

## Known risks, carried forward

1. **DOM-to-PNG is a re-render, not a pixel copy.** If the friction being logged is itself a rendering bug, the image may not show it faithfully. Mitigated by storing the view and press target alongside, so the entry stays useful — not eliminated.
2. **iOS long-press may fight Safari's callout.** Task 10 Step 6 checks it on the real phone; the quiet button is the unaffected fallback, which is the main reason there are several ways in.
3. **Four ways in is more than most features need.** The justification is that each covers a case the others cannot (Task 6's table), and Task 8 exists precisely so this can be checked against real use rather than defended forever. If the report shows one going unused, that is a finding, not a failure — and retiring it is June's call.
4. **`via` counts start empty.** Every existing entry predates this build, so the first report will show nothing. It needs a few weeks of real use before it says anything, which `MIN_FOR_A_VERDICT` enforces rather than leaving to judgment.
5. **The triage doc is written but unexercised.** Task 9 writes the first instructions and a test pins them to the record shape, but no triage pass has yet been run *using* them. The first one will find gaps. That is expected — the doc says so.

"""plan_mirror — the plan's readable copy in Anytype (one object, updated in place).

Rendering is pure and tested directly. The Anytype write layer is mocked — no live calls
(and conftest sets CD_DISABLE_PLAN_MIRROR so no test anywhere can hit the real note).
"""
import sys, os, datetime as dt
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import plan_mirror
import plan_generate as pg


_CLOCK_PLAN = {
    "shape": "clock",
    "woven_frame": "a poetic frame that must NOT leak into the mirror",
    "generated_at": "2026-07-12T21:50:42",
    "source": "refresh",
    "blocks": [
        {"label": "Morning", "time": "09:00 – 12:00",
         "framing": "metaphor-laden prose that must NOT leak",
         "items": [
             {"time": "09:00 – 09:15", "task": "Clean the toilet"},
             {"time": "09:15 – 10:00", "task": "Do the dishes"},
         ]},
        {"label": "Midday", "time": "12:00 – 15:00",
         "items": [{"time": "12:00 – 13:00", "task": "Lunch"}]},
    ],
    "still_here": [
        {"label": "Paper revision", "note": "held for a focused session"},
        {"label": "Waiting on surgeon's office"},
    ],
}

_PRIORITY_PLAN = {
    "shape": "priority",
    "generated_at": "2026-07-12T08:00:00",
    "items": [{"name": "First thing"}, {"name": "Second thing"}],
    "still_here": [],
}


# --- rendering (pure) --------------------------------------------------------

def test_render_clock_plan_age_first_blocks_still_footer():
    now = dt.datetime(2026, 7, 12, 22, 0)
    body = plan_mirror.render_body(_CLOCK_PLAN, now=now)
    lines = body.splitlines()
    assert lines[0] == "Built today at 9:50 PM."          # age line first
    assert "**09:00 – 12:00 — Morning**" in body           # block header: time + label
    assert "- 09:00 – 09:15  Clean the toilet" in body     # item: time + name
    assert "Still waiting — not on today's plan:" in body
    assert "- Paper revision — held for a focused session" in body
    assert "- Waiting on surgeon's office" in body          # note-less item renders bare
    assert body.rstrip().endswith(plan_mirror.FOOTER)       # honest two-surfaces footer last


def test_render_does_not_leak_llm_prose():
    # The mirror is times + names only: woven_frame / framing prose (where metaphors live)
    # must never reach June's readable copy.
    body = plan_mirror.render_body(_CLOCK_PLAN, now=dt.datetime(2026, 7, 12, 22, 0))
    assert "poetic frame" not in body
    assert "metaphor-laden" not in body


def test_render_priority_plan_is_numbered_list():
    body = plan_mirror.render_body(_PRIORITY_PLAN, now=dt.datetime(2026, 7, 12, 9, 0))
    assert "a list to pull from, in order" in body
    assert "1. First thing" in body
    assert "2. Second thing" in body


def test_render_age_line_yesterday_and_missing():
    body = plan_mirror.render_body(_CLOCK_PLAN, now=dt.datetime(2026, 7, 13, 8, 0))
    assert body.splitlines()[0] == "Built yesterday at 9:50 PM."
    plan = dict(_CLOCK_PLAN)
    plan.pop("generated_at")
    body = plan_mirror.render_body(plan, now=dt.datetime(2026, 7, 13, 8, 0))
    assert body.splitlines()[0] == "Built recently (the exact time wasn't recorded)."


# --- find-or-create-then-update idempotency (write layer mocked) -------------

class _WriteRecorder:
    """Mocks gsdo_objects + the read-back so mirror_plan runs with zero live calls."""
    def __init__(self):
        self.created, self.updated = [], []
        self.existing_id = None

    def install(self, monkeypatch):
        import gsdo_objects, anytype_test
        monkeypatch.setattr(gsdo_objects, "find_existing",
                            lambda type_key, name: self.existing_id)
        def _create(type_name, name, body=None, properties=None):
            self.created.append((type_name, name, body))
            self.existing_id = "note-1"     # after the first create, find_existing hits
            return "note-1"
        def _update(oid, name=None, properties=None, body=None):
            self.updated.append((oid, body))
            return oid
        monkeypatch.setattr(gsdo_objects, "create", _create)
        monkeypatch.setattr(gsdo_objects, "update", _update)
        # Read-back GET returns a body containing THIS write's age line (the per-write probe),
        # so the verify passes. _CLOCK_PLAN was generated 2026-07-12 21:50 → "today at 9:50 PM"
        # from either `now` the tests use.
        monkeypatch.setattr(anytype_test, "call",
                            lambda method, path, payload=None: (200, {"object": {
                                "id": "note-1",
                                "markdown": "Built today at 9:50 PM.\nrest of body"}}))


def test_mirror_creates_once_then_updates_same_object(monkeypatch):
    rec = _WriteRecorder()
    rec.install(monkeypatch)
    oid1 = plan_mirror.mirror_plan(_CLOCK_PLAN, now=dt.datetime(2026, 7, 12, 22, 0))
    oid2 = plan_mirror.mirror_plan(_CLOCK_PLAN, now=dt.datetime(2026, 7, 12, 23, 0))
    assert oid1 == oid2 == "note-1"                 # ONE object, stable id
    assert len(rec.created) == 1                    # created exactly once
    assert rec.created[0][1] == plan_mirror.MIRROR_NAME
    assert len(rec.updated) == 1                    # second run updates in place
    assert "Clean the toilet" in rec.updated[0][1]  # update carries the rendered body


def test_mirror_read_back_stale_body_raises(monkeypatch):
    # A stale body from a PREVIOUS write (different age line) must FAIL the verify — the
    # probe is per-write, so "some old mirror persists" can't pass as "this write persisted".
    rec = _WriteRecorder()
    rec.install(monkeypatch)
    import anytype_test
    monkeypatch.setattr(anytype_test, "call",
                        lambda method, path, payload=None: (200, {"object": {
                            "id": "note-1",
                            "markdown": "Built yesterday at 8:00 AM.\nold plan body\n"
                                        + plan_mirror.FOOTER}}))
    with pytest.raises(RuntimeError):
        plan_mirror.mirror_plan(_CLOCK_PLAN, now=dt.datetime(2026, 7, 12, 22, 0))


# --- best-effort wrapper ------------------------------------------------------

def test_safe_swallows_failure_and_logs(monkeypatch, capsys):
    monkeypatch.delenv("CD_DISABLE_PLAN_MIRROR", raising=False)
    def boom(plan, now=None):
        raise RuntimeError("Anytype app is closed")
    monkeypatch.setattr(plan_mirror, "mirror_plan", boom)
    assert plan_mirror.mirror_plan_safe(_CLOCK_PLAN) is None   # never raises
    err = capsys.readouterr().err
    assert "plan not mirrored" in err                          # one honest line


def test_safe_noops_under_test_sandbox_guard(monkeypatch):
    # conftest sets CD_DISABLE_PLAN_MIRROR: the safe path must refuse to touch live Anytype.
    def must_not_run(plan, now=None):
        raise AssertionError("mirror_plan must not be reached under the sandbox guard")
    monkeypatch.setattr(plan_mirror, "mirror_plan", must_not_run)
    assert plan_mirror.mirror_plan_safe(_CLOCK_PLAN) is None


# --- wire-in: generate_plan mirrors on success, not on failure ----------------

_CANNED = """prose

```json
{"woven_frame": "f",
 "blocks": [{"label": "Morning", "time": "9:00 AM – 12:00 PM", "framing": "x",
             "items": [{"time": "9:00 – 10:30 AM", "project": "Build",
                        "task": "do the thing", "why": "w", "ref": "T1"}]}],
 "still_here": []}
```
"""


def _stub_generation(monkeypatch):
    monkeypatch.setattr(pg, "build_context",
                        lambda capacity=None, start_time=None, end_time=None, extra=None, **kw:
                        ("ctx", [{"id": "t1", "name": "do the thing"}],
                         dt.datetime(2026, 7, 12, 9, 0), "clock",
                         [], dt.datetime(2026, 7, 12, 18, 0)))
    monkeypatch.setattr(pg, "generate", lambda prompt: _CANNED)
    monkeypatch.setattr(pg, "log_surfaced_batch", lambda items, **k: None)


def test_generate_plan_mirrors_the_saved_plan(monkeypatch):
    _stub_generation(monkeypatch)
    mirrored = []
    monkeypatch.setattr(plan_mirror, "mirror_plan_safe",
                        lambda plan, now=None: mirrored.append(plan))
    saved = pg.generate_plan(source="refresh")
    assert len(mirrored) == 1
    assert mirrored[0] is saved            # mirrors exactly what was cached


def test_generate_plan_failure_does_not_mirror(monkeypatch):
    _stub_generation(monkeypatch)
    monkeypatch.setattr(pg, "generate",
                        lambda prompt: (_ for _ in ()).throw(RuntimeError("backend down")))
    mirrored = []
    monkeypatch.setattr(plan_mirror, "mirror_plan_safe",
                        lambda plan, now=None: mirrored.append(plan))
    with pytest.raises(RuntimeError):
        pg.generate_plan(source="refresh")
    assert mirrored == []                  # no mirror of a failed generation


def test_mirror_failure_never_breaks_generation(monkeypatch):
    # Even if the SAFE wrapper itself somehow raised, generate_plan still returns the plan.
    _stub_generation(monkeypatch)
    monkeypatch.setattr(plan_mirror, "mirror_plan_safe",
                        lambda plan, now=None: (_ for _ in ()).throw(RuntimeError("boom")))
    saved = pg.generate_plan(source="refresh")
    assert saved["blocks"]                 # generation unaffected

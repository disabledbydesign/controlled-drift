"""The contract between what writes a friction entry and what reads one.

⚠ IF THIS TEST FAILS, docs/friction_triage.md IS NOW WRONG. That is the entire point of it: the
triage instructions describe a record shape, and nothing else would notice if the shape moved out
from under them. Fix the doc in the same commit as the schema change, or the next triage pass
reads fields that are not there any more. (June asked for exactly this guard, 2026-07-19.)

The single source of truth for the record is scripts/signal_log.py::log_signal (the four record
keys) together with scripts/server.py's /api/logday handler (which reference keys a friction entry
can carry). The doc quotes that shape; these tests are what make the quote breakable.
"""
import base64, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import signal_log, shot_store

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

DOC_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "friction_triage.md")

# Every key docs/friction_triage.md tells a reader to look at. Adding one here is cheap; removing
# one means the doc has to change too. These are exactly the keys /api/logday can put in
# `reference` for a log_day entry.
DOCUMENTED_REFERENCE_KEYS = {"kind", "tags", "shot", "view", "target", "via", "marks", "size"}
# What signal_log.log_signal writes, and all it writes. `resolved` is deliberately NOT here: no
# code writes it, it is added by hand during a triage pass, so a freshly written record must not
# have it.
DOCUMENTED_RECORD_KEYS = {"ts", "source", "reference", "raw"}


def _doc():
    with open(DOC_PATH) as f:
        return f.read()


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
    assert set(rec) == DOCUMENTED_RECORD_KEYS, (
        "signal_log now writes %s, but docs/friction_triage.md says a record is %s"
        % (sorted(set(rec)), sorted(DOCUMENTED_RECORD_KEYS))
    )
    undocumented = set(rec["reference"]) - DOCUMENTED_REFERENCE_KEYS
    assert not undocumented, (
        "reference now carries %s, which docs/friction_triage.md does not describe"
        % sorted(undocumented)
    )
    assert rec["reference"]["shot"] == name


def test_the_triage_doc_names_every_key_a_reader_is_told_to_use():
    """A key that exists but is undocumented is invisible to the next triage pass."""
    doc = _doc()
    for key in sorted(DOCUMENTED_REFERENCE_KEYS):
        assert key in doc, "docs/friction_triage.md never mentions reference.%s" % key


def test_the_triage_doc_names_the_read_route():
    doc = _doc()
    assert "/api/shot/" in doc, (
        "docs/friction_triage.md does not tell a reader how to open a stored snapshot "
        "(the GET /api/shot/{name} route in scripts/server.py)"
    )


def test_the_triage_doc_names_the_sources_that_are_not_friction():
    """Filtering by source is step one of a pass; the doc has to name what it is filtering out."""
    doc = _doc()
    for source in signal_log.SOURCES:
        assert source in doc, (
            "signal_log.SOURCES includes %r but docs/friction_triage.md never names it, so a "
            "triage pass would not know whether to filter it out" % source
        )


def test_a_text_only_entry_is_still_valid(tmp_path, monkeypatch):
    """The old shape must keep working — every one of the existing 45 log_day entries in June's
    real log predates the capture and carries only `kind` and `tags`."""
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    signal_log.log_signal("plain", source="log_day", reference={"kind": "log_day", "tags": ["issue"]})
    rec = signal_log.read_signals()[-1]
    assert set(rec) == DOCUMENTED_RECORD_KEYS, (
        "a text-only entry now writes %s rather than %s"
        % (sorted(set(rec)), sorted(DOCUMENTED_RECORD_KEYS))
    )
    assert set(rec["reference"]) <= DOCUMENTED_REFERENCE_KEYS


def test_nothing_writes_the_resolved_key(tmp_path, monkeypatch):
    """docs/friction_triage.md tells the reader `resolved` is added BY HAND during a pass. If some
    code starts writing it, that instruction is wrong and the doc has to say so."""
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    signal_log.log_signal("x", source="log_day", reference={"kind": "log_day", "tags": ["issue"]})
    rec = signal_log.read_signals()[-1]
    assert "resolved" not in rec, (
        "log_signal now writes `resolved`, but docs/friction_triage.md says no code does"
    )
    assert "resolved" in _doc(), "docs/friction_triage.md never explains the hand-added `resolved` key"


def test_the_stored_record_is_one_json_object_per_line(tmp_path, monkeypatch):
    """The doc tells a reader to read the file line by line. That has to stay true."""
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))
    signal_log.log_signal("first\nwith a newline in it", source="log_day",
                          reference={"kind": "log_day", "tags": ["issue"]})
    signal_log.log_signal("second", source="log_day", reference={"kind": "log_day", "tags": ["day"]})
    with open(os.path.join(str(tmp_path), "signal_log.jsonl")) as f:
        lines = [ln for ln in f if ln.strip()]
    assert len(lines) == 2, "a two-entry log wrote %d lines, so it is no longer line-per-record" % len(lines)
    assert json.loads(lines[0])["raw"] == "first\nwith a newline in it"

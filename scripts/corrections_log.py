#!/usr/bin/env python3
"""Append-only log of June's CORRECTIONS — anything she changed that the system had proposed —
AND of what the system itself authored, so the two can be told apart.

RENAMED 2026-07-18 (was `plan_corrections_log` / `plan_corrections.jsonl`). It began as a
plan-only log (§9 item 7) but `kind` always distinguished record types, and it now also carries
field-semantics revisions. The old name understated its scope, and the repo rule is to route new
signals through an EXISTING log rather than add a thirteenth — so the name widened instead.
Existing records were migrated; `kind` values are unchanged.

v1 logs only; the learning loop reads it but does not yet act on it.

WHY AUTHORSHIP LIVES HERE (2026-07-18, docs/api_contract_v2.md §7)
------------------------------------------------------------------
June edits a value SHE entered -> an ordinary edit; she changed her mind. June edits a value the
LLM authored -> a CORRECTION OF THE MODEL, the highest-value learning signal the system can
produce. Telling them apart requires knowing who authored the value being overwritten, and until
now nothing recorded that (the one exception is `Duration source`, which stays ON the object
because the SCHEDULER reads it — that is the test for any exception: does something other than
the learning loop read it?).

Provenance is a fact about HISTORY, not part of the domain model. Nothing in planning, selection
or rendering needs to know who authored a field. So it lives in this log and never on an Anytype
object: the objects stay clean, no schema bloat, and nothing has to be migrated through §5 type
conversion (a second chance to lose it).

⚠ DIVERGENCE FROM docs/api_contract_v2.md §7.5, deliberate. That section's [INFERRED] suggestion
was to put authorship stamps in `signal_log.jsonl` under a `"llm_authorship"` source tag, and it
explicitly invited the alternative ("if that placement is wrong..."). It is wrong: `signal_log`
is documented as "June's own words... CAPTURE ONLY", and an authorship stamp is the system
recording what IT generated — the opposite of her voice, and high enough in volume to swamp hers.
This log already discriminates record types by `kind`, already holds the correction half, and
`log_correction(kind, before, after)` already has the exact shape §7.4(1) asks for
(`before: null`, `after: <value>`). Co-locating them means ONE forward-fold over ONE file
resolves `authored_by`, which is the property §7.5 actually wanted. No new log either way.

`'unknown'` IS A REAL, HONEST VALUE. Every object written before this shipped has no provenance.
Guessing `'user'` for those would poison the loop with false negatives ("she rarely corrects the
model") — worse than having no data, because it looks like data. The loop must filter to
`authored_by == 'llm'` and treat `'unknown'` as unusable, never as `'user'`.

The path resolves through cd_paths at call time (default scripts/data/corrections.jsonl), so the
test suite's sandbox redirect deterministically keeps test runs out of real data.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths

# Field names for the parts of an object that are not ordinary properties. Same vocabulary as
# docs/api_contract_v2.md §7.4, plus `__filing__` (below).
TITLE_FIELD = "__title__"
#: Not a field on the object at all — the weeding gate's account of WHY it filed an item where it
#: did (its dedup + routing justification). This used to be written into the object's `Context`,
#: where June reads it and the planner re-reads it on every generation; it is process output, so
#: it belongs in history. Logging it here keeps the durability that motivated the 2026-07-02
#: decision without putting the model's reasoning in a field that means something else.
FILING_FIELD = "__filing__"

AUTHORS = ("llm", "user", "unknown")


def _path(path=None):
    return path or cd_paths.data_file("corrections.jsonl")


def _append(rec, path=None):
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def log_correction(kind, before, after, path=None, *, object_id=None, object_type=None,
                   field=None, authored_by=None, surface=None, generation_id=None):
    """kind: e.g. 'move_time' | 'reject' | 'reorder' | 'field_semantics'. before/after: JSON-serializable or None.

    The keyword provenance arguments are all optional and are written only when given, so every
    pre-existing caller and every pre-existing record keeps its exact shape. When present,
    `authored_by` means WHO AUTHORED `before` — the value June is overwriting — which is the
    load-bearing fact for the learning loop.
    """
    if authored_by is not None and authored_by not in AUTHORS:
        raise ValueError(f"authored_by must be one of {AUTHORS}, got {authored_by!r}")
    rec = {"ts": dt.datetime.now().isoformat(), "kind": kind, "before": before, "after": after}
    for key, val in (("object_id", object_id), ("object_type", object_type), ("field", field),
                     ("authored_by", authored_by), ("surface", surface),
                     ("generation_id", generation_id)):
        if val is not None:
            rec[key] = val
    _append(rec, path)


def log_authorship(object_id, field, value, *, object_type=None, authored_by="llm",
                   surface=None, generation_id=None, path=None):
    """Record that `field` on `object_id` was authored with `value` by `authored_by`.

    An authorship stamp, not a correction: `before` is null and `after` is the value written.
    Emitted by the LLM write paths at creation time (capture, plan generation, focus-period
    authoring) so that a LATER edit by June can resolve what it is overwriting.

    Grain is FIELD-level, not object-level, on purpose: one object legitimately carries both
    LLM-authored and user-authored fields at once. The clearest case is a Focus Period, whose
    `Intent` is always June's own words (never reworded — backend spec §17) while every other
    structured field on the same object is the model's.
    """
    if authored_by not in AUTHORS:
        raise ValueError(f"authored_by must be one of {AUTHORS}, got {authored_by!r}")
    log_correction("authorship", None, value, path=path, object_id=object_id,
                   object_type=object_type, field=field, authored_by=authored_by,
                   surface=surface, generation_id=generation_id)


def read_records(path=None):
    """Every record, in append order. Empty list if the log doesn't exist yet."""
    try:
        with open(_path(path)) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def resolve_authored_by(object_id, field, path=None):
    """Who authored the CURRENT value of `field` on `object_id`: 'llm' | 'user' | 'unknown'.

    A forward fold over the log, last-write-wins:
      - the most recent `authorship` stamp for this (object_id, field) gives its `authored_by`;
      - a more recent CORRECTION means June overwrote it, so the current value is hers -> 'user'
        (the record's own `authored_by` describes the value she replaced, not the one now there);
      - nothing recorded at all -> 'unknown', which is honest and must not be read as 'user'.
    """
    answer = "unknown"
    for rec in read_records(path):
        if rec.get("object_id") != object_id or rec.get("field") != field:
            continue
        if rec.get("kind") == "authorship":
            answer = rec.get("authored_by") or "unknown"
        else:
            answer = "user"
    return answer

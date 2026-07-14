#!/usr/bin/env python3
"""Block chunk length — the per-project duration of a "work on X" block.

TWO stores, on purpose (display_grain_design.md decision 2):

  1. The SETTLED length is a durable Project preference in Anytype (field "Block chunk
     min"), alongside Side/Engagement — backed up, visible to the map + agent surface.
     `get_chunk_min` reads it (off the loaded project dict); `set_chunk_min` writes it.

  2. Every scheduling/set EVENT is also appended to a local timestamped log
     (block_duration_log.jsonl). This is the raw material Plan 2's recency-weighted
     proposal will mine — the full `ts` is kept so weekday and time-of-day are derivable
     later (June doesn't yet know which patterns matter; log rich now, mine later).

This split follows Anytype-is-master: durable preference -> Anytype; ephemeral/analytic
raw material -> local. The log path resolves through cd_paths at call time, so tests stay
sandboxed. Mirrors the completion_log / chunk_log append idiom.
"""
import os, json, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths
import gsdo_objects

BLOCK_DEFAULT_MIN = 90   # cold-start length, used only when the Project field is unset


def _path(path=None):
    return path or cd_paths.data_file("block_duration_log.jsonl")


def _append(event, project_id, minutes, path=None):
    rec = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
           "date": dt.date.today().isoformat(),
           "event": event, "project_id": project_id, "minutes": int(minutes)}
    p = _path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def get_chunk_min(project, default=BLOCK_DEFAULT_MIN):
    """The project's settled chunk length in minutes, or `default` when unset.

    Reads the "chunk_min" key off the loaded project dict (daily_plan.load_active_items
    reads Anytype's "Block chunk min" field into it). A number field can come back as a
    float; normalize to int."""
    v = project.get("chunk_min")
    return int(v) if v is not None else default


def _get_object(object_id):
    """Re-fetch one object to read its persisted state. Raises if it can't be read."""
    from anytype_test import call
    import gsdo_anytype as g
    st, b = call("GET", f"/spaces/{g.get_space_id()}/objects/{object_id}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"could not read back {object_id!r}: {st} {b}")
    return b["object"]


def set_chunk_min(project_id, minutes, path=None):
    """Persist June's chosen chunk length: write the durable Anytype Project field, PROVE it
    persisted (read-back — a good answer is not a saved object), THEN append the local 'set'
    event (so a logged event always reflects a real write). Property passed by display name
    ("Block chunk min"); its auto-generated key is block_chunk_min. Raises on mismatch."""
    minutes = int(minutes)
    gsdo_objects.update(project_id, properties={"Block chunk min": minutes})
    obj = _get_object(project_id)
    pv = {p.get("key"): p for p in obj.get("properties", [])}
    got = (pv.get("block_chunk_min", {}) or {}).get("number")
    if got != minutes:
        raise RuntimeError(
            f"set_chunk_min({project_id!r}): Block chunk min did not persist (wrote {minutes}, read-back={got!r})")
    _append("set", project_id, minutes, path)


def log_scheduled(project_id, minutes, path=None):
    """Record that a block of this length was scheduled today — a timestamped event only
    (no Anytype write); the raw material for the future recency-weighted proposal."""
    _append("scheduled", project_id, minutes, path)


def read_events(path=None):
    p = _path(path)
    try:
        with open(p) as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []

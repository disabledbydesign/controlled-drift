#!/usr/bin/env python3
"""Mutations the overlay performs on Anytype tasks — the surface acting, not just planning.

So far the overlay only *plans* (reads) and *negotiates* (regenerates). This is the first
write June makes through the surface: marking a task done from where she already is, no
terminal, no app-switch. It is the UI expression of the two-layer "who closes Done" design —
June-facing tasks, June closes here; agent-facing tasks, the finishing agent closes.

Discipline (CLAUDE.md): a good answer is not a saved object. Every mutation here re-fetches
the object and PROVES the change persisted before reporting success — never "I PATCHed it,
probably fine." Raises on any failure; nothing silent.
"""
import sys, time, os
import datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call
import gsdo_anytype as g
import gsdo_objects
import when_resolve

# Live property keys (confirmed 2026-07-12): the Scheduled date and the GSDO Task status select.
SCHEDULED_KEY = "scheduled"
TASK_STATUS_KEY = "gsdo_task_status"


def _get_object(task_id):
    """Re-fetch one object to read its persisted state. Raises if it can't be read."""
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{task_id}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"could not read back task {task_id!r}: {st} {b}")
    return b["object"]


def complete_task(task_id):
    """Mark a task done in Anytype and confirm it persisted. Returns the confirmed state:
        {"id", "name", "status": "Done", "done": True}

    Completion = the GSDO **Task status** select -> 'Done' (`gsdo_task_status`). This is the
    property the whole system already uses — the weeding pipeline, orient_map, how June
    closed tasks in session 15, and what she sees in Anytype. Verified live: the built-in
    `status`/`done` properties are vestigial (always empty), so writing them would split the
    task's truth in two. One property, the one everything else reads.
    """
    gsdo_objects.update(task_id, properties={"Task status": "Done"})

    # Read back and PROVE it — a good answer is not a saved object.
    obj = _get_object(task_id)
    pv = {p.get("key"): p for p in obj.get("properties", [])}
    status = (pv.get("gsdo_task_status", {}).get("select") or {}).get("name")
    if status != "Done":
        raise RuntimeError(
            f"complete_task({task_id!r}): Task status did not persist (read-back={status!r})")
    # Durable actual-side record (the completed half of planned-vs-actual). Logged only AFTER
    # the read-back proof, so a logged completion always reflects a real one. Best-effort: the
    # completion already persisted in Anytype — a logging hiccup must never fail it.
    try:
        import completion_log
        completion_log.log_completion(task_id, obj.get("name"))
    except Exception:
        pass
    return {"id": task_id, "name": obj.get("name"), "status": "Done", "done": True}


def set_task_duration(item_id, minutes):
    """Set an item's estimated duration (minutes) on its Anytype object + PROVE it persisted.
    Works for any object carrying the shared 'Duration min' field (a real task or recurring) —
    the persistent side of the general duration-edit surface. A block's length is a Project
    preference, handled separately in block_duration; the /api/duration route dispatches between
    them. Raises on a read-back mismatch (no silent write)."""
    minutes = int(minutes)
    gsdo_objects.update(item_id, properties={"Duration min": minutes})
    obj = _get_object(item_id)
    pv = {p.get("key"): p for p in obj.get("properties", [])}
    got = (pv.get("gsdo_duration_min", {}) or {}).get("number")
    if got != minutes:
        raise RuntimeError(
            f"set_task_duration({item_id!r}): Duration min did not persist (wrote {minutes}, read-back={got!r})")
    return {"id": item_id, "name": obj.get("name"), "duration_min": minutes}


def uncomplete_task(task_id):
    """Undo a completion — the mis-tap fix. Sets Task status back to 'Ready' (the canonical
    active/execution-ready status), so the task returns to the plan. Read-back confirmed.

    Reverts to 'Ready' rather than restoring the exact prior status: a task that lands in a
    plan is Active/Ready/None anyway, so 'Ready' is the right general 'it's live again' state
    — we don't carry a per-task status-history just to cover a rarer case (keep it simple).
    Completion is the common path; this is the safety valve for a wrong tap.
    """
    gsdo_objects.update(task_id, properties={"Task status": "Ready"})

    obj = _get_object(task_id)
    pv = {p.get("key"): p for p in obj.get("properties", [])}
    status = (pv.get("gsdo_task_status", {}).get("select") or {}).get("name")
    if status != "Ready":
        raise RuntimeError(
            f"uncomplete_task({task_id!r}): Task status did not persist (read-back={status!r})")
    try:
        import completion_log
        completion_log.log_uncompletion(task_id)
    except Exception:
        pass
    return {"id": task_id, "name": obj.get("name"), "status": "Ready", "done": False}


def complete_stream(stream_id):
    """Mark a work-stream (Project) Done in Anytype and confirm it persisted. Returns:
        {"id", "name", "engagement": "Done", "done": True}

    Completion for a STREAM = the Engagement select -> 'Done' — the property the whole
    map already reads (orient_map routes engagement == 'Done' to the Finished section).
    One property, the one everything else reads: same principle as complete_task.

    Used by the monthly status checker (status_check.py) for its ONE allowed autonomous
    change: marking demonstrably-finished work as Done. The checker's gate — not this
    function — decides WHETHER; this function only makes the write honest (read-back).
    """
    gsdo_objects.update(stream_id, properties={"Engagement": "Done"})

    obj = _get_object(stream_id)
    pv = {p.get("key"): p for p in obj.get("properties", [])}
    eng = (pv.get("engagement", {}).get("select") or {}).get("name")
    if eng != "Done":
        raise RuntimeError(
            f"complete_stream({stream_id!r}): Engagement did not persist (read-back={eng!r})")
    return {"id": stream_id, "name": obj.get("name"), "engagement": "Done", "done": True}


def _when_label(scheduled, is_today, is_parked):
    """The chip label for a task's 'when' — same shape the capture receipt uses (Today / a short
    date like 'Thu Jul 16' / Parked). Kept local so this module stays decoupled from the capture
    stack (a pure 4-line formatter, not worth a cross-module import)."""
    if is_today:
        return "Today"
    if scheduled:
        return dt.date.fromisoformat(scheduled).strftime("%a %b %-d")
    if is_parked:
        return "Parked"
    return None


def reschedule_task(task_id, when_text, today=None):
    """Tap-to-fix a captured task's 'when' from the receipt. Anchors the resolver TOKEN the chip
    sends (today/tomorrow/someday/a weekday/ISO) to a real date, then either WRITES a Scheduled
    date or SETS status Parked — it NEVER clears a date (that sidesteps gsdo_objects.update
    dropping None, and 'someday' → Parked already drops the task off today via status alone).
    Read-back PROVES it persisted (a good answer is not a saved object): the date is confirmed by
    comparing PARSED dates (tolerant of Anytype's datetime/tz normalization), never raw strings.
    Returns {"id", "when_label"}. Raises on a genuine mismatch or an unresolvable when."""
    today = today or dt.date.today()
    scheduled, is_today, is_parked = when_resolve.resolve_when(when_text, today)

    if is_parked:
        gsdo_objects.update(task_id, properties={"Task status": "Parked"})
        obj = _get_object(task_id)
        pv = {p.get("key"): p for p in obj.get("properties", [])}
        status = (pv.get(TASK_STATUS_KEY, {}).get("select") or {}).get("name")
        if status != "Parked":
            raise RuntimeError(
                f"reschedule_task({task_id!r}): park did not persist (read-back status={status!r})")
    elif scheduled:
        gsdo_objects.update(task_id, properties={"Scheduled": scheduled})
        obj = _get_object(task_id)
        pv = {p.get("key"): p for p in obj.get("properties", [])}
        persisted = when_resolve._as_date(pv.get(SCHEDULED_KEY, {}).get("date"))
        intended = when_resolve._as_date(scheduled)
        # Confirm the date landed. A present-but-different date is a genuine failure; a mere
        # format difference (T00:00:00Z vs date) is not — both sides are parsed to compare.
        # An ABSENT date is a failure, not a pass: the write silently not landing is exactly
        # what read-back exists to catch (a None here used to slip through this guard).
        if persisted != intended:
            raise RuntimeError(
                f"reschedule_task({task_id!r}): Scheduled did not persist "
                f"(read-back={persisted!r}, intended={intended!r})")
    else:
        # The chip only ever sends resolvable tokens; an unresolvable one is surfaced, not
        # silently swallowed (and we never clear a date to "fix" it).
        raise ValueError(f"reschedule_task({task_id!r}): could not resolve when {when_text!r}")

    return {"id": task_id, "when_label": _when_label(scheduled, is_today, is_parked)}


# Anytype archives asynchronously; see the polling note in archive_object. Small and bounded —
# the observed lag was well under a second, and a real failure must still surface quickly.
_ARCHIVE_POLL_TRIES = 6
_ARCHIVE_POLL_DELAY = 0.25


def _archived_marker(obj):
    """Is this re-fetched object marked archived? True / False / None (no marker field at all).

    DELETE archives rather than hard-deletes, so the object may still be readable — the proof of
    removal is therefore a marker on the object, not a 404. Anytype's Object schema carries this
    as a top-level `archived` bool; the aliases are tolerated so a field rename doesn't turn a
    real archive into a spurious failure. None means "this object exposes no archived marker",
    which is undetermined, not success — the caller must NOT read it as confirmation.
    """
    for key in ("archived", "is_archived", "deleted", "is_deleted"):
        if key in obj:
            return bool(obj[key])
    props = {p.get("key"): p for p in obj.get("properties", [])}
    for key in ("archived", "is_archived"):
        p = props.get(key)
        if isinstance(p, dict) and "checkbox" in p:
            return bool(p["checkbox"])
    return None


def archive_object(object_id):
    """Undo a just-made capture by moving the object to Anytype's bin (DELETE archives, it
    doesn't hard-delete — recoverable in the app). The honest undo of a *creation* is removal,
    not a status flip. Returns {"id","archived"}; raises on anything unproven.

    A good answer is not a saved object — and an accepted DELETE is not an archived object. The
    HTTP status only says the API took the request, so this re-fetches and confirms the removal
    in the object's OWN state: either it is no longer readable (404/410) or it comes back carrying
    an archived marker. An object that reads back live and unmarked is a failed undo and raises.
    """
    sid = g.get_space_id()
    st, b = call("DELETE", f"/spaces/{sid}/objects/{object_id}")
    if st not in (200, 204):
        raise RuntimeError(f"could not archive object {object_id!r}: {st} {b}")

    # Read back and PROVE it — never confirm an undo on the API's acknowledgment alone.
    #
    # ⚠ POLL, do not read once. CONFIRMED LIVE 2026-07-18 by the type-conversion probe: the
    # FIRST re-fetch immediately after a successful DELETE read `archived: False`, and a moment
    # later read True. **Anytype archives ASYNCHRONOUSLY**, the same way schema tag/property
    # deletes do (BUILD_DOC §6). A single immediate read-back therefore reports FAILURE for an
    # archive that actually succeeded — and `delete_object` inherits that.
    #
    # BUILD_DOC §6 carried this as "archive_object re-fetch behavior after DELETE is UNCONFIRMED,
    # needs one live undo". That probe was the live undo; the answer is that it is a race.
    #
    # Polling keeps the discipline intact — an object that never marks archived STILL raises, so
    # a genuine failure is not swallowed. Only the timing assumption changed.
    last = None
    for attempt in range(_ARCHIVE_POLL_TRIES):
        st2, b2 = call("GET", f"/spaces/{sid}/objects/{object_id}")
        if st2 in (404, 410):
            return {"id": object_id, "archived": True}
        if st2 != 200 or not isinstance(b2, dict) or "object" not in b2:
            raise RuntimeError(
                f"could not confirm archive of {object_id!r}: read-back {st2} {b2}")
        last = _archived_marker(b2["object"])
        if last is True:
            return {"id": object_id, "archived": True}
        if attempt < _ARCHIVE_POLL_TRIES - 1:
            time.sleep(_ARCHIVE_POLL_DELAY)
    raise RuntimeError(
        f"archive_object({object_id!r}): object still reads back unarchived after "
        f"{_ARCHIVE_POLL_TRIES} checks over ~{_ARCHIVE_POLL_TRIES * _ARCHIVE_POLL_DELAY:.1f}s "
        f"(archived marker={last!r})")


if __name__ == "__main__":
    # Manual live check: python3 scripts/task_actions.py <task_id>
    if len(sys.argv) != 2:
        print("usage: python3 scripts/task_actions.py <task_id>")
        sys.exit(2)
    import json
    print(json.dumps(complete_task(sys.argv[1]), indent=2))

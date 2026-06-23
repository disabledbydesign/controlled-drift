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
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call
import gsdo_anytype as g
import gsdo_objects


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
    return {"id": task_id, "name": obj.get("name"), "status": "Done", "done": True}


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
    return {"id": task_id, "name": obj.get("name"), "status": "Ready", "done": False}


if __name__ == "__main__":
    # Manual live check: python3 scripts/task_actions.py <task_id>
    if len(sys.argv) != 2:
        print("usage: python3 scripts/task_actions.py <task_id>")
        sys.exit(2)
    import json
    print(json.dumps(complete_task(sys.argv[1]), indent=2))

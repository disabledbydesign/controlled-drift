#!/usr/bin/env python3
"""Controlled Drift MCP server — the agent-facing surface over Anytype.

WHY THIS EXISTS. Operating Controlled Drift from a cold Claude instance currently means
invoking the `drift` skill (~200 lines) so the instance learns the write layer, the type model,
the link properties, and the read-back discipline. That's discoverability-at-read-time: the
protocol is a document the agent has to parse before it can act. This server makes the protocol
*the interface* — each tool is a verb the agent can call directly, with the type model and the
read-back already baked in. A cold agent doesn't read about how to create a task; it calls
create_task. The drift skill stays for June's interactive sessions (capture/weed/plan/stuck —
the judgment-heavy work); this is the "just do the mechanical write" layer for agent-only tasks.

WHAT IT WRAPS (no new logic — the deterministic write layer the rest of the system already uses):
  - gsdo_objects.create / .update   — create + update any object (read-back proven here)
  - task_actions.complete_task      — mark a task Done (canonical gsdo_task_status, read-back)
  - gsdo_anytype.fetch_all_objects  — read the space (paginated, auth-handled)

DISCIPLINE (carried from the skill, made mechanical):
  - Every create/complete reads the object back and confirms it persisted before returning. A
    good answer is not a saved object; the tool result is only success after the read-back.
  - Errors are returned as {"error": ...} — never a raw traceback to the model, never a crash
    that takes the server down. A failed write is surfaced honestly, not swallowed.
  - Links resolve by name → id against the live space (Task→Project, Recurring→Project,
    Project→Goal). A name that doesn't match yields no link, never a wrong one.

This server speaks stdio MCP. It is launched by Claude (see registration in ~/.claude/
settings.json) using the isolated venv at ~/.controlled-drift/mcp-venv (which has `mcp`); the CD
scripts it imports are pure stdlib, so nothing else is needed.
"""
import sys, os

# The CD scripts live next to this file; import them directly (they're stdlib-only).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import gsdo_objects
import task_actions
import field_semantics
from anytype_test import call

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("controlled-drift")

# Field semantics, surfaced AT THE CALL SITE. The tool descriptions are what a writing agent
# actually reads, so the "which field does this text belong in" rules are appended to the tools
# that write free text. This is the fix for the field-semantics leak: the rules used to live only
# in the capture prompt, so an agent writing through this server never saw them and routed status
# notes into `Affective`. Full rationale + spec citations: python3 scripts/field_semantics.py
_ROUTING = field_semantics.routing_brief()


def _with_field_semantics(fn):
    """Append the field-routing rules to a tool's docstring BEFORE FastMCP reads it.

    Decorator order matters: this must sit UNDER @mcp.tool() so it runs first and mcp.tool()
    registers the augmented description. Sourced from field_semantics so the rules can never
    drift from the ones describe_model.py and the write layer use.
    """
    fn.__doc__ = f"{(fn.__doc__ or '').rstrip()}\n\n{_ROUTING}\n"
    return fn

# The five object types the system uses (Note is plain Anytype). Matches capture_generate.
ALLOWED_TYPES = ("Task", "Recurring", "Strategy", "Goal", "Project", "Note")

# Per-type link target property (confirmed against the live model): a Task or Recurring links to
# a Project; a Project links to a Goal; Goal/Strategy/Note don't link. Mirrors capture_generate.
_LINK_PROP = {"Task": "Linked Projects", "Recurring": "Project link", "Project": "Goal link"}

# Which existing type a given object type links *to* (for resolving a link name → id).
_LINK_TARGET_TYPE = {"Task": "gsdo_project", "Recurring": "gsdo_project", "Project": "gsdo_goal"}


# --- shared helpers ----------------------------------------------------------

def _read_back(oid):
    """Re-fetch a just-written object and return it, or raise — the persisted-proof gate."""
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"read-back failed for {oid!r}: {st} {b}")
    return b["object"]


def _resolve_link(type_name, link_name):
    """Resolve a link target *name* to an object id, matching the type that `type_name` links to.
    Returns (link_id, link_prop) or (None, None) if there's no link for this type / no match.
    A non-match yields no link — never a wrong one (the same guard the weeding gate uses)."""
    link_prop = _LINK_PROP.get(type_name)
    if not link_prop or not link_name:
        return None, None
    want_key = _LINK_TARGET_TYPE.get(type_name)
    sid = g.get_space_id()
    for o in g.fetch_all_objects(sid):
        if o.get("type", {}).get("key") == want_key and o.get("name") == link_name:
            return o["id"], link_prop
    return None, link_prop  # named a target but no match → no link, surfaced in the result


# --- tools -------------------------------------------------------------------

@mcp.tool()
@_with_field_semantics
def create_task(name: str, project_name: str = "", status: str = "Ready",
                context: str = "") -> dict:
    """Create a Task in Controlled Drift's Anytype space and confirm it persisted.

    name:         the task, in plain words (e.g. "Email the SSRC program officer").
    project_name: optional — the exact name of a Project to link it to. If it doesn't match an
                  existing Project, the task is still created, just unlinked (see `linked`).
    status:       "Ready" (default), "Active", "Needs Clarifying", "Blocked", or "Done".
    context:      optional free-text notes the system should keep with the task.

    Returns {id, name, status, linked} on success, or {error} on failure.
    """
    try:
        name = (name or "").strip()
        if not name:
            return {"error": "create_task: name is required"}
        link_id, link_prop = _resolve_link("Task", project_name.strip() if project_name else "")
        props = {"Task status": status or "Ready"}
        if link_id:
            props[link_prop] = [link_id]
        if context.strip():
            props["Context"] = context.strip()
        oid = gsdo_objects.create("Task", name, properties=props)
        obj = _read_back(oid)
        if obj.get("name") != name:
            return {"error": f"read-back mismatch: created as {obj.get('name')!r}"}
        return {"id": oid, "name": name, "status": status or "Ready",
                "linked": bool(link_id),
                "link_note": None if (link_id or not project_name)
                else f"no Project named {project_name!r} — created unlinked"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
@_with_field_semantics
def create_object(type_name: str, name: str, link_to: str = "", context: str = "") -> dict:
    """Create any Controlled Drift object (Goal, Project, Recurring, Strategy, Note, or Task).

    type_name: one of Task, Recurring, Strategy, Goal, Project, Note.
    name:      the object's name, in plain words.
    link_to:   optional — for a Task/Recurring, the Project name to link to; for a Project, the
               Goal name. Goals, Strategies, and Notes don't link. No match → created unlinked.
    context:   optional free-text the system keeps with the object.

    Returns {id, type, name, linked} on success, or {error} on failure.
    """
    try:
        type_name = (type_name or "").strip().capitalize()
        name = (name or "").strip()
        if type_name not in ALLOWED_TYPES:
            return {"error": f"unknown type {type_name!r} (expected one of {ALLOWED_TYPES})"}
        if not name:
            return {"error": "create_object: name is required"}
        link_id, link_prop = _resolve_link(type_name, link_to.strip() if link_to else "")
        props = {}
        if link_id:
            props[link_prop] = [link_id]
        if context.strip():
            props["Context"] = context.strip()
        oid = gsdo_objects.create(type_name, name, properties=props or None)
        obj = _read_back(oid)
        if obj.get("name") != name:
            return {"error": f"read-back mismatch: created as {obj.get('name')!r}"}
        return {"id": oid, "type": type_name, "name": name, "linked": bool(link_id),
                "link_note": None if (link_id or not link_to)
                else f"no {('Goal' if type_name=='Project' else 'Project')} named {link_to!r} — created unlinked"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
@_with_field_semantics
def update_object(object_id: str, name: str = "", status: str = "", context: str = "") -> dict:
    """Update an existing object's name, Task status, and/or context. Reads back to confirm.

    object_id: the id (from create_* or list_tasks).
    name:      optional new name.
    status:    optional new Task status (Tasks only): Ready/Active/Needs Clarifying/Blocked/Done.
    context:   optional new context text.

    Returns {id, name} on success, or {error}. At least one field must be given.
    """
    try:
        object_id = (object_id or "").strip()
        if not object_id:
            return {"error": "update_object: object_id is required"}
        props = {}
        if status.strip():
            props["Task status"] = status.strip()
        if context.strip():
            props["Context"] = context.strip()
        new_name = name.strip() or None
        if not props and not new_name:
            return {"error": "update_object: nothing to change (give name, status, or context)"}
        gsdo_objects.update(object_id, name=new_name, properties=props or None)
        obj = _read_back(object_id)
        return {"id": object_id, "name": obj.get("name")}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def field_meaning(field_name: str = "") -> dict:
    """What a Controlled Drift field MEANS — read this before writing free text into one.

    field_name: a field's display name (e.g. "Affective", "Blocked on", "Context"). Leave blank
                to get every field's one-line meaning at once.

    Returns {field, hint, means, not, instead, rules, source} for one field, or {fields: {...}}
    for all of them. Fields with no documented meaning are reported as undefined — do not infer
    a meaning for those. June can revise these meanings; what you get back is the current value.
    """
    try:
        name = (field_name or "").strip()
        if not name:
            return {"fields": {k: field_semantics.one_line(k) for k in field_semantics.FIELDS},
                    "undefined": list(field_semantics.UNDEFINED),
                    "routing": _ROUTING}
        e = field_semantics.resolved(name)
        if e is None:
            reason = field_semantics.undefined_reason(name)
            if reason:
                return {"field": name, "undefined": True, "reason": reason}
            return {"error": f"no field semantics recorded for {name!r}"}
        return {"field": e["field"], "hint": e["hint"], "means": e["means"],
                "not": e.get("not_this"), "instead": e.get("instead") or {},
                "rules": e.get("usage") or [], "source": e["source"],
                "revised_by_june": e.get("overridden") or []}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def complete_task(task_id: str) -> dict:
    """Mark a Task done (canonical gsdo_task_status → Done), with read-back confirmation.

    Use this to close an agent-facing task you finished. Returns {id, name, status, done} or
    {error}. (For a June-facing task she closes herself in the overlay — leave it to her.)
    """
    try:
        task_id = (task_id or "").strip()
        if not task_id:
            return {"error": "complete_task: task_id is required"}
        return task_actions.complete_task(task_id)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_tasks(include_done: bool = False) -> dict:
    """List Tasks in the space — id, name, status — so you can find one to update or complete.

    include_done: False (default) hides Done tasks; True includes them.
    Returns {count, tasks: [{id, name, status}]} or {error}.
    """
    try:
        sid = g.get_space_id()
        out = []
        for o in g.fetch_all_objects(sid):
            if o.get("type", {}).get("key") != "task":
                continue
            pv = {p.get("key"): p for p in o.get("properties", [])}
            status = (pv.get("gsdo_task_status", {}).get("select") or {}).get("name") or ""
            if not include_done and status == "Done":
                continue
            out.append({"id": o["id"], "name": o.get("name"), "status": status})
        return {"count": len(out), "tasks": out}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_context() -> dict:
    """Orientation for a cold agent: the Goals and Projects in the space, by name + id, so links
    resolve correctly. Call this first when you don't know what exists. Returns
    {goals: [{id, name}], projects: [{id, name}]} or {error}."""
    try:
        sid = g.get_space_id()
        goals, projects = [], []
        for o in g.fetch_all_objects(sid):
            key = o.get("type", {}).get("key")
            if key == "gsdo_goal":
                goals.append({"id": o["id"], "name": o.get("name")})
            elif key == "gsdo_project":
                projects.append({"id": o["id"], "name": o.get("name")})
        return {"goals": goals, "projects": projects}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()

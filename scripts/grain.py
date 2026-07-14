#!/usr/bin/env python3
"""Display grain — the one deterministic place that decides what unit a project
shows as in the daily plan.

Two questions, two functions:

  classify(project)  -> "excluded" | "task" | "block"
      Which grain does this project get? A discrete chore (task), a "work on X"
      chunk (block), or nothing (excluded). Grain only — NOT visibility. The
      engagement show/hide gate is a separate decision made elsewhere.

  project_arc(...)   -> list[dict] | None
      For a block, the project's ordered steps (done / here / ahead) so the
      overlay can render an arc under the chunk. None when the project has no
      direct tasks (caller renders a bare chunk).

No LLM, no composition — reads stored fields, returns data.
"""


def classify(project):
    """Decide the daily-plan grain for a project.

    Order matters — evaluated top to bottom:
      Fun / hobby        -> excluded (held out of the plan entirely)
      is a workstream    -> excluded (workstreams are a layer, not a plan item)
      Daily life         -> task    (a discrete chore, shown as itself)
      everything else    -> block   (a "work on X" chunk)

    `project` is a dict like {"name":..., "side":..., "is_workstream":...};
    side may be None.
    """
    side = project.get("side")
    if side == "Fun / hobby":
        return "excluded"
    if project.get("is_workstream"):
        return "excluded"
    if side == "Daily life":
        return "task"
    return "block"


def block_unit(project, shape, arc, chunk_min):
    """A "work on X" block as a TASK-SHAPED dict with a SYNTHETIC id (block:<project_id>).

    The synthetic id is what lets a block ride the existing id-keyed pipeline exactly like a
    task: _build_task_refs tokenizes it, the LLM orders it by focus/strategy, _resolve_ids /
    _retime / blocks_from_scheduled key on it. The block-only fields (block, shape, arc,
    chunk_min) are Python-owned and re-attached by id downstream — the model only ever echoes
    the ref token, never these. `duration_min == chunk_min` so the scheduler can place the slot.

      shape     "arc"  → opens to a step arc (project has direct tasks)
                "chunk"→ a bare chunk of time (task-less bundle of subprojects)
      arc       the [{"text","state"}] list from project_arc, or None for a bare chunk
      chunk_min the block's length in minutes (block_duration.get_chunk_min)
    """
    return {"id": f"block:{project['id']}",
            "name": f"Work on {project['name']}",
            "block": True,
            "project_id": project["id"],
            "project": project["name"],
            "shape": shape,
            "arc": arc,
            "chunk_min": chunk_min,
            "duration_min": chunk_min,
            "linked_projects": [project["name"]]}


def _id_list(raw):
    """Normalize an objects-relation value to a list of id strings.

    Mirrors orient_map._id_list — linked_projects entries are id strings, but
    sometimes come back as dicts carrying an "id".
    """
    out = []
    for x in raw or []:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict) and x.get("id"):
            out.append(x["id"])
    return out


def _tkey(o):
    """An object's type key. Type is a dict {"key": ...} but can arrive as a
    bare value — guard as orient_map does."""
    t = o.get("type")
    return t.get("key") if isinstance(t, dict) else t


def project_arc(project_name, all_objects, proj_id_to_name):
    """The project's direct tasks as an ordered arc, or None if it has none.

    Returns a list of {"text": <task name>, "state": <"done"|"here"|"ahead">, "id": <task id>},
    ordered by "Step order" then task name (no-order tasks sort last, stable by
    name — mirrors orient_map._steps_for). The `id` is the real Anytype task id so
    the overlay can wire a checkbox per arc step (check + undo). State:
        done  -> a finished step
        here  -> the FIRST not-done step
        ahead -> every not-done step after the first

    `all_objects` MUST be the raw Anytype objects list (from g.fetch_all_objects)
    — it INCLUDES done tasks, which the arc needs to show the ✓ steps. Do not
    pass a pre-filtered daily-plan task list; that drops done tasks.

    `proj_id_to_name` maps project id -> project name; a task belongs to this
    project when one of its linked_projects ids resolves to `project_name`.

    Returns None when the project has zero direct tasks.
    """
    steps = []
    for o in all_objects:
        if _tkey(o) != "task":
            continue
        props = {p.get("key"): p for p in o.get("properties", [])}
        by_name = {p.get("name"): p for p in o.get("properties", [])}

        linked_ids = _id_list((props.get("linked_projects") or {}).get("objects"))
        linked_names = [proj_id_to_name.get(pid) for pid in linked_ids]
        if project_name not in linked_names:
            continue

        # Task status lives under "Task status" (key gsdo_task_status), not
        # "status". Done = status "Done" OR the built-in done checkbox.
        status_sel = (by_name.get("Task status") or {}).get("select") or {}
        status = status_sel.get("name") if isinstance(status_sel, dict) else None
        done = (status == "Done") or bool((props.get("done") or {}).get("checkbox"))

        # Step order read by NAME — its Anytype key is auto-generated.
        order = (by_name.get("Step order") or {}).get("number")

        steps.append({"id": o.get("id"), "name": o.get("name", ""), "done": done, "order": order})

    if not steps:
        return None

    steps.sort(key=lambda s: (s["order"] is None,
                              s["order"] if s["order"] is not None else 0,
                              s["name"]))

    arc = []
    here_marked = False
    for s in steps:
        if s["done"]:
            state = "done"
        elif not here_marked:
            state = "here"
            here_marked = True
        else:
            state = "ahead"
        arc.append({"text": s["name"], "state": state, "id": s["id"]})
    return arc

#!/usr/bin/env python3
"""The write layer behind the Review & Reorganize surface — backend spec §1, contract §4.

Today the surface stages edits client-side and exports `controlled_drift_changes.json` for Claude
to apply. This module is the other half of that replacement: the surface writes to Anytype
DIRECTLY, with the `drift` skill's discipline — idempotent write → **re-fetch and prove the change
is present** → only then report success. The export diff stays as the offline fallback (spec §1);
nothing here removes it.

Five deterministic actions, one shape
------------------------------------
`set_title` · `set_vals` · `move_object` · `create_child` · `delete_object`, plus
`set_recurring_paused`. Every one except delete returns the contract's single envelope:

    {"ok": True, "object": <a GET /api/tree node, RE-FETCHED from Anytype after the write>}

`object` is a real read, not the request echoed back and not a dict we assembled from what we
meant to write. Contract §4 records that the server currently answers writes in three
inconsistent tiers (partial object + plan · plan only · a bare scalar) and that the HTTP layer
throws away read-backs the helpers already performed. This does not add a fourth tier: it returns
what §4 specifies, so the client can render "Saved" FROM THE OBJECT rather than from `ok`.

Delete is the one deliberate exception, also per §4: `{"ok", "id", "archived": True}`. A DELETE
archives, so there is no object left to return — the proof is `task_actions.archive_object`, which
already re-fetches and confirms the archived marker rather than trusting the 204.

Read-back is per FIELD, not per request
---------------------------------------
`_verify` compares every value we intended against the value that came back, using the same
`api_tree._vals` the read endpoint uses — so a write is confirmed against the exact projection the
UI will later read. Dates are compared parsed (Anytype normalizes to ISO datetimes), multi-selects
as sets. A mismatch RAISES; a value that comes back ABSENT is a mismatch, not a pass. That last
clause is deliberate: contract §4 lists `reschedule_task` guarding with
`if persisted is not None and persisted != intended`, where a field that vanished entirely slips
through as success.

⚠ THE CREATE-DEDUP HAZARD (BUILD_DOC §6) — handled explicitly, never silently
-----------------------------------------------------------------------------
`gsdo_objects.create` dedups by normalized name and returns an EXISTING object's id **without
writing any of the properties it was given**. For a capture pipeline that is a useful backstop;
for a surface where June types a title into a form it is a trap — she would appear to create a
task and instead silently edit nothing on someone else's object. Two guards, because one is a
race and the other is not:

1. `create_child` looks the name up FIRST and refuses with `DuplicateName` (HTTP 409) naming the
   object that already holds it. She gets a real choice; nothing is written.
2. Even if the check and the create raced, the post-create verification would catch it — a
   deduped return has the wrong parent link (or no link), and `_verify` raises. The hazard cannot
   pass silently through both.

An EMPTY title is refused outright (400). `_norm_name("")` matches every other empty-named object,
so an empty-title create is the dedup hazard at its worst. ⚠ Contract §4 has the UI posting
`{title: ''}` and filling the name in afterwards; that flow needs the client to send a title (or a
placeholder) before it POSTs. Flagged rather than papered over.

Field semantics
---------------
`gsdo_objects.create/update` already call `field_semantics.check_scalar_affect` — guard #3, the one
mechanical content rule (an affect field is free text, never a 1–5 scalar). Nothing here adds a
semantic validator: whether a sentence is "affect" or "status" is a judgment call and June's
explicit decision is that the machine does not make it. Mechanical checks only.

Logging — an existing log, not a thirteenth
-------------------------------------------
Every applied change goes to `corrections_log` (spec §11, contract §7). It is the only log that
carries `authored_by` — WHO wrote the value being overwritten — which is the whole point of the
correction signal: June editing her own value is a change of mind, June editing an LLM's value is
a labelled instance of the model being wrong. `authored_by` is resolved per field from the log's
own history and is `'unknown'` when nothing recorded it, never guessed as `'user'`.

Deliberate divergence from contract §7.5, which routes engagement to `engagement_log` and other
field edits to `signal_log`: those are three files answering one question, and `signal_log` is
documented as June's own words, capture only. `corrections_log`'s own module docstring already
made this argument for the authorship half; this extends it to the surface's edits. The ONE
exception is the recurring active flag, which goes through `recurring_active.set_recurring_active`
— the documented single writer of that flag — and lands in `reactivation_log` there. Not
duplicated here; that means a paused-toggle carries no `authored_by`, stated rather than hidden.

SEAM FOR SPEC §5 (type conversion) — deliberately NOT built here
----------------------------------------------------------------
Task ↔ Recurring ↔ Subproject ↔ Workstream conversion is a larger job (data-preserving prop carry,
relink, and an open question — contract Q2 — about whether Anytype supports an in-place type
change at all). It plugs in at exactly three places in this module, and nowhere else:
  • `_LEVEL_TYPE` — level → Anytype type name; a conversion moves an object between these.
  • `_link_prop_for` — the parent link changes with the type, so a conversion must relink.
  • `_verify` / `node_for` — the same read-back and node projection apply unchanged.
It additionally needs a LEAF GUARD (contract §4 guard 1: an object with children cannot become a
Task/Recurring) — `_descendant_ids` here is the primitive that answers it, already written and
already used by the move cycle guard.

NOT built here, and why: `clear-field` (`POST /api/object/{id}/clear-field`, contract §4). It must
REMOVE a property rather than set it empty, because key-presence IS the tri-state (spec §4:
absent = inherit, present-but-empty = explicitly none). Whether the live Anytype PATCH can remove
a property value is unverified, and verifying it means writing to June's real space. Left out
rather than shipped on a guess.
"""
import sys, os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anytype_test import call
import gsdo_anytype as g
import gsdo_objects
import api_schema
import api_tree
import task_actions
import recurring_active
import corrections_log

SURFACE = "review_reorganize"

#: Which parent field is not a property at all. Contract §7.4's vocabulary for the non-field parts
#: of an object; `corrections_log` already defines `__title__`.
PARENT_FIELD = "__parent__"

#: UI level → Anytype type name. SUBPROJECT / WORKSTREAM / PROJECT are all the `Project` type
#: (spec §5) — level is a UI concept, type is storage. §5 conversion moves objects across this map.
_LEVEL_TYPE = {
    "GOAL": "Goal", "PROJECT": "Project", "SUBPROJECT": "Project", "WORKSTREAM": "Project",
    "TASK": "Task", "RECURRING": "Recurring", "STRATEGY": "Strategy",
}

#: The reverse, for reading: an object's type alone fixes the level we write AT. All three Project
#: levels share one `api_schema.PROPERTY_FOR` entry, so PROJECT is the correct write-level for any
#: of them — the finer PROJECT/SUBPROJECT/WORKSTREAM distinction only matters for rendering, and
#: `node_for` computes it there from the live graph.
_WRITE_LEVEL = {"Goal": "GOAL", "Project": "PROJECT", "Task": "TASK",
                "Recurring": "RECURRING", "Strategy": "STRATEGY"}

#: (child write-level, parent type name) → the objects-relation that expresses "sits under".
#: ⚠ These read back as bare id STRINGS under "objects" (not "object") — `api_tree._ids` handles it.
_LINK_PROP = {
    ("TASK", "Project"): "Linked Projects",
    ("RECURRING", "Project"): "Project link",
    ("PROJECT", "Project"): "Parent project",
    ("PROJECT", "Goal"): "Goal link",
}

#: Every link a level can carry, so a move can clear the one it is moving OFF of. A Project under a
#: Goal that moves under a Project must lose its Goal link, or the tree reads it two ways.
_ALL_LINKS = {
    "TASK": ["Linked Projects"],
    "RECURRING": ["Project link"],
    "PROJECT": ["Parent project", "Goal link"],
}

WORKSTREAM_PROP = "Is workstream"   # live display name of the `is_workstream` checkbox


class WriteRefused(Exception):
    """A guard said no. Maps to 400 — the request was understood and is not allowed."""


class DuplicateName(Exception):
    """A create would have collided with the dedup guard. Maps to 409; carries the existing id."""

    def __init__(self, message, existing_id):
        super().__init__(message)
        self.existing_id = existing_id


# --- reading -----------------------------------------------------------------

def _get_object(oid):
    """Re-fetch one object and return its persisted state. Raises if it cannot be read — an
    unreadable read-back is undetermined, never a pass."""
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise LookupError(f"could not read object {oid!r}: {st} {b}")
    return b["object"]


def _type_name(obj):
    t = obj.get("type")
    return t.get("name") if isinstance(t, dict) else t


def _write_level(obj):
    lvl = _WRITE_LEVEL.get(_type_name(obj))
    if lvl is None:
        raise WriteRefused(
            f"{_type_name(obj)!r} is not one of the five GSDO types this surface writes")
    return lvl


def _link_ids(obj, prop_name):
    for p in obj.get("properties", []):
        if p.get("name") == prop_name and "objects" in p:
            return api_tree._ids(p["objects"])
    return []


def node_for(object_id):
    """The `GET /api/tree` node for one object, built from a fresh read of the live space.

    Built through `api_tree` rather than reimplemented, so the object the UI gets back after a
    write is byte-identical in shape to the one it got from the read endpoint — including `level`
    (which needs the workstream walk-up) and `children`. One extra live read per write; writes are
    one-at-a-time and human-paced, and a node assembled from partial knowledge would be the kind of
    plausible-but-wrong payload this repo has paid for before.
    """
    sid = g.get_space_id()
    payload = api_tree.build_tree_from(g.fetch_all_objects(sid))
    found = _find_node(payload, object_id)
    if found is None:
        raise RuntimeError(
            f"api_write: {object_id!r} wrote successfully but does not appear anywhere in the "
            f"tree read back afterwards — refusing to report a write we cannot show")
    return found


def _find_node(payload, object_id):
    def walk(nodes):
        for n in nodes:
            if n["id"] == object_id:
                return n
            hit = walk(n.get("children") or [])
            if hit is not None:
                return hit
        return None

    for group in ([payload["nodes"], payload["strategies"]]
                  + [b["nodes"] for b in payload["orphans"].values()]):
        hit = walk(group)
        if hit is not None:
            return hit
    return None


def _descendant_ids(object_id, objs):
    """Every object beneath `object_id` in the live graph, by id. The primitive behind the move
    cycle guard — and the one spec §5's leaf guard will need to answer "does this have children?"."""
    children = {}
    for o in objs:
        for prop in ("Parent project", "Linked Projects", "Project link"):
            for pid in _link_ids(o, prop):
                children.setdefault(pid, set()).add(o["id"])
    seen, stack = set(), [object_id]
    while stack:
        cur = stack.pop()
        for kid in children.get(cur, ()):
            if kid not in seen:
                seen.add(kid)
                stack.append(kid)
    return seen


# --- read-back verification --------------------------------------------------

def _as_date(v):
    """A date for comparison, tolerant of Anytype's datetime/timezone normalization."""
    if not isinstance(v, str) or not v:
        return None
    try:
        return dt.date.fromisoformat(v[:10])
    except ValueError:
        return None


def _same(intended, got):
    if isinstance(intended, list) or isinstance(got, list):
        a = set(intended if isinstance(intended, list) else [intended])
        b = set(got if isinstance(got, list) else [got])
        return a == b
    if isinstance(intended, bool) or isinstance(got, bool):
        return bool(intended) == bool(got)
    if isinstance(intended, (int, float)) and isinstance(got, (int, float)):
        return float(intended) == float(got)
    di, dg = _as_date(intended), _as_date(got)
    if di is not None or dg is not None:
        return di == dg
    return intended == got


def _verify(object_id, level, intended_vals, title=None):
    """Re-fetch and PROVE every intended value is present. Returns the re-fetched raw object.

    Absence is a failure. `_vals` emits only keys the object actually sets (the tri-state rule), so
    a field that silently failed to write comes back missing — and that is exactly the case
    `if persisted is not None` guards have let through elsewhere in this codebase.
    """
    obj = _get_object(object_id)
    if title is not None and (obj.get("name") or "") != title:
        raise RuntimeError(f"api_write: title did not persist on {object_id!r} "
                           f"(wrote {title!r}, read back {obj.get('name')!r})")
    got = api_tree._vals(obj, level)
    for key, want in (intended_vals or {}).items():
        if key not in got:
            raise RuntimeError(f"api_write: {key!r} did not persist on {object_id!r} "
                               f"(wrote {want!r}, read back: absent)")
        if not _same(want, got[key]):
            raise RuntimeError(f"api_write: {key!r} did not persist on {object_id!r} "
                               f"(wrote {want!r}, read back {got[key]!r})")
    return obj


def _verify_links(object_id, expected):
    """Prove each link property holds exactly the ids we meant. `expected` is
    {property name: [ids]}; an empty list asserts the link was CLEARED."""
    obj = _get_object(object_id)
    for prop, want in expected.items():
        got = _link_ids(obj, prop)
        if sorted(got) != sorted(want):
            raise RuntimeError(f"api_write: {prop!r} did not persist on {object_id!r} "
                               f"(wrote {want!r}, read back {got!r})")
    return obj


# --- value coercion ----------------------------------------------------------

def _property_for(level, val_key):
    prop = api_schema.PROPERTY_FOR.get(level, {}).get(val_key)
    if prop is None:
        prop = api_tree.EXTRA_PROPERTY_FOR.get(level, {}).get(val_key)
    if prop is None:
        raise WriteRefused(f"{val_key!r} is not a writable field on a {level}")
    return prop


def _coerce(prop_name, value):
    """The value in the shape `gsdo_objects` wants. Multi-selects arrive from the UI either as a
    list or as the joined string contract §4 shows `toggleMulti` sending; both normalize to a list
    of option names, which is what the write layer resolves to tag ids."""
    p = g.find_property(prop_name)
    if p is None:
        raise WriteRefused(f"property {prop_name!r} is not in the live space")
    fmt = p.get("format")
    if fmt == "multi_select":
        if value in (None, ""):
            return []
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        return list(value)
    if fmt == "checkbox":
        return bool(value)
    if fmt == "number" and isinstance(value, str):
        if value.strip() == "":
            raise WriteRefused(f"{prop_name!r} is a number; got an empty string")
        return float(value) if "." in value else int(value)
    return value


# --- logging -----------------------------------------------------------------

def _log(object_id, object_type, field, before, after, kind="surface_edit"):
    """One correction record per changed field. `authored_by` describes WHO WROTE `before` — the
    value being overwritten — resolved from the log's own history, `'unknown'` when nothing
    recorded it. Best-effort: the write already persisted and was proven; a logging hiccup must
    never turn a real save into a reported failure (the same posture `task_actions.complete_task`
    takes around `completion_log`). Failures are printed, never swallowed silently."""
    try:
        corrections_log.log_correction(
            kind, before, after, object_id=object_id, object_type=object_type, field=field,
            authored_by=corrections_log.resolve_authored_by(object_id, field), surface=SURFACE)
    except Exception as e:
        print(f"[api_write] correction log failed for {object_id!r}.{field}: {e}", file=sys.stderr)


# --- the five write actions --------------------------------------------------

def set_title(object_id, title):
    """Rename. Read-back proves the new name is on the object before this reports success."""
    title = (title or "").strip()
    if not title:
        raise WriteRefused("a title cannot be empty")
    before = _get_object(object_id)
    level = _write_level(before)
    old = before.get("name") or ""
    if old != title:
        gsdo_objects.update(object_id, name=title)
    _verify(object_id, level, {}, title=title)
    _log(object_id, _type_name(before), corrections_log.TITLE_FIELD, old, title)
    return {"ok": True, "object": node_for(object_id)}


def set_vals(object_id, vals):
    """Set one or more fields by the UI's valKeys. Every value is proven present on read-back.

    `paused` on a Recurring is routed to `recurring_active.set_recurring_active`, the documented
    SINGLE writer of the `Active` flag — writing `Active` generically here would bypass its
    read-back and its reactivation log. Note the polarity flip: the UI stores `paused`, Anytype
    stores `Active` (contract Q3/Q6).
    """
    if not isinstance(vals, dict) or not vals:
        raise WriteRefused("set needs a non-empty vals object")
    before = _get_object(object_id)
    level = _write_level(before)

    if level == "RECURRING" and "paused" in vals:
        if len(vals) > 1:
            raise WriteRefused("set the recurring paused flag on its own, not alongside "
                               "other fields — it has its own writer")
        return set_recurring_paused(object_id, bool(vals["paused"]))

    before_vals = api_tree._vals(before, level)
    props, intended = {}, {}
    for key, value in vals.items():
        prop = _property_for(level, key)
        coerced = _coerce(prop, value)
        # A valKey whose stored polarity is the inverse of the UI's (contract Q3) is flipped on
        # the way IN; `api_tree._vals` flips it back on the way out, so `intended` stays UI-space.
        props[prop] = (not coerced) if (level, key) in api_tree.INVERTED_VALS else coerced
        intended[key] = coerced

    gsdo_objects.update(object_id, properties=props)     # guard #3 runs inside
    _verify(object_id, level, intended)

    for key in vals:
        _log(object_id, _type_name(before), _property_for(level, key),
             before_vals.get(key), intended[key])
    return {"ok": True, "object": node_for(object_id)}


def move_object(object_id, parent_id):
    """Re-parent. Sets the link the new parent's TYPE calls for and clears the one it moved off of,
    so the object is never reachable two ways. Both are proven on read-back — including the clear,
    which is the half most likely to silently not happen."""
    child = _get_object(object_id)
    level = _write_level(child)
    if level not in _ALL_LINKS:
        raise WriteRefused(f"a {_type_name(child)} has no parent to move it under")
    parent = _get_object(parent_id)
    parent_type = _type_name(parent)
    link = _LINK_PROP.get((level, parent_type))
    if link is None:
        raise WriteRefused(f"a {_type_name(child)} cannot sit under a {parent_type}")
    if parent_id == object_id:
        raise WriteRefused("an object cannot be its own parent")

    sid = g.get_space_id()
    if parent_id in _descendant_ids(object_id, g.fetch_all_objects(sid)):
        raise WriteRefused("that would move an object inside its own subtree")

    old_parents = {p: _link_ids(child, p) for p in _ALL_LINKS[level]}
    props = {link: [parent_id]}
    for other in _ALL_LINKS[level]:
        if other != link and old_parents[other]:
            props[other] = []          # clear — read-back below proves it actually cleared
    gsdo_objects.update(object_id, properties=props)
    _verify_links(object_id, {p: props.get(p, old_parents[p]) for p in _ALL_LINKS[level]})

    _log(object_id, _type_name(child), PARENT_FIELD,
         sorted({i for ids in old_parents.values() for i in ids}) or None, [parent_id],
         kind="surface_move")
    return {"ok": True, "object": node_for(object_id)}


def create_child(level, title, parent_id=None):
    """Create an object at `level`, optionally linked under `parent_id`.

    ⚠ The dedup hazard is handled here and only here — see the module docstring. A colliding name
    raises `DuplicateName` BEFORE anything is written, and the post-create verification catches the
    race case because a deduped id would not carry the parent link we just asked for.
    """
    type_name = _LEVEL_TYPE.get(level)
    if type_name is None:
        raise WriteRefused(f"{level!r} is not a level this surface creates")
    title = (title or "").strip()
    if not title:
        raise WriteRefused(
            "a new object needs a title. An empty name would match every other empty-named "
            "object in gsdo_objects.create's dedup check and silently return one of them "
            "instead of creating anything.")

    t = g.find_type(type_name)
    if t is None:
        raise LookupError(f"type {type_name!r} not found in the live space")
    existing = gsdo_objects.find_existing(t.get("key"), title)
    if existing:
        raise DuplicateName(
            f"a {type_name} named {title!r} already exists — the write layer dedups by name and "
            f"would have edited nothing. Open that one, or use a different name.", existing)

    write_level = _WRITE_LEVEL[type_name]
    props = {}
    if level == "WORKSTREAM":
        props[WORKSTREAM_PROP] = True
    expected_links = {}
    if parent_id:
        parent_type = _type_name(_get_object(parent_id))
        link = _LINK_PROP.get((write_level, parent_type))
        if link is None:
            raise WriteRefused(f"a {type_name} cannot sit under a {parent_type}")
        props[link] = [parent_id]
        expected_links[link] = [parent_id]

    new_id = gsdo_objects.create(type_name, title, properties=props)
    _verify(new_id, write_level, {}, title=title)
    if expected_links:
        # Also the dedup backstop: a deduped return would not carry the link we just asked for.
        _verify_links(new_id, expected_links)

    # June typed this, so stamp it hers — a later edit then reads as her changing her mind, not as
    # an unknown-provenance record the loop has to discard.
    try:
        corrections_log.log_authorship(new_id, corrections_log.TITLE_FIELD, title,
                                       object_type=type_name, authored_by="user", surface=SURFACE)
    except Exception as e:
        print(f"[api_write] authorship log failed for {new_id!r}: {e}", file=sys.stderr)
    return {"ok": True, "object": node_for(new_id)}


def delete_object(object_id):
    """Archive (Anytype's DELETE archives; it is recoverable in the app). `archive_object` already
    re-fetches and confirms the archived marker rather than trusting the 204, so this adds the log
    and the contract's response shape and nothing else."""
    obj = _get_object(object_id)
    out = task_actions.archive_object(object_id)
    _log(object_id, _type_name(obj), corrections_log.TITLE_FIELD,
         obj.get("name"), None, kind="surface_delete")
    return {"ok": True, "id": out["id"], "archived": True}


def set_recurring_paused(object_id, paused):
    """The in-my-plan toggle. Delegates to the single writer of `Active`, which reads back and logs
    to `reactivation_log` itself; this only flips the polarity and returns the contract's envelope."""
    obj = _get_object(object_id)
    if _type_name(obj) != "Recurring":
        raise WriteRefused("only a Recurring carries the in-my-plan toggle")
    recurring_active.set_recurring_active(object_id, not bool(paused))
    return {"ok": True, "object": node_for(object_id)}

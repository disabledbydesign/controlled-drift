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

SPEC §5 (type conversion) — BUILT, and contract Q2 is CLOSED
------------------------------------------------------------
`convert_type` reclassifies a miscategorised object — June's stated primary use is correcting the
weeding gate when it filed a one-time Task as a Recurring or the reverse.

**Contract Q2, answered empirically against the live space on 2026-07-18, not guessed:** Anytype
DOES support an in-place type change. `PATCH /spaces/{sid}/objects/{oid}` accepts `type_key` and
returns 200; the re-fetched object carries the new type, **the same id**, and every property value
it had before — including values for properties the new type does not link (a `Task status` rode
through onto a Recurring). The probe method and its object's full lifecycle are recorded below.

That answer collapses the hard half of the job. The create-new → copy-props → relink → delete-old
path contract Q2 feared would have had to reproduce the object's id or break every inbound
reference (linked projects, plan-cache rows, arc step ids, focus-period front/paused lists, this
log's own `object_id`, June's bookmarks). It preserves the id **by construction**, because it never
makes a second object. Nothing is orphaned because nothing moves.

It plugs into exactly the three seam points named here, and nowhere else:
  • `_LEVEL_TYPE` — target level → Anytype type name; the conversion writes across this map.
  • `_LINK_PROP` — the parent link changes with the type, so a conversion must relink.
  • `_verify` / `node_for` — the same read-back and node projection apply unchanged.

Three guards, each refusing rather than doing something lossy:
  1. **Leaf guard** (contract §4 guard 1): an object with children cannot become a Task or a
     Recurring. `_descendant_ids` answers it, and the message NAMES the children to move first.
  2. **Un-hostable parent**: a Project under a Goal cannot become a Task, because no link expresses
     "Task under Goal" — converting would silently orphan it. Refused, naming the fix.
  3. **Nothing-to-do**: Subproject and Project are the SAME storage (both the `Project` type,
     `is_workstream` false); what makes one a subproject is sitting under another project. Asking
     to convert between them is a move, not a conversion, and is refused saying so — rather than
     reporting a success that changed nothing and handing back a node still reading `SUBPROJECT`.

What is deliberately NOT enforced here: contract §4 guard 2 (the picker only offers Task/Recurring
when the node has a schedulable ancestor). That is an offering rule, not a data constraint —
enforcing it server-side would refuse to convert an unparented object, and unparented Tasks and
Recurrings are legitimate in June's real data (`api_tree` maintains four orphan buckets precisely
so they are not lost). Also not enforced: spec §15's calendar-owned-field rule, because `source`
is not on the live Recurring type yet — stated rather than silently assumed.

The Q2 probe, in full, so nobody has to re-run it
-------------------------------------------------
One throwaway object, created and destroyed in June's live space; nothing else was written.
  1. `create("Task", "ZZZ throwaway type-change probe 2026-07-18 delete me", properties={Context,
     Duration min: 25, Task status: Ready})` → id `bafyreigkyt…il3nm`, reads back as `Task`.
  2. `PATCH /spaces/{sid}/objects/{oid}` `{"type_key": "gsdo_recurring"}` → **HTTP 200**.
  3. Re-fetch: same id, `type.key == "gsdo_recurring"`, and all three property values present —
     `Context` and `Duration min` intact, and `Task status` STILL SET although Recurring does not
     link it. This is the preservation guarantee spec §5 asks for, observed rather than assumed.
  4. `DELETE` → 200; re-fetched `archived == True` and absent from `fetch_all_objects`.

⚠ FINDING FOR SOMEONE ELSE'S FILE, surfaced not fixed: the archive marker is NOT visible on an
immediate re-fetch. Step 4's first read (issued right after the DELETE returned) came back
`archived == False`; a second read moments later returned `archived == True`. Anytype applies the
archive asynchronously, the same way BUILD_DOC §6 records for schema tag/property deletes.
`task_actions.archive_object` re-fetches EXACTLY ONCE, immediately, and raises when the marker is
not yet `True` — so on the live API it can report a spurious failure for an archive that in fact
succeeded, and `delete_object` below inherits that. BUILD_DOC §6 lists this behaviour as
"UNCONFIRMED against the live API (2026-07-17), needs one live undo": this probe WAS that live
undo, and the answer is that it is a race. The fix is to poll until the marker appears (the
established pattern for Anytype's async deletes) — not made here, because `task_actions.py` is
outside this change and the repo rule is to change only what was asked.

`clear-field` (`POST /api/object/{id}/clear-field`, contract §4) IS built here now — see
`clear_field` below. It must REMOVE a property rather than set it empty, because key-presence IS
the tri-state (spec §4: absent = inherit, present-but-empty = explicitly none). This docstring
previously recorded that removal was UNVERIFIED and refused to ship on a guess. It has now been
verified live (2026-07-18) against scratch objects created and archived inside the probe, and the
answer is FORMAT-DEPENDENT — which is why one blanket implementation would have been wrong:

    field      format         explicit-empty?   removable?
    access     multi_select   NO  (writing []   YES — writing [] IS the removal; the property
                              deletes it)            comes back ABSENT, identical to never-set
    affective  text           YES ('' reads     NO verified path — '' persists as PRESENT-empty,
                              back as present)       which is explicit-none, not removal
    blockMin   number         NO (0 is a real   NO verified path
                              value)

So the spec §4 tri-state is fully representable for `affective` and NOT representable for
`access`: for a multi_select, "set here, deliberately none" and "unset, inherit" are the same
bytes. That is a property of the storage, not a shortcut taken here — the same honest limit
`resolve.py` already records for checkboxes ("A checkbox therefore has no tri-state"). The UI
must not offer a state the store cannot hold; `clear_field` refuses rather than pretending.
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
import intentionally_none

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

#: Not a property on the object — the object's TYPE, as the correction log's vocabulary for the
#: non-field parts of an object (contract §7.4, alongside `__title__` and `PARENT_FIELD`).
TYPE_FIELD = "__type__"

#: The conversion targets contract §4 lists for `setType`, mapped onto what they mean in storage:
#: (Anytype type name, intended `is_workstream`; None = the flag does not apply to this type).
#: ⚠ Subproject and Project are deliberately IDENTICAL — spec §5 says the two differ by nesting
#: depth, not by anything stored. `convert_type` refuses that pair rather than pretending.
_CONVERT_TARGET = {
    "Task": ("Task", None),
    "Recurring": ("Recurring", None),
    "Subproject": ("Project", False),
    "Project": ("Project", False),
    "Workstream": ("Project", True),
}

#: Targets that cannot hold children (contract §4 guard 1, spec §5's leaf guard).
_LEAF_TARGETS = ("Task", "Recurring")


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


def _checkbox(obj, prop_name):
    """One checkbox property's value, or None when the object does not set it at all. The
    absent/false distinction is kept because `is_workstream` unset and explicitly-false are the
    same for rendering but not for "did this conversion have anything to do"."""
    for p in obj.get("properties", []):
        if p.get("name") == prop_name and "checkbox" in p:
            return bool(p["checkbox"])
    return None


def _stored_values(obj):
    """{property display name: typed value} for every property the object actually SETS.

    This is the snapshot spec §5's preservation rule is proven against: whatever is in here before
    a conversion must still be in here afterwards, unchanged, except for the handful of properties
    the conversion deliberately rewrites. Built with `api_tree._value` so it reads values the same
    way everything else in this layer does, and skips `_UNSET` so an empty property is not
    mistaken for a value that later vanished.
    """
    out = {}
    for p in obj.get("properties", []):
        name = p.get("name")
        if not name:
            continue
        if "objects" in p:
            out[name] = sorted(api_tree._ids(p["objects"]))
            continue
        val = api_tree._value(p)
        if val is not api_tree._UNSET:
            out[name] = val
    return out


def _direct_children(object_id, objs):
    """Objects whose parent link points AT `object_id`, as (id, name). The leaf guard needs these
    by name — "it has sub-items" is not actionable, "move these three first" is."""
    kids = []
    for o in objs:
        for prop in ("Parent project", "Linked Projects", "Project link"):
            if object_id in _link_ids(o, prop):
                kids.append((o["id"], o.get("name") or "(untitled)"))
                break
    return kids


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


def _marker_values(obj):
    """The raw `Intentionally none` list on an object, or None when the property is absent."""
    for p in obj.get("properties", []):
        if api_tree._prop_name(obj, p) == intentionally_none.PROPERTY:
            v = api_tree._value(p)
            return None if isinstance(v, api_tree._Unset) else v
    return None


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
    # Which inheritable fields this write turns into, or out of, "intentionally none".
    # See `intentionally_none` for why the marker is a separate property and not a tag in the
    # field's own option list.
    mark, unmark = set(), set()
    for key, value in vals.items():
        prop = _property_for(level, key)
        coerced = _coerce(prop, value)
        # A valKey whose stored polarity is the inverse of the UI's (contract Q3) is flipped on
        # the way IN; `api_tree._vals` flips it back on the way out, so `intended` stays UI-space.
        props[prop] = (not coerced) if (level, key) in api_tree.INVERTED_VALS else coerced
        intended[key] = coerced
        if key in intentionally_none.MARKABLE:
            (mark if intentionally_none.is_empty_value(coerced) else unmark).add(key)

    if mark or unmark:
        was = _marker_values(before)
        marker = was
        for k in mark:
            marker = intentionally_none.with_key(marker, k, True)
        for k in unmark:
            marker = intentionally_none.with_key(marker, k, False)
        # Written ONLY when it actually changes. Setting a real value on a field that was never
        # marked is the common case by far, and writing an unchanged marker every time would add
        # a pointless correction-log entry to every ordinary edit — and would demand the property
        # exist on spaces that have no use for it.
        if intentionally_none.marked_keys(marker) != intentionally_none.marked_keys(was):
            props[intentionally_none.PROPERTY] = marker

    gsdo_objects.update(object_id, properties=props)     # guard #3 runs inside
    # A MARKED field is verified as present-and-empty, which is exactly what `_vals` now reports
    # for it — so `_verify` proves the marker landed, not just that the (deleted) field is gone.
    _verify(object_id, level, intended)

    for key in vals:
        _log(object_id, _type_name(before), _property_for(level, key),
             before_vals.get(key), intended[key])
    return {"ok": True, "object": node_for(object_id)}


#: Which inheritable fields can actually be REMOVED so the object inherits again, by the
#: storage format of their property. Verified live 2026-07-18 (see module docstring): writing an
#: empty list to a multi_select deletes the property outright, while a text property keeps `''`
#: as a present-but-empty value and a number has no empty at all. Keyed by format rather than by
#: field name so a fourth inheritable field gets the right answer without a second table to
#: forget — but a format NOT listed here is refused, never guessed.
_REMOVABLE_BY_FORMAT = {"multi_select": []}


def clear_field(object_id, val_key):
    """Remove one field so the object inherits it from its nearest ancestor again (contract §4).

    This is NOT `set_vals(id, {key: ''})`. Key-presence IS the tri-state: a property REMOVED
    inherits, a property present-but-empty is an intentional "none". Writing `''` here would
    silently collapse those two into one and break inheritance across the subtree — the exact
    failure `api_tree._vals` exists to prevent.

    Refuses, rather than half-working, for a format with no verified removal path. A refusal is
    honest and recoverable; a write that reports success while the value stays put is neither.
    """
    before = _get_object(object_id)
    level = _write_level(before)
    prop_name = _property_for(level, val_key)

    prop = g.find_property(prop_name)
    if prop is None:
        raise WriteRefused(f"property {prop_name!r} is not in the live space")
    fmt = prop.get("format")
    if fmt not in _REMOVABLE_BY_FORMAT:
        raise WriteRefused(
            f"{prop_name!r} cannot be cleared back to inheriting — a {fmt} property has no "
            f"verified way to remove its value in Anytype, only to overwrite it")

    before_vals = api_tree._vals(before, level)

    # A field can be "set here" by the MARKER alone (intentionally none). Going back to
    # inheriting has to drop that too, or the object keeps overriding with nothing and the
    # Inherit button appears to do nothing.
    marker_before = _marker_values(before)
    if val_key in intentionally_none.marked_keys(marker_before):
        gsdo_objects.update(object_id, properties={
            intentionally_none.PROPERTY: intentionally_none.with_key(marker_before, val_key, False),
        })
        after_m = _get_object(object_id)
        if val_key in api_tree._vals(after_m, level):
            raise RuntimeError(f"api_write: {val_key!r} did not clear on {object_id!r} "
                               f"(still marked intentionally-none)")
        _log(object_id, _type_name(before), prop_name, before_vals.get(val_key), None)
        return {"ok": True, "object": node_for(object_id)}

    if val_key not in before_vals:
        # Already inheriting. Not an error and not a write — saying so beats a no-op that
        # reports success and leaves her unsure whether anything happened.
        return {"ok": True, "object": node_for(object_id), "already_inheriting": True}

    gsdo_objects.update(object_id, properties={prop_name: _REMOVABLE_BY_FORMAT[fmt]})

    # Read back and prove the key is GONE. `_verify` proves presence; this is its mirror image,
    # and it is the half that actually matters here — a clear that silently did nothing would
    # otherwise report success while the field kept inheriting-blocking its old value.
    after = _get_object(object_id)
    if val_key in api_tree._vals(after, level):
        raise RuntimeError(f"api_write: {val_key!r} did not clear on {object_id!r} "
                           f"(still reads back {api_tree._vals(after, level)[val_key]!r})")

    _log(object_id, _type_name(before), prop_name, before_vals.get(val_key), None)
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


# Interval unit + its "no schedule at all" value. See the as_needed default in convert_type.
INTERVAL_UNIT_PROP = "Interval unit"
AS_NEEDED = "as_needed"


def convert_type(object_id, target):
    """Reclassify a miscategorised object, KEEPING every value it already holds (spec §5).

    June's stated primary use: the weeding gate filed a one-time Task as a Recurring, or the
    reverse, and she wants it corrected without retyping what she entered.

    In-place, because the live API allows it (contract Q2, probed 2026-07-18 — see the module
    docstring). The object's ID NEVER CHANGES, so every inbound reference survives untouched:
    linked projects, plan-cache rows, arc step ids, focus-period lists, this log's own history.

    Three writes at most, each proven by read-back before the next claim is made:
      1. the type itself (`type_key`),
      2. the parent relink — the property expressing "sits under" is type-dependent, so a Task
         under a project uses `Linked Projects` where a Recurring uses `Project link`; the old
         one is CLEARED or the tree would reach the object two ways (the same reason
         `move_object` clears),
      3. `is_workstream`, which is the only thing distinguishing a Workstream from a Project.

    The final read-back is the one that matters most: it proves the new type landed, the links are
    exactly right, AND that nothing was dropped — every property the object held before is still
    held, with the same value, apart from the ones just listed. A conversion that silently lost a
    field would be the exact failure spec §5 exists to prevent, so it raises rather than reports.
    """
    target = (target or "").strip()
    if target not in _CONVERT_TARGET:
        raise WriteRefused(
            f"{target!r} is not a type this surface converts to — "
            f"pick one of {', '.join(_CONVERT_TARGET)}")
    type_name, want_ws = _CONVERT_TARGET[target]

    before = _get_object(object_id)
    old_type = _type_name(before)
    old_level = _write_level(before)          # also refuses a non-GSDO type outright
    new_level = _WRITE_LEVEL[type_name]
    cur_ws = _checkbox(before, WORKSTREAM_PROP)

    # Guard 3 — nothing to do. Checked BEFORE any write so a no-op never reports a success.
    if old_type == type_name and (want_ws is None or bool(cur_ws) == want_ws):
        if type_name == "Project":
            raise WriteRefused(
                f"this is already a {target.lower() if target != 'Subproject' else 'project'} "
                "— a subproject and a project are the same kind of object, and what makes one a "
                "subproject is that it sits under another project. Move it instead of converting "
                "it.")
        raise WriteRefused(f"this is already a {type_name}")

    objs = g.fetch_all_objects(g.get_space_id())

    # Guard 1 — the leaf guard. Naming the children makes the refusal actionable.
    if target in _LEAF_TARGETS:
        kids = _direct_children(object_id, objs)
        if kids:
            names = ", ".join(name for _, name in kids[:5])
            more = f" (and {len(kids) - 5} more)" if len(kids) > 5 else ""
            raise WriteRefused(
                f"this has {len(kids)} item{'s' if len(kids) != 1 else ''} under it, and a "
                f"{type_name} cannot hold anything: {names}{more}. Move them somewhere else "
                f"first, then convert.")

    # Guard 2 — the parent must be able to host the new kind, or the object would be orphaned.
    old_parents = {p: _link_ids(before, p) for p in _ALL_LINKS.get(old_level, [])}
    parent_id = next((ids[0] for ids in old_parents.values() if ids), None)
    new_link = None
    if parent_id is not None:
        parent_type = _type_name(_get_object(parent_id))
        new_link = _LINK_PROP.get((new_level, parent_type))
        if new_link is None:
            raise WriteRefused(
                f"this sits under a {parent_type}, and a {type_name} cannot sit under a "
                f"{parent_type}. Move it under a project first, then convert.")

    kept_before = _stored_values(before)

    # 1. the type. Written on its own, before any property write, so the properties that follow
    #    are resolved against the type the object actually has by then.
    gsdo_objects.update(object_id, type_key=g.find_type(type_name)["key"])
    after_type = _get_object(object_id)
    if _type_name(after_type) != type_name:
        raise RuntimeError(
            f"api_write: type did not persist on {object_id!r} "
            f"(wrote {type_name!r}, read back {_type_name(after_type)!r})")

    # 2 + 3. relink and the workstream flag, in one write — both are ordinary properties.
    props, expected_links = {}, {}
    for prop in _ALL_LINKS.get(new_level, []):
        expected_links[prop] = [parent_id] if prop == new_link else []
    for prop in _ALL_LINKS.get(old_level, []):
        expected_links.setdefault(prop, [])
    for prop, want in expected_links.items():
        if sorted(_link_ids(after_type, prop)) != sorted(want):
            props[prop] = want
    if want_ws is not None and bool(cur_ws) != want_ws:
        props[WORKSTREAM_PROP] = want_ws

    # 4. Converting TO a Recurring: default the cadence to `as_needed` if it has none.
    #
    # ⚠ WITHOUT THIS THE CONVERTED OBJECT SILENTLY VANISHES FROM HER PLAN.
    # datetime_seam.py:119 draws a hard line between two states that both look "unset":
    #     unit == "as_needed"  -> surfaces when Active is on. A real, usable state.
    #     unit missing/empty   -> `return False` unconditionally. "Never-configured stays off",
    #                             i.e. permanently invisible, with nothing to explain why.
    # A Task carries no interval, so a straight conversion lands in the SECOND branch.
    #
    # June's use case (2026-07-18) is precisely why this matters: "a recurring is essentially a
    # task... conversion is important because if the LLM miscategorises the type, I need to be
    # able to see and verify it in the UI as it is entered, so I can fix it then." She converts
    # BECAUSE the thing should recur — so producing a recurring that can never surface is the one
    # outcome the feature must not have.
    #
    # `as_needed` is the honest default rather than a guessed cadence: spec §3 defines it as a
    # recurring with NO schedule, entering the plan only when she toggles it Active, when capture
    # adds it, or when a focus period names it. So the object is visible in Routines, inert until
    # asked for, and the cadence stays hers to set. Active is deliberately NOT set here — a
    # conversion should not push work into today's plan on its own.
    if new_level == "RECURRING" and not _stored_values(after_type).get(INTERVAL_UNIT_PROP):
        props[INTERVAL_UNIT_PROP] = AS_NEEDED
    if props:
        gsdo_objects.update(object_id, properties=props)

    # The proof. Links first, then the no-field-was-dropped check.
    final = _verify_links(object_id, expected_links)
    if want_ws is not None and bool(_checkbox(final, WORKSTREAM_PROP)) != want_ws:
        raise RuntimeError(
            f"api_write: {WORKSTREAM_PROP!r} did not persist on {object_id!r} "
            f"(wrote {want_ws!r}, read back {_checkbox(final, WORKSTREAM_PROP)!r})")

    rewritten = set(expected_links) | {WORKSTREAM_PROP}
    kept_after = _stored_values(final)

    # The cadence default gets its own read-back, because the no-field-was-dropped loop below
    # cannot cover it: that loop walks `kept_before`, and the whole point of the default is that
    # the field was ABSENT before. Without this check a silently-failed interval write reports
    # success and leaves exactly the permanently-invisible recurring the default exists to prevent.
    if props.get(INTERVAL_UNIT_PROP) == AS_NEEDED and not kept_after.get(INTERVAL_UNIT_PROP):
        raise RuntimeError(
            f"api_write: {INTERVAL_UNIT_PROP!r} did not persist on {object_id!r} "
            f"(wrote {AS_NEEDED!r}, read back {kept_after.get(INTERVAL_UNIT_PROP)!r}) — a "
            f"Recurring with no interval unit can never surface in her plan, so this is a "
            f"failed convert, not a partial one")
    for name, was in kept_before.items():
        if name in rewritten:
            continue
        if name not in kept_after:
            raise RuntimeError(
                f"api_write: converting {object_id!r} to {target} DROPPED {name!r} "
                f"(was {was!r}, now absent) — spec §5 requires every value to survive a "
                f"conversion, so this is a failed convert, not a partial one")
        if not _same(was, kept_after[name]):
            raise RuntimeError(
                f"api_write: converting {object_id!r} to {target} CHANGED {name!r} "
                f"(was {was!r}, now {kept_after[name]!r})")

    _log(object_id, old_type, TYPE_FIELD, old_type, type_name, kind="surface_convert")
    if new_link is not None and props:
        _log(object_id, type_name, PARENT_FIELD,
             sorted({i for ids in old_parents.values() for i in ids}) or None, [parent_id],
             kind="surface_convert")
    return {"ok": True, "object": node_for(object_id)}


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

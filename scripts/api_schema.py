#!/usr/bin/env python3
"""The payload behind `GET /api/schema` — what the new surface builds its whole form layer from.

The new UI (`app/`) generates EVERY select, multi-select chip, toggle, date picker, number
field, recurrence editor and notes textarea by iterating this payload. Nothing downstream is
hardcoded, so a wrong schema does not degrade the UI — it produces an empty one
(docs/api_contract_v2.md §3.1).

Three sources are merged here, and the split is deliberate:

1. **Option vocabularies come from LIVE Anytype.** The relation schema is the source of truth
   for what values exist (backend spec §16). We never hardcode an option list — we read the
   property's tags. A hardcoded list is how the UI ends up offering a value the space cannot
   store (live example: `Engagement` no longer carries Sprint / Hyperfixation, but the frontend
   fixture still lists both).

2. **Field order, labels and hint copy are UI-authored** and cannot be derived from Anytype —
   Anytype knows a property exists, not that `Deadline` belongs after `Side` on a Project.
   Those live in the declarative tables below.

3. **Field semantics come from `field_semantics.py`**, the single definition of what each field
   means. June's requirement is that she can SEE these in the UI and eventually revise them, so
   they ride along in a separate `fields` section rather than being folded into the control
   tuples. ⚠ Two keys in each entry are AGENT-facing, not June-facing: `source` (spec citations)
   and `observed` (live-data archaeology, including stale-claim corrections). They are carried so
   the payload is complete, but a June-facing form should render `hint` / `means` / `not_this` /
   `instead` and leave those two out of her way.

⚠ The control tuples are POSITIONAL and the UI destructures them by index, so arity and order
are load-bearing (contract §2.1, and the 2026-07-17 fixture-extraction note: the 4th slot means
a relation key for `select`/`multi` and a second VALUE key for `recur`). This module emits them
byte-for-byte in the fixture's shape. It deliberately does NOT inject semantic hints into the
tuples: that would both change arity on kinds whose declared type has no hint slot AND change
June-facing copy, which is her call, not a build decision.

Reading only. Nothing here writes to Anytype.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import field_semantics


# --- 1. relations -----------------------------------------------------------
# relKey -> the live Anytype property whose tags ARE the vocabulary, the UI's label for it,
# and the preferred display order. `order` is a PREFERENCE, not a filter: an option that is
# live but unlisted is still emitted (appended), because hiding a live value would let the UI
# silently disagree with the space. An option that is listed but NOT live is dropped, because
# offering it would produce a write the space cannot store.
#
# Note two places where the UI's label deliberately differs from the property name:
#   `unit`  -> property "Interval unit", labelled "Frequency" in the form
#   `proj`  -> property "Engagement" (Project-level), labelled "Engagement"
RELATIONS = {
    "goalEng":        {"property": "Goal engagement", "label": "Engagement",
                       "order": ["Backburner", "Open", "Steady", "Sprint"]},
    "goalStatus":     {"property": "Goal status", "label": "Status",
                       "order": ["Active", "Parked", "Achieved"]},
    "horizon":        {"property": "Horizon", "label": "Horizon",
                       "order": ["Chapter", "Milestone", "Short-term", "Medium-term",
                                 "Long-term", "Ongoing"]},
    "proj":           {"property": "Engagement", "label": "Engagement",
                       "order": ["Backburner", "Open", "Steady", "Sprint", "Hyperfixation",
                                 "Needs Clarifying", "Done"]},
    "projStatus":     {"property": "Project status", "label": "Status",
                       "order": ["Active", "Parked", "Inactive"]},
    "side":           {"property": "Side", "label": "Side",
                       "order": ["Work", "Daily life", "Fun / hobby", "Wellbeing"]},
    "taskStatus":     {"property": "Task status", "label": "Status",
                       "order": ["Ready", "Active", "Blocked", "In Design", "Parked",
                                 "Needs Clarifying", "Done"]},
    "access":         {"property": "Access conditions", "label": "Access conditions",
                       "order": ["Requires-talking-to-a-person", "Can-be-done-lying-down",
                                 "Involves-leaving-house", "Requires-deep-thinking",
                                 "Involves-bureaucracy", "Induces-pain"]},
    "unit":           {"property": "Interval unit", "label": "Frequency",
                       "order": ["day", "week", "month", "as_needed"]},
    "dow":            {"property": "Day of week", "label": "Day of week",
                       "order": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
    "strategyState":  {"property": "Applies when", "label": "Applies when",
                       "order": ["Always", "Low energy", "Overwhelmed", "Sprint", "Stuck"]},
    "strategyStatus": {"property": "Strategy status", "label": "Status",
                       "order": ["Active", "Retired"]},
}


# --- 2. controls / notes ----------------------------------------------------
# Positional tuples, verbatim in the shape `app/src/fixtures/schema.ts` declares.
#   ['select'|'multi', label, valKey, relKey, hint?]
#   ['date',   label, valKey, null, hint?]
#   ['number', label, valKey, null?, null?]
#   ['time'|'toggle', label, valKey]
#   ['recur',  label, countKey, unitKey]      <- 4th slot is a VALUE key here, not a relation
CONTROLS = {
    "GOAL": [
        ["select", "Engagement", "engagement", "goalEng"],
        ["select", "Goal status", "status", "goalStatus"],
        ["select", "Horizon", "horizon", "horizon"],
    ],
    "PROJECT": [
        ["select", "Engagement", "engagement", "proj"],
        ["select", "Project status", "status", "projStatus"],
        ["select", "Side", "side", "side"],
        ["date", "Deadline", "deadline"],
        ["number", "Typical block (min)", "blockMin", None, None],
        ["multi", "Access conditions", "access", "access",
         "Block-level default — tasks inherit unless they set their own."],
    ],
    "SUBPROJECT": [
        ["select", "Engagement", "engagement", "proj"],
        ["select", "Project status", "status", "projStatus"],
        ["select", "Side", "side", "side"],
        ["number", "Typical block (min)", "blockMin", None, None],
        ["multi", "Access conditions", "access", "access",
         "Block-level default — tasks inherit unless they set their own."],
    ],
    "WORKSTREAM": [
        ["select", "Engagement", "engagement", "proj"],
        ["select", "Status", "status", "projStatus"],
        ["number", "Typical block (min)", "blockMin", None, None],
        ["multi", "Access conditions", "access", "access",
         "Block-level default — tasks inherit unless they set their own."],
    ],
    "TASK": [
        ["select", "Task status", "status", "taskStatus"],
        ["date", "Due date", "due", None,
         "Deadline — drives urgency and ordering in the plan."],
        ["date", "Scheduled", "scheduled", None,
         "The day your plan has placed it (usually set when you schedule or move it)."],
        ["number", "Duration (min)", "duration"],
        ["toggle", "AI Autonomous", "ai"],
        ["toggle", "Needs clarifying", "needs"],
        ["multi", "Access conditions", "access", "access"],
    ],
    "RECURRING": [
        ["recur", "Repeats", "count", "unit"],
        ["multi", "Day of week", "dow", "dow"],
        ["number", "Day of month", "dom"],
        ["time", "Time of day", "tod"],
        ["number", "Duration (min)", "duration"],
        ["toggle", "AI Autonomous", "ai"],
        ["toggle", "Needs clarifying", "needs"],
        ["multi", "Access conditions", "access", "access"],
    ],
    "STRATEGY": [
        ["select", "Applies when", "when", "strategyState"],
        ["select", "Strategy status", "status", "strategyStatus"],
    ],
}

NOTES = {
    "GOAL": [["Reaching for", "reaching"], ["Resolution condition", "resolution"],
             ["Context", "context"], ["Barriers", "barriers"]],
    "PROJECT": [["Reaching for", "reaching"], ["Description", "description"],
                ["Context", "context"], ["Affective", "affective"], ["Barriers", "barriers"]],
    "SUBPROJECT": [["Reaching for", "reaching"], ["Context", "context"],
                   ["Affective", "affective"]],
    "WORKSTREAM": [["Reaching for", "reaching"], ["Context", "context"]],
    "TASK": [["Context", "context"], ["Access notes", "accessNotes"],
             ["Affective", "affective"], ["Blocked on", "blocked"],
             ["Relevant docs", "docs"]],
    "RECURRING": [["Context", "context"], ["Access notes", "accessNotes"],
                  ["Affective", "affective"], ["Blocked on", "blocked"],
                  ["Relevant docs", "docs"]],
    "STRATEGY": [["Directive", "directive"], ["Notes", "context"]],
}


# --- 3. valKey -> live Anytype property, per level --------------------------
# The bridge the semantics lookup needs: the UI speaks camelCase valKeys, `field_semantics`
# is keyed by the live display name. Levels are UI concepts, not Anytype types (SUBPROJECT and
# WORKSTREAM are both the `Project` type — backend spec §5), so the type used for the
# type-scoped semantics lookup is named separately.
LEVEL_TYPE = {
    "GOAL": "Goal", "PROJECT": "Project", "SUBPROJECT": "Project", "WORKSTREAM": "Project",
    "TASK": "Task", "RECURRING": "Recurring", "STRATEGY": "Strategy",
}

# ⚠ `directive` maps to the live `What for` property, NOT to a new `Directive` field. June
# decided 2026-07-18 (docs/BUILD_DOC.md §8, "use the existing strategy data structure"): the
# mockup drifted from the data model and the data model wins. `What for` is empirically where
# her instructions live across all 12 real Strategy objects. The UI's valKey stays `directive`
# because that is the frontend contract; only the storage target is corrected here.
# The most minutes any duration-family field will accept — a full day. A fact about days, not a
# view about how long June's work should take (the full reasoning lives at server.py's
# /api/duration guard: an example-turned-rule is exactly the failure mode BLOCK_DEFAULT_MIN = 90
# already was). ONE source of truth, because a duration reaches Anytype by two doors — the
# dedicated /api/duration route and the generic object-field write (set_vals) — and a cap on only
# one is a cap on neither. DURATION_VAL_KEYS names the UI valKeys that mean "minutes".
MAX_DURATION_MIN = 24 * 60
DURATION_VAL_KEYS = frozenset({"duration", "blockMin"})

PROPERTY_FOR = {
    "GOAL": {"engagement": "Goal engagement", "status": "Goal status", "horizon": "Horizon",
             "reaching": "Reaching for", "resolution": "Resolution condition",
             "context": "Context", "barriers": "Barriers"},
    "PROJECT": {"engagement": "Engagement", "status": "Project status", "side": "Side",
                "deadline": "Deadline", "blockMin": "Block chunk min",
                "access": "Access conditions", "reaching": "Reaching for",
                "description": "Description", "context": "Context",
                "affective": "Affective", "barriers": "Barriers"},
    "TASK": {"status": "Task status", "due": "Due date", "scheduled": "Scheduled",
             "duration": "Duration min", "ai": "AI autonomous", "needs": "Needs clarifying",
             "access": "Access conditions", "context": "Context",
             "accessNotes": "Access notes", "affective": "Affective",
             "blocked": "Blocked on", "docs": "Relevant docs"},
    "RECURRING": {"count": "Interval count", "unit": "Interval unit", "dow": "Day of week",
                  "dom": "Day of month", "tod": "Time of day", "duration": "Duration min",
                  "ai": "AI autonomous", "needs": "Needs clarifying",
                  "access": "Access conditions", "context": "Context",
                  "accessNotes": "Access notes", "affective": "Affective",
                  "blocked": "Blocked on", "docs": "Relevant docs"},
    "STRATEGY": {"when": "Applies when", "status": "Strategy status",
                 "directive": "What for", "context": "Context"},
}
# SUBPROJECT and WORKSTREAM are Projects; they surface a subset of the same properties.
PROPERTY_FOR["SUBPROJECT"] = dict(PROPERTY_FOR["PROJECT"])
PROPERTY_FOR["WORKSTREAM"] = dict(PROPERTY_FOR["PROJECT"])


def _live_options():
    """{property display name: [option names]} for every select/multi_select we surface.

    One pass over the space's properties, then one tags call per property we actually need.
    Raises rather than returning a partial vocabulary — a schema missing its options renders an
    empty form, and an empty form that looks fine is worse than a visible error.
    """
    sid = g.get_space_id()
    st, body = g.call("GET", f"/spaces/{sid}/properties?limit=200")
    if st != 200:
        raise RuntimeError(f"api_schema: listing properties failed: {st} {body}")
    by_name = {}
    for p in (body or {}).get("data", []):
        by_name.setdefault(p.get("name"), p)

    wanted = {r["property"] for r in RELATIONS.values()}
    out = {}
    for name in sorted(wanted):
        prop = by_name.get(name)
        if prop is None:
            raise RuntimeError(f"api_schema: property {name!r} is not in the live space — "
                               f"the schema endpoint cannot honestly report its options")
        pid = prop["id"]
        st, tb = g.call("GET", f"/spaces/{sid}/properties/{pid}/tags?limit=200")
        if st != 200:
            raise RuntimeError(f"api_schema: reading tags of {name!r} failed: {st} {tb}")
        out[name] = [t.get("name") for t in (tb or {}).get("data", []) if t.get("name")]
    return out


def _ordered(live, preferred):
    """Preferred order first (live members only), then any live option we did not anticipate."""
    live_set = set(live)
    ordered = [o for o in preferred if o in live_set]
    ordered += [o for o in live if o not in set(preferred)]
    return ordered


def _field_entry(level, val_key):
    """Semantics for one form field, or None when the field has no documented meaning.

    `field_semantics.one_line` is type-scoped on purpose: a field live on a type the specs never
    documented it for returns None rather than the other type's meaning. Kept here.
    """
    prop = PROPERTY_FOR.get(level, {}).get(val_key)
    if not prop:
        return None
    type_name = LEVEL_TYPE[level]
    entry = field_semantics.resolved(prop)
    hint = field_semantics.one_line(prop, type_name=type_name)
    if entry is None:
        reason = field_semantics.undefined_reason(prop)
        if reason is None:
            return None
        return {"property": prop, "hint": None, "documented": False, "reason": reason,
                "does": field_semantics.does(prop)}
    return {
        "property": prop,
        "documented": True,
        # `hint` is None when the field is documented but not for THIS type — an honest gap,
        # not a missing definition. The UI shows no hint rather than the wrong one.
        "hint": hint,
        "means": entry.get("means"),
        "not_this": entry.get("not_this"),
        "instead": entry.get("instead") or {},
        "usage": entry.get("usage") or [],
        "source": entry.get("source"),
        "observed": entry.get("observed"),
        "does": entry.get("does"),
        # So June can see in the UI which of these SHE has revised, and what the repo default was.
        "overridden": entry.get("overridden") or [],
        "default": entry.get("default") or {},
    }


def build_schema():
    """The `GET /api/schema` body. Reads the live space; never writes."""
    live = _live_options()
    relations = {}
    for rel_key, spec in RELATIONS.items():
        relations[rel_key] = {
            "label": spec["label"],
            "options": _ordered(live[spec["property"]], spec["order"]),
            # Which live property the vocabulary came from — so a mismatch is debuggable from
            # the payload itself instead of by re-reading this module.
            "property": spec["property"],
        }

    fields = {}
    for level in CONTROLS:
        per_level = {}
        for ctrl in CONTROLS[level]:
            kind = ctrl[0]
            # `recur` carries TWO value keys (count, unit) in slots 2 and 3.
            keys = [ctrl[2], ctrl[3]] if kind == "recur" else [ctrl[2]]
            for k in keys:
                e = _field_entry(level, k)
                if e:
                    per_level[k] = e
        for label, val_key in NOTES[level]:
            e = _field_entry(level, val_key)
            if e:
                per_level[val_key] = e
        fields[level] = per_level

    return {
        "relations": relations,
        "controls": {lvl: [list(c) for c in CONTROLS[lvl]] for lvl in CONTROLS},
        "notes": {lvl: [list(n) for n in NOTES[lvl]] for lvl in NOTES},
        "fields": fields,
        "levelTypes": dict(LEVEL_TYPE),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_schema(), indent=2, ensure_ascii=False))

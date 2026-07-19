#!/usr/bin/env python3
"""v1 chat-authoring seam for a Focus Period: create the object AND capture June's raw
words as learning signal in one call — so config authoring/corrections are logged from
day one, before the overlay authoring UI (Phase 6) exists.

Authoring is speak -> structure -> confirm (NOT auto-generated content): June says her
week, an instance structures it into fields, she confirms. The caller must resolve any
project names -> ids before passing `properties` (the write side of gsdo_objects.create
formats an `objects` relation as a list of ids; the read side hands back id/name pairs).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import gsdo_objects
import signal_log
import corrections_log

#: `Intent` is June's own words and is NEVER reworded by the generator (backend spec §17), so on
#: an otherwise model-authored period it is user-authored. Stamping it 'llm' would record a
#: correction of the model every time she edits her own sentence — a false positive in exactly
#: the signal this is built to measure. This one field is why provenance is per-FIELD and not
#: per-object: a single Focus Period legitimately carries both at once.
USER_AUTHORED_FIELDS = ("Intent",)

FOCUS_SURFACE = "focus_period_authoring"


def _stamp_period_authorship(object_id, name, properties, surface=FOCUS_SURFACE):
    """Stamp who authored each structured field of a Focus Period. Best-effort: never lose a
    period that already persisted over a logging failure, but print rather than swallow (§5.1)."""
    try:
        corrections_log.log_authorship(object_id, corrections_log.TITLE_FIELD, name,
                                       object_type="Focus Period", surface=surface)
        for field, value in (properties or {}).items():
            by = "user" if field in USER_AUTHORED_FIELDS else "llm"
            corrections_log.log_authorship(object_id, field, value, object_type="Focus Period",
                                           authored_by=by, surface=surface)
    except Exception as e:                                    # noqa: BLE001
        print(f"[warn] authorship not stamped for focus period {object_id}: {e}", file=sys.stderr)


def resolve_project_names_to_ids(names, objects=None):
    """Resolve project display-names -> Anytype ids for the Foreground/Paused relations.

    The write side of a Focus Period needs ids (the objects relation is a list of ids);
    June speaks names. Raises on an unknown name — never silently drops a project she named.
    `objects` may be passed (already-fetched) for testing; otherwise fetched live.

    Payload recipe (what author_focus_period's `properties` looks like):
      {"Period start": "2026-06-30", "Period end": "2026-07-06", "Intent": "...",
       "Availability start"/"Availability end": ISO date, "Availability note": "...",
       "Days off"/"Days on": "2026-07-03, 2026-07-04",  # CSV or JSON array
       "Output format": "Auto"|"Clock schedule"|"Priority list",
       "Workday start": "11:00", "Workday end": "22:00",
       "Foreground projects": [<id>, ...], "Paused projects": [<id>, ...]}
    """
    if objects is None:
        objects = g.fetch_all_objects(g.get_space_id())
    by_name = {}
    for o in objects:
        t = o.get("type")
        tk = t.get("key") if isinstance(t, dict) else t
        if tk == "gsdo_project" and o.get("name"):
            by_name[o["name"]] = o["id"]
    ids = []
    for n in names:
        if n not in by_name:
            raise ValueError(f"project {n!r} not found — can't foreground/pause it")
        ids.append(by_name[n])
    return ids


def _log_her_words(raw_text, source, object_id, name):
    """Record raw_text in signal_log ONLY when there are words of hers in it.

    `signal_log.jsonl` is documented and read as June's OWN TYPED WORDS. Both write routes accept
    an empty `raw_text` (the per-field editor changes one field with no sentence typed at all),
    and logging that produces a record stamped `config_correction` with nothing in it — a claim
    that she said something on this action when she said nothing. Same rule as commit 1522ad5,
    which moved machine-recorded deferrals out of this log for the same reason.

    Withholding the signal is not a silent failure: nothing was asked for and nothing is claimed.
    The object write itself has already happened and is unaffected."""
    if not (raw_text or "").strip():
        return
    signal_log.log_signal(raw_text, source=source,
                          reference={"kind": "focus_period", "id": object_id, "name": name})


def author_focus_period(raw_text, name, properties, source="config_authoring"):
    """Create a Focus Period and log June's raw words as signal. Returns the new object id.
    source='config_correction' when editing an existing period's framing."""
    oid = gsdo_objects.create("Focus Period", name, properties=properties)
    _stamp_period_authorship(oid, name, properties)
    _log_her_words(raw_text, source, oid, name)
    return oid


def update_focus_period(object_id, raw_text, name, properties, source="config_correction"):
    """Update an existing Focus Period IN PLACE (v1 choice — the period object is short-lived;
    archive-on-lapse is Phase 8) and log June's words as a correction signal. Returns object_id.
    The caller resolves project names -> ids first, same as the create path."""
    gsdo_objects.update(object_id, name=name, properties=properties)
    # An edit pass re-authors these fields, so it re-stamps them. The fold is last-write-wins, so
    # the newer stamp is what a later correction resolves against.
    _stamp_period_authorship(object_id, name, properties, surface=source)
    _log_her_words(raw_text, source, object_id, name)
    return object_id

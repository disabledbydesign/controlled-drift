#!/usr/bin/env python3
"""The adapter between the two halves of Focus Period authoring (Phase 6, Task 3/6B).

`focus_period_generate.generate_focus_period` emits a flat dict of *proposed* fields
(project NAMES, ISO date strings, its own key names). `focus_period_author.author_focus_period`
wants `properties` keyed by Anytype DISPLAY NAMES, with project IDs and days as CSV text. Nothing
mapped between them — this module is that missing seam, plus the two things that gate a safe write:

  * missing_required()  — a period with no start/end never becomes active (load_active_focus_period
    needs both) and nothing tells June — a silent failure. We detect it and BLOCK the write.
  * reflect_back()      — a DETERMINISTIC template (NOT a second LLM call) over the already-structured
    fields, so the confirmation surface June depends on carries no freshly-generated prose (no-metaphors
    guard) and is testable. Compressed summary + per-field items she can verify and fix one at a time.

All three are pure over their inputs (name->id resolution takes the objects list), so they test
offline and the write path stays honest: the LLM's job was speech->structure; every step after is
deterministic.
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import focus_period as fp
import focus_period_author as author
import recurring_active

_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# The only two fields a period cannot fire without (focus_period.load_active_focus_period requires
# both start and end). Missing either = a period that silently never activates.
_REQUIRED = (("start_date", "start date"), ("end_date", "end date"))

_VALID_SHAPES = ("Auto", "Clock schedule", "Priority list")


def _fmt_iso(s, weekday=True):
    """'2026-07-04' -> 'Sat Jul 4' (or 'Jul 4'). Returns '' for empty/malformed — never raises,
    so a bad date shows as blank in the reflect-back rather than crashing the confirm surface."""
    if not s:
        return ""
    try:
        d = dt.date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return ""
    base = f"{_MONTHS[d.month]} {d.day}"
    return f"{_WEEKDAYS[d.weekday()]} {base}" if weekday else base


def _fmt_range(a, b):
    fa, fb = _fmt_iso(a), _fmt_iso(b)
    if fa and fb:
        return f"{fa} – {fb}"
    return fa or fb


def _csv(vals):
    """ISO date list -> 'a, b, c' text for the CSV/JSON date fields. Skips blanks."""
    return ", ".join(str(v) for v in (vals or []) if v)


def missing_required(fields):
    """The required scalars a period can't activate without. Returns a list of plain labels
    (e.g. ['end date']) — empty when the write is safe. The UI surfaces these and blocks save,
    the same Needs-Clarifying pattern the capture flow uses."""
    return [label for key, label in _REQUIRED if not (fields or {}).get(key)]


def to_write_properties(fields, objects=None):
    """Map generate_focus_period output -> (name, properties) for author_focus_period.

    Key renames to display names, project NAMES -> IDs (raises on an unknown name — never silently
    drops a project June named), ISO date lists -> CSV text, output_format preserved EXACTLY as one
    of the three select values. `objects` may be passed (already-fetched) for testing.

    Caller should run missing_required() first and block — this function will still build a
    properties dict without start/end (so a fix flow can proceed), but authoring one is the silent
    failure we guard against upstream."""
    f = fields or {}
    name = f.get("name") or "Focus period"

    fg = author.resolve_project_names_to_ids(f.get("foreground_projects") or [], objects=objects)
    paused = author.resolve_project_names_to_ids(f.get("paused_projects") or [], objects=objects)

    shape = f.get("output_format") or "Auto"
    if shape not in _VALID_SHAPES:
        shape = "Auto"  # never write a garbage select value; Auto is the safe default

    props = {"Output format": shape}
    # only set what's present — an absent field should stay unset, not be written as empty
    if f.get("start_date"):        props["Period start"] = f["start_date"]
    if f.get("end_date"):          props["Period end"] = f["end_date"]
    if f.get("intent"):            props["Intent"] = f["intent"]
    if f.get("availability_start"): props["Availability start"] = f["availability_start"]
    if f.get("availability_end"):  props["Availability end"] = f["availability_end"]
    if f.get("availability_note"): props["Availability note"] = f["availability_note"]
    if f.get("days_off"):          props["Days off"] = _csv(f["days_off"])
    if f.get("days_on"):           props["Days on"] = _csv(f["days_on"])
    if f.get("workday_end"):       props["Workday end"] = f["workday_end"]
    if fg:                         props["Foreground projects"] = fg
    if paused:                     props["Paused projects"] = paused
    return name, props


# How each written property must be compared on read-back. Anything not listed is plain text.
_DATE_PROPS = ("Period start", "Period end", "Availability start", "Availability end")
_DATELIST_PROPS = ("Days off", "Days on")
_OBJECT_PROPS = ("Foreground projects", "Paused projects")


def verify_persisted(props, obj):
    """Prove EVERY property to_write_properties wrote actually landed on the re-fetched object.

    Returns a list of plain mismatch descriptions — empty means the whole write is confirmed.
    The commit/update routes read back and then checked only start and end, so any other field
    (intent, availability, days off, output format, foreground/paused projects) could fail to
    persist while the route still reported success. Comparison is by MEANING, not raw string:
    dates are parsed (Anytype normalizes an ISO date to a datetime), date lists compare as sets,
    and the objects relations compare as id sets (they read back as bare id strings).
    """
    if not isinstance(obj, dict):
        return ["the period object could not be re-fetched"]
    by_name = fp._by_name(obj)
    out = []
    for pname, want in (props or {}).items():
        if pname in _DATE_PROPS:
            got = fp._date(by_name, pname)
            try:
                intended = dt.date.fromisoformat(str(want)[:10])
            except (ValueError, TypeError):
                intended = None
            if got != intended:
                got_s = got.isoformat() if got else None
                out.append(f"{pname}: wrote {want!r}, read back {got_s!r}")
        elif pname in _DATELIST_PROPS:
            got, _err = fp._parse_date_list(by_name, pname)
            intended = [t.strip()[:10] for t in str(want).split(",") if t.strip()]
            if set(got) != set(intended):
                out.append(f"{pname}: wrote {intended!r}, read back {got!r}")
        elif pname in _OBJECT_PROPS:
            got = sorted({oid for oid, _n in fp._objects_pairs(by_name, pname)})
            intended = sorted(set(want or []))
            if got != intended:
                out.append(f"{pname}: wrote {intended!r}, read back {got!r}")
        elif pname == "Output format":
            sel = (by_name.get(pname) or {}).get("select") or {}
            got = sel.get("name") if isinstance(sel, dict) else sel
            if got != want:
                out.append(f"{pname}: wrote {want!r}, read back {got!r}")
        else:
            got = fp._text(by_name, pname)
            if (got or "").strip() != str(want).strip():
                out.append(f"{pname}: wrote {want!r}, read back {got!r}")
    return out


def resolve_reactivate_names(names, objects=None):
    """Resolve as-needed-Recurring display names -> Anytype ids for commit-time activation.

    Unlike resolve_project_names_to_ids, an unmatched name is NOT an error — it's surfaced back
    to the caller instead (a mis-heard/renamed task is real signal June should see, not a reason
    to fail or silently drop the rest of the commit). Returns (resolved_ids, unresolved_names).
    `objects` may be passed (already-fetched, e.g. by the commit route) to avoid a second fetch."""
    if objects is None:
        objects = g.fetch_all_objects(g.get_space_id())
    by_name = {o["name"]: o["id"] for o in recurring_active.as_needed_objects(objects)
              if o.get("name")}
    resolved, unresolved = [], []
    for n in (names or []):
        if n in by_name:
            resolved.append(by_name[n])
        else:
            unresolved.append(n)
    return resolved, unresolved


def _iso(d):
    """A date object (or None) -> ISO string (or None). For turning a stored period back into
    the generate-style fields dict the edit flow works on."""
    return d.isoformat() if d else None


def period_to_fields(period):
    """Inverse of the write path: a loaded period (daily_plan/load_active_items shape, with
    `foreground`/`paused` resolved to current NAMES and dates as date objects) -> the flat,
    generate-style fields dict the reflect-back + per-field editors operate on. This is what
    seeds an EDIT: June starts from the period's current state, not a blank slate."""
    p = period or {}
    return {
        "name": p.get("name") or "",
        "start_date": _iso(p.get("start")),
        "end_date": _iso(p.get("end")),
        "intent": p.get("intent") or "",
        "availability_start": _iso(p.get("availability_start")),
        "availability_end": _iso(p.get("availability_end")),
        "availability_note": p.get("availability_note") or "",
        "days_off": list(p.get("days_off") or []),
        "days_on": list(p.get("days_on") or []),
        "output_format": p.get("output_format") or "Auto",
        "workday_end": p.get("workday_end"),
        "foreground_projects": list(p.get("foreground") or []),
        "paused_projects": list(p.get("paused") or []),
    }


# fields whose change the diff reflect-back should mark (the ones a reflect item represents)
_ITEM_FIELDS = {
    "foreground": ("foreground_projects",),
    "dates": ("start_date", "end_date"),
    "availability": ("availability_start", "availability_end"),
    "days_off": ("days_off",),
    "output_format": ("output_format",),
    "intent": ("intent",),
    "paused": ("paused_projects",),
    "workday_end": ("workday_end",),
    "reactivate_tasks": ("reactivate_tasks",),
}


def reflect_back(fields, original=None):
    """A deterministic confirmation payload over the structured fields — NOT a second LLM call.

    Shape (rendered by the overlay): a compressed `summary` (uses the label the generate step
    already produced), an itemized `items` list June can verify + fix one field at a time, and
    `blocking` (missing required fields) so the UI blocks save until they're resolved. Each item
    carries an `edit` hint so the client opens the right deterministic editor (date picker /
    project selector / text / select) — no re-speaking, no LLM round-trip."""
    f = fields or {}
    fg = f.get("foreground_projects") or []
    paused = f.get("paused_projects") or []
    days_off = f.get("days_off") or []

    items = [
        {"key": "foreground", "label": "In front", "edit": "projects",
         "display": ", ".join(fg) if fg else "—"},
        {"key": "dates", "label": "Dates", "edit": "daterange",
         "display": _fmt_range(f.get("start_date"), f.get("end_date")) or "not set"},
        {"key": "availability", "label": "Availability window", "edit": "daterange",
         "display": _fmt_range(f.get("availability_start"), f.get("availability_end")) or "none"},
        {"key": "days_off", "label": "Days off", "edit": "dates",
         "display": ", ".join(_fmt_iso(d, weekday=True) for d in days_off) if days_off
                    else "weekends (default)"},
        {"key": "output_format", "label": "Plan shape", "edit": "select",
         "display": f.get("output_format") or "Auto"},
        {"key": "intent", "label": "Intent", "edit": "text",
         "display": f.get("intent") or "—"},
    ]
    if paused:
        items.append({"key": "paused", "label": "Paused", "edit": "projects",
                      "display": ", ".join(paused)})
    if f.get("workday_end"):
        items.append({"key": "workday_end", "label": "Working until", "edit": "text",
                      "display": f["workday_end"]})
    reactivate = f.get("reactivate_tasks") or []
    if reactivate:
        items.append({"key": "reactivate_tasks", "label": "Reopening", "edit": "text",
                      "display": ", ".join(reactivate)})

    # Edit mode: mark which items CHANGED vs the period's original state, so an unintended
    # change (an LLM revision that clobbered an unrelated field) is visible before anything
    # writes — the confirm gate for a spoken edit is this diff, not blind trust.
    if original is not None:
        for it in items:
            it["changed"] = any((original or {}).get(k) != f.get(k)
                                for k in _ITEM_FIELDS.get(it["key"], ()))

    return {
        "summary": (f.get("name") or "Your focus period"),
        "items": items,
        "blocking": missing_required(f),
        "is_edit": original is not None,
    }

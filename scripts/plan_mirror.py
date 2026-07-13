#!/usr/bin/env python3
"""Mirror June's confirmed daily plan into ONE Anytype object, updated in place.

Why this exists: the founding spec (AI_LAYER_SPEC.md §10) required June's confirmed plan to
stay human-readable even when the AI layer is down. The built system put the plan only in a
local cache (~/.controlled-drift/current_plan.json) + the overlay — so if the server/overlay is
down, the plan is unreadable. This mirrors the plan into a single Anytype Note that Anytype
renders on its own, no server needed. It is a COPY for when the main surface is down; the live
plan is the overlay.

June's decision (2026-07-12): ONE object, updated idempotently every generation — a cheap in,
NO per-day accumulation. The learning loop already keeps daily history (plan_snapshots.jsonl);
this object is only the current readable copy.

Best-effort: a mirror failure (Anytype app closed, API down) must NEVER break or delay plan
generation. The generation path calls mirror_plan_safe(), which swallows any failure and logs
one honest line. Never a retry-loop against a closed app.
"""
import sys, os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_objects

# The single stable object we find-or-create then update every generation. Dedup is by
# normalized name (gsdo_objects.find_existing / create), so this name IS the idempotency key —
# keep it stable.
MIRROR_NAME = "Today's plan — Controlled Drift"
NOTE_TYPE_KEY = "note"          # built-in Note type key (find_existing keys on type_key)
NOTE_TYPE_NAME = "Note"         # friendly name for gsdo_objects.create

FOOTER = ("This is a copy for when the main surface is down. "
          "The live plan is in the overlay.")


# --- rendering (pure — no network) ------------------------------------------

def _fmt_time(when):
    """A datetime -> '9:50 PM'. Plain clock time June reads at a glance."""
    return when.strftime("%-I:%M %p")


def _relative_day(then, today):
    """Plain words for how old the plan is: today / yesterday / N days ago / in N days.
    `then` and `today` are dates. No bare dates (a date string is jargon to scan past)."""
    delta = (then - today).days
    if delta == 0:
        return "today"
    if delta == -1:
        return "yesterday"
    if delta < -1:
        return f"{-delta} days ago"
    if delta == 1:
        return "tomorrow"
    return f"in {delta} days"


def _age_line(plan, now):
    """First line: when this plan was built, in plain words. Falls back honestly if the
    timestamp is missing or unparseable (never invents a time)."""
    raw = plan.get("generated_at")
    if not raw:
        return "Built recently (the exact time wasn't recorded)."
    try:
        built = dt.datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return "Built recently (the exact time wasn't recorded)."
    day = _relative_day(built.date(), now.date())
    return f"Built {day} at {_fmt_time(built)}."


def _item_name(item):
    """The task name for one plan item. Clock items use 'task'; priority items use 'name'.
    Handle both so either plan shape renders."""
    return item.get("task") or item.get("name") or "(unnamed)"


def render_body(plan, now=None):
    """Render the cached plan dict into a plain-language Markdown body for the mirror Note.

    Shape: age line first, then the plan itself (clock blocks, or a fragmented-day priority
    list), then the still-waiting items, then the honest footer. June-facing: plain words, no
    metaphors, no internal jargon. The mirror deliberately does NOT echo the plan's woven_frame
    or per-block framing prose — only times + task names — so no LLM metaphors leak in.
    """
    now = now or dt.datetime.now()
    lines = [_age_line(plan, now), ""]

    shape = plan.get("shape")
    blocks = plan.get("blocks") or []
    items = plan.get("items") or []

    if shape == "priority" or (items and not blocks):
        # Fragmented day: an ordered list to pull from, no fixed times.
        lines.append("Today — a list to pull from, in order (no fixed times):")
        lines.append("")
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {_item_name(item)}")
    else:
        # Clock day: labelled time-blocks, each with its items' times + names.
        lines.append("Today's plan:")
        for block in blocks:
            lines.append("")
            label = block.get("label") or ""
            time = block.get("time") or ""
            header = " — ".join(p for p in (time, label) if p) or "(block)"
            lines.append(f"**{header}**")
            for item in block.get("items", []):
                t = item.get("time") or ""
                name = _item_name(item)
                lines.append(f"- {t}  {name}" if t else f"- {name}")

    still = plan.get("still_here") or []
    if still:
        lines.append("")
        lines.append("Still waiting — not on today's plan:")
        for s in still:
            label = s.get("label") or s.get("name") or "(unnamed)"
            note = s.get("note")
            lines.append(f"- {label} — {note}" if note else f"- {label}")

    lines.append("")
    lines.append("---")
    lines.append(FOOTER)
    return "\n".join(lines)


# --- writing (find-or-create ONE object, then update its body) --------------

def mirror_plan(plan, now=None):
    """Write the plan into the single mirror Note, idempotently.

    Find-or-create the Note by its stable name (create() already dedups by name, so a repeat
    create returns the same id), then UPDATE its body. Read-back verifies the body persisted
    (a good answer is not a saved object). Returns the object id.

    Raises on a real failure — callers that must not be broken by a mirror failure use
    mirror_plan_safe() instead.
    """
    body = render_body(plan, now=now)
    existing_id = gsdo_objects.find_existing(NOTE_TYPE_KEY, MIRROR_NAME)
    if existing_id:
        oid = existing_id
        gsdo_objects.update(oid, body=body)
    else:
        # First run: create carries the body straight in (create sends `body`).
        oid = gsdo_objects.create(NOTE_TYPE_NAME, MIRROR_NAME, body=body)

    # Read-back: prove the body actually landed. The GET returns the rendered body under
    # `markdown` (escaped) and a `snippet` preview. The probe is the AGE LINE — the first line
    # of the body we just wrote — because it changes with every generation; probing something
    # constant (the footer) would false-pass on a STALE body left by a previous write
    # (cross-family review finding, 2026-07-12).
    import gsdo_anytype as g
    from anytype_test import call
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"plan_mirror: could not read back the mirror note {oid!r}: {st} {b}")
    obj = b["object"]
    got = (obj.get("markdown") or "") + " " + (obj.get("snippet") or "")
    # Strip Markdown backslash-escapes before matching (Anytype escapes _, -, etc.).
    got_plain = got.replace("\\", "")
    probe = body.splitlines()[0].replace("\\", "")
    if probe not in got_plain:
        raise RuntimeError(
            f"plan_mirror: mirror note {oid!r} body did not persist "
            f"(read-back missing this write's age line {probe!r})")
    return oid


def mirror_plan_safe(plan, now=None):
    """Best-effort mirror: never raises, never delays generation. Returns the object id on
    success, or None on any failure — logging one honest line to stderr (the repo's
    best-effort pattern, same as the plan-snapshot warn). Never retries against a closed app.
    """
    if os.environ.get("CD_DISABLE_PLAN_MIRROR"):
        # Structural test-sandbox guard (set by tests/conftest.py): the file sandbox can't
        # intercept a live API write, so the mirror itself refuses when the suite is running.
        return None
    try:
        return mirror_plan(plan, now=now)
    except Exception as e:
        # One honest line; the plan is already cached, so generation is unaffected. Anytype
        # being closed / the API being down is the common, expected cause.
        print(f"[warn] plan not mirrored to Anytype (the local plan is unaffected): {e}",
              file=sys.stderr)
        return None


if __name__ == "__main__":
    # Manual live check: render + mirror the currently cached plan.
    import plan_store
    plan = plan_store.load_plan()
    if plan is None:
        print("no cached plan to mirror")
        sys.exit(1)
    print(render_body(plan))
    print("\n--- mirroring ---")
    oid = mirror_plan_safe(plan)
    print(f"mirror object id: {oid}")

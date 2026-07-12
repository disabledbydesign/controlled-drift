"""Shared, network-free builder for a captured item's OPTIONAL Anytype field values.

Single source of truth for BOTH write paths (capture_generate._creation_props and
memory_pass.apply_candidate) so the two can never diverge on how a duration / affect /
blocked-on / access-condition is validated and shaped. All validation is here; the callers
just pass raw values in and splice the returned dict into their props.

Rules (from the 2026-07-12 capture audit + June's decisions + repo guards):
  - Never invent: an absent/blank/invalid value writes NOTHING (the reader's own no-value
    path then applies — e.g. the scheduler's default duration).
  - Affect fidelity (June, 2026-07-12): each item's affect matches the scope June's words
    gave it — a feeling about one item lands on that item; a feeling she states about the
    whole dump lands on every item (her information, honored); nothing given → blank (fine).
    The scope decision lives in the LLM contract, upstream; this helper just stores what
    arrives per item, verbatim.
  - Guard #3: Affective is free text, never a scalar. A bare number is NOT a valid affect
    note and is dropped, never stored as "3".
  - Access conditions is a fixed multi-select; only the live option names are ever written
    (an unknown tag is dropped, never created). ALLOWED_ACCESS + build_optional_props are
    the single extension point when the "what should a plan-making agent know about a day"
    field set grows (June's open design thread) — both write paths inherit any change here.
"""

# MUST stay in sync with scripts/build_task.py:22-24 (the live multi-select options).
ALLOWED_ACCESS = (
    "Can-be-done-lying-down",
    "Involves-leaving-house",
    "Requires-talking-to-a-person",
)


def _duration_prop(raw):
    if raw is None or isinstance(raw, bool):
        return None
    try:
        val = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def _text_prop(raw):
    # Guard #3 lives here too: a non-string (e.g. a bare number) is not a valid free-text note.
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    return raw or None


def _access_prop(raw):
    if not isinstance(raw, (list, tuple)):
        return None
    kept = [v for v in raw if v in ALLOWED_ACCESS]
    return kept or None


def build_optional_props(*, duration_min=None, affect=None, blocked_on=None,
                         access_conditions=None):
    """Return {display_name: value} for ONLY the optional fields that validate."""
    props = {}
    dur = _duration_prop(duration_min)
    if dur is not None:
        props["Duration min"] = dur
    aff = _text_prop(affect)
    if aff is not None:
        props["Affective"] = aff
    blk = _text_prop(blocked_on)
    if blk is not None:
        props["Blocked on"] = blk
    acc = _access_prop(access_conditions)
    if acc is not None:
        props["Access conditions"] = acc
    return props

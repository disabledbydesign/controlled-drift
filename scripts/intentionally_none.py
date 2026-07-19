"""The marker that makes spec §4's tri-state representable for fields whose storage cannot hold
an explicit empty.

── the problem this exists for ──────────────────────────────────────────────
Spec §4 needs THREE states per inheritable field:

    unset   -> defer to the parent (inherit)
    custom  -> this object's own value
    custom  -> ... INCLUDING an explicit empty, meaning "intentionally none"

The resolver stops at the first ancestor where the key is PRESENT, not the first where it is
truthy — so an explicit empty must be distinguishable from an absent key. Whether it actually is
depends on the property's storage FORMAT, verified live 2026-07-18 against June's real space:

    field      format         explicit-empty survives a round-trip?
    access     multi_select   NO  — writing [] DELETES the property outright
    affective  text           YES — '' reads back as present
    blockMin   number         NO  — there is no empty; 0 is a real value

So for `access` and `blockMin`, "I checked this field and none of it applies" and "I never
touched this field" are the same bytes, and the override silently reverts to inheriting on
reload. June, 2026-07-19, asked for it to work: overriding to empty is a real need — a task
under dev work whose inherited conditions genuinely do not apply.

── why a separate property, and NOT an option in the field itself ───────────
The obvious fix is a "none of these" tag inside `Access conditions`. It was rejected on
evidence: the daily plan READS those tags and prints them —

    daily_plan.py:562   extras.append(f"access: {', '.join(t['access'])}")

— so a marker living in that list would surface in her plan as a fake access condition, and
would also reach `plan_generate.py`'s tag filtering, where it would act as a phantom constraint
on task selection. Teaching five separate consumers to ignore a magic tag is the shape of a
design going wrong. Here the marker is invisible to everything that reads access tags; only the
`vals` serializer consults it.

June also settled the UI question that killed the tag approach ("if none are selected in the UI,
is 'none of these' automatically selected?"): YES, automatic — and therefore never a box she
ticks. Unticking everything IS the statement. She never sees or manages this marker.

── the shape ────────────────────────────────────────────────────────────────
ONE multi_select property, `Intentionally none`, whose options are the DISPLAY NAMES of the
inheritable fields. A task carrying `Intentionally none: Access conditions` reads correctly in
Anytype on its own terms, which is the point — this is data she can look at, not hidden magic.

Its own empty state is meaningful and needs no marker of its own: nothing overridden to empty
means the property is simply absent. So the mechanism does not recurse.
"""

# The inheritable fields, by valKey -> the display name used as this property's option.
# Mirrors `INHERIT` in `app/src/model/fields.ts` and spec §4's list.
MARKABLE = {
    "access": "Access conditions",
    "blockMin": "Block chunk min",
    "affective": "Affective",
}

PROPERTY = "Intentionally none"

#: Option list for `ensure_property`. Order is the spec's, not alphabetical.
OPTIONS = ["Access conditions", "Block chunk min", "Affective"]


def marked_keys(marker_values):
    """The valKeys a stored `Intentionally none` list marks as set-here-and-empty.

    `marker_values` is whatever the property read back as — a list of option names, or None when
    the property is absent. Unknown option names are IGNORED rather than raising: a stray value
    should not take down a tree read.
    """
    if not marker_values:
        return set()
    names = marker_values if isinstance(marker_values, list) else [marker_values]
    by_label = {label: key for key, label in MARKABLE.items()}
    return {by_label[n] for n in names if n in by_label}


def with_key(marker_values, val_key, marked):
    """The new `Intentionally none` list with `val_key` added (marked=True) or removed.

    Returns a list of option NAMES, ready to write. Order follows `OPTIONS` so a rewrite of the
    same set does not churn the stored value and produce a pointless correction-log entry.
    """
    keys = marked_keys(marker_values)
    if marked:
        keys.add(val_key)
    else:
        keys.discard(val_key)
    labels = {MARKABLE[k] for k in keys if k in MARKABLE}
    return [o for o in OPTIONS if o in labels]


def is_empty_value(value):
    """Whether a value being written means "none" for a markable field.

    `''`, `[]`, `None` all mean none. `0` deliberately does NOT — for `blockMin` a zero-minute
    block is a real (if odd) value, and treating it as "none" would silently discard it.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    return False

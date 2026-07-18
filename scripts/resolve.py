#!/usr/bin/env python3
"""One inheritance walk for every field that inherits down the Parent-project chain.

WHY THIS EXISTS (backend spec §4). June's framing is the requirement: a workstream usually has
a SHARED profile all its tasks follow, and a project may have a PREDICTABLE access condition —
but an individual task or subproject sometimes DIVERGES. So the model is inherit-the-shared-
default, override-when-it-differs. Before this module there were three separate hand-rolled
walks of the same parent chain (Side and is_workstream in `daily_plan.py`, `_is_workstream` in
`orient_map.py`), and the block-grain fields §4 adds (access conditions, block duration,
affective) would have been a fourth, fifth and sixth. This is the one walk they all use.

The TypeScript side has the same resolver at `app/src/model/fields.ts` (`effective`), ported
from mockup v4. That file is the reference implementation for the tri-state below.


THE TRI-STATE, AND HOW "ABSENT" IS SPELLED IN PYTHON
----------------------------------------------------
Spec §4 needs three states per inheritable field, not two:

    unset   = defer to the parent (inherit)
    custom  = this node's own value ...
    custom  = ... INCLUDING an explicit empty, meaning "intentionally none"

So the walk stops at the first node whose value is PRESENT, which is not the same as the first
node whose value is TRUTHY. An ancestor holding an explicit empty stops the walk and answers
"none, deliberately" — a different answer from "nothing up this chain had a value at all", and
the caller can tell them apart because `Resolved.source` is the ancestor in the first case and
None in the second.

The TS version spells presence as `hasOwnProperty(vals, vk) && vals[vk] !== undefined`, so a key
explicitly set to `undefined` is skipped and the walk continues past it, while a key set to `''`
stops it. Python cannot use key-presence the same way: the loaders in `daily_plan.py` build flat
dicts that always assign every key (`{"side": side}` with `side = None` when the tag is unset),
so `"side" in node` is True for every node and would make the tri-state unreachable. The faithful
analog is to treat `None` as Python's `undefined` — the value Anytype's readers produce for an
unset property — and everything else, `""` and `[]` included, as present:

    value is None   -> absent, keep walking      (TS: key missing / undefined)
    value == ""     -> present, STOP, "none"     (TS: key present but empty)

`is_absent` is a parameter rather than hardcoded because one existing caller genuinely needs a
different rule; see `Hierarchy.effective`.
"""

from collections import namedtuple

# `value` is the resolved value. `source` is the node it came from — the node itself when it had
# its own value, an ancestor when inherited, and None when nothing in the chain had one. Callers
# that only want the value can ignore `source`; callers rendering "inherited from X" need it, and
# it is the only way to tell an ancestor's deliberate empty from nothing-to-inherit.
Resolved = namedtuple("Resolved", ["value", "source", "inherited"])

#: Default presence rule — see the module docstring. `None` means defer to the parent.
def absent_if_none(value):
    return value is None


#: Presence rule for checkbox-style fields, where the storage layer cannot represent "unset":
#: Anytype hands back False for an unticked box, so False has to mean "defer to the parent"
#: rather than "deliberately not a workstream". Under this rule the walk reproduces exactly the
#: OR-up-the-chain behaviour `is_workstream` had before it moved here. A checkbox therefore has
#: no tri-state — it cannot express "intentionally none" — and that is a property of the
#: storage, not a shortcut taken here.
def absent_if_falsey(value):
    return not value


class Hierarchy:
    """A parent-chain index over a set of nodes, plus the `effective` walk over it.

    The three accessors are injectable because the two call sites hold their nodes in different
    shapes: `daily_plan.py` has flat dicts (`{"id":…, "parent_project_id":…, "side":…}`), while
    `orient_map.py` walks raw Anytype objects whose parent lives inside a properties list. Both
    get the same walk without either having to convert its data first.
    """

    def __init__(self, nodes, id_of=None, parent_id_of=None, get=None):
        self._id_of = id_of or (lambda n: n["id"])
        self._parent_id_of = parent_id_of or (lambda n: n.get("parent_project_id"))
        self._get = get or (lambda n, field: n.get(field))
        self.by_id = {self._id_of(n): n for n in nodes}

    def parent_of(self, node):
        """The node's parent, or None at the root — or when the parent id points at something
        outside this index (a real case: a parent project filtered out of the active set)."""
        return self.by_id.get(self._parent_id_of(node))

    def effective(self, node, field, is_absent=absent_if_none, include_self=True):
        """Resolve `field` for `node`: its own value, else the nearest ancestor's.

        `include_self=False` answers the different question "what WOULD I inherit if I had no
        value of my own" — starting at the parent, ignoring the node's own value. That is what
        the TypeScript `effective()` does, because its caller (`inheritRow`) renders an
        inheritance hint next to a field the user is editing. Python's callers want the resolved
        value, so the default starts at the node itself.

        Cycle-safe: a parent chain that loops terminates instead of hanging. Cycles are possible
        because Anytype does not stop June from making two projects each other's parent.
        """
        seen = set()
        cur = node if include_self else self.parent_of(node)
        while cur is not None:
            cur_id = self._id_of(cur)
            if cur_id in seen:
                break                       # cycle — stop rather than spin
            seen.add(cur_id)
            value = self._get(cur, field)
            if not is_absent(value):
                return Resolved(value, cur, cur is not node)
            cur = self.parent_of(cur)
        return Resolved(None, None, False)

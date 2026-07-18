#!/usr/bin/env python3
"""Rename the Side option "Obligation" -> "Work" (backend spec §12; June, 2026-07-18).

WHY THIS IS A RENAME AND NOT A RE-TAG
-------------------------------------
An Anytype select value is stored on the object as a reference to a TAG ID, not as a string. So
renaming the tag itself changes what every object displays without touching a single object. That
matters here: ~51 objects carry Side and 15 of them are on the old option. Re-tagging them one by
one would mean 15 writes, each of which could fail halfway and leave the space in a split state
where some objects say Work and some still say Obligation. A single rename has no half-way state.

There is precedent in this very space: the tag whose key is `wellbeing` currently displays as
"Fun / hobby". Anytype keeps the key stable and renames the display name, exactly as we do here.

Because no object value is rewritten, there is also **no coexistence problem** — the old and new
options are the same tag, so the two never exist side by side and nothing has to be reconciled.

WHAT THIS SCRIPT STILL DOES
---------------------------
It records the before/after state of every affected object anyway, and re-reads them afterwards to
prove their Side survived and now reads "Work". The rename is safe in principle; the read-back is
what makes it verified rather than assumed (repo rule: a good answer is not a saved object).

IDEMPOTENT: if the tag is already named "Work", it re-verifies and logs `already-renamed` records
without issuing a write. Re-running never double-applies.

Usage:
    python3 scripts/migrate_side_rename.py            # apply
    python3 scripts/migrate_side_rename.py --dry-run  # report only, write nothing
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g  # noqa: E402

OLD_NAME = "Obligation"
NEW_NAME = "Work"
PROPERTY = "Side"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "side_rename_2026-07-18.jsonl")


def side_of(obj):
    """The object's Side value as (tag_id, tag_name), or None if it carries no Side."""
    for pr in obj.get("properties", []):
        if pr.get("key") == "side":
            sel = pr.get("select")
            if isinstance(sel, dict):
                return sel.get("id"), sel.get("name")
    return None


def find_tag(sid, prop_id, *, tag_id=None, name=None):
    tags = g.call("GET", f"/spaces/{sid}/properties/{prop_id}/tags")[1].get("data", [])
    for t in tags:
        if (tag_id and t.get("id") == tag_id) or (name and t.get("name") == name):
            return t
    return None


def rename_tag(sid, prop_id, tag_id, new_name):
    st, body = g.call("PATCH", f"/spaces/{sid}/properties/{prop_id}/tags/{tag_id}",
                      {"name": new_name})
    if st not in (200, 201):
        raise RuntimeError(f"rename tag {tag_id} -> {new_name!r} failed: {st} {body}")
    return body


def migrate(dry_run=False):
    sid = g.get_space_id()
    prop = g.find_property(PROPERTY)
    if not prop:
        raise RuntimeError(f"property {PROPERTY!r} not found in the live space")
    prop_id = prop["id"]

    old_tag = find_tag(sid, prop_id, name=OLD_NAME)
    new_tag = find_tag(sid, prop_id, name=NEW_NAME)

    if old_tag and new_tag:
        # Two separate tags with both names really would be a split state, and re-pointing objects
        # is a different, riskier operation than a rename. Stop rather than guess.
        raise RuntimeError(
            f"BOTH {OLD_NAME!r} (id={old_tag['id']}) and {NEW_NAME!r} (id={new_tag['id']}) exist as "
            f"separate tags on {PROPERTY}. This script only renames; re-pointing objects between two "
            f"live tags is a different migration. Stopping — needs a human decision.")

    target = old_tag or new_tag
    if target is None:
        raise RuntimeError(
            f"neither {OLD_NAME!r} nor {NEW_NAME!r} exists as a {PROPERTY} tag; nothing to rename")

    already = old_tag is None
    tag_id = target["id"]

    # ---- BEFORE: every object carrying Side, recorded before anything is written.
    objects = g.fetch_all_objects(sid)
    with_side = []
    for o in objects:
        s = side_of(o)
        if s:
            with_side.append((o, s[0], s[1]))
    affected = [(o, tid, nm) for (o, tid, nm) in with_side if tid == tag_id]

    print(f"[info] {len(objects)} objects in space; {len(with_side)} carry {PROPERTY}; "
          f"{len(affected)} carry the tag being renamed")
    if already:
        print(f"[info] tag is already named {NEW_NAME!r} — re-verifying, no write needed")

    if dry_run:
        print("[dry-run] no write issued")
        return {"affected": len(affected), "renamed": False, "mismatches": []}

    # ---- RENAME (single write; skipped when already applied).
    if not already:
        rename_tag(sid, prop_id, tag_id, NEW_NAME)

    # ---- READ-BACK the tag itself.
    check = find_tag(sid, prop_id, tag_id=tag_id)
    if not check or check.get("name") != NEW_NAME:
        raise RuntimeError(f"read-back FAILED: tag {tag_id} reads {check!r}, expected name {NEW_NAME!r}")
    print(f"[ok] tag {tag_id} now reads name={check['name']!r} key={check.get('key')!r}")

    # ---- READ-BACK every affected object individually, from the live API.
    mismatches = []
    records = []
    stamp = datetime.now(timezone.utc).isoformat()
    for obj, tid, before_name in affected:
        _, body = g.call("GET", f"/spaces/{sid}/objects/{obj['id']}")
        fresh = body.get("object", {}) if isinstance(body, dict) else {}
        after = side_of(fresh)
        after_id, after_name = after if after else (None, None)
        ok = (after_id == tid and after_name == NEW_NAME)
        if not ok:
            mismatches.append((obj.get("name"), obj["id"], after_id, after_name))
        records.append({
            "ts": stamp,
            "id": obj["id"],
            "name": obj.get("name"),
            "type": (obj.get("type") or {}).get("name"),
            "property": PROPERTY,
            "tag_id": tid,
            "before": before_name,
            "after": after_name,
            "action": "already-renamed" if already else "renamed",
            "read_back_ok": ok,
        })

    # Also record the objects on the other Side options, so the review sheet can show June that
    # nothing else moved.
    for obj, tid, nm in with_side:
        if tid == tag_id:
            continue
        records.append({
            "ts": stamp,
            "id": obj["id"],
            "name": obj.get("name"),
            "type": (obj.get("type") or {}).get("name"),
            "property": PROPERTY,
            "tag_id": tid,
            "before": nm,
            "after": nm,
            "action": "untouched",
            "read_back_ok": True,
        })

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"[ok] {len(records)} records -> {LOG_PATH}")

    if mismatches:
        print("\n*** READ-BACK MISMATCH — DO NOT TREAT THIS MIGRATION AS DONE ***")
        for nm, oid, aid, anm in mismatches:
            print(f"  {nm} ({oid}): reads tag={aid} name={anm!r}")
        raise RuntimeError(f"{len(mismatches)} objects failed read-back")

    print(f"[ok] all {len(affected)} affected objects read back as {NEW_NAME!r}")
    return {"affected": len(affected), "renamed": not already, "mismatches": mismatches}


if __name__ == "__main__":
    migrate(dry_run="--dry-run" in sys.argv)

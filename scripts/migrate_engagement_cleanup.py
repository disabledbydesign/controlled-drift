#!/usr/bin/env python3
"""Retire the Sprint/Hyperfixation Engagement values (2026-07-16).

Reconciliation (docs/spec_reconciliation_selection_2026-07-11.md): the Project `Engagement`
select is now Steady/Open/Needs Clarifying/Backburner/Done only. Sprint is retired in favor
of a Focus Period foreground action; Hyperfixation is retired in favor of the qualitative
Engagement notes / Affective free-text. `scripts/build_project.py` no longer offers either as
a select option going forward; this script cleans up any project still carrying one of the
old values on the LIVE space, then deletes the two now-dead tags from the Engagement property.

Read select fields by DISPLAY NAME, not key (Engagement's key is Anytype-auto-generated and
unpredictable — same convention as daily_plan.py:97-98).

Anytype schema-tag DELETE is ASYNCHRONOUS (probe-confirmed 2026-07-16): the DELETE call
returns 200 ~0.5-1s BEFORE the tag actually disappears from the property's tag list. Trusting
the 200 alone is a silent failure; checking once right after is a FALSE failure (the tag is
still there, but only because propagation hasn't caught up yet). delete_retired_tags polls a
fresh GET of the tag list after each DELETE, bounded, and raises if the tag never disappears.
Note: this deliberately does NOT reuse gsdo_anytype.find_property to verify a deletion —
find_property is documented (2026-07-16 probe) to serve a cached view of the schema, so any
deletion check here goes through a fresh GET /spaces/{sid}/properties(/tags) call instead.

Usage:
  python3 scripts/migrate_engagement_cleanup.py            # dry run: prints the proposed
                                                            # mapping, changes nothing
  python3 scripts/migrate_engagement_cleanup.py --apply    # migrates every live retired-value
                                                            # project to Steady, confirms zero
                                                            # remain, THEN deletes the two tags
"""
import sys, os, time

sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import gsdo_objects


# The reconciled set drops these two; Steady is the closest surviving value for a project
# that was being actively pursued under either retired label (spec_reconciliation_selection_
# 2026-07-11.md — Sprint/Hyperfixation are retired, not replaced by a new closer tag).
RETIRED_VALUES = {"Sprint", "Hyperfixation"}
REPLACEMENT_VALUE = "Steady"

ENGAGEMENT_PROPERTY_NAME = "Engagement"


# --- data shaping -------------------------------------------------------------

def _live_projects(data):
    """Pure. Extract {"id","name","engagement"} for every gsdo_project object in raw Anytype
    data (as returned by gsdo_anytype.fetch_all_objects). Engagement is read BY DISPLAY NAME
    ("Engagement"), not by key — the key is Anytype-auto-generated and unpredictable, the same
    convention daily_plan.py uses at load time."""
    out = []
    for o in data:
        t = o.get("type")
        tkey = t.get("key") if isinstance(t, dict) else t
        if tkey != "gsdo_project":
            continue
        by_name = {p.get("name"): p for p in o.get("properties", [])}
        eng = (by_name.get(ENGAGEMENT_PROPERTY_NAME) or {}).get("select") or {}
        eng = eng.get("name") if isinstance(eng, dict) else None
        out.append({"id": o.get("id"), "name": o.get("name"), "engagement": eng})
    return out


def _read_engagement(sid, oid):
    """Live, uncached read of one object's Engagement value, by display name. Raises on a failed
    GET — a blipped read must NOT silently return None, which apply_migration would misread as
    'already off the retired values' and skip a real migration (no-silent-failures guard; mirrors
    capture_generate._get_object / backfill_engagement._get_project)."""
    st, body = g.call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(body, dict) or "object" not in body:
        raise RuntimeError(f"_read_engagement: GET object {oid!r} failed: {st} {body}")
    obj = body["object"]
    by_name = {p.get("name"): p for p in obj.get("properties", [])}
    eng = (by_name.get(ENGAGEMENT_PROPERTY_NAME) or {}).get("select") or {}
    return eng.get("name") if isinstance(eng, dict) else None


# --- Step 1: propose ------------------------------------------------------------

def propose_migration(projects):
    """Pure. For each project dict {"id","name","engagement",...} whose `engagement` is a
    retired value (Sprint or Hyperfixation), propose migrating it to Steady — the closest
    surviving value (a Sprint/Hyperfixation project was, by definition, being actively
    pursued; Steady is the surviving "actively pursuing this" state). A project already off
    the retired values is excluded from the output entirely — nothing to propose.

    Returns a list of {"id","name","current","proposed"} in input order. June may override
    any per-project proposal (edit the dict's "proposed" value) before calling
    apply_migration — this function never applies anything itself."""
    out = []
    for p in projects:
        eng = p.get("engagement")
        if eng in RETIRED_VALUES:
            out.append({"id": p["id"], "name": p["name"], "current": eng,
                        "proposed": REPLACEMENT_VALUE})
    return out


# --- Step 2: apply ---------------------------------------------------------------

def apply_migration(proposals):
    """Idempotent. For each proposal {"id","name","current","proposed",...}: re-read the
    project's LIVE Engagement value (not the value captured when the proposal was built —
    another actor may have already fixed it since), skip if it's already off the retired
    values (re-run safe), otherwise write `proposed` via gsdo_objects.update and read the
    object back BY NAME to confirm the write landed. Raises RuntimeError on any mismatch
    between what was written and what reads back — never silently continues past a failed
    write.

    Returns a list of {"id","name","status","engagement"} — status is "migrated" or
    "skipped" (already off the retired values)."""
    sid = g.get_space_id()
    results = []
    for p in proposals:
        oid, name, proposed = p["id"], p["name"], p["proposed"]
        live_val = _read_engagement(sid, oid)
        if live_val not in RETIRED_VALUES:
            results.append({"id": oid, "name": name, "status": "skipped",
                            "engagement": live_val})
            continue
        gsdo_objects.update(oid, properties={ENGAGEMENT_PROPERTY_NAME: proposed})
        new_val = _read_engagement(sid, oid)
        if new_val != proposed:
            raise RuntimeError(
                f"apply_migration: {name!r} ({oid}) read back as Engagement={new_val!r} "
                f"after updating to {proposed!r} — write did not take")
        results.append({"id": oid, "name": name, "status": "migrated", "engagement": new_val})
    return results


# --- Step 3: delete the retired tags ---------------------------------------------

def delete_retired_tags(poll_attempts=10, poll_interval=0.5):
    """Delete the Sprint and Hyperfixation tags from the Engagement select property.

    MUST only be called after apply_migration has proven zero live projects still carry a
    retired value — deleting a tag still referenced by an object would strand it. That
    ordering is enforced by the __main__ flow below, not by this function (this function has
    no way to see "all projects"; it only deletes tags).

    Anytype tag deletion is ASYNCHRONOUS (probe-confirmed 2026-07-16): DELETE returns 200
    up to ~1s before the tag actually disappears from GET .../tags. This polls a FRESH
    GET .../tags after each DELETE (bounded — poll_attempts x poll_interval, default 5s
    total) until the tag name is actually gone, and raises if it never disappears in that
    window. Never trusts the 200 alone (silent failure) and never checks only once (false
    failure — the tag can still legitimately be there for another ~0.5s).

    No-op (returns "already-absent") for a tag that's already gone — safe to re-run.

    Returns {"Sprint": status, "Hyperfixation": status} where status is one of
    "deleted" / "already-absent"."""
    sid = g.get_space_id()
    prop = g.find_property(ENGAGEMENT_PROPERTY_NAME)
    if prop is None:
        raise RuntimeError(f"delete_retired_tags: {ENGAGEMENT_PROPERTY_NAME!r} property not found")
    pid = prop["id"]

    results = {}
    for tag_name in RETIRED_VALUES:
        # Fresh GET, not find_property — find_property is a cached schema view (2026-07-16
        # probe); a deletion check must never trust anything but a live list.
        tags = g.call("GET", f"/spaces/{sid}/properties/{pid}/tags")[1].get("data", [])
        tag = next((t for t in tags if t.get("name") == tag_name), None)
        if tag is None:
            results[tag_name] = "already-absent"
            continue
        st, body = g.call("DELETE", f"/spaces/{sid}/properties/{pid}/tags/{tag['id']}")
        if st not in (200, 201, 204):
            raise RuntimeError(f"delete_retired_tags: DELETE {tag_name!r} failed: {st} {body}")
        gone = False
        for _ in range(poll_attempts):
            time.sleep(poll_interval)
            fresh = g.call("GET", f"/spaces/{sid}/properties/{pid}/tags")[1].get("data", [])
            if not any(t.get("name") == tag_name for t in fresh):
                gone = True
                break
        if not gone:
            raise RuntimeError(
                f"delete_retired_tags: {tag_name!r} tag still present after "
                f"{poll_attempts * poll_interval:.1f}s of polling — DELETE returned {st} but "
                "the change never propagated")
        results[tag_name] = "deleted"
    return results


# --- CLI --------------------------------------------------------------------------

def _print_table(proposals):
    print(f"{len(proposals)} live project(s) carry a retired Engagement value:\n")
    width = max((len(p["name"]) for p in proposals), default=4)
    for p in proposals:
        print(f"  {p['name']:<{width}}   {p['current']:<14} -> {p['proposed']}")
    print()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Migrate live Sprint/Hyperfixation projects to Steady, then delete the "
                    "two retired tags from the Engagement property. Bare run = dry-run "
                    "(prints the proposed mapping, changes nothing). Pass --apply to migrate "
                    "+ delete for real.")
    ap.add_argument("--apply", action="store_true",
                    help="Actually migrate + delete tags. Without this flag: dry-run only.")
    args = ap.parse_args()

    sid = g.get_space_id()
    data = g.fetch_all_objects(sid)
    projects = _live_projects(data)
    proposals = propose_migration(projects)

    if not proposals:
        print("No live projects carry a retired Engagement value (Sprint/Hyperfixation). "
              "Nothing to migrate.")
    else:
        _print_table(proposals)

    if not args.apply:
        print("(dry-run — no changes made. Re-run with --apply to migrate + delete the "
              "retired tags.)")
        sys.exit(0)

    if proposals:
        results = apply_migration(proposals)
        for r in results:
            print(f"  [{r['status']}] {r['name']} -> Engagement={r.get('engagement')}")

        # Guard order (required): re-fetch to confirm zero live projects still carry a
        # retired value BEFORE touching schema — deleting a tag still referenced by an
        # object would strand it.
        fresh_data = g.fetch_all_objects(sid)
        remaining = propose_migration(_live_projects(fresh_data))
        if remaining:
            names = ", ".join(p["name"] for p in remaining)
            raise RuntimeError(
                f"migrate_engagement_cleanup: {len(remaining)} project(s) still carry a "
                f"retired Engagement value after apply_migration ({names}) — refusing to "
                "delete the tags while they may still be referenced.")

    print("\nAll live projects clear of retired Engagement values. Deleting the "
          "Sprint/Hyperfixation tags...")
    tag_results = delete_retired_tags()
    for name, status in tag_results.items():
        print(f"  [{status}] {name}")
    print("\nDone.")

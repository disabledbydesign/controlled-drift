#!/usr/bin/env python3
"""Backfill Engagement onto existing Projects with no value, so 'active' (plan_input_seam_
design.md decision 1 + REFINEMENT) is unambiguous going into daily_plan.load_active_items's
active-only filter.

Engagement is UNIVERSAL now — the old "Daily-life stays unset on purpose" exemption is retired, so
this covers the ~4 Daily-life projects too, each getting a real value June confirms. It also
applies June-ratified REQUIRED END-STATES (data changes set regardless of current value, held until
this seam is built): `Networking and relationships` -> Side=Daily life + Engagement=Open, so
"Email Donna Haraway" becomes a discrete daily-life task that surfaces if-room, not daily.

Reviewable, like duration_backfill.py: a bare run proposes + prints the mapping (no writes);
--run writes only after June confirms. Idempotent: a fill-the-blank proposal skips a project that
already gained a value; a required-end-state proposal applies regardless.
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import gsdo_objects
from anytype_test import call


_REQUIRED_END_STATES = {
    "Networking and relationships": {"side": "Daily life", "engagement": "Open"},
}
_DAILY_LIFE_HINT = {"household": "Steady", "chore": "Steady", "medical": "Steady",
                    "self-care": "Steady", "self care": "Steady"}


def _pv_by_name(obj, name, field):
    for p in obj.get("properties", []):
        if p.get("name") == name:
            return p.get(field)
    return None


def load_projects(sid=None):
    sid = sid or g.get_space_id()
    out = []
    for o in g.fetch_all_objects(sid):
        if o.get("type", {}).get("key") != "gsdo_project":
            continue
        out.append({"id": o["id"], "name": o.get("name"),
                    "engagement": (_pv_by_name(o, "Engagement", "select") or {}).get("name"),
                    "side": (_pv_by_name(o, "Side", "select") or {}).get("name"),
                    "project_status": (_pv_by_name(o, "Project status", "select") or {}).get("name")})
    return out


def _daily_life_hint(name):
    low = (name or "").lower()
    for kw, val in _DAILY_LIFE_HINT.items():
        if kw in low:
            return val
    return "Open"    # social / relationships / unknown daily-life -> available if-room, not daily


def propose_backfill(projects):
    out = []
    for p in projects:
        name = p["name"]
        req = _REQUIRED_END_STATES.get(name)
        if req:
            out.append({"id": p["id"], "name": name, "current": p.get("engagement"),
                        "proposed": req["engagement"], "side": req["side"]})
            continue
        if p.get("engagement"):
            continue
        if p.get("side") == "Daily life":
            proposed = _daily_life_hint(name)
        else:
            proposed = "Backburner" if p.get("project_status") == "Inactive" else "Open"
        out.append({"id": p["id"], "name": name, "current": p.get("engagement"), "proposed": proposed})
    return out


def _get_project(oid):
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"read-back failed for {oid!r}: {st} {b}")
    return b["object"]


def apply_backfill(proposals):
    result = {"updated": 0, "skipped": 0, "failed": []}
    for item in proposals:
        try:
            forced = "side" in item
            current = (_pv_by_name(_get_project(item["id"]), "Engagement", "select") or {}).get("name")
            if current and not forced:
                result["skipped"] += 1
                continue
            props = {"Engagement": item["proposed"]}
            if item.get("side"):
                props["Side"] = item["side"]
            gsdo_objects.update(item["id"], properties=props)
            back = _get_project(item["id"])
            got_eng = (_pv_by_name(back, "Engagement", "select") or {}).get("name")
            if got_eng != item["proposed"]:
                raise RuntimeError(f"Engagement read-back mismatch for {item['id']!r}: "
                                   f"wrote {item['proposed']}, read-back={got_eng!r}")
            if item.get("side"):
                got_side = (_pv_by_name(back, "Side", "select") or {}).get("name")
                if got_side != item["side"]:
                    raise RuntimeError(f"Side read-back mismatch for {item['id']!r}: "
                                       f"wrote {item['side']}, read-back={got_side!r}")
            result["updated"] += 1
        except Exception as e:
            result["failed"].append({"id": item["id"], "name": item["name"], "error": str(e)})
    return result


def format_proposal(proposals):
    if not proposals:
        return "No projects need an engagement backfill — nothing to do."
    lines = [f"{len(proposals)} project(s) to set:"]
    for p in proposals:
        side_bit = f"  (Side -> {p['side']})" if p.get("side") else ""
        lines.append(f"  - {p['name']}  ->  Engagement {p['proposed']}{side_bit}")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Backfill blank Project Engagement (June-confirmed)")
    ap.add_argument("--run", action="store_true", help="write the proposed values (with read-back)")
    args = ap.parse_args()
    proposals = propose_backfill(load_projects())
    print(format_proposal(proposals))
    if args.run:
        print("\n--- applying ---")
        print(json.dumps(apply_backfill(proposals), indent=2))
    else:
        print("\nRun --run to write these values after June confirms the mapping above.")

#!/usr/bin/env python3
"""SUPERSEDED FIRST CUT — do not treat this as the design.
See docs/map_and_arc.md ("What the map is", settled 2026-06-20).

June tested this live and it was the wrong approach, for two reasons:
  1. It ENCODES instead of DESCRIBES — it shows filled/empty symbols and
     one-word codes (now / held / done) that June then has to decode. The map
     must instead say, in plain words, what each work stream is and where it
     stands. She reads it; she never decodes it.
  2. It LOCKS the map to a fixed, closed list of states (the five-value
     Engagement field). That is a brittle bet that will fight the system once
     it is actually running. The map must read from open, flexible structure —
     a stored, plain-language description per stream.
Rebuild this to read and show stored plain-language descriptions, on open
structure. The notes below describe the superseded approach, kept for the
record of what was tried and why it was wrong.

---

Deterministic Orient map renderer.

The map is NOT composed by the LLM. It is a deterministic read of Anytype
fields, so it renders the same way every time and no session can re-improvise
it (or re-spotlight something you're avoiding):

  ● now / ○ held / ✓ done  <-  Engagement field
                               (Backburner -> ○ held;  Done -> ✓;  else -> ● now)
  work-stream name         <-  object name
  goal frame               <-  Goal name + Horizon + Reaching for

NOTE — one field, two jobs (documented coupling). The Engagement field
(Steady / Sprint / Hyperfixation / Backburner / Done) is the SINGLE source
that drives the now/held/done circle. The map shows the plain words
(now / held / done), never the word "Engagement" — so there is no metaphor to
decode. Engagement's five values map APPROXIMATELY, not exactly, onto three
circles; that approximation is the only fuzziness. If the circle and the
engagement signal ever need to say different things, the clean split is to
give the circle its own now/held/done field and leave Engagement alone. Until
then, this is the documented mapping.

The map view is names + circles only — calm and scannable. The detail for a
work stream (what it's doing, where you are in it) lives in that stream's own
fields and is shown only when you open it (`detail` below), never crammed into
the map.

Change what's "active" by changing a stream's Engagement field. The field
decides — not the model.

  python3 scripts/orient_map.py "Build Controlled Drift"
  python3 scripts/orient_map.py "Build Controlled Drift" --detail "Seeing your time, and seeing what you actually did"
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g


def _props(o):
    return {p.get("key"): p for p in o.get("properties", [])}

def _sel(props, key):
    v = props.get(key) or {}
    s = v.get("select") if isinstance(v, dict) else None
    return s.get("name") if isinstance(s, dict) and s else None

def _txt(props, key):
    v = props.get(key) or {}
    return v.get("text") if isinstance(v, dict) else None

def _objs(props, key):
    v = props.get(key) or {}
    return (v.get("objects") or []) if isinstance(v, dict) else []

def _tkey(o):
    t = o.get("type")
    return t.get("key") if isinstance(t, dict) else t

# Engagement -> circle glyph. Anything not held/done reads as "now" (you're in it).
_HELD = {"Backburner": "○", "Done": "✓"}
def circle_for(engagement):
    return _HELD.get(engagement, "●")

# active first, then held, then done — a stable, field-driven order
def _rank(engagement):
    if engagement == "Done":
        return 2
    if engagement == "Backburner":
        return 1
    return 0


def _load():
    sid = g.get_space_id()
    objs = g.fetch_all_objects(sid)
    goals = [o for o in objs if _tkey(o) == "gsdo_goal"]
    projects = [o for o in objs if _tkey(o) == "gsdo_project"]
    return goals, projects


def render_map(project_name):
    goals, projects = _load()
    proj = next((o for o in projects if o.get("name") == project_name), None)
    if proj is None:
        return f"(no project named {project_name!r} found)"
    pid = proj["id"]
    pprops = _props(proj)
    goal_ids = _objs(pprops, "gsdo_goal_link")
    goal = next((o for o in goals if o["id"] in goal_ids), None)

    streams = [o for o in projects
               if pid in _objs(_props(o), "gsdo_parent_project")]
    streams.sort(key=lambda o: _rank(_sel(_props(o), "engagement")))

    lines = []
    if goal:
        gp = _props(goal)
        hz = _sel(gp, "gsdo_horizon")
        rf = _txt(gp, "gsdo_reaching_for_(text)")
        lines.append(f"GOAL:  {goal['name']}" + (f"  ({hz.lower()})" if hz else ""))
        if rf:
            lines.append(f"       {rf}")
        lines.append("")

    lines.append(f"WORK STREAMS — the work of {proj['name']}:")
    lines.append("(● now · ○ held · ✓ done)")
    lines.append("")
    if not streams:
        lines.append("  (none yet)")
    for s in streams:
        eng = _sel(_props(s), "engagement")
        lines.append(f"  {circle_for(eng)} {s['name']}")

    other = max(0, len(goals) - (1 if goal else 0))
    if other:
        lines.append("")
        lines.append(f"{other} other goals — say the word.")
    return "\n".join(lines)


def render_detail(project_name, stream_name):
    """What you see when you OPEN one work stream — its own fields, nothing else."""
    _, projects = _load()
    s = next((o for o in projects if o.get("name") == stream_name), None)
    if s is None:
        return f"(no work stream named {stream_name!r} found)"
    sp = _props(s)
    eng = _sel(sp, "engagement") or "—"
    ctx = _txt(sp, "gsdo_context")
    lines = [f"{circle_for(_sel(sp, 'engagement'))} {s['name']}  [{eng}]"]
    if ctx:
        lines.append("")
        lines.append(ctx)
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Deterministic Orient map")
    ap.add_argument("project", nargs="?", default="Build Controlled Drift")
    ap.add_argument("--detail", default=None, help="open one work stream by name")
    args = ap.parse_args()
    if args.detail:
        print(render_detail(args.project, args.detail))
    else:
        print(render_map(args.project))

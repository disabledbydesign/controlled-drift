#!/usr/bin/env python3
"""Daily plan pipeline — Step 2 of the Controlled Drift system.

Pipeline (§1 of daily_list.md):
  1. Load active items from Anytype (Goals, Projects, Tasks, Strategies, Recurring-for-today)
  2. Run neglect query (items not surfaced in N days)
  3. Ask June for a capacity signal
  4. Feed all context to the daily_list.md prompt → LLM proposes order + frame
  5. Compute clock-time schedule (deterministic Python, never LLM)
  6. Present the negotiable plan in chat
  7. On confirm: update last_surfaced in Anytype, append to surface_log, log corrections

Run: python3 scripts/daily_plan.py
     (or invoke via /drift when June asks "what should I do today")
"""
import sys, os, datetime as dt, json

sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call
import gsdo_anytype as g
from datetime_seam import recurring_items_for_today
from neglect import query_neglected
from scheduler import schedule
from surface_log import log_surfaced_batch
from plan_corrections_log import log_correction


# --- Data loading -----------------------------------------------------------

def _prop_val(props_dict, key, kind):
    p = props_dict.get(key, {})
    return p.get(kind) if p else None


def load_active_items(sid):
    """Load Goals, Projects, Tasks (Active/Needs-Clarifying), Strategies from Anytype."""
    data = call("GET", f"/spaces/{sid}/objects?limit=200")[1].get("data", [])
    goals, projects, tasks, strategies, recurrings = [], [], [], [], []

    for obj in data:
        t = obj.get("type")
        tkey = t.get("key") if isinstance(t, dict) else t
        name = obj.get("name", "")
        oid = obj.get("id")
        props = {p.get("key"): p for p in obj.get("properties", [])}

        def pv(key, kind):
            return _prop_val(props, key, kind)

        if tkey == "gsdo_goal":
            status = (pv("gsdo_status", "select") or {}).get("name")
            if status in (None, "Active"):
                goals.append({"id": oid, "name": name,
                               "reaching_for": pv("gsdo_reaching_for", "text"),
                               "context": pv("gsdo_context", "text")})

        elif tkey == "gsdo_project":
            status = (pv("gsdo_status", "select") or {}).get("name")
            if status in (None, "Active"):
                projects.append({"id": oid, "name": name,
                                  "context": pv("gsdo_context", "text"),
                                  "affective": pv("gsdo_affective", "text"),
                                  "deadline": pv("gsdo_deadline", "date")})

        elif tkey == "task":
            status_tag = pv("status", "select") or {}
            status = status_tag.get("name") if isinstance(status_tag, dict) else status_tag
            if status in (None, "Active", "Needs Clarifying"):
                done = pv("done", "checkbox")
                if done:
                    continue
                access_tags = pv("gsdo_access", "multi_select") or []
                access = [t.get("name") for t in access_tags if isinstance(t, dict)]
                tasks.append({"id": oid, "name": name,
                               "status": status,
                               "duration_min": pv("gsdo_duration_min", "number"),
                               "affective": pv("gsdo_affective", "text"),
                               "access": access,
                               "blocked_on": pv("gsdo_blocked_on", "text"),
                               "context": pv("gsdo_context", "text")})

        elif tkey == "gsdo_strategy":
            status = (pv("gsdo_status", "select") or {}).get("name")
            if status in (None, "Active"):
                strategies.append({"id": oid, "name": name,
                                    "what_for": pv("gsdo_what_for", "text"),
                                    "context": pv("gsdo_context", "text")})

        elif tkey == "gsdo_recurring":
            recurrings.append(obj)

    today_recurrings = recurring_items_for_today(recurrings)
    return goals, projects, tasks, strategies, today_recurrings


def load_neglected(days=3):
    """Items not surfaced in N days (Tasks + Projects)."""
    try:
        return query_neglected(days=days)
    except Exception as e:
        print(f"[warn] neglect query failed: {e}", file=sys.stderr)
        return []


# --- Context formatting for the LLM ----------------------------------------

def format_context(goals, projects, tasks, strategies, today_recurrings, neglected, capacity):
    """Build the context block that gets injected into the daily_list.md prompt."""
    lines = []

    lines.append(f"Current time: {dt.datetime.now().strftime('%A %B %d, %Y — %I:%M %p')}")
    lines.append(f"Capacity signal: {capacity or '(none given)'}")
    lines.append("")

    if strategies:
        lines.append("## Active strategies")
        for s in strategies:
            desc = s.get("what_for") or s.get("context") or ""
            lines.append(f"- {s['name']}" + (f": {desc}" if desc else ""))
        lines.append("")

    if goals:
        lines.append("## Active goals")
        for g_ in goals:
            rf = g_.get("reaching_for") or ""
            lines.append(f"- {g_['name']}" + (f" (reaching for: {rf})" if rf else ""))
        lines.append("")

    if projects:
        lines.append("## Active projects")
        for p in projects:
            ctx = p.get("context") or ""
            aff = p.get("affective") or ""
            line = f"- {p['name']}"
            if ctx:
                line += f" | context: {ctx}"
            if aff:
                line += f" | affective: {aff}"
            lines.append(line)
        lines.append("")

    if tasks:
        lines.append("## Active tasks")
        for t in tasks:
            line = f"- {t['name']}"
            extras = []
            if t.get("status") == "Needs Clarifying":
                extras.append("needs clarifying")
            if t.get("blocked_on"):
                extras.append(f"blocked on: {t['blocked_on']}")
            if t.get("duration_min"):
                extras.append(f"~{t['duration_min']}min")
            if t.get("affective"):
                extras.append(f"affective: {t['affective']}")
            if t.get("access"):
                extras.append(f"access: {', '.join(t['access'])}")
            if extras:
                line += f" ({'; '.join(extras)})"
            lines.append(line)
        lines.append("")

    if today_recurrings:
        lines.append("## Recurring items scheduled today")
        for r in today_recurrings:
            lines.append(f"- {r['name']} at {r['fixed_time'].strftime('%H:%M')}")
        lines.append("")

    # Only show in neglected: items that were previously surfaced but have gone stale.
    # "Never surfaced" items are already in the active lists above — showing them twice
    # is noise (the system is new and everything looks neglected on first run).
    active_names = {t["name"] for t in tasks} | {p["name"] for p in projects}
    neglected_stale = [n for n in neglected
                       if n.get("last_surfaced") is not None
                       and n["name"] not in {r["name"] for r in today_recurrings}
                       and n["name"] not in active_names]
    if neglected_stale:
        lines.append("## Items not surfaced recently (resurfacing)")
        for n in neglected_stale:
            ls = n.get("last_surfaced")
            lines.append(f"- {n['name']} (last seen {ls.date()})")
        lines.append("")

    return "\n".join(lines)


# --- Clock-time schedule ----------------------------------------------------

def build_schedule(llm_ordered_items, today_recurrings, start_time=None):
    """Merge LLM-proposed task order with today's Recurring fixed anchors.
    llm_ordered_items: list of {"name", "duration_min", ...} in proposed order.
    Returns scheduled list with start_time/end_time on each item.
    """
    start_time = start_time or dt.datetime.now().replace(second=0, microsecond=0)
    all_items = list(llm_ordered_items) + [
        {**r, "fixed_time": r["fixed_time"]} for r in today_recurrings
        if r["name"] not in {it["name"] for it in llm_ordered_items}
    ]
    return schedule(all_items, start_time)


# --- Anytype writes ----------------------------------------------------------

def update_last_surfaced(sid, item_ids):
    """Write today's date to last_surfaced on each item."""
    today_iso = dt.date.today().isoformat()
    ls_prop = g.find_property("Last surfaced")
    if ls_prop is None:
        print("[warn] 'Last surfaced' property not found — skipping update", file=sys.stderr)
        return
    for oid in item_ids:
        call("PATCH", f"/spaces/{sid}/objects/{oid}",
             {"properties": [{"key": ls_prop["key"], "date": today_iso}]})


# --- Main -------------------------------------------------------------------

def run():
    sid = g.get_space_id()
    goals, projects, tasks, strategies, today_recurrings = load_active_items(sid)
    neglected = load_neglected()

    print("\n=== Controlled Drift — Daily Plan ===\n")
    try:
        capacity = input("Capacity signal (one word/phrase, or Enter to skip): ").strip()
    except EOFError:
        capacity = ""

    context_block = format_context(
        goals, projects, tasks, strategies, today_recurrings, neglected, capacity)

    # Read the prompt template
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "daily_list.md")
    with open(prompt_path) as f:
        prompt_template = f.read()

    # Inject context into prompt
    prompt = prompt_template.replace(
        "- Capacity signal: [what June said about today, or empty]",
        f"- Capacity signal: {capacity or '(none given)'}"
    ).replace(
        "- Active tasks/projects/goals/strategies: [via MCP]",
        f"- Active tasks/projects/goals/strategies:\n\n{context_block}"
    ).replace(
        "- Current time: [system time, for the downstream scheduler]",
        f"- Current time: {dt.datetime.now().strftime('%A %B %d, %Y — %I:%M %p')}"
    )

    print("\n--- Context loaded. Prompt ready for LLM. ---")
    print(f"Goals: {len(goals)}  Projects: {len(projects)}  Tasks: {len(tasks)}  "
          f"Strategies: {len(strategies)}  Recurring today: {len(today_recurrings)}  "
          f"Neglected: {len(neglected)}")
    print("\nContext block:\n")
    print(context_block)
    print("\n--- Full prompt injected into daily_list.md ---")
    print("(In the /drift skill flow, this prompt + context goes to the LLM.)")
    print("(Run via /drift for the full negotiation loop.)")

    # Build the clock-time schedule: LLM-ordered flexible tasks + Recurring fixed anchors.
    # The LLM proposes ORDER (via daily_list.md); Python places items in TIME deterministically.
    # v1: tasks don't yet have LLM ordering wired (that comes from the /drift negotiation loop),
    # so we pass them in load order. The schedule is still useful for showing Recurring anchors.
    scheduled = build_schedule(
        [{"name": t["name"], "duration_min": t.get("duration_min")} for t in tasks],
        today_recurrings,
    )
    print("\n--- Proposed clock-time schedule ---")
    for item in scheduled:
        start = item.get("start_time")
        end = item.get("end_time")
        if start and end:
            print(f"  {start.strftime('%H:%M')}–{end.strftime('%H:%M')}  {item['name']}")

    try:
        confirm = input("\nConfirm and update last_surfaced? [y/N]: ").strip().lower()
    except EOFError:
        confirm = "n"
    if confirm == "y":
        surfaced_ids = [t["id"] for t in tasks] + [r["id"] for r in today_recurrings]
        update_last_surfaced(sid, surfaced_ids)
        log_surfaced_batch(
            [{"id": t["id"], "name": t["name"], "type": "task"} for t in tasks] +
            [{"id": r["id"], "name": r["name"], "type": "recurring"} for r in today_recurrings]
        )
        # Log each scheduled item as a plan-correction baseline (kind="initial_placement").
        # When June later moves an item, log_correction("move_time", before, after) captures the delta.
        for item in scheduled:
            if item.get("start_time"):
                log_correction("initial_placement", None,
                               {"name": item["name"],
                                "start": item["start_time"].isoformat(),
                                "end": item.get("end_time", "").isoformat() if item.get("end_time") else None})
        print(f"✓ Updated last_surfaced on {len(surfaced_ids)} items. Schedule logged.")


if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""Seed access-condition tags on active tasks (one-time interactive script).

The overlay's low-energy generate mode selects tasks tagged Can-be-done-lying-down.
Without data in that field, the capacity routing works but the LLM has nothing to
prioritize. Run this once to propose tags from task names + context, confirm per task,
and write via gsdo_objects.update().

Usage:
    python3 scripts/seed_access_tags.py

Keys at the prompt:
    y — yes, apply this tag
    n — no, skip this tag
    s — skip the entire task (move to next)
    q — quit
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plan_generate
import gsdo_objects as o
import gsdo_anytype as g
from anytype_test import call

TAG_LYING_DOWN = "Can-be-done-lying-down"
TAG_LEAVING_HOUSE = "Involves-leaving-house"

# Keywords that suggest a task can be done lying down (reading, writing, email, research...)
_LYING_DOWN_SIGNALS = {
    "email", "read", "reading", "write", "writing", "draft", "review", "research",
    "notes", "note", "plan", "planning", "think", "thinking", "watch", "watching",
    "listen", "listening", "respond", "reply", "edit", "editing", "look up", "check",
    "browse", "schedule", "document", "update", "draft", "revise", "outline",
}

# Keywords that suggest leaving the house
_LEAVING_HOUSE_SIGNALS = {
    "drive", "driving", "walk", "walking", "pick up", "pickup", "drop off", "errand",
    "store", "shop", "shopping", "appointment", "office", "clinic", "pharmacy",
    "mail", "post office", "library", "gym", "laundry", "grocery", "groceries",
    "meet", "meeting", "lunch", "dinner", "coffee", "transit", "bus", "train",
}


def _propose_tags(name, context=""):
    """Return a list of suggested tag names based on keywords in the task name + context."""
    text = (name + " " + context).lower()
    proposed = []
    if any(sig in text for sig in _LYING_DOWN_SIGNALS):
        proposed.append(TAG_LYING_DOWN)
    if any(sig in text for sig in _LEAVING_HOUSE_SIGNALS):
        proposed.append(TAG_LEAVING_HOUSE)
    return proposed


def _prompt(question):
    try:
        return input(question).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"


def _current_access_tags(task):
    """Return the task's existing access-condition values, or []."""
    access = task.get("access") or []
    return access if isinstance(access, list) else []


def main():
    print("Loading active tasks from Anytype…")
    try:
        context_str, tasks, _ = plan_generate.build_context()
    except Exception as e:
        print(f"ERROR loading tasks: {e}")
        sys.exit(1)

    print(f"Found {len(tasks)} active tasks.\n")

    tagged = 0
    skipped = 0
    sid = g.get_space_id()

    for task in tasks:
        tid = task.get("id")
        name = task.get("name") or "(unnamed)"
        linked_projects = task.get("linked_projects") or []
        project = linked_projects[0] if linked_projects else ""
        context_text = task.get("context") or ""
        existing = _current_access_tags(task)
        proposed = _propose_tags(name, context_text)

        # Only surface tasks where we have a proposal not already applied
        new_tags = [t for t in proposed if t not in existing]
        if not new_tags:
            continue

        print(f"\n{'─'*60}")
        print(f"  {name}")
        if project:
            print(f"  Project: {project}")
        if existing:
            print(f"  Already tagged: {', '.join(existing)}")
        print()

        tags_to_apply = []
        task_skipped = False

        for tag in new_tags:
            ans = _prompt(f"  Tag as [{tag}]? (y/n/s/q): ")
            if ans == "q":
                print(f"\nDone. Tagged {tagged} tasks, skipped {skipped}.")
                return
            if ans == "s":
                task_skipped = True
                break
            if ans == "y":
                tags_to_apply.append(tag)

        if task_skipped:
            skipped += 1
            continue

        if not tags_to_apply:
            continue

        all_tags = list(existing) + tags_to_apply
        print(f"  Saving: {', '.join(tags_to_apply)}…", end=" ", flush=True)
        try:
            o.update(tid, properties={"Access conditions": all_tags})
            # Read back to confirm
            _, resp = call("GET", f"/spaces/{sid}/objects/{tid}")
            saved = resp.get("object", {})
            saved_props = saved.get("properties", {})
            saved_access = saved_props.get("Access conditions") or saved_props.get("access") or []
            confirmed = all(t in (saved_access if isinstance(saved_access, list) else []) for t in tags_to_apply)
            if confirmed:
                print("✓")
                tagged += 1
            else:
                print(f"WARNING: read-back didn't confirm tags (got: {saved_access})")
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\n{'─'*60}")
    print(f"Done. Tagged {tagged} tasks, skipped {skipped}.")
    if tagged == 0:
        print("Tip: if no tasks matched, check that task names mention keywords like")
        print("'email', 'read', 'write', 'drive', 'errand', etc.")


if __name__ == "__main__":
    main()

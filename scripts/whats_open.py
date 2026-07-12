#!/usr/bin/env python3
"""What's open in THIS repo — the live work-stream map for whatever project the
current directory is bound to.

Cross-repo by design: run it from any bound repo and it reads that repo's `.gsdot`
binding, finds the project, and renders that project's open work streams straight
from Anytype. It is the live map, not a doc — nothing here can go stale.

FOR AGENTS: call this before proposing or "reinventing" work in a repo — it tells
you what threads already exist and where each one is, so you don't start from a
blank slate or duplicate a thread that's already tracked.

Usage:
  python3 <REPO>/scripts/whats_open.py                 # bound project(s) of cwd
  python3 <REPO>/scripts/whats_open.py --dir /path      # binding of another dir
  python3 <REPO>/scripts/whats_open.py --project "Name"  # a specific project
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(__file__))
from gsdt_bind import load_context
from orient_map import render_map


def whats_open(start_dir=".", project=None):
    if project:
        return _with_notice(render_map(project))
    ctx = load_context(start_dir)
    if not ctx or not ctx.get("projects"):
        return ("No Controlled Drift binding found for this directory.\n"
                "  - pass --project \"Project Name\" to render a specific project, or\n"
                "  - bind this repo first (invoke the drift skill and say \"bind this folder\").")
    blocks = []
    for p in ctx["projects"]:
        name = p.get("name")
        if name:
            blocks.append(render_map(name))
    out = "\n\n".join(blocks) if blocks else "(binding found, but no named project to render)"
    return _with_notice(out)


def _with_notice(map_text):
    """Append the status checker's notice (pending questions / overdue check) so the
    map itself says when its own statuses are in doubt. Nothing pending -> unchanged."""
    import status_check
    notice = status_check.status_notice()
    return f"{map_text}\n\n{notice}" if notice else map_text


def main():
    ap = argparse.ArgumentParser(description="Live work-stream map for the current repo's bound project")
    ap.add_argument("--dir", default=".", help="directory to resolve the binding from (default: cwd)")
    ap.add_argument("--project", default=None, help="render this project by name instead of the bound one")
    args = ap.parse_args()
    print(whats_open(args.dir, args.project))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Sweep helper — deterministic file selection and state for Orient Mode 2.

The LLM (drift skill) orchestrates the full sweep; this script provides:
  select   — file inventory applying inclusion/exclusion rules
  stale    — staleness check (last_sweep in .gsdot vs. today)
  signals  — code signal extraction (Task 2)
  update   — update last_sweep in .gsdot (Task 3)

Usage:
  python3 scripts/sweep.py select [folder]    → JSON {planning, code, docs}
  python3 scripts/sweep.py stale [folder]     → "true" | "false"
  python3 scripts/sweep.py signals <file>     → JSON list of signals
  python3 scripts/sweep.py update [folder] --items '[...]'
"""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from gsdt_bind import read_binding, find_marker

# --- Constants ---------------------------------------------------------------

SKIP_DIRS = frozenset([
    "node_modules", "__pycache__", ".git", "vendor",
    "dist", "distro", "build",
])
PLANNING_DIRS = frozenset(["docs", "prompts", "plans", "planning", "specs"])
CODE_EXTS = frozenset([".py", ".js", ".ts", ".rb", ".go", ".rs", ".java", ".sh", ".tsx", ".jsx"])
COMPLETION_MARKERS = ["# done", "# completed", "# shipped", "# merged", "status: complete"]
SMALL_REPO_THRESHOLD = 15


# --- Helpers -----------------------------------------------------------------

def _is_archive(path):
    """Return True if the path looks like archived content.

    Checks:
    - The basename contains 'archive' (catches ROADMAP_archived.md)
    - Any directory component is exactly 'archive' or 'archives'
      (not substring — avoids false-positive on pytest temp dir names like
      test_select_excludes_archive_i0)
    """
    path = path.lower().replace("\\", "/")
    dirname, basename = path.rsplit("/", 1) if "/" in path else ("", path)
    if "archive" in basename:
        return True
    dir_parts = dirname.split("/")
    return any(p in ("archive", "archives") for p in dir_parts)


def _has_completion_marker(filepath):
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= 5:
                    break
                if any(m in line.lower() for m in COMPLETION_MARKERS):
                    return True
    except Exception:
        pass
    return False


def _is_binary(filepath):
    try:
        with open(filepath, "rb") as f:
            return b"\x00" in f.read(1024)
    except Exception:
        return True


# --- Public API --------------------------------------------------------------

def select_files(folder):
    """Apply inclusion/exclusion rules; return files by category.

    Returns {"planning": [...abs paths...], "code": [...], "docs": [...]}
    planning = CLAUDE.md + root .md files
    code     = root-level code files + one level of non-planning subdirs
    docs     = .md files in planning subdirs (docs/, prompts/, plans/, etc.)
    """
    folder = os.path.abspath(folder)
    planning, code, docs = [], [], []

    root_entries = os.listdir(folder)

    # Root-level files
    for name in root_entries:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        if _is_archive(path) or _is_binary(path):
            continue
        low = name.lower()
        _, ext = os.path.splitext(low)
        if low == "claude.md":
            planning.append(path)
            continue
        if low.endswith(".md"):
            if not _has_completion_marker(path):
                planning.append(path)
        elif ext in CODE_EXTS:
            if not _has_completion_marker(path):
                code.append(path)

    # One level of subdirectories
    for name in root_entries:
        subdir = os.path.join(folder, name)
        if not os.path.isdir(subdir):
            continue
        if name in SKIP_DIRS or _is_archive(subdir):
            continue

        is_planning = name.lower() in PLANNING_DIRS

        for fname in os.listdir(subdir):
            fpath = os.path.join(subdir, fname)
            if not os.path.isfile(fpath):
                continue
            if _is_archive(fpath) or _is_binary(fpath):
                continue
            if _has_completion_marker(fpath):
                continue
            _, ext = os.path.splitext(fname.lower())
            if is_planning and fname.lower().endswith(".md"):
                docs.append(fpath)
            elif ext in CODE_EXTS and not is_planning:
                code.append(fpath)

    return {"planning": planning, "code": code, "docs": docs}


def total_readable_count(files_by_category):
    return sum(len(v) for v in files_by_category.values())


def is_sweep_stale(folder, days=7):
    """True if no sweep has run or last_sweep is older than `days` days.
    Returns False (not applicable) for unbound folders."""
    binding = read_binding(folder)
    if not binding:
        return False
    last = binding.get("last_sweep")
    if not last:
        return True
    try:
        last_dt = datetime.date.fromisoformat(last)
        return (datetime.date.today() - last_dt).days >= days
    except Exception:
        return True


def get_last_sweep_info(folder):
    """Return {last_sweep, items_surfaced} from .gsdot, or {} if unbound."""
    binding = read_binding(folder)
    if not binding:
        return {}
    return {
        "last_sweep": binding.get("last_sweep"),
        "items_surfaced": binding.get("items_surfaced", []),
    }


# --- CLI ---------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Controlled Drift sweep helpers")
    sub = ap.add_subparsers(dest="cmd")

    p_sel = sub.add_parser("select", help="list files to read, by category")
    p_sel.add_argument("folder", nargs="?", default=".")

    p_stale = sub.add_parser("stale", help="print true/false — is last_sweep stale?")
    p_stale.add_argument("folder", nargs="?", default=".")
    p_stale.add_argument("--days", type=int, default=7)

    args = ap.parse_args()

    if args.cmd == "select":
        result = select_files(args.folder)
        print(json.dumps(result, indent=2))
    elif args.cmd == "stale":
        print("true" if is_sweep_stale(args.folder, args.days) else "false")
    else:
        ap.print_help()

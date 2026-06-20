# Sweep Workflow Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Orient Mode 2 sweep workflow — file selection, code signal extraction, learning loop state, CLAUDE.md write on binding, and drift skill updates to wire it all together.

**Architecture:** A Python helper layer (`scripts/sweep.py`, `scripts/sweep_log.py`) provides the deterministic pieces: file inventory/selection, signal extraction, `.gsdot` state updates, and the feedback log. The drift skill (LLM layer) orchestrates using these helpers — it calls `sweep.py select` to get the file list, dispatches Haiku subagents to read them in parallel for large repos, synthesizes findings against Anytype structure, presents a grouped proposal to June, and writes confirmed items via existing `gsdo_objects.create()`. This plan builds only the Python helpers and the skill update; the LLM orchestration is in the skill text.

**Tech Stack:** Python 3, existing `gsdt_bind.py` / `gsdo_anytype.py` / `gsdo_objects.py` / `notify.py` scripts. Anytype Local API at `localhost:31009` (auth via `.env`). No new dependencies.

**Design doc:** `docs/sweep_design.md` — authoritative. Read it before building. This plan operationalizes it.

## Global Constraints

- All scripts go in `scripts/`; all tests go in `tests/`
- All Anytype writes use `gsdo_objects.create()` — never hand-roll API calls
- No silent failures: raise, don't assert or print-and-continue
- Read-back before ding (the operating guard — do not skip)
- `.gsdot` writes must preserve existing fields (load → merge → write, never overwrite wholesale)
- `sweep_log.py`'s `write_log_entry()` must NEVER be called on a required/scheduled basis — it's for genuine signal only. The plan's tests must not call it in a way that implies it's mandatory.
- Tests must self-clean: no test artifacts left in real Anytype space, no `.gsdot` mutations in the real repo (use temp dirs)
- Both SKILL.md copies must be kept in sync: `skills/drift/SKILL.md` (in-repo) AND `~/.claude/skills/drift/SKILL.md` (global)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/sweep.py` | Create | File selection, code signal extraction, staleness check, `update_last_sweep()` |
| `scripts/sweep_log.py` | Create | `.gsdot-log.md` read/write |
| `scripts/gsdt_bind.py` | Modify | Add `_write_claude_md()`, call it from `init_binding()` |
| `skills/drift/SKILL.md` | Modify | CLAUDE.md check on every open; stale-sweep offer; Mode 2 → `sweep.py`; binding creation → auto-sweep |
| `~/.claude/skills/drift/SKILL.md` | Modify | Mirror of in-repo skill (copy after in-repo update) |
| `tests/test_sweep.py` | Create | Tests for `sweep.py` selection + signal extraction + state |
| `tests/test_sweep_log.py` | Create | Tests for `sweep_log.py` |
| `tests/test_gsdt_bind_claude_md.py` | Create | Tests for `_write_claude_md()` |

---

### Task 1: `scripts/sweep.py` — file selection and staleness check

**Files:**
- Create: `scripts/sweep.py`
- Create: `tests/test_sweep.py` (selection + staleness tests)

**Interfaces:**
- Produces:
  - `select_files(folder: str) -> dict[str, list[str]]` — keys: `"planning"`, `"code"`, `"docs"`. Values: absolute paths.
  - `total_readable_count(files_by_category: dict) -> int`
  - `is_sweep_stale(folder: str, days: int = 7) -> bool`
  - `get_last_sweep_info(folder: str) -> dict` — `{"last_sweep": str|None, "items_surfaced": list}`
  - CLI: `python3 scripts/sweep.py select [folder]` → JSON to stdout
  - CLI: `python3 scripts/sweep.py stale [folder]` → prints `"true"` or `"false"`, exits 0

- [ ] **Step 1: Write failing tests**

```python
# tests/test_sweep.py
import os, json, tempfile, pytest
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

def make_tree(tmp, structure):
    """structure: {relative_path: content_string_or_None_for_dir}"""
    for path, content in structure.items():
        full = os.path.join(tmp, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if content is None:
            os.makedirs(full, exist_ok=True)
        else:
            with open(full, 'w') as f:
                f.write(content)

def test_select_includes_root_md(tmp_path):
    make_tree(str(tmp_path), {"ROADMAP.md": "# plan\nopen item", "CLAUDE.md": "notes"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    names = [os.path.basename(p) for p in files["planning"]]
    assert "ROADMAP.md" in names
    assert "CLAUDE.md" in names

def test_select_excludes_node_modules(tmp_path):
    make_tree(str(tmp_path), {"node_modules/pkg/index.js": "// code", "ROADMAP.md": "open"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    assert not any("node_modules" in p for p in files["code"])

def test_select_excludes_archive_dir(tmp_path):
    make_tree(str(tmp_path), {"archive/old.md": "done stuff", "ROADMAP.md": "open"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    assert not any("archive" in p for p in files["planning"] + files["docs"])

def test_select_excludes_archive_in_filename(tmp_path):
    make_tree(str(tmp_path), {"ROADMAP_archived.md": "old", "ROADMAP.md": "open"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    names = [os.path.basename(p) for p in files["planning"]]
    assert "ROADMAP_archived.md" not in names
    assert "ROADMAP.md" in names

def test_select_excludes_completion_marker(tmp_path):
    make_tree(str(tmp_path), {
        "DONE.md": "# DONE\nnothing open",
        "ROADMAP.md": "open item",
    })
    from sweep import select_files
    files = select_files(str(tmp_path))
    names = [os.path.basename(p) for p in files["planning"]]
    assert "DONE.md" not in names
    assert "ROADMAP.md" in names

def test_select_includes_planning_subdir(tmp_path):
    make_tree(str(tmp_path), {"docs/plan.md": "TODO: something"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    assert any("plan.md" in p for p in files["docs"])

def test_select_skips_deep_code(tmp_path):
    make_tree(str(tmp_path), {"src/deep/nested/util.py": "# TODO: fix"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    # two levels deep — should NOT be included (only root + one level)
    assert not any("nested" in p for p in files["code"])

def test_total_readable_count(tmp_path):
    make_tree(str(tmp_path), {"ROADMAP.md": "open", "docs/plan.md": "open", "app.py": "# TODO"})
    from sweep import select_files, total_readable_count
    files = select_files(str(tmp_path))
    assert total_readable_count(files) >= 3

def test_is_sweep_stale_no_binding(tmp_path):
    from sweep import is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == False  # unbound → not applicable

def test_is_sweep_stale_no_last_sweep(tmp_path):
    import json
    gsdot = {"system": "Controlled Drift", "binds_to": {"projects": [{"id": "x", "name": "X"}]}}
    with open(os.path.join(str(tmp_path), ".gsdot"), "w") as f:
        json.dump(gsdot, f)
    from sweep import is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == True

def test_is_sweep_stale_recent(tmp_path):
    import json, datetime
    gsdot = {"system": "Controlled Drift",
             "binds_to": {"projects": [{"id": "x", "name": "X"}]},
             "last_sweep": datetime.date.today().isoformat()}
    with open(os.path.join(str(tmp_path), ".gsdot"), "w") as f:
        json.dump(gsdot, f)
    from sweep import is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == False

def test_is_sweep_stale_old(tmp_path):
    import json, datetime
    old = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
    gsdot = {"system": "Controlled Drift",
             "binds_to": {"projects": [{"id": "x", "name": "X"}]},
             "last_sweep": old}
    with open(os.path.join(str(tmp_path), ".gsdot"), "w") as f:
        json.dump(gsdot, f)
    from sweep import is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == True
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/june/Documents/GitHub/cyborg-memory/controlled-drift
python3 -m pytest tests/test_sweep.py -v 2>&1 | head -30
```
Expected: `ModuleNotFoundError: No module named 'sweep'`

- [ ] **Step 3: Write `scripts/sweep.py` — file selection and staleness**

```python
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
    parts = path.lower().replace("\\", "/").split("/")
    return any("archive" in p for p in parts)


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
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_sweep.py -v
```
Expected: all 11 tests pass.

- [ ] **Step 5: Smoke-test the CLI**

```bash
python3 scripts/sweep.py select . 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print('planning:', len(d['planning']), 'code:', len(d['code']), 'docs:', len(d['docs']))"
python3 scripts/sweep.py stale .
```
Expected: select prints counts, stale prints "true" (no last_sweep in .gsdot yet).

- [ ] **Step 6: Commit**

```bash
git add scripts/sweep.py tests/test_sweep.py
git commit -m "feat(sweep): file selection, staleness check — sweep.py Task 1"
```

---

### Task 2: `scripts/sweep.py` — code signal extraction

**Files:**
- Modify: `scripts/sweep.py` (add `extract_code_signals()` + `signals` CLI subcommand)
- Modify: `tests/test_sweep.py` (add signal extraction tests)

**Interfaces:**
- Consumes: `scripts/sweep.py` from Task 1
- Produces:
  - `extract_code_signals(filepath: str) -> list[dict]`
    Each dict: `{"source_file": str, "source_excerpt": str, "signal_type": str, "signal_text": str}`
    `signal_type`: `"todo"` | `"fixme"` | `"stub"` | `"hack"`
  - CLI: `python3 scripts/sweep.py signals <filepath>` → JSON list

- [ ] **Step 1: Add failing tests**

Append to `tests/test_sweep.py`:

```python
def test_extract_signals_todo(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("x = 1\n# TODO: fix the edge case\ny = 2\n")
    from sweep import extract_code_signals
    sigs = extract_code_signals(str(f))
    assert len(sigs) == 1
    assert sigs[0]["signal_type"] == "todo"
    assert "fix the edge case" in sigs[0]["source_excerpt"]

def test_extract_signals_fixme(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("# FIXME: broken on windows\npass\n")
    from sweep import extract_code_signals
    sigs = extract_code_signals(str(f))
    assert any(s["signal_type"] == "fixme" for s in sigs)

def test_extract_signals_stub(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def foo():\n    raise NotImplementedError\n")
    from sweep import extract_code_signals
    sigs = extract_code_signals(str(f))
    assert any(s["signal_type"] == "stub" for s in sigs)

def test_extract_signals_empty_file(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("def foo():\n    return 42\n")
    from sweep import extract_code_signals
    assert extract_code_signals(str(f)) == []

def test_extract_signals_includes_source_file(tmp_path):
    f = tmp_path / "util.py"
    f.write_text("# TODO: add validation\n")
    from sweep import extract_code_signals
    sigs = extract_code_signals(str(f))
    assert sigs[0]["source_file"] == str(f)
```

- [ ] **Step 2: Run to confirm failure**

```bash
python3 -m pytest tests/test_sweep.py::test_extract_signals_todo -v
```
Expected: `AttributeError: module 'sweep' has no attribute 'extract_code_signals'`

- [ ] **Step 3: Implement `extract_code_signals()` in `scripts/sweep.py`**

Two edits to `scripts/sweep.py`:

**Edit A** — update the import line at the very top of the file to add `re`:
```python
import os, sys, json, datetime, re
```

**Edit B** — add the following after `get_last_sweep_info`, before the `if __name__ == "__main__":` block:

```python
_SIGNAL_PATTERNS = [
    (r"#\s*TODO[:\s]+(.*)", "todo"),
    (r"#\s*FIXME[:\s]+(.*)", "fixme"),
    (r"#\s*HACK[:\s]+(.*)", "hack"),
    (r"raise\s+NotImplementedError(\([^)]*\))?", "stub"),
]

def extract_code_signals(filepath):
    """Extract TODO/FIXME/stub signals from a code file.
    Returns list of {source_file, source_excerpt, signal_type, signal_text}.
    """
    results = []
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        for pattern, sig_type in _SIGNAL_PATTERNS:
            m = re.search(pattern, stripped, re.IGNORECASE)
            if m:
                signal_text = m.group(1).strip() if m.lastindex and m.group(1) else stripped
                results.append({
                    "source_file": filepath,
                    "source_excerpt": stripped,
                    "signal_type": sig_type,
                    "signal_text": signal_text,
                    "line": i,
                })
                break  # one signal per line
    return results
```

Also add `signals` subcommand to the CLI block inside `if __name__ == "__main__":`, after the existing `p_stale` parser:

```python
    p_sig = sub.add_parser("signals", help="extract task signals from a code file")
    p_sig.add_argument("filepath")
```

And in the dispatch block, add:

```python
    elif args.cmd == "signals":
        print(json.dumps(extract_code_signals(args.filepath), indent=2))
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_sweep.py -v
```
Expected: all tests pass (original 11 + 5 new = 16 total).

- [ ] **Step 5: Smoke-test the CLI**

```bash
python3 scripts/sweep.py signals scripts/gsdt_bind.py
```
Expected: JSON list (may be empty if no TODOs in that file — that's correct).

- [ ] **Step 6: Commit**

```bash
git add scripts/sweep.py tests/test_sweep.py
git commit -m "feat(sweep): code signal extraction — sweep.py Task 2"
```

---

### Task 3: `scripts/sweep.py` — `update_last_sweep()` + `scripts/sweep_log.py`

**Files:**
- Modify: `scripts/sweep.py` (add `update_last_sweep()` + `update` CLI subcommand)
- Create: `scripts/sweep_log.py`
- Create: `tests/test_sweep_log.py`
- Modify: `tests/test_sweep.py` (add `update_last_sweep` tests)

**Interfaces:**
- Consumes: `scripts/sweep.py` Tasks 1–2; `scripts/gsdt_bind.py` `find_marker()`
- Produces:
  - `update_last_sweep(folder: str, items_surfaced: list[str] | None = None) -> None`
    Loads `.gsdot`, merges `last_sweep` + `items_surfaced`, writes back. Raises `FileNotFoundError` if no binding.
  - `sweep_log.write_log_entry(folder: str, entry_text: str) -> None`
    Appends a dated entry to `.gsdot-log.md`. Never call on a required/scheduled basis.
  - `sweep_log.read_log(folder: str) -> str`
    Returns full log text or `""` if absent.
  - CLI: `python3 scripts/sweep.py update [folder] --items '["a","b"]'`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_sweep_log.py
import os, json, tempfile, datetime
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

def _make_bound_dir(tmp):
    gsdot = {"system": "Controlled Drift", "binds_to": {"projects": [{"id": "x", "name": "X"}]}}
    with open(os.path.join(tmp, ".gsdot"), "w") as f:
        json.dump(gsdot, f)

def test_update_last_sweep_writes_date(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep import update_last_sweep
    update_last_sweep(str(tmp_path))
    with open(os.path.join(str(tmp_path), ".gsdot")) as f:
        data = json.load(f)
    assert data["last_sweep"] == datetime.date.today().isoformat()

def test_update_last_sweep_preserves_binds_to(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep import update_last_sweep
    update_last_sweep(str(tmp_path))
    with open(os.path.join(str(tmp_path), ".gsdot")) as f:
        data = json.load(f)
    assert "binds_to" in data

def test_update_last_sweep_with_items(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep import update_last_sweep
    update_last_sweep(str(tmp_path), items_surfaced=["Task A", "Task B"])
    with open(os.path.join(str(tmp_path), ".gsdot")) as f:
        data = json.load(f)
    assert data["items_surfaced"] == ["Task A", "Task B"]

def test_update_last_sweep_no_binding_raises(tmp_path):
    from sweep import update_last_sweep
    import pytest
    with pytest.raises(FileNotFoundError):
        update_last_sweep(str(tmp_path))

def test_write_log_entry_creates_file(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep_log import write_log_entry, read_log
    write_log_entry(str(tmp_path), "Something went well: CLAUDE.md check caught 2 items.")
    log = read_log(str(tmp_path))
    assert "Something went well" in log
    assert datetime.date.today().isoformat() in log

def test_write_log_entry_appends(tmp_path):
    _make_bound_dir(str(tmp_path))
    from sweep_log import write_log_entry, read_log
    write_log_entry(str(tmp_path), "First entry.")
    write_log_entry(str(tmp_path), "Second entry.")
    log = read_log(str(tmp_path))
    assert "First entry" in log
    assert "Second entry" in log

def test_read_log_absent_returns_empty(tmp_path):
    from sweep_log import read_log
    assert read_log(str(tmp_path)) == ""
```

- [ ] **Step 2: Run to confirm failure**

```bash
python3 -m pytest tests/test_sweep_log.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'sweep_log'` and `update_last_sweep` import errors.

- [ ] **Step 3: Implement `update_last_sweep()` in `scripts/sweep.py`**

Add after `get_last_sweep_info`, before the `_SIGNAL_PATTERNS` list (i.e., before the `if __name__ == "__main__":` block if Task 2 hasn't run yet, or between `get_last_sweep_info` and `_SIGNAL_PATTERNS` if it has):

```python
def update_last_sweep(folder, items_surfaced=None):
    """Write last_sweep (today) and optionally items_surfaced to .gsdot.
    Loads, merges, and writes back — never overwrites wholesale.
    Raises FileNotFoundError if no binding found.
    """
    path = find_marker(folder)
    if not path:
        raise FileNotFoundError(f"No .gsdot binding found from {os.path.abspath(folder)}")
    with open(path) as f:
        marker = json.load(f)
    marker["last_sweep"] = datetime.date.today().isoformat()
    if items_surfaced is not None:
        marker["items_surfaced"] = list(items_surfaced)
    with open(path, "w") as f:
        json.dump(marker, f, indent=2)
        f.write("\n")
```

Add `update` subcommand to the CLI block:

```python
    p_upd = sub.add_parser("update", help="write last_sweep to .gsdot after a sweep")
    p_upd.add_argument("folder", nargs="?", default=".")
    p_upd.add_argument("--items", default=None,
                       help='JSON array of item names surfaced, e.g. \'["Task A","Task B"]\'')
```

In the dispatch block:

```python
    elif args.cmd == "update":
        items = json.loads(args.items) if args.items else None
        update_last_sweep(args.folder, items)
        print(f"[ok] last_sweep updated: {datetime.date.today().isoformat()}")
```

- [ ] **Step 4: Create `scripts/sweep_log.py`**

```python
#!/usr/bin/env python3
"""Sweep feedback log (.gsdot-log.md) — read/write helpers.

IMPORTANT: write_log_entry() is for genuine signal only — something that would
help a future instance run sweeps better. Do NOT call it as a required step or
on a routine sweep with no surprises. Noise in this log makes it useless.
"""
import os, datetime
import sys; sys.path.insert(0, os.path.dirname(__file__))
from gsdt_bind import find_marker

LOG_FILENAME = ".gsdot-log.md"


def write_log_entry(folder, entry_text):
    """Append a dated entry to .gsdot-log.md.
    Call ONLY when there's genuine signal about what worked or went wrong.
    """
    marker_path = find_marker(folder)
    if not marker_path:
        raise FileNotFoundError(f"No .gsdot found from {os.path.abspath(folder)}")
    log_path = os.path.join(os.path.dirname(marker_path), LOG_FILENAME)
    today = datetime.date.today().isoformat()
    entry = f"\n---\n## {today}\n\n{entry_text.strip()}\n"
    with open(log_path, "a") as f:
        f.write(entry)


def read_log(folder):
    """Return full .gsdot-log.md text, or '' if absent or unbound."""
    marker_path = find_marker(folder)
    if not marker_path:
        return ""
    log_path = os.path.join(os.path.dirname(marker_path), LOG_FILENAME)
    try:
        with open(log_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""
```

- [ ] **Step 5: Add update_last_sweep tests to test_sweep.py**

Append to `tests/test_sweep.py`:

```python
def test_update_last_sweep_stale_becomes_fresh(tmp_path):
    import json, datetime
    old = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
    gsdot = {"system": "Controlled Drift",
             "binds_to": {"projects": [{"id": "x", "name": "X"}]},
             "last_sweep": old}
    with open(os.path.join(str(tmp_path), ".gsdot"), "w") as f:
        json.dump(gsdot, f)
    from sweep import update_last_sweep, is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == True
    update_last_sweep(str(tmp_path))
    assert is_sweep_stale(str(tmp_path)) == False
```

- [ ] **Step 6: Run all tests**

```bash
python3 -m pytest tests/test_sweep.py tests/test_sweep_log.py -v
```
Expected: all pass (17 sweep + 7 log = 24 total).

- [ ] **Step 7: Commit**

```bash
git add scripts/sweep.py scripts/sweep_log.py tests/test_sweep.py tests/test_sweep_log.py
git commit -m "feat(sweep): update_last_sweep + feedback log — Task 3"
```

---

### Task 4: Update `gsdt_bind.py` — CLAUDE.md write on binding creation

**Files:**
- Modify: `scripts/gsdt_bind.py`
- Create: `tests/test_gsdt_bind_claude_md.py`

**Interfaces:**
- Consumes: existing `gsdt_bind.init_binding()`
- Produces:
  - `_write_claude_md(folder: str, project_name: str, goal_name: str | None) -> None`
    Creates or appends a `## Controlled Drift binding` section to `CLAUDE.md`.
    Idempotent: if the section already exists, does nothing.
  - `init_binding()` now calls `_write_claude_md()` after writing the `.gsdot` marker.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_gsdt_bind_claude_md.py
import os, sys, tempfile
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

def test_write_claude_md_creates_file(tmp_path):
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "Build Controlled Drift", "Builder practice")
    path = os.path.join(str(tmp_path), "CLAUDE.md")
    assert os.path.isfile(path)
    content = open(path).read()
    assert "Controlled Drift binding" in content
    assert "Build Controlled Drift" in content
    assert "Builder practice" in content

def test_write_claude_md_appends_to_existing(tmp_path):
    claude_md = os.path.join(str(tmp_path), "CLAUDE.md")
    with open(claude_md, "w") as f:
        f.write("# My project\n\nExisting content.\n")
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "My Project", None)
    content = open(claude_md).read()
    assert "Existing content" in content
    assert "Controlled Drift binding" in content

def test_write_claude_md_idempotent(tmp_path):
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "My Project", "My Goal")
    _write_claude_md(str(tmp_path), "My Project", "My Goal")
    content = open(os.path.join(str(tmp_path), "CLAUDE.md")).read()
    assert content.count("Controlled Drift binding") == 1

def test_write_claude_md_no_goal(tmp_path):
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "My Project", None)
    content = open(os.path.join(str(tmp_path), "CLAUDE.md")).read()
    assert "My Project" in content
    assert "Goal:" not in content
```

- [ ] **Step 2: Run to confirm failure**

```bash
python3 -m pytest tests/test_gsdt_bind_claude_md.py -v
```
Expected: `ImportError: cannot import name '_write_claude_md'`

- [ ] **Step 3: Add `_write_claude_md()` to `scripts/gsdt_bind.py`**

Add after the `_detect_parent_project_id` function:

```python
_CLAUDE_MD_MARKER = "## Controlled Drift binding"

def _write_claude_md(folder, project_name, goal_name=None):
    """Write or append a Controlled Drift section to CLAUDE.md.
    Idempotent: if the section already exists, does nothing.
    """
    path = os.path.join(os.path.abspath(folder), "CLAUDE.md")
    section_lines = [
        "",
        _CLAUDE_MD_MARKER,
        "",
        f"This repo is bound to Controlled Drift → Project: {project_name}"
        + (f" (Goal: {goal_name})" if goal_name else "") + ".",
        f"When working here: capture any todo/commitment mentions to Anytype "
        f"under {project_name!r} by default.",
        "The `drift` skill is active here — June never has to name a function.",
        "Binding: `.gsdot` in this directory.",
        "",
    ]
    section = "\n".join(section_lines)
    if os.path.isfile(path):
        with open(path) as f:
            content = f.read()
        if _CLAUDE_MD_MARKER in content:
            return  # Already present — do nothing
        with open(path, "a") as f:
            f.write(section)
    else:
        with open(path, "w") as f:
            f.write(section.lstrip())
```

- [ ] **Step 4: Call `_write_claude_md()` from `init_binding()`**

In `init_binding()`, after the line `print(f"  [marker] {marker_path}")` and before `notify.ding()`:

```python
    # 4b. write or update CLAUDE.md at the folder root
    _write_claude_md(folder, project_name, goal_name)
    print(f"  [claude.md] updated at {os.path.join(os.path.abspath(folder), 'CLAUDE.md')}")
```

- [ ] **Step 5: Run all tests**

```bash
python3 -m pytest tests/ -v
```
Expected: all pass (16 existing + 24 sweep/log + 4 CLAUDE.md = 44 total).

- [ ] **Step 6: Commit**

```bash
git add scripts/gsdt_bind.py tests/test_gsdt_bind_claude_md.py
git commit -m "feat(bind): write CLAUDE.md on binding creation — Task 4"
```

---

### Task 5: Update drift SKILL.md — CLAUDE.md check, stale-sweep offer, Mode 2 wiring

**Files:**
- Modify: `skills/drift/SKILL.md`
- Copy to: `~/.claude/skills/drift/SKILL.md` (mirror — must stay in sync)

**Note:** No tests for this task — the skill is LLM instruction text. Review is the gate.

This task makes four additions to the skill:

1. **CLAUDE.md check on every drift open** — before anything else, check for and read `CLAUDE.md` at the repo root.
2. **Stale-sweep offer** — after the binding startup check, if bound and sweep is stale, surface a one-time offer.
3. **Mode 2 description** — replace the current vague "read repo files" with the concrete `sweep.py`-based workflow.
4. **Binding creation → auto-sweep** — make the binding creation flow end by triggering a sweep.

- [ ] **Step 1: Read the current skill in full**

```bash
cat /Users/june/Documents/GitHub/cyborg-memory/controlled-drift/skills/drift/SKILL.md
```

Read the whole file — not just the first 80 lines. The sections to replace are: `## On startup: check for a directory binding` (the full section through the three-case bullet list) and the `*Mode 2 —` paragraph inside the Orient function section. Identify both before editing.

- [ ] **Step 2: Update the "On startup" section**

Replace the current "On startup: check for a directory binding" section with:

```markdown
## On startup: check directory binding, CLAUDE.md, and sweep staleness

**Step 1 — Read CLAUDE.md (always, before anything else):**
If `CLAUDE.md` exists at the current working directory, read it now. Agents leave todos there. This is fast and happens regardless of whether a binding or sweep is active.

**Step 2 — Check for a directory binding:**
```python
import sys; sys.path.insert(0, "REPO/scripts")
from gsdt_bind import load_context
ctx = load_context()   # walks up from cwd to find nearest .gsdot
```

Three cases (same as before):
1. `.gsdot` found here → offer: *"This folder is connected to [Project name]. Work from that context, or general session?"*
2. No `.gsdot` here, parent has one → offer: *"This folder doesn't have a binding. Work from [parent]'s context, create a new project here, or general session?"* → if new project: run binding creation flow, then immediately run a sweep.
3. Nothing found → no offer; proceed with full Anytype space in context.

**Step 3 — Check sweep staleness (only if bound):**
```python
from sweep import is_sweep_stale
if is_sweep_stale("."):
    # Surface a one-time offer — do not repeat
```
If stale, offer once: *"I haven't read through this project's files in a while — want me to check what's here and catch anything not yet in Anytype?"* She can decline. If she accepts, run Mode 2. Do not re-offer in the same session.
```

- [ ] **Step 3: Update Mode 2 description**

Replace the current Mode 2 paragraph with:

```markdown
*Mode 2 — additive sweep ("catch me up," "what am I missing," stale trigger, or new binding):*

**Step 1 — File inventory (deterministic):**
```python
from sweep import select_files, total_readable_count
files = select_files(".")
count = total_readable_count(files)
```

**Step 2 — Read files:**
- If `count < 15`: lead agent reads the files directly (no subagents).
- If `count >= 15`: dispatch Haiku subagents in parallel, one per category:
  - Agent A: files in `files["planning"]`
  - Agent B: files in `files["code"]` — use `python3 REPO/scripts/sweep.py signals <filepath>` per file to extract signals; do not read full code content
  - Agent C: files in `files["docs"]`
  Each agent returns a list of `{source_file, source_excerpt, signal_type, signal_text}` dicts.
- Also read `.gsdot-log.md` via `sweep_log.read_log(".")` for prior sweep notes — read before synthesizing.

**Step 3 — Load Anytype context:**
Load the bound project's Goal, Projects (including sub-projects), and Tasks. This is the reference structure.

**Step 4 — Synthesize (lead agent):**
- For each finding: ask "does this map to an existing sub-project or work stream?" If yes, it's a task under that stream (check if already captured). If no, it's a new work stream candidate.
- Code comparison: for findings that look like open items in planning docs, check quickly whether there's code evidence the work was already done. Flag uncertain cases as "might already be complete — verify before adding."
- Group all surviving findings into named work streams. Never produce a flat list. Subdirectory organization is a hint (not authoritative).
- Format as a proposal with sources (see `docs/sweep_design.md` for proposal format).

**Step 5 — Gate:**
Present the full grouped proposal to June. She confirms/edits/rejects. Only after confirmation:
- Create confirmed items via `gsdo_objects.create()`
- Read-back each created object
- Call `python3 REPO/scripts/sweep.py update . --items '[...]'` with the confirmed item names
- Ding once for the batch

**Step 6 — Log (only if there's genuine signal):**
```python
from sweep_log import write_log_entry
# Call ONLY if something unexpected happened, something worked well,
# or a problem came up and was resolved. NOT on routine sweeps.
# write_log_entry(".", "What worked: ... What went wrong: ... Resolution: ...")
```
```

- [ ] **Step 4: Add the binding creation → auto-sweep note**

In the "Binding creation flow" subsection, add after the ding step:

```markdown
5. Immediately run a Mode 2 sweep for the new binding — this is the initial sweep that catches everything already in the repo. No separate offer needed; the binding creation implies it.
```

- [ ] **Step 5: Mirror to global**

```bash
cp /Users/june/Documents/GitHub/cyborg-memory/controlled-drift/skills/drift/SKILL.md \
   /Users/june/.claude/skills/drift/SKILL.md
echo "mirrored"
```

- [ ] **Step 6: Run the full test suite to confirm nothing broke**

```bash
python3 -m pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add skills/drift/SKILL.md
git commit -m "feat(skill): CLAUDE.md check, stale-sweep offer, Mode 2 workflow — Task 5"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| CLAUDE.md check every drift open | Task 5 |
| Stale-sweep offer (last_sweep) | Tasks 3 + 5 |
| File selection rules (inclusions, exclusions, depth) | Task 1 |
| Archive exclusion (dir + filename) | Task 1 |
| Completion marker exclusion | Task 1 |
| Code signal extraction (TODO/FIXME/stub) | Task 2 |
| Small-repo threshold (< 15 → direct read) | Tasks 1 + 5 |
| Subagent split by category (≤ 4 Haiku) | Task 5 (skill) |
| Lead agent synthesis + dedup against Anytype | Task 5 (skill) |
| Code comparison pass (light, flag uncertain) | Task 5 (skill) |
| Grouped proposal with sources | Task 5 (skill) |
| Human gate before Anytype writes | Task 5 (skill) |
| update_last_sweep + items_surfaced in .gsdot | Task 3 |
| .gsdot-log.md feedback log (conditional) | Task 3 |
| CLAUDE.md write on binding creation | Task 4 |
| Binding creation → auto-sweep | Task 5 |
| .gsdot-log.md read before synthesis | Task 5 (skill) |

**No gaps found.** Job search special case (no code pass) is handled in Task 5 via the skill's "if count < 15 → direct read" path, which for a non-code repo will naturally produce zero code findings. The code scan pass is effectively skipped because there are no code files.

**Placeholder check:** All steps contain actual code. No TBDs. Types are consistent across tasks (`dict[str, list[str]]` from `select_files` is consumed correctly in Task 5's skill description).

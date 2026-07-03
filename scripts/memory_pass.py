#!/usr/bin/env python3
"""Daily memory pass — moves June-facing items that got misfiled into Claude's own persistent
memory (~/.claude/projects/*/memory/*.md) into Anytype, where her task system actually lives.

Full design: docs/superpowers/plans/2026-07-02-daily-memory-pass.md. Slices:
  Slice 1 (steps 1-4): read + parse every project's memory files, track which entries have
    already been extracted (content-hash state file), fetch the live Anytype schema.
  Slice 2 (this file, steps 5-9): assemble the prompt, call plan_generate.generate(), create
    confirmed candidates via gsdo_objects.create with read-back, log every decision.
  Slice 3 (not yet built): launchd scheduling.

Global, not repo-scoped (decided 2026-07-02): every Claude Code project gets its own memory
folder, and this misfiling problem isn't unique to Controlled Drift's — so the default glob
covers every project, not just this one.

Reuses, never reinvents: plan_generate.generate (the pluggable LLM seam), gsdo_objects.create
(the deterministic write layer — now carrying its own exact-name dedup guard, see gsdo_objects.py)
with the same read-back-proves-persistence discipline as capture_generate.py / cd_mcp_server.py.
"""
import sys, os, re, glob, json, hashlib, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml
import cd_paths
import gsdo_anytype as g
import gsdo_objects
import plan_generate
import generation_log
import memory_pass_log
from anytype_test import call

DEFAULT_PROJECTS_ROOT = os.path.expanduser("~/.claude/projects")
STATE_FILE_NAME = "memory_pass_state.json"

# Files that are known indexes, not memory entries — no YAML frontmatter to parse, so they'd
# otherwise show up every run as an unparseable file. MEMORY.md is the standing example (every
# project folder has exactly one): a plain markdown index of pointers, not a memory record.
_INDEX_FILENAMES = {"MEMORY.md"}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n?(.*)$", re.DOTALL)


# --- step 1: discover + parse -------------------------------------------------

def _parse_memory_file(path):
    """Parse one memory file's YAML frontmatter + body. Returns a dict, or None if the file
    has no parseable frontmatter (not a memory entry — e.g. an index file or malformed leftover).
    Never raises: an unparseable file is skipped, not a crash that takes the whole pass down."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        frontmatter = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(frontmatter, dict):
        return None
    body = m.group(2).strip()
    metadata = frontmatter.get("metadata") or {}
    # Two frontmatter shapes exist across the real corpus (confirmed 2026-07-02 against all
    # project memory folders): newer entries nest `metadata: {type: ...}` (this repo's own
    # convention, per CLAUDE.md); older entries across most other projects put `type:` at the
    # top level, unnested — that's actually the MAJORITY shape (269 of 411 files), not a rare
    # exception. Nested wins if both are somehow present; either alone resolves.
    entry_type = None
    if isinstance(metadata, dict) and metadata.get("type"):
        entry_type = metadata.get("type")
    elif frontmatter.get("type"):
        entry_type = frontmatter.get("type")
    return {
        "name": frontmatter.get("name"),
        "description": frontmatter.get("description"),
        "type": entry_type,
        "body": body,
        # Hash the body only (not frontmatter, not the whole file): editing a description or
        # fixing a typo in an unrelated part of the file shouldn't force re-processing; the
        # body's wording changing SHOULD get reconsidered (run-twice-safe, not never-look-again).
        "content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def discover_memory_entries(projects_root=None):
    """Glob <projects_root>/*/memory/*.md, parse each, tag with its source project slug.

    projects_root defaults to the real ~/.claude/projects (global — every project's memory
    folder). Override for testing: point it at a scratch directory shaped the same way
    (<root>/<fake-project>/memory/*.md) so a dry run never touches June's real files.

    Returns a list of entry dicts, each also carrying source_file (basename) and source_project
    (the project-slug directory name) so two different projects' memory can't collide in dedup
    or logging.
    """
    root = projects_root or DEFAULT_PROJECTS_ROOT
    pattern = os.path.join(root, "*", "memory", "*.md")
    entries = []
    for path in sorted(glob.glob(pattern)):
        if os.path.basename(path) in _INDEX_FILENAMES:
            continue
        parsed = _parse_memory_file(path)
        if parsed is None:
            continue
        project_slug = os.path.basename(os.path.dirname(os.path.dirname(path)))
        parsed["source_file"] = os.path.basename(path)
        parsed["source_project"] = project_slug
        parsed["path"] = path
        entries.append(parsed)
    return entries


# --- step 2: per-entry extraction state --------------------------------------

def _state_path(path=None):
    return path or cd_paths.config_file(STATE_FILE_NAME)


def load_state(path=None):
    """{content_hash: {source_file, source_project, status, anytype_id, extracted_at}}."""
    path = _state_path(path)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state, path=None):
    path = _state_path(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def mark_extracted(state, entry, anytype_id=None, outcome="created"):
    """Record an entry as handled by the pass. `status` stays the single "extracted" gate
    unextracted() checks — an entry the model judged as correctly-filed memory is JUST AS
    handled as one that got created, and must not be re-sent to the model tomorrow (the whole
    point of the state file: steady state only ever re-examines what's new). `outcome` keeps
    the finer-grained reason (created / skipped-dedup / skipped-not-anytype) for later reading.

    Call ONLY after the actual decision is final — for a create, only after a read-back-proven
    write (never before: a crash mid-run must not falsely mark something extracted that was
    never actually written)."""
    state[entry["content_hash"]] = {
        "source_file": entry["source_file"],
        "source_project": entry["source_project"],
        "status": "extracted",
        "outcome": outcome,
        "anytype_id": anytype_id,
        "extracted_at": dt.datetime.now().isoformat(),
    }
    return state


# --- step 3: filter to unextracted -------------------------------------------

def unextracted(entries, state):
    """Entries whose content hash isn't already marked extracted in state."""
    return [e for e in entries if state.get(e["content_hash"], {}).get("status") != "extracted"]


# --- step 4: live schema, for prompt injection -------------------------------

def fetch_live_schema():
    """The space's current types + their linked properties, so the prompt tracks schema
    changes as they evolve instead of hardcoding today's 5 types. Returns
    [{"name":..., "key":..., "properties": [prop_name, ...]}, ...]."""
    sid = g.get_space_id()
    types = call("GET", f"/spaces/{sid}/types?limit=100")[1].get("data", [])
    return [
        {
            "name": t.get("name"),
            "key": t.get("key"),
            # Some built-in types (e.g. "Template") report properties: null, not [] — a bare
            # .get(..., []) default doesn't catch an explicit null value, only a missing key.
            "properties": [p.get("name") for p in (t.get("properties") or [])],
        }
        for t in types
    ]


def format_schema(schema):
    lines = []
    for t in schema:
        props = ", ".join(p for p in t["properties"] if p) or "(no properties)"
        lines.append(f"- {t['name']} ({t['key']}): {props}")
    return "\n".join(lines) if lines else "(no types found)"


# --- step 5: prompt assembly --------------------------------------------------

PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prompts",
                           "daily_memory_pass.md")

# Rough token budget for ONE call covering every unextracted entry across every project. Past
# this, the run falls back to one generate() call PER PROJECT instead. Not hypothetical: Slice
# 1's dry-run against the real corpus found the first-ever backfill runs ~300k estimated tokens
# total (411 entries, 21 projects) — this fallback is what that backfill actually needs. A
# steady-state daily run (a handful of new entries) stays far under this and always takes the
# single-call path; the per-project split only ever engages for a large first-run backfill.
SINGLE_CALL_TOKEN_BUDGET = 40000
_CHARS_PER_TOKEN = 4

ALLOWED_TYPES = ("Task", "Recurring", "Strategy", "Goal", "Project", "Note")

# A Task or Recurring links to a Project; a Project links to a Goal. Same rule as
# capture_generate.py / cd_mcp_server.py — kept identical so a candidate never links the wrong
# kind of object, whichever surface created it.
_LINK_PROP = {"Task": "Linked Projects", "Recurring": "Project link", "Project": "Goal link"}
_LINK_TARGET_TYPE = {"Task": "gsdo_project", "Recurring": "gsdo_project", "Project": "gsdo_goal"}


def _entry_id(entry):
    """Stable identifier for matching a candidate back to its source entry. Falls back to the
    filename when an entry's own `name` frontmatter field is missing/empty (rare, but a memory
    file with no `name:` shouldn't silently become unmatchable)."""
    return entry.get("name") or entry["source_file"]


def _format_entries_block(entries):
    lines = []
    for e in entries:
        lines.append(f"### ENTRY — name: {_entry_id(e)!r}  project: {e['source_project']!r}  "
                     f"stated_type: {e['type']!r}")
        if e.get("description"):
            lines.append(f"description: {e['description']}")
        lines.append("body:")
        lines.append(e["body"])
        lines.append("")
    return "\n".join(lines)


def _assemble_prompt(entries, schema):
    with open(PROMPT_PATH, encoding="utf-8") as f:
        template = f.read()
    parts = [
        template,
        "",
        "### LIVE ANYTYPE SCHEMA — the only types/properties you may use",
        "",
        format_schema(schema),
        "",
        f"### MEMORY ENTRIES FOR THIS RUN ({len(entries)} entries)",
        "",
        _format_entries_block(entries),
    ]
    return "\n".join(parts)


def _estimate_tokens(text):
    return len(text) // _CHARS_PER_TOKEN


def plan_batches(entries, schema):
    """Single call across every entry, unless the REAL assembled prompt is too big — then one
    call per source project. Decided by measuring the actual prompt, not guessing from entry
    counts (schema size and body length both affect the real total)."""
    if not entries:
        return []
    single_prompt = _assemble_prompt(entries, schema)
    if _estimate_tokens(single_prompt) <= SINGLE_CALL_TOKEN_BUDGET:
        return [entries]
    by_project = {}
    for e in entries:
        by_project.setdefault(e["source_project"], []).append(e)
    return list(by_project.values())


# --- step 6: generation ---------------------------------------------------------

def generate_candidates(entries, schema, backend=None):
    """One generate() call for this batch of entries. Returns (candidates, malformed, meta)
    where meta carries backend/timing for the caller to log. Raises on a generation or
    top-level-parse failure (a run that produced nothing usable is a real failure, surfaced
    honestly) — but a single malformed ELEMENT inside a valid array is dropped into `malformed`,
    never fatal to the rest of the batch (mirrors capture_generate.py's per-item handling)."""
    prompt = _assemble_prompt(entries, schema)
    backend_name = backend or os.environ.get("CD_BACKEND", "mistral")
    model = plan_generate._active_model(backend_name)
    backend_label = f"{backend_name}/{model}" if model else backend_name
    t0 = time.monotonic()
    try:
        model_text = plan_generate.generate(prompt, backend=backend)
        candidates, malformed = _parse_candidates(model_text)
    except Exception as e:
        generation_log.log_generation(
            backend=backend_label, duration_s=time.monotonic() - t0,
            success=False, source="memory_pass",
            error_type=type(e).__name__, error_msg=str(e))
        raise
    generation_log.log_generation(
        backend=backend_label, duration_s=time.monotonic() - t0,
        success=True, source="memory_pass",
        structural={"n_entries": len(entries), "n_candidates": len(candidates),
                    "n_malformed": len(malformed)})
    return candidates, malformed


def _parse_candidates(model_text):
    """Extract the candidate array from the model's fenced ```json block."""
    blocks = re.findall(r"```json\s*(.*?)\s*```", model_text, re.DOTALL)
    if not blocks:
        raise RuntimeError("model output had no ```json block — cannot process memory pass")
    try:
        parsed = json.loads(blocks[-1].strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"model's JSON block did not parse: {e}")
    if not isinstance(parsed, list):
        raise RuntimeError(f"model's JSON block was not a list (got {type(parsed).__name__})")
    candidates, malformed = [], []
    for c in parsed:
        if isinstance(c, dict) and c.get("source_entry") and c.get("source_project"):
            candidates.append(c)
        else:
            malformed.append(c if isinstance(c, dict) else {"_raw": c})
    return candidates, malformed


# --- steps 7-9: per-candidate write ---------------------------------------------

def _get_object(oid):
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"read-back failed for {oid!r}: {st} {b}")
    return b["object"]


def _resolve_link(type_name, link_name):
    """Resolve a link target NAME to an id, matching the type `type_name` links to. A named-but-
    unmatched link yields no link, never a wrong one (same guard as cd_mcp_server._resolve_link)."""
    link_prop = _LINK_PROP.get(type_name)
    if not link_prop or not link_name:
        return None, link_prop
    want_key = _LINK_TARGET_TYPE.get(type_name)
    sid = g.get_space_id()
    for o in g.fetch_all_objects(sid):
        if o.get("type", {}).get("key") == want_key and o.get("name") == link_name:
            return o["id"], link_prop
    return None, link_prop


def apply_candidate(candidate):
    """Create (or reuse, on an exact-name dedup hit) the Anytype object for one confirmed
    candidate, read back to prove it persisted. Returns a result dict with `outcome` in
    {"created", "skipped-dedup"}. Raises on any failure — the caller catches per-candidate so
    one bad item never aborts the rest of the batch (same discipline as capture_generate.py)."""
    name = (candidate.get("proposed_name") or "").strip()
    if not name:
        raise ValueError("candidate has no proposed_name")

    # needs_clarifying forces Task/Needs-Clarifying and drops any link — never invent one (guard
    # 2 from the task spec). This MUST run before validating proposed_type against ALLOWED_TYPES:
    # an under-specified entry is exactly the case where the model may reasonably leave
    # proposed_type null (it doesn't know), so validating the raw value first would wrongly raise
    # on the one case this override exists to handle. The model's own proposed_type/link_to are
    # deliberately overridden here, not just validated around — an under-specified entry should
    # surface plainly to June for her to sort, not get slotted into a type or link the model
    # wasn't actually confident about.
    needs_clarifying = bool(candidate.get("needs_clarifying"))
    if needs_clarifying:
        type_name = "Task"
        link_id, link_prop = None, None
    else:
        type_name = (candidate.get("proposed_type") or "").strip().capitalize()
        if type_name not in ALLOWED_TYPES:
            raise ValueError(f"proposed_type {candidate.get('proposed_type')!r} not in {ALLOWED_TYPES}")
        link_id, link_prop = _resolve_link(type_name, (candidate.get("link_to") or "").strip())

    type_rec = g.find_type(type_name)
    if type_rec is None:
        raise ValueError(f"type {type_name!r} not found in the live schema")

    # Explicit pre-check (in addition to gsdo_objects.create's own internal guard) so the
    # decision log can tell "already existed" apart from "created just now" — the task spec's
    # run-twice-safe guard asks for this to be visible, not just silently correct underneath.
    existing_id = gsdo_objects.find_existing(type_rec.get("key"), name)
    if existing_id:
        _get_object(existing_id)  # still prove it's really there before trusting it
        return {"outcome": "skipped-dedup", "anytype_id": existing_id,
                "name": name, "type": type_name, "needs_clarifying": needs_clarifying}

    props = {}
    if candidate.get("context_verbatim"):
        props["Context"] = candidate["context_verbatim"]
    if needs_clarifying:
        props["Task status"] = "Needs Clarifying"
    elif type_name == "Task":
        props["Task status"] = "Ready"
    if link_id:
        props[link_prop] = [link_id]

    oid = gsdo_objects.create(type_name, name, properties=props)
    obj = _get_object(oid)
    if obj.get("name") != name:
        raise RuntimeError(f"read-back mismatch for {name!r}: got {obj.get('name')!r}")
    return {"outcome": "created", "anytype_id": oid, "name": name, "type": type_name,
            "needs_clarifying": needs_clarifying}


# --- orchestration: the whole pass ----------------------------------------------

def run_pass(projects_root=None, state_path=None, backend=None, log_path=None):
    """The full Slice 1+2 pass: discover -> filter to unextracted -> batch -> generate ->
    create/read-back/log each candidate -> persist state. Returns a tally dict.

    State is saved after EVERY successful per-entry decision, not just once at the end — a
    crash partway through a large batch must not lose the entries already confirmed handled.
    """
    entries = discover_memory_entries(projects_root=projects_root)
    state = load_state(path=state_path)
    to_process = unextracted(entries, state)

    tally = {"processed": 0, "created": 0, "needs_clarifying": 0, "skipped_dedup": 0,
             "skipped_not_anytype": 0, "rejected_malformed": 0, "failed": 0}
    if not to_process:
        return tally

    schema = fetch_live_schema()
    batches = plan_batches(to_process, schema)
    entries_by_id = {(e["source_project"], _entry_id(e)): e for e in to_process}

    for batch in batches:
        candidates, malformed = generate_candidates(batch, schema, backend=backend)

        for c in malformed:
            tally["rejected_malformed"] += 1
            memory_pass_log.log_decision("rejected-malformed", candidate=c, path=log_path)

        for candidate in candidates:
            key = (candidate.get("source_project"), candidate.get("source_entry"))
            entry = entries_by_id.get(key)
            tally["processed"] += 1
            if entry is None:
                tally["rejected_malformed"] += 1
                memory_pass_log.log_decision("rejected-malformed", candidate=candidate,
                                             error="no matching input entry", path=log_path)
                continue

            if not candidate.get("belongs_in_anytype"):
                mark_extracted(state, entry, outcome="skipped-not-anytype")
                save_state(state, path=state_path)
                tally["skipped_not_anytype"] += 1
                memory_pass_log.log_decision("skipped-not-anytype", entry=entry,
                                             candidate=candidate, path=log_path)
                continue

            try:
                result = apply_candidate(candidate)
            except Exception as e:
                tally["failed"] += 1
                memory_pass_log.log_decision("failed", entry=entry, candidate=candidate,
                                             error=str(e), path=log_path)
                continue  # NOT marked extracted — a failed create must be retried next run

            mark_extracted(state, entry, anytype_id=result["anytype_id"],
                          outcome=result["outcome"])
            save_state(state, path=state_path)
            if result["outcome"] == "skipped-dedup":
                tally["skipped_dedup"] += 1
            else:
                tally["created"] += 1
                if result.get("needs_clarifying"):
                    tally["needs_clarifying"] += 1
            memory_pass_log.log_decision(result["outcome"], entry=entry, candidate=candidate,
                                         anytype_id=result["anytype_id"], path=log_path)

    return tally


# --- CLI ----------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Daily memory pass — memory files -> Anytype")
    ap.add_argument("--dry-run", action="store_true",
                     help="parse + report counts only — no LLM call, no writes (default if no other action given)")
    ap.add_argument("--memory-dir", default=None,
                     help="override the projects root (default ~/.claude/projects) — point at a "
                          "scratch dir shaped <root>/<project>/memory/*.md for safe testing")
    ap.add_argument("--state-file", default=None,
                     help="override the state file path (default ~/.controlled-drift/memory_pass_state.json)")
    ap.add_argument("--log-file", default=None,
                     help="override the decision log path (default scripts/data/memory_pass_log.jsonl)")
    ap.add_argument("--backend", default=None, help="override CD_BACKEND for this run")
    ap.add_argument("--run", action="store_true",
                     help="actually call the LLM and write to Anytype (real run, not a dry-run)")
    args = ap.parse_args()

    if args.run:
        tally = run_pass(projects_root=args.memory_dir, state_path=args.state_file,
                         backend=args.backend, log_path=args.log_file)
        print(json.dumps(tally, indent=2))
    else:
        entries = discover_memory_entries(projects_root=args.memory_dir)
        state = load_state(path=args.state_file)
        new_entries = unextracted(entries, state)
        already = len(entries) - len(new_entries)

        by_project = {}
        for e in new_entries:
            by_project.setdefault(e["source_project"], []).append(e)

        print(f"projects root: {args.memory_dir or DEFAULT_PROJECTS_ROOT}")
        print(f"state file:    {_state_path(args.state_file)}")
        print(f"total memory entries parsed: {len(entries)}")
        print(f"already extracted (skipped): {already}")
        print(f"new/unextracted:             {len(new_entries)}")
        print()
        for project, es in sorted(by_project.items()):
            print(f"### {project} ({len(es)} unextracted)")
            for e in es:
                print(f"  - {e['source_file']}: name={e['name']!r} type={e['type']!r} "
                      f"body_len={len(e['body'])} hash={e['content_hash'][:12]}")
        print()
        try:
            schema = fetch_live_schema()
            print("live schema:")
            print(format_schema(schema))
            if new_entries:
                batches = plan_batches(new_entries, schema)
                print(f"\nwould run as {len(batches)} generate() call(s) "
                      f"({'single batch' if len(batches) == 1 else 'chunked by project'})")
        except Exception as e:
            print(f"[warn] could not fetch live schema (is Anytype running?): {e}", file=sys.stderr)

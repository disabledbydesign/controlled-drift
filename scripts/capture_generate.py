#!/usr/bin/env python3
"""Headless capture/weed for the overlay — the Add tab's engine.

In Claude Code, "capture" needs no separate LLM call because Claude Code *is* the LLM: it
reads what June says, infers type, links to the right project, runs the alignment check, then
writes. The overlay is a plain Python server with no intelligence of its own, so it has to call
an LLM itself to get that same behavior — otherwise it writes bare, orphaned, unaligned items,
which is the opposite of the system's telos. This module is that call.

It reuses the weeding gate (prompts/weeding_gate.md) — the same logic that already handles a
single item AND a messy dump identically (it reads input as a web either way). The gate runs
headless here (no human mid-loop), so a JSON-output contract is appended next to the parser that
reads it, exactly as plan_generate appends its own. The LLM proposes a grouped set of items to
create, with a type, a project/goal link, and the reasoning per item; this module creates them
(read-back proven) and logs the turn to the session store. Correction happens after, via undo or
a follow-up message — the session history makes that possible. Full design:
docs/session_layer_design.md.

Reuses, never reinvents: plan_generate.generate (the pluggable LLM seam), gsdo_objects.create
(the deterministic write layer), session_store (the working-memory log).
"""
import sys, os, re, json, time
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import gsdo_objects
import plan_generate
import session_store
import generation_log
from anytype_test import call

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "weeding_gate.md")

ALLOWED_TYPES = ("Task", "Recurring", "Strategy", "Goal", "Project", "Note")

# Anytype type keys (confirmed live 2026-06-23).
_TYPE_KEYS = {"gsdo_goal": "goal", "gsdo_project": "project", "task": "task",
              "gsdo_recurring": "recurring"}

# Per-type link target + property (confirmed against the live property list 2026-06-23): a Task
# or Recurring links to a Project; a Project links to a Goal; Goal/Strategy/Note don't link.
_LINK_PROP = {"Task": "Linked Projects", "Recurring": "Project link", "Project": "Goal link"}

# The token KIND each type may link to: Tasks/Recurring → a Project (P#); a Project → a Goal
# (G#). Enforced so a Task never gets linked to a Goal via Linked Projects (type-mismatched,
# corrupt data) — a wrong-kind token is dropped, never applied. Same rule as the daily plan's
# id-threading: no valid match → no link, never the wrong one.
#
# ⚠️ DIVERGENCE TO WATCH (flagged for June, 2026-06-23): this guard is OVERLAY-ONLY, because the
# P#/G# tokens are an overlay mechanism. The Claude Code drift skill links objects directly
# (the instance picks the id) and has NO equivalent guard, so it COULD link a Task to a Goal.
# The underlying data-model rule ("a Task's Linked Projects must point at a Project, a Project's
# Goal link at a Goal") belongs in the SHARED write layer (gsdo_objects.create) so both paths
# inherit it and can't drift. Until that consolidation lands, this is the only enforcement and
# the Claude Code path relies on instance judgment. See docs/session_layer_design.md.
_LINK_TOKEN_PREFIX = {"Task": "P", "Recurring": "P", "Project": "G"}

# If the assembled prompt grows past this rough token estimate we log it (never silent) — the
# day's task volume is what makes this real later; right now it's tiny.
PROMPT_TOKEN_WARN = 24000
_CHARS_PER_TOKEN = 4


# --- context: existing structure, with link tokens --------------------------

def _load_weed_context():
    """Load the whole space and split by type — Goals/Projects for alignment + link targets,
    Tasks/Recurring for the dedup check. This is the documented weeding-gate load path
    (fetch_all_objects + filter by type key), which paginates and handles auth."""
    sid = g.get_space_id()
    objs = g.fetch_all_objects(sid)
    goals = [o for o in objs if o.get("type", {}).get("key") == "gsdo_goal"]
    projects = [o for o in objs if o.get("type", {}).get("key") == "gsdo_project"]
    tasks = [o for o in objs if o.get("type", {}).get("key") == "task"]
    recurrings = [o for o in objs if o.get("type", {}).get("key") == "gsdo_recurring"]
    return sid, goals, projects, tasks, recurrings


def _build_ref_table(goals, projects):
    """Assign each Goal a G# token and each Project a P# token, so the LLM links an item by
    copying a short token (it does that reliably) instead of echoing a 50-char id (which it
    mangles). Mirrors plan_generate._build_task_refs. Returns (ref_map, id2name, table_text)."""
    ref_map, id2name, lines = {}, {}, []
    for i, goal in enumerate(goals, start=1):
        tok = f"G{i}"
        ref_map[tok] = goal["id"]
        id2name[goal["id"]] = goal.get("name")
        lines.append(f"  {tok} — {goal.get('name')}  (Goal)")
    for i, proj in enumerate(projects, start=1):
        tok = f"P{i}"
        ref_map[tok] = proj["id"]
        id2name[proj["id"]] = proj.get("name")
        lines.append(f"  {tok} — {proj.get('name')}  (Project)")
    return ref_map, id2name, "\n".join(lines)


def _format_dedup_list(tasks, recurrings):
    """Existing Task/Recurring names so the LLM can spot a same-subject duplicate (the cross-type,
    different-name dupe the weeding gate warns about) and mark it skip rather than recreate it."""
    lines = []
    for t in tasks:
        lines.append(f"  - {t.get('name')}  (Task)")
    for r in recurrings:
        lines.append(f"  - {r.get('name')}  (Recurring)")
    return "\n".join(lines) if lines else "  (none yet)"


# --- the JSON-output contract (appended to weeding_gate.md) ------------------

_WEED_JSON_INSTRUCTION = """

---

## HOW THIS RUNS — read before producing output

You are running the weeding gate **headless and automated** — there is **no human in the
conversation to confirm with.** Everything you need is in this prompt; you are headless, with no
tools or MCP to look anything up. Therefore:

- **Do NOT ask questions or wait for confirmation.** Produce the JSON block below. June corrects
  afterward (she can undo an item or send a follow-up message), so propose your best reading.
- **Read the input as a web first** (find the through-lines), then route each item to a type —
  exactly as the gate describes above. Keep the grouping; it is the accessible surface.
- **Link by token.** To link an item to existing work, copy the matching token from the EXISTING
  GOALS & PROJECTS list: a **Task or Recurring** links to a **Project** token (P#); a **Project**
  links to a **Goal** token (G#); Goals, Strategies, and Notes do not link. Copy the token
  EXACTLY; use null if nothing fits (a no-fit is signal — a new goal/project may be emerging).
- **Dedup (mechanics only — the judgment is in the gate above).** Apply the gate's dedup rule:
  skip ONLY a genuine same-action duplicate; same topic/project/person is NOT a duplicate; when
  unsure, create and note the overlap rather than drop it. Express the decision here as: `action`
  = "skip" with a `dedup_note` for a true duplicate; OR `action` = "create" — and if you saw a
  *possible* overlap you chose not to treat as a duplicate, set `dedup_note` on the created item
  too (record the doubt; it's a signal, not a reason to drop). No overlap seen → omit `dedup_note`.
- **Capacity/affect.** If a feeling or capacity signal runs through the input ("this is heavy,"
  "I've been avoiding this," frustration, urgency), capture it once in `capacity_read` with
  `source` = "stated" if June said it outright or "inferred" if you read it from how she wrote.

## REQUIRED OUTPUT — THE JSON BLOCK ONLY

Output **ONLY** one fenced ```json block — nothing before or after. Do not write the prose
validation surface; the JSON carries it. Shape:

```json
{
  "opening": "one plain sentence naming the through-line or tension you found",
  "capacity_read": {"text": "what you read", "source": "stated|inferred", "reasoning": "why"} ,
  "groups": [
    {
      "label": "short group label",
      "through_line": "the shortest true phrase for why these belong together",
      "items": [
        {
          "type": "Task|Recurring|Strategy|Goal|Project|Note",
          "name": "the item, in June's words",
          "link": "P3 | G1 | null",
          "status": "Ready | Needs Clarifying | null",
          "action": "create | skip",
          "dedup_note": "why skipped, if skipped, else null",
          "reasoning": "why this type and this link — June must be able to see the why"
        }
      ]
    }
  ]
}
```

`capacity_read` may be null if no signal is present. `status` applies to Tasks (default "Ready";
"Needs Clarifying" if too vague to act on). Keep every `reasoning` present — the system must be
able to show June why each thing landed where it did.
"""


# --- prompt assembly --------------------------------------------------------

def _format_history(history):
    """Render recent capture turns as compact context so a follow-up ('actually link that to
    Job Search') resolves against what was just done. Oldest→newest."""
    if not history:
        return ""
    lines = ["", "## EARLIER THIS SESSION (most recent capture turns — for follow-up context)", ""]
    for e in history:
        if e.get("intent") == "undo":
            lines.append(f"- [undo] {e.get('result_summary')}")
            continue
        created = e.get("created") or []
        made = "; ".join(f"{c.get('type')}: {c.get('name')}"
                         + (f" -> {c.get('project')}" if c.get("project") else "")
                         for c in created) or "(nothing created)"
        lines.append(f'- June said: "{e.get("raw_input")}" -> {made}')
    return "\n".join(lines)


def _assemble_prompt(text, ref_table, dedup_list, history):
    with open(PROMPT_PATH) as f:
        template = f.read()
    parts = [
        template,
        "\n\n---\n\n## ACTUAL INPUTS FOR THIS RUN — authoritative, use ONLY these",
        "",
        "You are headless: the existing structure you would normally load is provided right here. "
        "Nothing is missing — link and dedup against these lists.",
        "",
        "### EXISTING GOALS & PROJECTS — link items to these by token",
        ref_table or "  (none yet)",
        "",
        "### EXISTING TASKS/RECURRING — for the dedup check (do not recreate these)",
        dedup_list,
        _format_history(history),
        "",
        "### JUNE'S INPUT TO WEED",
        "",
        text,
    ]
    return "\n".join(parts) + _WEED_JSON_INSTRUCTION


# --- parsing ----------------------------------------------------------------

def parse_weed(model_text):
    """Extract the structured weed result from the model's fenced ```json block. Raises if
    absent or unparseable — a run that produced no usable result is a failure surfaced honestly,
    never a silent empty capture."""
    blocks = re.findall(r"```json\s*(.*?)\s*```", model_text, re.DOTALL)
    if not blocks:
        raise RuntimeError("model output had no ```json block — cannot weed")
    try:
        parsed = json.loads(blocks[-1].strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"model's JSON block did not parse: {e}")
    parsed.setdefault("groups", [])
    parsed.setdefault("opening", "")
    parsed.setdefault("capacity_read", None)
    return parsed


# --- creating ---------------------------------------------------------------

def _get_object(oid):
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"could not read back created object {oid!r}: {st} {b}")
    return b["object"]


def _creation_props(type_name, item, link_id):
    """The properties to write for a confirmed item. Conservative + bare-by-default: only set
    what the design specifies per type, using property names verified against the live model."""
    props = {}
    if type_name == "Task":
        props["Task status"] = item.get("status") or "Ready"
    elif type_name == "Project":
        props["Engagement"] = "Steady"        # captured project is live by default (design)
    elif type_name == "Strategy":
        props["Strategy status"] = "Active"    # an adopted strategy is active
    # Goal, Recurring, Note: bare (June sets specifics later)
    link_prop = _LINK_PROP.get(type_name)
    if link_prop and link_id:
        props[link_prop] = [link_id]
    if item.get("context"):
        props["Context"] = item["context"]
    return props


def _create_one(type_name, item, ref_map, id2name):
    """Create one confirmed item and PROVE it persisted (read-back). Returns the record kept in
    the session log + shown to June. Raises on any failure so the caller logs it and moves on —
    one bad item never aborts the rest of the batch."""
    name = (item.get("name") or "").strip()
    if not name:
        raise ValueError("item has no name")
    tok = item.get("link")
    # Resolve only a RIGHT-KIND token (Task/Recurring->P#, Project->G#); a wrong-kind or unknown
    # token yields no link rather than a mismatched one (corrupt links are worse than none).
    expected = _LINK_TOKEN_PREFIX.get(type_name)
    link_id = ref_map.get(tok) if (tok and expected and str(tok).startswith(expected)) else None
    props = _creation_props(type_name, item, link_id)
    oid = gsdo_objects.create(type_name, name, properties=props)
    obj = _get_object(oid)
    if obj.get("name") != name:
        raise RuntimeError(f"read-back mismatch for {name!r}: got {obj.get('name')!r}")
    return {
        "id": oid,
        "type": type_name,
        "name": name,
        "project": id2name.get(link_id) if link_id else None,
        "alignment_reasoning": item.get("reasoning"),
        "dedup_note": item.get("dedup_note"),   # a create-with-overlap doubt, if the model flagged one
    }


def _summarize(created, failed, skipped):
    bits = []
    if created:
        bits.append(f"added {len(created)}")
    if skipped:
        bits.append(f"skipped {len(skipped)} (already there)")
    if failed:
        bits.append(f"{len(failed)} failed")
    return ", ".join(bits) if bits else "nothing to add"


# --- the public entry point -------------------------------------------------

def capture(text):
    """Weed June's input into typed, linked Anytype objects and log the turn.

    Returns {opening, capacity_read, groups, created[], failed[], skipped[], result_summary}.
    Never silent: a generation/parse failure logs to the session store and re-raises; a single
    item's create failure is logged and recorded in `failed` without losing the rest.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("capture: empty text")

    sid, goals, projects, tasks, recurrings = _load_weed_context()
    ref_map, id2name, ref_table = _build_ref_table(goals, projects)
    dedup_list = _format_dedup_list(tasks, recurrings)
    history = session_store.recent_entries("capture")
    prompt = _assemble_prompt(text, ref_table, dedup_list, history)

    approx_tokens = len(prompt) // _CHARS_PER_TOKEN
    if approx_tokens > PROMPT_TOKEN_WARN:
        # Not fatal (Mistral large ~30k), but the abandonment failure mode starts with silent
        # degradation — so a growing prompt gets recorded for the health view, never hidden.
        session_store.log_failure("capture", "prompt_large", {
            "approx_tokens": approx_tokens,
            "n_projects": len(projects), "n_tasks": len(tasks)})

    backend = os.environ.get("CD_BACKEND", "mistral")
    model = plan_generate._active_model(backend)
    backend_label = f"{backend}/{model}" if model else backend
    t0 = time.monotonic()
    try:
        model_text = plan_generate.generate(prompt)
        parsed = parse_weed(model_text)
    except Exception as e:
        generation_log.log_generation(
            backend=backend_label, duration_s=time.monotonic() - t0,
            success=False, source="capture",
            error_type=type(e).__name__, error_msg=str(e))
        session_store.log_failure("capture", "generation_failed", {
            "error_type": type(e).__name__, "error": str(e), "raw_input": text})
        raise

    created, failed, skipped = [], [], []
    for grp in parsed.get("groups", []):
        for item in grp.get("items", []):
            if item.get("action") == "skip":
                skipped.append({"name": item.get("name"), "note": item.get("dedup_note")})
                continue
            tname = item.get("type")
            if tname not in ALLOWED_TYPES:
                session_store.log_failure("capture", "unknown_type", {"item": item})
                failed.append({"name": item.get("name"), "error": f"unknown type {tname!r}"})
                continue
            try:
                created.append(_create_one(tname, item, ref_map, id2name))
            except Exception as e:
                session_store.log_failure("capture", "create_failed", {
                    "name": item.get("name"), "type": tname, "error": str(e)})
                failed.append({"name": item.get("name"), "error": str(e)})

    # Durable learning signal — logged deterministically on every weed (not LLM-dependent), so the
    # dedup loop gets a clean, automatic corpus of the model's own uncertainty (the dedup_notes).
    # This log is append-only/permanent; the session log holds the same notes but is windowed.
    generation_log.log_generation(
        backend=backend_label, duration_s=time.monotonic() - t0,
        success=True, source="capture",
        structural=generation_log.check_capture(parsed, created, skipped, failed))

    summary = _summarize(created, failed, skipped)
    session_store.append_entry("capture", {
        "intent": "weed",
        "raw_input": text,
        "capacity_read": parsed.get("capacity_read"),
        "groups": parsed.get("groups"),
        "created": created,
        "corrections": [],
        "result_summary": summary,
    })
    return {
        "opening": parsed.get("opening"),
        "capacity_read": parsed.get("capacity_read"),
        "groups": parsed.get("groups"),
        "created": created,
        "failed": failed,
        "skipped": skipped,
        "result_summary": summary,
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Weed text into Anytype (headless)")
    ap.add_argument("text", help="the input to weed")
    ap.add_argument("--dry-prompt", action="store_true", help="print the assembled prompt, no LLM")
    args = ap.parse_args()
    if args.dry_prompt:
        sid, goals, projects, tasks, recurrings = _load_weed_context()
        ref_map, id2name, ref_table = _build_ref_table(goals, projects)
        print(_assemble_prompt(args.text, ref_table, _format_dedup_list(tasks, recurrings),
                               session_store.recent_entries("capture")))
    else:
        print(json.dumps(capture(args.text), indent=2))

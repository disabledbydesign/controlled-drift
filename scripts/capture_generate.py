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
import datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import gsdo_objects
import plan_generate
import session_store
import generation_log
import when_resolve
import capture_fields
import recurring_active
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
# CONSOLIDATION LANDED (2026-07-12): the underlying data-model rule — a Task's/Recurring's project
# link must point at a Project, a Project's Goal link at a Goal — now ALSO lives in the SHARED
# write layer (gsdo_objects.guard_link_kinds, applied inside create_object), so the drift skill
# and MCP writes inherit it too and can no longer link a Task to a Goal. This token-level check
# stays as the overlay's first line (it maps P#/G# tokens before a real id even exists); the
# shared guard is the backstop every writer passes through. See docs/session_layer_design.md.
_LINK_TOKEN_PREFIX = {"Task": "P", "Recurring": "P", "Project": "G"}

# If the assembled prompt grows past this rough token estimate we log it (never silent) — the
# day's task volume is what makes this real later; right now it's tiny.
PROMPT_TOKEN_WARN = 24000
_CHARS_PER_TOKEN = 4


# --- context: existing structure, with link tokens --------------------------

def _load_weed_context():
    """Load the whole space and split by type — Goals/Projects for alignment + link targets,
    Tasks/Recurring/Strategies for the dedup check. This is the documented weeding-gate load
    path (fetch_all_objects + filter by type key), which paginates and handles auth."""
    sid = g.get_space_id()
    objs = g.fetch_all_objects(sid)
    goals = [o for o in objs if o.get("type", {}).get("key") == "gsdo_goal"]
    projects = [o for o in objs if o.get("type", {}).get("key") == "gsdo_project"]
    tasks = [o for o in objs if o.get("type", {}).get("key") == "task"]
    recurrings = [o for o in objs if o.get("type", {}).get("key") == "gsdo_recurring"]
    strategies = [o for o in objs if o.get("type", {}).get("key") == "gsdo_strategy"]
    return sid, goals, projects, tasks, recurrings, strategies


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


def _as_needed_recurrings(recurrings):
    """Recurring objects whose Interval unit is as_needed — the reactivation candidates the weed
    context offers the model, regardless of current Active state (an OFF one is exactly the case
    to reactivate; an already-ON one is still a valid re-tap the model can route to `reactivate`
    rather than silently duplicate)."""
    out = []
    for r in recurrings:
        props = {p.get("key"): p for p in r.get("properties", [])}
        unit = (props.get("interval_unit") or {}).get("select") or {}
        if unit.get("name") == "as_needed":
            out.append(r)
    return out


def _build_as_needed_ref_table(as_needed):
    """Assign each as-needed Recurring an R# token, mirroring _build_ref_table's G#/P# tokens —
    the model links to it the same reliable way (copy a short token, not a 50-char id)."""
    ref_map, id2name, lines = {}, {}, []
    for i, r in enumerate(as_needed, start=1):
        tok = f"R{i}"
        ref_map[tok] = r["id"]
        id2name[r["id"]] = r.get("name")
        lines.append(f"  {tok} — {r.get('name')}  (Recurring, as-needed)")
    return ref_map, id2name, "\n".join(lines)


def _dedup_extra(obj, id2name):
    """'under <Project>' + a short Context snippet, appended to a dedup-list line so the model has
    more than a bare name to recognize a same-subject item worded differently. Root case (June,
    2026-07-16): she forgot she'd already added 'Pay bills to Sutter and LabQuest' that morning;
    that evening's capture created 'Follow up on outstanding medical bills with Sutter and
    LabQuest' as a flagged-but-distinct item because the bare name alone gave the model too little
    to recognize the overlap — she had to undo it by hand. Forgetting is a real, expected use
    case, not a mistake to design around; the dedup check exists exactly for this. Both fields
    come from data already fetched for this call (no extra API cost). Silently absent when unset
    — never invents a project or context that isn't there."""
    props = {p.get("key"): p for p in obj.get("properties", [])}
    proj_ids = ((props.get("linked_projects") or {}).get("objects")
                or (props.get("gsdo_project_link") or {}).get("objects") or [])
    proj_name = None
    for pid in proj_ids:
        pid = pid.get("id") if isinstance(pid, dict) else pid
        if pid in id2name:
            proj_name = id2name[pid]
            break
    ctx = (props.get("gsdo_context") or {}).get("text")
    bits = []
    if proj_name:
        bits.append(f"under {proj_name}")
    if ctx:
        snippet = ctx.strip()
        if len(snippet) > 100:
            snippet = snippet[:97] + "..."
        bits.append(f'context: "{snippet}"')
    return f"  ({'; '.join(bits)})" if bits else ""


def _format_dedup_list(tasks, recurrings, strategies=(), id2name=None):
    """Existing Task/Recurring/Strategy names so the LLM can spot a same-subject duplicate (the
    cross-type, different-name dupe the weeding gate warns about) and mark it skip rather than
    recreate it. Strategies were missing from this list entirely until 2026-07-02 — a same
    Strategy said across separate capture turns could never be recognized as a duplicate, since
    the LLM was never shown existing Strategies to check against (root cause of a same-text
    Strategy created 3x). Tasks/Recurring also carry their project + Context (see _dedup_extra) —
    bare names alone weren't enough signal to catch a same-subject item worded differently."""
    id2name = id2name or {}
    lines = []
    for t in tasks:
        lines.append(f"  - {t.get('name')}  (Task){_dedup_extra(t, id2name)}")
    for r in recurrings:
        lines.append(f"  - {r.get('name')}  (Recurring){_dedup_extra(r, id2name)}")
    for s in strategies:
        lines.append(f"  - {s.get('name')}  (Strategy)")
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
- **Reactivate an existing as-needed task (do NOT create a duplicate).** If an item is June asking to
  do a task that is ALREADY in EXISTING AS-NEEDED TASKS ("do the dishes", "clean the fridge"), set
  `action` = "reactivate" and `reactivate_ref` = its R# token — this turns the existing task back on.
  Only for a clear match to that list. If you're unsure it's the same task, `action` = "create" as
  normal (a duplicate June can see and undo beats silently reactivating the wrong thing).
- **Capacity/affect.** If a feeling or capacity signal runs through the input ("this is heavy,"
  "I've been avoiding this," frustration, urgency), capture it once in `capacity_read` with
  `source` = "stated" if June said it outright or "inferred" if you read it from how she wrote.
- **Per-item fields.** If June names how long something takes, how she feels about something,
  what it's waiting on, or an access condition (has to leave the house, can be done lying
  down, needs a phone call), record it on the item(s) in `duration_min` / `affect` / `blocked_on` /
  `access_conditions`. Only from her words — absent stays absent, and blank affect is fine.
  For `affect`, honor the scope she gave the feeling: about one item → that item only; about
  everything ("all of this feels heavy") → on every item, because that's the information she
  provided. Never invent scope in either direction. `affect` goes on the object; `capacity_read`
  stays the whole turn's session signal — set both when both are true, but don't auto-copy one
  into the other. These feed the planner directly; a guessed duration mis-shapes her day.
- **Project engagement (type==Project only).** When an item becomes a Project, read June's words for
  how she's engaging with it and set `engagement`: a clear "I'm starting / focusing on / this is due" ->
  "Steady"; "set aside / not now / someday" -> "Backburner"; a thing she names but isn't necessarily
  starting -> "Open". Default "Open" when there's no signal — a new project should be available and
  findable, never pushed at her uninvited, never a guess of Steady, and never Sprint/Hyperfixation
  (retired). Put any deadline / cadence / intensity she voiced into `engagement_notes`. Non-Project
  items carry neither.

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
          "action": "create | skip | reactivate",
          "reactivate_ref": "R2 | null",
          "dedup_note": "why skipped, if skipped, else null",
          "reasoning": "why this type and this link — June must be able to see the why",
          "when": "<when June wants it, IN HER WORDS: 'today', a weekday like 'thursday', 'tomorrow', an ISO date, or 'someday'. EMPTY STRING if she didn't say. Never guess a time.>",
          "duration_min": <MINUTES, as a number, ONLY if June STATED or clearly implied it ("a quick 15 min", "an hour"). null if she gave no duration signal. This is her word — never put a guess here.>,
          "duration_estimate_min": <YOUR best-guess MINUTES for how long this Task actually takes, for EVERY Task, using the DURATION PRIORS below plus the task's linked project as context. This is a separate field from duration_min on purpose: duration_min is what June said; this is what you estimate. Give a real number, not null, unless the task is genuinely too vague to size (Needs Clarifying) — a rough honest estimate beats the flat 30-minute fallback every unsized Task currently gets. null for non-Task types.>,
          "affect": "<how June feels about THIS item, in her words ('dreading it', 'excited about this one'). Match the SCOPE she gave the feeling: said about one item → only that item; said about the whole dump ('I'm dreading all of this') → put it on every item, because that's her information. Do NOT invent scope — never widen a single-item remark to the dump or narrow a dump-wide statement to one item. Empty string if she gave this item no signal (blank is fine). Never a number or rating.>",
          "blocked_on": "<what this is waiting on, in June's words, if she said it's blocked/waiting ('waiting on Donna', 'once the key arrives'). Empty string if nothing.>",
          "access_conditions": [<zero or more of EXACTLY these, only when her words indicate them: "Can-be-done-lying-down", "Involves-leaving-house", "Requires-talking-to-a-person". Empty list if none. Do NOT invent other values.>],
          "engagement": "<ONLY for type==Project: how June is engaging with this thread, read from HER words. 'I'm starting/focusing on X', a deadline, 'this is my main thing right now' -> \"Steady\" (a normal daily move). 'set X aside', 'not now', 'someday/maybe' -> \"Backburner\". A thing she names but isn't necessarily starting -> \"Open\". Default \"Open\" when she gives no engagement signal — NEVER guess Steady, and NEVER use Sprint/Hyperfixation (retired). Omit for non-Project types.>",
          "engagement_notes": "<ONLY for type==Project: the situated specifics of her engagement, in HER words, that the coarse label can't hold — a deadline ('due July 1'), a cadence ('~30 min daily'), an intensity/affective note ('hyperfixating but stuck', 'this one's urgent'). Empty string if she gave none. Never invent.>"
        }
      ]
    }
  ]
}
```

`capacity_read` may be null if no signal is present. `status` applies to Tasks (default "Ready";
"Needs Clarifying" if too vague to act on). `duration_min` is June's STATED time (null unless she
said one); `duration_estimate_min` is YOUR estimate for a Task and should be filled for every
sizable Task. Keep every `reasoning` present — the system must be able to show June why each thing
landed where it did.

`engagement` / `engagement_notes` apply ONLY to Projects — the coarse engagement set is Steady / Open /
Backburner (default Open when unsignalled); Sprint and Hyperfixation are retired, so never propose them —
intensity or hyperfixation-context belongs in `engagement_notes`, not the select.

## DURATION PRIORS — use these to estimate `duration_estimate_min`

""" + capture_fields.DURATION_PRIORS + """
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


def _assemble_prompt(text, ref_table, dedup_list, history, as_needed_table=None):
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
        "### EXISTING AS-NEEDED TASKS — reactivate one of these by token instead of creating a duplicate",
        as_needed_table or "  (none yet)",
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
    # Per-item optional fields default so downstream never KeyErrors (mirrors how `when` and the
    # other item keys are read with .get). Absent stays absent — None/"" here means "no signal",
    # which build_optional_props turns into no written prop (the flat-default behavior).
    for grp in parsed.get("groups", []):
        for item in grp.get("items", []):
            item.setdefault("duration_min", None)
            item.setdefault("duration_estimate_min", None)
            item.setdefault("affect", "")
            item.setdefault("blocked_on", "")
            item.setdefault("access_conditions", [])
            item.setdefault("engagement", "Open")
            item.setdefault("engagement_notes", "")
            item.setdefault("reactivate_ref", None)
    return parsed


# --- creating ---------------------------------------------------------------

def _get_object(oid):
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"could not read back created object {oid!r}: {st} {b}")
    return b["object"]


def _creation_props(type_name, item, link_id, scheduled=None, is_parked=False):
    """The properties to write for a confirmed item. Conservative + bare-by-default: only set
    what the design specifies per type, using property names verified against the live model.

    `scheduled`/`is_parked` come from when_resolve (the anchored 'when'). A Task with a resolved
    date carries it on `Scheduled`; a 'someday' Task is Parked (its real "off today" — the plan
    path excludes Parked by status, no future-date logic needed)."""
    props = {}
    if type_name == "Task":
        props["Task status"] = item.get("status") or "Ready"
        if scheduled:
            props["Scheduled"] = scheduled
        if is_parked:
            props["Task status"] = "Parked"   # override "Ready" — someday drops off today via status
    elif type_name == "Project":
        # Born with the weeding LLM's proposed engagement (Open by default; Steady only when June's
        # words said she's starting it; Backburner when she's setting it aside) + any situated notes.
        # Replaces the old blind hardcoded Steady. The shared builder is the single validator/default,
        # so this path and the memory pass cannot diverge. (June, 2026-07-16.)
        props.update(capture_fields.build_project_engagement_props(
            engagement=item.get("engagement"),
            engagement_notes=item.get("engagement_notes"),
        ))
    elif type_name == "Strategy":
        props["Strategy status"] = "Active"    # an adopted strategy is active
    # Goal, Recurring, Note: bare (June sets specifics later)
    link_prop = _LINK_PROP.get(type_name)
    if link_prop and link_id:
        props[link_prop] = [link_id]
    # The weeding-gate JSON contract emits "reasoning" (why this landed where it did), never a
    # "context" key — writing from item.get("context") was dead code (always None) since the
    # gate was built, so no captured item of any type ever got its Context field filled in and
    # the model's stated reasoning vanished once it aged out of the session receipt. Reasoning
    # IS the intended Context content (found 2026-07-02, alongside a Strategy created with none).
    if item.get("reasoning"):
        props["Context"] = item["reasoning"]
    # Per-item optional fields (duration / affect / blocked-on / access), validated + shaped by the
    # shared builder so this path and the memory pass cannot diverge. Each value is read from THIS
    # item alone — a dump-wide feeling already arrives written on every item (the scope judgment is
    # the LLM's, per DECISION 1), so there is nothing to thread through from the turn level. A
    # blank/invalid value emits no key, preserving the bare-by-default behavior.
    props.update(capture_fields.build_optional_props(
        duration_min=item.get("duration_min"),
        duration_estimate_min=item.get("duration_estimate_min"),
        affect=item.get("affect"),
        blocked_on=item.get("blocked_on"),
        access_conditions=item.get("access_conditions"),
    ))
    return props


def _when_label(scheduled, is_today, is_parked):
    """The chip June sees for an item's 'when'. "Today" / a short date ("Thu Jul 16") / "Parked".
    None when she gave no when (undated, eligible any day) — no chip, and status stays Ready
    (undated is NOT the same as someday/Parked)."""
    if is_today:
        return "Today"
    if scheduled:
        return dt.date.fromisoformat(scheduled).strftime("%a %b %-d")
    if is_parked:
        return "Parked"
    return None


def _create_one(type_name, item, ref_map, id2name, scheduled=None, is_today=False, is_parked=False):
    """Create one confirmed item and PROVE it persisted (read-back). Returns the record kept in
    the session log + shown to June. Raises on any failure so the caller logs it and moves on —
    one bad item never aborts the rest of the batch. The when tuple (from when_resolve) sets the
    Task's Scheduled date / Parked status and rides back on the record as when_label + is_today."""
    name = (item.get("name") or "").strip()
    if not name:
        raise ValueError("item has no name")
    tok = item.get("link")
    # Resolve only a RIGHT-KIND token (Task/Recurring->P#, Project->G#); a wrong-kind or unknown
    # token yields no link rather than a mismatched one (corrupt links are worse than none).
    expected = _LINK_TOKEN_PREFIX.get(type_name)
    link_id = ref_map.get(tok) if (tok and expected and str(tok).startswith(expected)) else None
    props = _creation_props(type_name, item, link_id, scheduled=scheduled, is_parked=is_parked)
    oid = gsdo_objects.create(type_name, name, properties=props)
    obj = _get_object(oid)
    if obj.get("name") != name:
        raise RuntimeError(f"read-back mismatch for {name!r}: got {obj.get('name')!r}")
    record = {
        "id": oid,
        "type": type_name,
        "name": name,
        "project": id2name.get(link_id) if link_id else None,
        "alignment_reasoning": item.get("reasoning"),
        "dedup_note": item.get("dedup_note"),   # a create-with-overlap doubt, if the model flagged one
        "when_label": _when_label(scheduled, is_today, is_parked),
        "is_today": bool(is_today),
    }
    if type_name == "Project":
        # So the receipt can render the tap-to-change engagement chip on a newly-created Project
        # without a second fetch — the value actually written (props is the single validator/
        # default via capture_fields.build_project_engagement_props), never re-derived.
        record["engagement"] = props.get("Engagement") or "Open"
    return record


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

def capture(text, today=None):
    """Weed June's input into typed, linked Anytype objects and log the turn.

    Returns {opening, capacity_read, groups, created[], failed[], skipped[], result_summary,
    has_today}. Never silent: a generation/parse failure logs to the session store and re-raises;
    a single item's create failure is logged and recorded in `failed` without losing the rest.

    `today` is injectable (tests pin it); Python owns the date, so a resolved "thursday" anchors
    to a real ISO day before anything is written — a weekday word never reaches Anytype."""
    text = (text or "").strip()
    if not text:
        raise ValueError("capture: empty text")
    today = today or dt.date.today()

    sid, goals, projects, tasks, recurrings, strategies = _load_weed_context()
    ref_map, id2name, ref_table = _build_ref_table(goals, projects)
    # Reactivation candidates: R# tokens merged into the SAME ref_map the P#/G# link tokens use,
    # so `reactivate_ref` resolves through one lookup, not a parallel channel.
    r_ref_map, r_id2name, as_needed_table = _build_as_needed_ref_table(_as_needed_recurrings(recurrings))
    ref_map.update(r_ref_map)
    id2name.update(r_id2name)
    dedup_list = _format_dedup_list(tasks, recurrings, strategies, id2name=id2name)
    history = session_store.recent_entries("capture")
    prompt = _assemble_prompt(text, ref_table, dedup_list, history, as_needed_table=as_needed_table)

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
            if item.get("action") == "reactivate":
                rid = ref_map.get(item.get("reactivate_ref"))
                if not rid:
                    session_store.log_failure("capture", "reactivate_unresolved", {"item": item})
                    failed.append({"name": item.get("name"), "error": "reactivate_ref did not resolve"})
                    continue
                try:
                    recurring_active.set_recurring_active(rid, True)  # ONE writer (Task 3); read-back + log inside
                    obj = _get_object(rid)                    # prove + get the real name for the receipt
                    created.append({"id": rid, "type": "Recurring", "name": obj.get("name"),
                                    "action": "reactivate", "project": None,
                                    "alignment_reasoning": item.get("reasoning"),
                                    "when_label": None, "is_today": False})
                except Exception as e:
                    session_store.log_failure("capture", "reactivate_failed",
                                              {"name": item.get("name"), "error": str(e)})
                    failed.append({"name": item.get("name"), "error": str(e)})
                continue
            tname = item.get("type")
            if tname not in ALLOWED_TYPES:
                session_store.log_failure("capture", "unknown_type", {"item": item})
                failed.append({"name": item.get("name"), "error": f"unknown type {tname!r}"})
                continue
            # Python owns the date: anchor the free-text 'when' to a real ISO day BEFORE writing,
            # so "thursday" can never reach Anytype as a weekday word. (Only Tasks carry a
            # Scheduled date / Parked-someday; the tuple is inert for other types.)
            scheduled, is_today, is_parked = when_resolve.resolve_when(item.get("when", ""), today)
            try:
                created.append(_create_one(tname, item, ref_map, id2name,
                                           scheduled=scheduled, is_today=is_today, is_parked=is_parked))
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
        # belt-and-suspenders — the async capture worker discards this return, so the overlay
        # reads is_today off the session entry's created items; has_today is here for direct callers.
        "has_today": any(c.get("is_today") for c in created),
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Weed text into Anytype (headless)")
    ap.add_argument("text", help="the input to weed")
    ap.add_argument("--dry-prompt", action="store_true", help="print the assembled prompt, no LLM")
    args = ap.parse_args()
    if args.dry_prompt:
        sid, goals, projects, tasks, recurrings, strategies = _load_weed_context()
        ref_map, id2name, ref_table = _build_ref_table(goals, projects)
        _, _, as_needed_table = _build_as_needed_ref_table(_as_needed_recurrings(recurrings))
        print(_assemble_prompt(args.text, ref_table,
                               _format_dedup_list(tasks, recurrings, strategies, id2name=id2name),
                               session_store.recent_entries("capture"),
                               as_needed_table=as_needed_table))
    else:
        print(json.dumps(capture(args.text), indent=2))

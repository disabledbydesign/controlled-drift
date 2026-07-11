#!/usr/bin/env python3
"""Headless daily-plan generation for the overlay — the engine behind the surface.

`daily_plan.py` builds context and hands generation to a human-in-the-loop /drift chat.
The overlay has no human in the loop: the morning push and the negotiate/refresh buttons
must call an LLM directly. This module is that path, reused by both.

Pluggable backend (decided with June, 2026-06-22): the LLM call lives behind one seam,
`generate(prompt)`, so the engine can swap without rework if Anthropic's Claude Code
billing changes (a change was announced for 2026-06-15, then paused — see the plan doc).
  - default "claude": headless `claude -p` over stdin (draws on June's subscription)
  - "local":          a free offline model (MLX) — brought up in Slice 2
Select with the CD_BACKEND env var.

The JSON-output contract lives HERE, appended to the daily_list.md prompt, not inside
daily_list.md — so the structured schema sits next to the parser that reads it, and the
validated chat-flow prompt stays untouched. The prose plan is still produced (for the
/drift flow); the overlay reads the JSON block this module appends a request for.
"""
import sys, os, json, re, subprocess, datetime as dt, time

sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import daily_plan as dp
from surface_log import log_surfaced_batch
from plan_corrections_log import log_correction
import plan_store
import session_store
import cd_paths
import generation_log

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "daily_list.md")
GEN_TIMEOUT = 300  # seconds. A full plan runs ~160s (JSON-only); 300 gives margin for a
                   # slow/variable run so it succeeds-slow rather than fails (a failed gen
                   # leaves a STALE plan, which is worse than a wait — and it's async anyway).
                   # The real fix for speed is fewer tasks per plan (the prioritization work).


# --- the pluggable LLM seam -------------------------------------------------

def generate(prompt, backend=None, model=None):
    """Run one LLM generation. Returns raw model text. Raises on failure (never silent)."""
    backend = backend or os.environ.get("CD_BACKEND", "mistral")
    if backend == "openrouter":
        return _generate_openrouter(prompt, model=model)
    if backend == "mistral":
        return _generate_mistral(prompt, model=model)
    if backend == "claude":
        return _generate_claude(prompt)
    if backend == "local":
        return _generate_local(prompt)
    raise ValueError(f"unknown CD_BACKEND {backend!r} (expected 'openrouter', 'mistral', 'claude', or 'local')")


def _claude_env():
    """Subprocess environment for `claude`, with the durable subscription token wired in.

    Single-source auth (June's call): generation rides her Claude subscription, so there's
    only ever one thing to migrate if billing changes. An interactive shell is already
    logged in; the unattended launchd morning push is NOT — so it authenticates with a
    long-lived token from `claude setup-token`, read from a file in the config dir.

    Precedence: an existing CLAUDE_CODE_OAUTH_TOKEN in the environment wins; otherwise read
    ~/.controlled-drift/claude_token if present. Absent both, `claude` falls back to its own
    interactive login (which works from June's terminal, fails headless — by design, that's
    what the token file is for).
    """
    env = dict(os.environ)
    if not env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        try:
            with open(cd_paths.config_file("claude_token")) as f:
                tok = f.read().strip()
            if tok:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = tok
        except FileNotFoundError:
            pass
    return env


def _generate_claude(prompt):
    """Headless `claude -p`, prompt on stdin. Confirmed working 2026-06-22.

    Runs from a NEUTRAL working directory (system temp), not the repo: invoking `claude`
    inside controlled-drift/ boots the full Claude Code agent for *this* project — loading
    its MCP servers (anytype, gmail, zotero…) and the Reframe hooks on every call, which
    adds minutes of latency. Generation needs none of that — just a plain completion — so
    we run it where that heavy config isn't picked up. (The lean call is also the right one
    for the future local backend.)
    """
    import tempfile
    try:
        proc = subprocess.run(
            ["claude", "-p"], input=prompt,
            capture_output=True, text=True, timeout=GEN_TIMEOUT,
            cwd=tempfile.gettempdir(), env=_claude_env(),
        )
    except FileNotFoundError:
        raise RuntimeError("`claude` CLI not found on PATH — install it or set CD_BACKEND=local")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude generation timed out after {GEN_TIMEOUT}s")
    if proc.returncode != 0:
        raise RuntimeError(f"claude generation failed (exit {proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def _generate_local(prompt):
    """Local MLX model — the free, offline, billing-proof backup backend.

    Model chosen by CD_LOCAL_MODEL (default Qwen2.5-7B, the best all-rounder of June's set).
    Applies the model's chat template so instruct models behave. NOTE: this loads weights on
    every call — fine for the once-a-day morning push, but for interactive use it should be
    fronted by a warm server so the model isn't reloaded each time (June's inference-time
    concern). Fails loudly if mlx_lm is missing — never fakes a plan.
    """
    try:
        from mlx_lm import load, generate as mlx_generate
    except ImportError:
        raise RuntimeError("mlx_lm not installed — `pip install mlx-lm`, or use CD_BACKEND=openrouter")
    model_name = os.environ.get("CD_LOCAL_MODEL", "mlx-community/Qwen2.5-7B-Instruct-4bit")
    model, tokenizer = load(model_name)
    messages = [{"role": "user", "content": prompt}]
    formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return mlx_generate(model, tokenizer, prompt=formatted, max_tokens=2048, verbose=False)


def _load_key(*env_vars):
    """Return the first non-empty value from env or ~/Documents/.env. Raises if none found."""
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            return val
    env_path = os.path.expanduser("~/Documents/.env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() in env_vars and v.strip():
                    return v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    raise RuntimeError(f"API key not found — set one of: {', '.join(env_vars)}")


def _http_post(url, payload, headers, timeout=None):
    """Minimal HTTP POST using stdlib — no requests dependency."""
    import urllib.request, urllib.error
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout or GEN_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        raise RuntimeError(f"HTTP {e.code} from {url}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error reaching {url}: {e.reason}")


def _generate_openrouter(prompt, model=None):
    """Direct HTTP call to OpenRouter (OpenAI-compatible). No claude CLI involved.

    Model: CD_OPENROUTER_MODEL env var, or pass model= explicitly (for the compare script).
    Default: Claude Sonnet 4 — verified working 2026-06-23.
    Key: REFRAME_SHARED_OPENROUTER_KEY from env or ~/Documents/.env.
    """
    key = _load_key("REFRAME_SHARED_OPENROUTER_KEY")
    model = model or os.environ.get("CD_OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
    data = _http_post(
        "https://openrouter.ai/api/v1/chat/completions",
        payload={"model": model, "messages": [{"role": "user", "content": prompt}]},
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"OpenRouter response missing content: {str(data)[:200]}")


def _generate_mistral(prompt, model=None):
    """Direct HTTP call to Mistral API (EU/GDPR, no-train on API inputs).

    Model: CD_MISTRAL_MODEL env var, or pass model= explicitly.
    Default: mistral-large-latest (30s, highest register quality tested 2026-06-23).
    Key: MISTRAL_API_KEY or REFRAME_SHARED_MISTRAL_KEY from env or ~/Documents/.env.
    """
    key = _load_key("MISTRAL_API_KEY", "REFRAME_SHARED_MISTRAL_KEY")
    model = model or os.environ.get("CD_MISTRAL_MODEL", "mistral-large-latest")
    data = _http_post(
        "https://api.mistral.ai/v1/chat/completions",
        payload={"model": model, "messages": [{"role": "user", "content": prompt}]},
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Mistral response missing content: {str(data)[:200]}")


def _active_model(backend):
    """The model string for this backend, for logging. None if not applicable."""
    if backend == "openrouter":
        return os.environ.get("CD_OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
    if backend == "mistral":
        return os.environ.get("CD_MISTRAL_MODEL", "mistral-large-latest")
    return None


def backend_descriptor(backend):
    """How a backend ACTUALLY resolves — display label, routing mechanism, and the concrete model
    it runs — so the settings UI shows the truth (computed here, can't drift from marketing copy).
    For 'claude' the model is the CLI's own default (we don't pin one), so it's reported as None."""
    if backend == "mistral":
        return {"label": "Mistral", "mechanism": "Mistral API (direct)",
                "model": os.environ.get("CD_MISTRAL_MODEL", "mistral-large-latest")}
    if backend == "openrouter":
        return {"label": "OpenRouter", "mechanism": "OpenRouter API",
                "model": os.environ.get("CD_OPENROUTER_MODEL", "anthropic/claude-sonnet-4")}
    if backend == "claude":
        return {"label": "Claude", "mechanism": "claude -p CLI (your subscription)", "model": None}
    if backend == "local":
        return {"label": "Local", "mechanism": "on-device (MLX)",
                "model": os.environ.get("CD_LOCAL_MODEL", "mlx-community/Qwen2.5-7B-Instruct-4bit")}
    return {"label": backend, "mechanism": backend, "model": None}


def build_prompt(capacity=None, extra=None):
    """Build the full generation prompt. Public for the compare script and manual testing."""
    full_context, tasks, start_time, shape = build_context(capacity=capacity)
    ref_map, task_table = _build_task_refs(tasks)
    prompt = _assemble_prompt(full_context, start_time, capacity=capacity,
                              extra=extra, task_table=task_table, shape=shape)
    return prompt, tasks, ref_map


# --- the JSON-output contract (appended to the daily_list.md prompt) ---------

_JSON_INSTRUCTION = """

---

## HOW THIS RUNS — read before producing output

You are generating this plan **headless and automated** — there is **no human in the
conversation to answer you.** Your output is written straight to a cache the overlay
displays. Therefore:

- **Do NOT ask questions, offer choices, or propose to wait.** There is no one to reply.
- **Always produce the JSON block below**, even with imperfect inputs (no capacity signal,
  an awkward hour, a long task list). Make reasonable assumptions.
- If it is **late at night** or the day's hours are mostly gone, do NOT schedule tasks
  past midnight or pretend a full day remains. Instead produce a short, gentle plan for
  the time that's actually left — a wind-down, the one small thing worth closing on, or an
  honest "rest now; here's the shape for tomorrow." Honesty lives **in the plan's content**
  (a calm minimal plan is valid), not in refusing to produce one.
- June still negotiates later via buttons; this is her starting point, not a contract.

## REQUIRED OUTPUT — THE JSON BLOCK ONLY

Output **ONLY** the single fenced ```json code block specified here — nothing before it,
nothing after it. **Do NOT write out the prose plan** described earlier in this prompt: the
JSON below already carries all of it — the woven frame, each block's framing, each item's
why — so the prose version is redundant and only slows you down. Skip straight to the JSON.
Use exactly this shape (keep clock times verbatim from the schedule — 24-hour format, e.g. "13:30 – 15:00"; the UI converts to 12-hour for display; `project`
is null for items with no project like Lunch; `why` is the short upward-link phrase,
omit/null if none; `ref` is the task-reference token — see TASK REFERENCE in the inputs —
for items that ARE one of the listed tasks, and null for non-task items like Lunch, breaks,
or household chores):

**THREE RULES FOR EVERY ITEM:**

1. `task` is what June reads on her phone — rewrite internal labels into plain action language
   she can act on immediately. "GRA open design Q — voice/instance formalization" → "Work through
   open questions about how GRA handles voice and instance attribution." No abbreviations,
   no ALL-CAPS markers, no parenthetical codes. A plain verb phrase, scannable at a glance.

2. `why` must be grounded in the Goals/Projects context above — read the goal's `reaching_for`
   and the project's purpose, then write one sentence connecting THIS task to THAT. Do not
   invent a rationale. Do not use project-internal jargon. If the connection is not clear from
   the context, write what the task concretely produces ("produces a decision she can act on
   next session") rather than a vague upward-link. No metaphors. Omit/null for interstitial items.

3. `interstitial`: set to true if this is a quick between-task action that doesn't need a full
   time block — trash, recycling, laundry switch, a 5-minute errand, anything ≤ 15 min where
   June returns to her desk right after. These render as slim in-line markers in the schedule,
   not full work blocks. No `why` for interstitial items. Set false (or omit) for all focused work.

```json
{
  "woven_frame": "the 2-3 sentence woven frame, as plain prose",
  "blocks": [
    {
      "label": "Morning",
      "time": "09:00 – 12:00",
      "framing": "the 1-2 sentence block framing",
      "items": [
        {"time": "09:00 – 10:30", "project": "Project/thread name", "task": "plain action phrase June can act on", "why": "one sentence grounded in her actual goal — what this produces or moves", "ref": "T1", "interstitial": false},
        {"time": "10:30 – 10:35", "project": null, "task": "Take out recycling", "why": null, "ref": null, "interstitial": true}
      ]
    }
  ],
  "still_here": [
    {"label": "thread or item name", "note": "the concrete reassurance — its rhythm / why deferred"}
  ]
}
```

This JSON is the whole output — it is exactly what June sees in the overlay. Keep the woven
frame specific and warm (per the guidance above), the block framings and why-phrases intact,
and the items in schedule order. No prose before or after — just the block.
"""


_JSON_INSTRUCTION_PRIORITY = """

---

## HOW THIS RUNS — read before producing output

You are generating this plan **headless and automated** — there is **no human in the
conversation to answer you.** Your output is written straight to a cache the overlay displays.
Do NOT ask questions or propose to wait. Always produce the JSON block below.

**TODAY IS A FRAGMENTED DAY.** June does not have fixed blocks of time — her time comes in
unpredictable windows (caregiving, low capacity, "a couple hours, don't know when"). A clock
schedule would be a lie today. So the output is a **priority list to pull from**, NOT a timed
schedule: a short, ordered set of what matters most, so when a window opens she takes the next
one that fits. **Do NOT invent clock times. Do NOT group into morning/afternoon blocks.**

The order is ALREADY DECIDED (foreground-first) in the priority list in the inputs above — keep
that order. Your job is to rewrite each item into plain language, add a grounded `why`, write a
short warm woven frame, and a one-line `header` naming what today's shape is and why.

## REQUIRED OUTPUT — THE JSON BLOCK ONLY

Output **ONLY** the single fenced ```json block — nothing before or after. Use exactly this shape:

- `header`: one plain sentence stating this is a fragmented day and how to use the list, e.g.
  "Today's fragmented — a short list to pull from, no fixed times. When a window opens, start at
  the top." No metaphors.
- each item's `task` is plain action language June can act on immediately (no codes, no ALL-CAPS,
  no jargon); `why` is one sentence grounded in her actual goal/project (what this produces or
  moves — never invented); `project` is the project/thread name or null; `ref` is the task's
  reference token from TASK REFERENCE (so she can mark it done), null if it isn't a listed task.
- keep the list SHORT (the inputs already cap it) and in the given order — do not reorder.

```json
{
  "shape": "priority",
  "woven_frame": "the 2-3 sentence woven frame, plain and warm",
  "header": "Today's fragmented — a short list to pull from, no fixed times. When a window opens, start at the top.",
  "items": [
    {"project": "Project/thread name", "task": "plain action phrase June can act on", "why": "one sentence grounded in her actual goal — what this produces or moves", "ref": "T1"}
  ],
  "still_here": [
    {"label": "thread or item name", "note": "the concrete reassurance — its rhythm / why deferred"}
  ]
}
```

This JSON is the whole output. No `blocks`, no clock times — a plain priority list. No prose
before or after — just the block.
"""


# --- context assembly (reuses daily_plan, minus the interactive input/print) -

def select_and_order_tasks(tasks, period):
    """Order tasks foreground-first and DROP paused-project tasks (the period overrides the
    enduring engagement). With no period, preserves the prior date-seeded hash order exactly —
    unchanged behavior. Matching is by the period's resolved foreground/paused project NAMES
    (themselves resolved from stored ids in load_active_items) against each task's linked_projects.
    This is the real reprioritization the addendum wants — not just a prose hint to the model."""
    import hashlib
    fg = set((period or {}).get("foreground") or [])
    paused = set((period or {}).get("paused") or [])

    def _proj(t):
        projs = t.get("linked_projects") or []
        return projs[0] if projs else ""

    kept = [t for t in tasks if _proj(t) not in paused]
    seed = hashlib.md5(dt.date.today().isoformat().encode()).hexdigest()

    def _key(t):
        proj = _proj(t)
        order = int(hashlib.md5((proj + seed).encode()).hexdigest()[:4], 16)
        # foreground first; within that, linked-before-unlinked (unchanged); then hash order
        return (0 if proj in fg else 1, 1 if not proj else 0, order)

    return sorted(kept, key=_key)


def build_context(capacity=None, start_time=None, end_time=None):
    """Load active items + compute the clock schedule, returning the full prompt context.

    Mirrors daily_plan.run() but with NO blocking input() and NO printing: capacity is
    ambient (passed in or None), never a front-door gate (SYNTHESIS: offer, don't gate).
    Returns (full_context_str, tasks, start_time) — tasks handed back for the neglect loop.

    Default start: 10:00 (if current time is before 10 AM, plan starts at 10).
    Default end: 18:00. Tasks that don't fit before end_time overflow into still_here.
    """
    sid = g.get_space_id()
    goals, projects, tasks, strategies, today_recurrings, period_ctx = dp.load_active_items(sid)
    neglected = dp.load_neglected()
    period = period_ctx["period"]
    is_off, in_window = period_ctx["is_off"], period_ctx["in_window"]

    now = dt.datetime.now().replace(second=0, microsecond=0)
    if start_time is None:
        day_start = now.replace(hour=10, minute=0)
        base = now if now >= day_start else day_start
        # Ceil to nearest 30 min so the plan runs on :00/:30 marks
        excess = base.minute % 30
        start_time = base if excess == 0 else base + dt.timedelta(minutes=30 - excess)
        start_time = start_time.replace(second=0, microsecond=0)
    if end_time is None:
        # Workday-end override: a sprint period widens the day (e.g. till 22:00), a gentle one
        # narrows it. Falls back to 18:00. The scheduler already honors end_time. This restores
        # the addendum's "a period can be MORE, not less" — the field is now actually applied.
        import focus_period as fp
        if period and period.get("workday_end"):
            wh, wm = fp.parse_hhmm(period["workday_end"])
            end_time = now.replace(hour=wh, minute=wm, second=0, microsecond=0)
        else:
            end_time = now.replace(hour=18, minute=0, second=0, microsecond=0)

    meals = dp.default_meal_anchors(today_recurrings, start_time)
    all_anchors = today_recurrings + meals
    # Task selection: foreground projects (period override) sort first; paused-project tasks
    # are dropped. With no period this preserves the prior date-seeded hash order exactly.
    ordered = select_and_order_tasks(tasks, period)
    # "Fun / hobby"-side (self-directed creative/dev) tasks are kept OUT of the daily plan by
    # default (June, 2026-07-11) so they don't crowd out Obligation + Wellbeing work; necessary
    # rest still stays. June toggles this from the overlay Settings panel (dp.include_hobby_block
    # reads settings.json). NB: `wellbeing` var below = the held-out Fun/hobby list (legacy name).
    schedulable, wellbeing = dp.partition_by_side(ordered, projects)

    # Output SHAPE (Phase 6, Task 6): a fragmented / unknown-timing day (a caregiving window, or
    # a period that asks for a priority list) can't be expressed as a clock schedule — forcing one
    # is the output-format-bias the addendum warns about. Python decides the shape deterministically
    # from the structured period + window; the schedule vs priority-list body follows from it.
    import focus_period as fp
    shape = fp.resolve_output_shape(period, in_window)

    if shape == "priority":
        # A foreground-first list to pull from when a window opens — no clock times. Python owns
        # the order (select_and_order_tasks already sorted foreground-first); the model only narrates.
        schedule_block = dp.format_priority_list(schedulable, period=period)
    else:
        task_items = [{"name": t["name"], "duration_min": t.get("duration_min")} for t in schedulable]
        hobby = dp.open_hobby_block(wellbeing) if dp.include_hobby_block() else None
        if hobby:
            task_items.append({"name": hobby["name"], "duration_min": hobby["duration_min"]})
        scheduled = dp.build_schedule(task_items, all_anchors, start_time, end_time=end_time)
        schedule_block = dp.format_schedule_blocks(scheduled)

        scheduled_names = {s["name"] for s in scheduled}
        overflow = [t for t in schedulable if t["name"] not in scheduled_names]
        if overflow:
            schedule_block += f"\n\n### Didn't fit before {end_time.strftime('%H:%M')} — put these in still_here\n"
            for t in overflow:
                schedule_block += f"  - {t['name']}\n"

    context_block = dp.format_context(
        goals, projects, tasks, strategies, today_recurrings, neglected, capacity,
        period=period, is_off=is_off, in_window=in_window)
    if period is None:
        context_block += ("\n\n## No active focus period\n"
                          "- There's no configuration for this stretch. If today's plan feels "
                          "off, June may want to set a focus period — offer it, gently, once.")
    full_context = context_block + "\n" + schedule_block
    # Return schedulable (not all tasks): wellbeing work is the open block, so it isn't
    # individually accounted / surfaced / ref-tokened downstream (never-pick-her-threads).
    return full_context, schedulable, start_time, shape


def _build_task_refs(tasks):
    """Assign each active task a short stable token (T1, T2, …) for the id-threading
    handshake. Returns (ref_map, table_text):

      ref_map    {"T1": anytype_id, ...} — Python owns the token->real-id mapping
      table_text the "T1 — <task name>" block injected into the prompt

    Why tokens, not raw ids: the model only has to copy a 2-char token verbatim (which it
    does reliably), while the 40+ char opaque Anytype id never enters its output to be
    mangled. The model echoes the token on each plan item; _resolve_ids maps it back here.
    """
    ref_map, lines = {}, []
    for i, t in enumerate(tasks, start=1):
        token = f"T{i}"
        ref_map[token] = t["id"]
        lines.append(f"  {token} — {t['name']}")
    return ref_map, "\n".join(lines)


def _format_current_plan(plan):
    """Compact summary of the displayed plan — passed to the LLM when renegotiating so it
    knows WHAT it's changing. Without this, 'move X to later' is unresolvable: the LLM
    has a fresh deterministic schedule that may not match what June sees on screen."""
    if not plan:
        return None
    lines = []
    for block in plan.get("blocks", []):
        lines.append(f"### {block.get('label', '?')} ({block.get('time', '?')})")
        for item in block.get("items", []):
            proj = item.get("project", "")
            task = item.get("task", "")
            t = item.get("time", "")
            prefix = f"[{proj}] " if proj else ""
            lines.append(f"  - {t}: {prefix}{task}")
    return "\n".join(lines) if lines else None


def _format_session_history(history):
    """Render recent negotiate turns so a follow-up adjustment ('and move job search later')
    resolves against what June already asked for today. Oldest→newest, compact."""
    if not history:
        return None
    lines = []
    for e in history:
        if e.get("intent") == "undo":
            lines.append(f"- [undo] {e.get('result_summary')}")
        else:
            lines.append(f'- June asked: "{e.get("raw_input")}" -> {e.get("result_summary")}')
    return "\n".join(lines)


def _assemble_prompt(full_context, start_time, capacity=None, extra=None, task_table=None,
                     history=None, current_plan=None, request_kind="reorder", shape="clock"):
    """Build the full prompt: the daily_list.md template + an authoritative inputs section
    holding the real data, + the JSON contract (+ any negotiation note).

    The data is APPENDED as its own clearly-labeled section, not slotted into placeholders
    inside the template. Placeholder-replacement is fragile — if the template's wording
    drifts, str.replace silently no-ops and the data vanishes from the prompt (exactly the
    bug that made a headless run report 'task data didn't load'). Appending can't silently
    fail: the data is always present and explicitly marked as the source of truth.
    """
    with open(PROMPT_PATH) as f:
        template = f.read()
    parts = [
        template,
        "\n\n---\n\n## ACTUAL INPUTS FOR THIS RUN — authoritative, use ONLY these",
        "",
        "Everything you need is in this prompt. You are headless: there are no tools or MCP "
        "servers to look anything up, and nothing is missing — if you reach for data, it is "
        "in the block below. Do not say data 'failed to load'; build the plan from what's here.",
        "",
        f"- Current time: {start_time.strftime('%A %B %d, %Y — %I:%M %p')}",
        f"- Capacity signal: {capacity or '(none given)'}",
        "",
        ("### Active goals / projects / tasks / strategies + the pre-computed priority list"
         if shape == "priority" else
         "### Active goals / projects / tasks / strategies + the pre-computed clock schedule"),
        "",
        full_context,
    ]
    if task_table:
        parts += [
            "",
            "### TASK REFERENCE — copy the matching `ref` token onto each plan item",
            "",
            "Each active task below has a short token. In the JSON output, set each task "
            "item's `ref` to the token of the task it represents, copied EXACTLY (do not "
            "invent, alter, or renumber tokens). Use null for non-task items (Lunch, breaks, "
            "household chores). This is how June marks a task done from the surface — a wrong "
            "or missing token just means that item can't be checked off, so be faithful.",
            "",
            task_table,
        ]
    history_text = _format_session_history(history)
    if history_text:
        parts += ["", "## EARLIER ADJUSTMENTS THIS SESSION (for follow-up context)", "",
                  history_text]
    if extra:
        if current_plan:
            parts += [
                "",
                "## CURRENT PLAN ON SCREEN (what June is looking at right now)",
                "",
                "This is the plan already displayed to June. She is asking to change it.",
                "Use this to understand what she means by 'move X' or 'put Y first' — her",
                "request is relative to THIS ordering, not the pre-computed schedule above.",
                "",
                current_plan,
            ]
        if request_kind == "generate":
            # A FRESH generation with June's words attached (freetext-generate, or a preset like
            # low-energy). Until 2026-07-02 this text was computed and logged but never reached
            # this prompt at all — the model built the plan blind to what she'd just said, which
            # is why naming a task explicitly here had zero effect on the output.
            parts += [
                "",
                "## JUNE'S REQUEST — CONTEXT FOR THIS GENERATION",
                "",
                "June said this when asking for today's plan. This is a FRESH generation from",
                "the full active list above (not a renegotiation of an existing plan) — but her",
                "words are the strongest signal for what matters today. If she names a task,",
                "project, or concern here, it must show up in the output: either as a block item,",
                "or named explicitly in still_here with a real reason tied to what she said. Do",
                "not drop something she just named without accounting for it somewhere.",
                "",
                extra,
            ]
        else:
            parts += [
                "",
                "## JUNE'S REQUEST — RENEGOTIATION",
                "",
                "**This is a renegotiation, not an initial generation.** The 'do not reorder items'",
                "constraint in the template above applies only to the initial automated plan.",
                "For this call: honor June's request — reorder, shift, or drop items as she asks.",
                "Recalculate times from the current moment to make the new ordering fit the window.",
                "Update the woven_frame and block framings to explain the new ordering rationale.",
                "",
                extra,
            ]
    prompt = "\n".join(parts)
    prompt += _JSON_INSTRUCTION_PRIORITY if shape == "priority" else _JSON_INSTRUCTION
    return prompt


def _norm(s):
    """Normalize a task string for fallback name-matching: lowercased, whitespace-collapsed."""
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _resolve_ids(plan, ref_map, tasks):
    """Thread the real Anytype task id onto each plan item, in place.

    Primary path: the model echoed a `ref` token -> map it back through ref_map.
    Fallback: no/unknown token, but the item's task text matches a real task name exactly
    (normalized) -> use that id. This is deliberately STRICT (exact normalized equality, not
    substring) — a loose match risks marking the WRONG task done, the one error worse than
    no id at all. No match -> the item simply carries no id and shows no done-affordance.
    """
    by_name = {_norm(t["name"]): t["id"] for t in tasks}
    context_by_id = {t["id"]: (t.get("context") or "").strip() for t in tasks}

    def _resolve_item(item):
        ref = item.pop("ref", None)  # consume the token; the overlay only needs the id
        tid = ref_map.get(ref) if ref else None
        if not tid:
            tid = by_name.get(_norm(item.get("task")))
        if tid:
            item["id"] = tid
            # Carry the task's stored description (its Context field) onto the item so the
            # overlay can show it on expand. Empty for most tasks until the weed writes one;
            # the overlay only renders the slot when there's text.
            desc = context_by_id.get(tid)
            if desc:
                item["description"] = desc

    for block in plan.get("blocks", []):        # clock shape
        for item in block.get("items", []):
            _resolve_item(item)
    for item in plan.get("items", []):          # priority shape (flat)
        _resolve_item(item)
    return plan


def _ensure_all_tasks_accounted(plan, tasks):
    """Force every active task to appear somewhere in the output — scheduled or in still_here.

    Nothing requires the model to place every input task in `blocks` OR name it in
    `still_here` — it can simply omit one, and nothing catches that: the task is untouched in
    Anytype, but June sees a shorter plan with no trace of what's missing or why (the
    2026-07-02 phone-call/dinner/drive-to-SF incident — all three vanished from a generation
    with no error, no log entry pointing at them). Run this AFTER `_resolve_ids` (which threads
    real ids onto scheduled items), as a deterministic set-difference — no model judgment. A
    duplicate mention (the model already named it in still_here under different wording) costs
    nothing; a silent drop costs June's trust that the plan is honest about what's there.
    """
    placed_ids = {item.get("id")
                  for block in plan.get("blocks", [])
                  for item in block.get("items", [])}
    placed_ids |= {item.get("id") for item in plan.get("items", [])}  # priority shape (flat)
    still_here = plan.setdefault("still_here", [])
    covered_labels = {_norm(sh.get("label")) for sh in still_here if sh.get("label")}
    for t in tasks:
        if t["id"] in placed_ids or _norm(t["name"]) in covered_labels:
            continue
        still_here.append({
            "label": t["name"],
            "note": "not addressed in this plan — added automatically so it isn't lost",
        })
    return plan


# --- parsing the model output ----------------------------------------------

def parse_plan(model_text):
    """Extract the structured plan dict from the model's fenced ```json block.

    Raises if no valid JSON block is found — a generation that didn't produce the
    overlay's data is a failure, surfaced honestly, not a silently-empty plan.
    """
    blocks = re.findall(r"```json\s*(.*?)\s*```", model_text, re.DOTALL)
    if not blocks:
        raise RuntimeError("model output had no ```json block — cannot render overlay")
    last = blocks[-1].strip()  # the plan block is emitted last
    try:
        plan = json.loads(last)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"model's JSON block did not parse: {e}")
    plan.setdefault("woven_frame", "")
    plan.setdefault("still_here", [])
    # Two shapes: a clock schedule (blocks[]) or a fragmented-day priority list (flat items[]).
    # Pin the shape definitively so the overlay renders the right branch (never guesses).
    if plan.get("shape") == "priority" or ("items" in plan and "blocks" not in plan):
        plan["shape"] = "priority"
        plan.setdefault("items", [])
    else:
        plan["shape"] = "clock"
        plan.setdefault("blocks", [])
    return plan


# --- the two public entry points --------------------------------------------

def generate_plan(capacity=None, source="generate", extra=None):
    """Fresh generation (morning push / refresh / freetext-generate / a generate-preset).

    `extra` is what June said when asking for this generation (freetext message, or a preset's
    payload text) — optional, since a plain refresh or the morning push has none. Threaded into
    the prompt with request_kind="generate" framing (distinct from reorder()'s renegotiation
    framing below): a fresh generation still selects from the whole active list, but her words
    are the strongest signal for what to prioritize. Writes cache, logs what surfaced.
    """
    full_context, tasks, start_time, shape = build_context(capacity=capacity)
    ref_map, task_table = _build_task_refs(tasks)
    prompt = _assemble_prompt(full_context, start_time, capacity=capacity, task_table=task_table,
                              extra=extra, request_kind="generate", shape=shape)
    backend = os.environ.get("CD_BACKEND", "mistral")
    model = _active_model(backend)
    backend_label = f"{backend}/{model}" if model else backend
    t0 = time.monotonic()
    try:
        model_text = generate(prompt)
        plan = parse_plan(model_text)
        _resolve_ids(plan, ref_map, tasks)
        _ensure_all_tasks_accounted(plan, tasks)
    except Exception as e:
        generation_log.log_generation(
            backend=backend_label, duration_s=time.monotonic() - t0,
            success=False, source=source,
            error_type=type(e).__name__, error_msg=str(e),
        )
        raise
    generation_log.log_generation(
        backend=backend_label, duration_s=time.monotonic() - t0,
        success=True, source=source,
        structural=generation_log.check_plan(plan, n_input_tasks=len(tasks)),
    )
    saved = plan_store.save_plan(plan, source=source)
    # Learning loop: durable snapshot of the full generated plan — the planned side of
    # planned-vs-actual (a future loop diffs it against Log Day). Best-effort; never break
    # a generation over a snapshot write.
    try:
        import plan_snapshot_log
        plan_snapshot_log.log_plan_snapshot(saved, source=source)
    except Exception as e:
        print(f"[warn] plan snapshot not written: {e}", file=sys.stderr)  # honest, non-breaking
    # Learning loop: every generation records what surfaced (neglect/rhythm history).
    if tasks:
        log_surfaced_batch([{"id": t["id"], "name": t["name"], "type": "task"} for t in tasks])
    return saved


def reorder(message, kind):
    """Reorder/reframe the current plan from June's request (a preset payload or freetext).

    Works on the existing cached plan — no new task selection from Anytype.
    `kind` labels the correction for the learning log: 'preset:<id>' or 'freetext'.
    Logs the before/after plan so the rhythm + duration loops have the delta. Also
    re-surfaces (the renegotiated plan is what she's now working from).
    """
    before = plan_store.load_plan()
    full_context, tasks, start_time, shape = build_context()
    ref_map, task_table = _build_task_refs(tasks)
    history = session_store.recent_entries("negotiate")
    current_plan_summary = _format_current_plan(before)
    prompt = _assemble_prompt(full_context, start_time, extra=message, task_table=task_table,
                              history=history, current_plan=current_plan_summary, shape=shape)
    backend = os.environ.get("CD_BACKEND", "mistral")
    model = _active_model(backend)
    backend_label = f"{backend}/{model}" if model else backend
    t0 = time.monotonic()
    try:
        model_text = generate(prompt)
        plan = parse_plan(model_text)
        _resolve_ids(plan, ref_map, tasks)
        _ensure_all_tasks_accounted(plan, tasks)
    except Exception as e:
        generation_log.log_generation(
            backend=backend_label, duration_s=time.monotonic() - t0,
            success=False, source=kind,
            error_type=type(e).__name__, error_msg=str(e),
        )
        raise
    generation_log.log_generation(
        backend=backend_label, duration_s=time.monotonic() - t0,
        success=True, source=kind,
        structural=generation_log.check_plan(plan, n_input_tasks=len(tasks)),
    )
    saved = plan_store.save_plan(plan, source=kind)

    # Learning loop #1: the correction itself (the richest signal — live negotiation).
    log_correction(kind, before=before, after=saved)
    # Learning loop #2: what surfaced in the renegotiated plan.
    if tasks:
        log_surfaced_batch([{"id": t["id"], "name": t["name"], "type": "task"} for t in tasks])
    # Learning loop #3 (meal timing): if Lunch moved, nudge the learned default.
    _maybe_learn_meal_time(saved)
    # Session history: record this turn so the NEXT negotiate sees it (the bounded conversation
    # June asked for — separate stream from capture). Best-effort; never break a renegotiation.
    try:
        session_store.append_entry("negotiate", {
            "intent": "negotiate",
            "raw_input": message,
            "result_summary": (saved.get("woven_frame") or "")[:200],
        })
    except Exception:
        pass
    return saved


def _maybe_learn_meal_time(plan):
    """If the new plan places Lunch at a time, nudge the learned meal default toward it.

    Best-effort + fails silently into the log: a meal-learning hiccup must never break a
    renegotiation. Parses the start time out of the item's 'time' string (e.g. '12:30 PM').
    """
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            if "lunch" in (item.get("task") or "").lower():
                t = _parse_first_time(item.get("time", ""))
                if t:
                    try:
                        dp.update_meal_learned_time("lunch", t.hour, t.minute)
                    except Exception:
                        pass
                return


def _parse_first_time(time_str):
    """Pull the first clock time out of a '9:00 – 10:30 AM' style string. None if absent."""
    m = re.search(r"(\d{1,2}):(\d{2})\s*([AaPp][Mm])?", time_str)
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2))
    ampm = (m.group(3) or "").lower()
    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    return dt.time(hour, minute)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Generate / renegotiate the daily plan (headless)")
    ap.add_argument("--capacity", default=None, help="optional ambient capacity signal")
    ap.add_argument("--reorder", default=None, help="a reorder/renegotiation message (freetext)")
    ap.add_argument("--dry-context", action="store_true",
                    help="just print the assembled context, no LLM call (cheap check)")
    args = ap.parse_args()

    if args.dry_context:
        ctx, tasks, st, _shape = build_context(capacity=args.capacity)
        print(ctx)
        print(f"\n[{len(tasks)} tasks would be logged as surfaced]")
    elif args.reorder:
        saved = reorder(args.reorder, kind="freetext")
        print(json.dumps(saved, indent=2))
    else:
        saved = generate_plan(capacity=args.capacity)
        print(json.dumps(saved, indent=2))

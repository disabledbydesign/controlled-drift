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
import sys, os, json, re, subprocess, datetime as dt

sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import daily_plan as dp
from surface_log import log_surfaced_batch
from plan_corrections_log import log_correction
import plan_store
import cd_paths

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "daily_list.md")
GEN_TIMEOUT = 240  # seconds; a generation that hangs longer is a failure, not a wait


# --- the pluggable LLM seam -------------------------------------------------

def generate(prompt, backend=None):
    """Run one LLM generation. Returns raw model text. Raises on failure (never silent)."""
    backend = backend or os.environ.get("CD_BACKEND", "claude")
    if backend == "claude":
        return _generate_claude(prompt)
    if backend == "local":
        return _generate_local(prompt)
    raise ValueError(f"unknown CD_BACKEND {backend!r} (expected 'claude' or 'local')")


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
        raise RuntimeError("mlx_lm not installed — `pip install mlx-lm`, or use CD_BACKEND=claude")
    model_name = os.environ.get("CD_LOCAL_MODEL", "mlx-community/Qwen2.5-7B-Instruct-4bit")
    model, tokenizer = load(model_name)
    messages = [{"role": "user", "content": prompt}]
    formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return mlx_generate(model, tokenizer, prompt=formatted, max_tokens=2048, verbose=False)


# --- the JSON-output contract (appended to the daily_list.md prompt) ---------

_JSON_INSTRUCTION = """

---

## HOW THIS RUNS — read before producing output

You are generating this plan **headless and automated** — there is **no human in the
conversation to answer you.** Your output is written straight to a cache the overlay
displays. Therefore:

- **Do NOT ask questions, offer choices, or propose to wait.** There is no one to reply.
- **Always produce a plan and the JSON block below**, even with imperfect inputs (no
  capacity signal, an awkward hour, a long task list). Make reasonable assumptions.
- If it is **late at night** or the day's hours are mostly gone, do NOT schedule tasks
  past midnight or pretend a full day remains. Instead produce a short, gentle plan for
  the time that's actually left — a wind-down, the one small thing worth closing on, or an
  honest "rest now; here's the shape for tomorrow." Honesty lives **in the plan's content**
  (a calm minimal plan is valid), not in refusing to produce one.
- June still negotiates later via buttons; this is her starting point, not a contract.

## REQUIRED OVERLAY OUTPUT

After the prose plan above, emit a single fenced ```json code block — and nothing after
it — containing the SAME plan as structured data the overlay renders. This block is
mandatory. Use exactly this shape (keep clock times verbatim from the schedule; `project`
is null for items with no project like Lunch; `why` is the short upward-link phrase,
omit/null if none):

```json
{
  "woven_frame": "the 2-3 sentence woven frame, as plain prose",
  "blocks": [
    {
      "label": "Morning",
      "time": "9:00 AM – 12:00 PM",
      "framing": "the 1-2 sentence block framing",
      "items": [
        {"time": "9:00 – 10:30 AM", "project": "Project/thread name", "task": "the specific next action", "why": "short why-here phrase"}
      ]
    }
  ],
  "still_here": [
    {"label": "thread or item name", "note": "the concrete reassurance — its rhythm / why deferred"}
  ]
}
```

The JSON must be faithful to the prose plan — same items, same times, same order. This
block is what June actually sees; the prose is for the chat flow.
"""


# --- context assembly (reuses daily_plan, minus the interactive input/print) -

def build_context(capacity=None, start_time=None):
    """Load active items + compute the clock schedule, returning the full prompt context.

    Mirrors daily_plan.run() but with NO blocking input() and NO printing: capacity is
    ambient (passed in or None), never a front-door gate (SYNTHESIS: offer, don't gate).
    Returns (full_context_str, tasks) — tasks is handed back so the caller can log what
    surfaced for the neglect/rhythm learning loop.
    """
    sid = g.get_space_id()
    goals, projects, tasks, strategies, today_recurrings = dp.load_active_items(sid)
    neglected = dp.load_neglected()

    start_time = start_time or dp._round_to_5(dt.datetime.now())
    meals = dp.default_meal_anchors(today_recurrings, start_time)
    all_anchors = today_recurrings + meals
    task_items = [{"name": t["name"], "duration_min": t.get("duration_min")} for t in tasks]
    scheduled = dp.build_schedule(task_items, all_anchors, start_time)
    schedule_block = dp.format_schedule_blocks(scheduled)

    context_block = dp.format_context(
        goals, projects, tasks, strategies, today_recurrings, neglected, capacity)
    full_context = context_block + "\n" + schedule_block
    return full_context, tasks, start_time


def _assemble_prompt(full_context, start_time, capacity=None, extra=None):
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
        "### Active goals / projects / tasks / strategies + the pre-computed clock schedule",
        "",
        full_context,
    ]
    if extra:
        parts += ["", "## JUNE'S REQUEST FOR THIS PLAN", "", extra]
    prompt = "\n".join(parts)
    prompt += _JSON_INSTRUCTION
    return prompt


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
    plan.setdefault("blocks", [])
    plan.setdefault("still_here", [])
    return plan


# --- the two public entry points --------------------------------------------

def generate_plan(capacity=None, source="generate"):
    """Fresh generation (morning push / refresh). Writes cache, logs what surfaced."""
    full_context, tasks, start_time = build_context(capacity=capacity)
    prompt = _assemble_prompt(full_context, start_time, capacity=capacity)
    model_text = generate(prompt)
    plan = parse_plan(model_text)
    saved = plan_store.save_plan(plan, source=source)
    # Learning loop: every generation records what surfaced (neglect/rhythm history).
    if tasks:
        log_surfaced_batch([{"id": t["id"], "name": t["name"], "type": "task"} for t in tasks])
    return saved


def negotiate(message, kind):
    """Renegotiate the current plan from June's request (a preset payload or freetext).

    `kind` labels the correction for the learning log: 'preset:<id>' or 'freetext'.
    Logs the before/after plan so the rhythm + duration loops have the delta. Also
    re-surfaces (the renegotiated plan is what she's now working from).
    """
    before = plan_store.load_plan()
    full_context, tasks, start_time = build_context()
    prompt = _assemble_prompt(full_context, start_time, extra=message)
    model_text = generate(prompt)
    plan = parse_plan(model_text)
    saved = plan_store.save_plan(plan, source=kind)

    # Learning loop #1: the correction itself (the richest signal — live negotiation).
    log_correction(kind, before=before, after=saved)
    # Learning loop #2: what surfaced in the renegotiated plan.
    if tasks:
        log_surfaced_batch([{"id": t["id"], "name": t["name"], "type": "task"} for t in tasks])
    # Learning loop #3 (meal timing): if Lunch moved, nudge the learned default.
    _maybe_learn_meal_time(saved)
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
    ap.add_argument("--negotiate", default=None, help="a renegotiation message (freetext)")
    ap.add_argument("--dry-context", action="store_true",
                    help="just print the assembled context, no LLM call (cheap check)")
    args = ap.parse_args()

    if args.dry_context:
        ctx, tasks, st = build_context(capacity=args.capacity)
        print(ctx)
        print(f"\n[{len(tasks)} tasks would be logged as surfaced]")
    elif args.negotiate:
        saved = negotiate(args.negotiate, kind="freetext")
        print(json.dumps(saved, indent=2))
    else:
        saved = generate_plan(capacity=args.capacity)
        print(json.dumps(saved, indent=2))

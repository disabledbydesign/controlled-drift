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


def build_prompt(capacity=None, extra=None):
    """Build the full generation prompt. Public for the compare script and manual testing."""
    full_context, tasks, start_time = build_context(capacity=capacity)
    ref_map, task_table = _build_task_refs(tasks)
    prompt = _assemble_prompt(full_context, start_time, capacity=capacity,
                              extra=extra, task_table=task_table)
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
Use exactly this shape (keep clock times verbatim from the schedule; `project`
is null for items with no project like Lunch; `why` is the short upward-link phrase,
omit/null if none; `ref` is the task-reference token — see TASK REFERENCE in the inputs —
for items that ARE one of the listed tasks, and null for non-task items like Lunch, breaks,
or household chores):

```json
{
  "woven_frame": "the 2-3 sentence woven frame, as plain prose",
  "blocks": [
    {
      "label": "Morning",
      "time": "9:00 AM – 12:00 PM",
      "framing": "the 1-2 sentence block framing",
      "items": [
        {"time": "9:00 – 10:30 AM", "project": "Project/thread name", "task": "the specific next action", "why": "short why-here phrase", "ref": "T1"}
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
                     history=None):
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
        parts += ["", "## JUNE'S REQUEST FOR THIS PLAN", "", extra]
    prompt = "\n".join(parts)
    prompt += _JSON_INSTRUCTION
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
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            ref = item.pop("ref", None)  # consume the token; the overlay only needs the id
            tid = ref_map.get(ref) if ref else None
            if not tid:
                tid = by_name.get(_norm(item.get("task")))
            if tid:
                item["id"] = tid
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
    plan.setdefault("blocks", [])
    plan.setdefault("still_here", [])
    return plan


# --- the two public entry points --------------------------------------------

def generate_plan(capacity=None, source="generate"):
    """Fresh generation (morning push / refresh). Writes cache, logs what surfaced."""
    full_context, tasks, start_time = build_context(capacity=capacity)
    ref_map, task_table = _build_task_refs(tasks)
    prompt = _assemble_prompt(full_context, start_time, capacity=capacity, task_table=task_table)
    backend = os.environ.get("CD_BACKEND", "mistral")
    model = _active_model(backend)
    backend_label = f"{backend}/{model}" if model else backend
    t0 = time.monotonic()
    try:
        model_text = generate(prompt)
        plan = parse_plan(model_text)
        _resolve_ids(plan, ref_map, tasks)
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
    ref_map, task_table = _build_task_refs(tasks)
    history = session_store.recent_entries("negotiate")
    prompt = _assemble_prompt(full_context, start_time, extra=message, task_table=task_table,
                              history=history)
    backend = os.environ.get("CD_BACKEND", "mistral")
    model = _active_model(backend)
    backend_label = f"{backend}/{model}" if model else backend
    t0 = time.monotonic()
    try:
        model_text = generate(prompt)
        plan = parse_plan(model_text)
        _resolve_ids(plan, ref_map, tasks)
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

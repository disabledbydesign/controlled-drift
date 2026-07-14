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


class ZeroRefPlanError(RuntimeError):
    """A generation whose plan items ALL resolved to no id — structurally unusable.

    Measured live 2026-07-11: the LLM sometimes ignores the ref-token contract and emits
    ref=None on every item (some runs, same prompt, resolve fine). A zero-ref plan LOOKS like
    a plan but every row carries no id, so mark-done, move, and held-back threading all
    silently fail — yet the current success path would cache it as a good plan. We treat that
    as a failure (not a plan), so the existing failure fallbacks fire: the morning push serves
    the labelled stale cache (which HAS working ids) rather than a dead plan, and the overlay
    refresh reports the failure per its contract. Distinct from a partial resolution (some refs
    missing is tolerated) — only the total-zero case is structural failure.
    """


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
    full_context, tasks, start_time, shape, _anchors, _end = build_context(capacity=capacity)
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
or household chores). One optional field — `user_set`: set `"user_set": true` on a meal item
(Lunch) ONLY when June explicitly asked to move it to a specific time this turn ("lunch at 2",
"push lunch later"). It tells the system to honor her time today and learn from it. Leave it off
on a normal day):

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

You compose this list: choose which candidate moves belong today and put them in the order that
serves June's Focus Period intent + her active Strategies + her capacity (you do NOT have to
include every candidate — deferring to still_here is expected, especially on a low day). Then
rewrite each item into plain language, add a grounded `why`, write a short warm woven frame, and a
one-line `header` naming what today's shape is and why.

## REQUIRED OUTPUT — THE JSON BLOCK ONLY

Output **ONLY** the single fenced ```json block — nothing before or after. Use exactly this shape:

- `header`: one plain sentence stating this is a fragmented day and how to use the list, e.g.
  "Today's fragmented — a short list to pull from, no fixed times. When a window opens, start at
  the top." No metaphors.
- each item's `task` is plain action language June can act on immediately (no codes, no ALL-CAPS,
  no jargon); `why` is one sentence grounded in her actual goal/project (what this produces or
  moves — never invented); `project` is the project/thread name or null; `ref` is the task's
  reference token from TASK REFERENCE (so she can mark it done), null if it isn't a listed task.
- keep the list SHORT; order it by your judgment (intent + strategies + capacity), most-fitting first.

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
    """Filter paused-project tasks and present the rest in a STABLE, foreground-first order for the
    LLM to compose from — this is NOT the final day order. Ordering + selection are the LLM's job
    (AI_LAYER_SPEC:69: "the LLM proposes ordering and content; Python places it in time"). The old
    date-seeded MD5 hash here WAS the drift (structural_diagnosis_2026-07-11:14, spec_reconciliation_
    selection_2026-07-11:5) — it shuffled the day deterministically-but-arbitrarily while the LLM was
    barred from re-sequencing, so an arbitrary order reached June dressed in prose. Now the order is
    just a calm, stable presentation (foreground first, then linked-before-discrete, then by name);
    the composer decides the real sequence from the Focus Period intent + Strategies + capacity."""
    fg = set((period or {}).get("foreground") or [])
    paused = set((period or {}).get("paused") or [])

    def _proj(t):
        projs = t.get("linked_projects") or []
        return projs[0] if projs else ""

    kept = [t for t in tasks if _proj(t) not in paused]

    def _key(t):
        proj = _proj(t)
        # foreground first; then linked-before-discrete; then a stable alphabetical tiebreak (NOT a
        # hash — the arbitrary daily shuffle was the drift). The LLM re-sequences from here.
        return (0 if proj in fg else 1, 1 if not proj else 0, proj.lower(), (t.get("name") or "").lower())

    return sorted(kept, key=_key)


def _match_extra(extra, projects, tasks):
    """When June explicitly asks ("put X in today"), find the project/task she named so the gate
    never hides or collapses it away. Errs toward INCLUSION: a missed paraphrase falls back to the
    normal gate, a false include just surfaces one extra real item — the safe direction. This is a
    lenient token overlap, not precise NLP; the model still gets `extra` and prioritizes among what
    is kept. Reconciled design: docs/spec_reconciliation_selection_2026-07-11.md (explicit-request
    override — an explicitly-named task must be a real move, never relegated to still_here)."""
    named = {"projects": set(), "task_ids": set()}
    if not extra:
        return named
    low = extra.lower()

    def hit(name):
        if not name:
            return False
        n = name.lower()
        return n in low or any(w in low for w in n.split() if len(w) >= 4)

    for p in projects:
        if hit(p.get("name")):
            named["projects"].add(p.get("name"))
    for t in tasks:
        if hit(t.get("name")):
            named["task_ids"].add(t.get("id"))
    return named


def _parse_date(raw):
    """Anytype date value -> a date, tolerantly. Accepts 'YYYY-MM-DD' and full ISO timestamps
    ('...T00:00:00Z', '...+00:00'). None/blank/unparseable -> None (never raises — a malformed
    date must not blind the pick, it just means 'no deadline signal here')."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        pass
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def _pick_within_thread(candidates, proj_deadline_raw, surface_dates):
    """Pick a thread's ONE surfaced item by the honest signal (reconciled selection model,
    docs/spec_reconciliation_selection_2026-07-11.md, item 4):

      1. nearest deadline first — effective deadline = the task's own Due date, else the
         project's Deadline (the thread's urgency floor). Any deadline outranks none.
      2. else least-recently-surfaced — oldest surface time first; a NEVER-surfaced task is
         maximally stale, so it sorts first.
      3. else the current stable order — `min` returns the first minimum, so a total tie falls
         back to exactly the given order. No hash.

    Pure + deterministic: `candidates` in their given order, `surface_dates` {id -> datetime}
    from the shared resolver, `proj_deadline_raw` the project's raw Deadline value (or None)."""
    proj_floor = _parse_date(proj_deadline_raw)

    def key(t):
        eff = _parse_date(t.get("due_date")) or proj_floor
        has_deadline = eff is not None
        deadline_key = eff if has_deadline else dt.date.max
        ls = surface_dates.get(t.get("id"))
        ls_key = ls if ls is not None else dt.datetime.min   # never surfaced = most stale = first
        return (0 if has_deadline else 1, deadline_key, ls_key)

    return min(candidates, key=key)


def _gate_and_collapse(tasks, projects, neglected, period, extra=None, surface_dates=None,
                       rollover_ids=None):
    """Engagement grain gate + one-next-move-per-thread (spec AI_LAYER_SPEC.md §2/§9; reconciled in
    docs/spec_reconciliation_selection_2026-07-11.md). Backburner/Open/unset are hidden unless the
    project is foregrounded (Focus Period) — and, for Backburner/unset only, unless neglected (Open
    is self-paced: never surfaced by neglect, only by foreground). Everything surfacing collapses to
    ONE next move per project-thread, PICKED by `_pick_within_thread` (nearest deadline, else
    least-recently-surfaced, else stable order) — not the storage-order accident. A task/project June
    named in `extra` is guaranteed through (task-named bypasses hide AND collapse; project-named is
    foregrounded, still one move). Held-back tasks are NOT dropped — they stay in Anytype, just not in
    today's plan; each surfaced item carries `held_back` (how many same-thread survivors are not shown)
    so the renderer can label 'next in X · N more'. No-project tasks are discrete actions: never
    collapsed together. `surface_dates` is injectable for pure testing; it defaults to the live log."""
    proj_eng = {p.get("name"): (p.get("engagement") or "unset") for p in projects}
    proj_deadline = {p.get("name"): p.get("deadline") for p in projects}
    fg = set((period or {}).get("foreground") or [])
    neg_names = {n.get("name") for n in (neglected or []) if isinstance(n, dict)}
    named = _match_extra(extra, projects, tasks)
    rollover_ids = set(rollover_ids or [])   # yesterday's undone: eligible so the model can carry them
    if surface_dates is None:
        from surface_log import surfaced_dates
        surface_dates = surfaced_dates()

    def proj_of(t):
        ps = t.get("linked_projects") or []
        return ps[0] if ps else ""

    def is_forced(t):
        # named-in-extra OR carried over from yesterday (undone): both bypass hide + collapse so the
        # task is a real, checkable candidate the model can choose to carry, not an invisible ghost row.
        return t.get("id") in named["task_ids"] or t.get("id") in rollover_ids

    # Pass 1 — the hide gate: which tasks survive to be considered at all.
    survivors = []
    for t in tasks:
        proj = proj_of(t)
        if not proj:
            # A task with NO linked project is a discrete standalone action (call the surgeon, go
            # for a walk, organize letters) — not a dormant project. Pass 2 already intends to keep
            # every no-project task ("discrete action — never collapsed"), but the old code hid them
            # HERE: proj_eng.get("", "unset") collided the empty-string project with the unset-
            # engagement default, so discrete tasks only ever surfaced once 16-days stale. They are
            # always eligible for the day. (June, 2026-07-13 — restoring the design's discrete
            # actions; the LLM composer decides how many actually fit today.)
            survivors.append(t)
            continue
        eng = proj_eng.get(proj, "unset")
        foregrounded = proj in fg or proj in named["projects"] or is_forced(t)
        if not foregrounded:
            if eng == "Open":
                continue                                   # available, self-paced: not pushed, not nagged
            if eng in ("Backburner", "unset") and proj not in neg_names:
                continue                                   # dormant: hidden unless neglected
        survivors.append(t)

    # Pick each real thread's ONE representative from its survivors, by the honest signal.
    by_thread = {}
    for t in survivors:
        proj = proj_of(t)
        if proj:
            by_thread.setdefault(proj, []).append(t)
    winner_id = {proj: _pick_within_thread(cands, proj_deadline.get(proj), surface_dates)["id"]
                 for proj, cands in by_thread.items()}

    # Pass 2 — collapse to one move per thread. A forced item (June-named OR carried over from
    # yesterday) ALWAYS passes and represents its thread, suppressing that thread's natural winner.
    # `forced_threads` is precomputed so the natural winner is suppressed even when it is iterated
    # BEFORE the forced task (survivors order isn't forced-first) — otherwise a forced task PLUS the
    # natural winner both survived: two moves for one thread. No-project (discrete) tasks never
    # collapse. (Several tasks that all match a loose `extra` can still co-surface — that is
    # _match_extra's breadth, not this collapse's job to trim.)
    forced_threads = {proj_of(t) for t in survivors if proj_of(t) and is_forced(t)}
    kept, seen_thread = [], set()
    for t in survivors:
        proj = proj_of(t)
        if not proj:
            kept.append(t)                                 # discrete action — never collapsed
            continue
        if is_forced(t):
            seen_thread.add(proj)
            kept.append(t)                                 # explicitly named / carried-over — always through
            continue
        if proj in seen_thread or proj in forced_threads:
            continue                                       # already shown, or a forced task represents this thread
        if t["id"] != winner_id[proj]:
            continue                                       # not the signal pick — its winner comes later
        seen_thread.add(proj)
        kept.append(t)

    # Annotate each surfaced task with its same-thread survivors that are held back (for the honest
    # 'N more' label + drill-down the renderer builds). `held_back` is the count (tests + the LLM
    # task-ref line depend on the int); `held_back_names` lists those not-shown items so the overlay
    # can reveal them on expand — held, not dropped. Discrete/no-project tasks: 0 / [].
    shown_ids_by_thread = {}
    for t in kept:
        proj = proj_of(t)
        if proj:
            shown_ids_by_thread.setdefault(proj, set()).add(t["id"])
    for t in kept:
        proj = proj_of(t)
        if not proj:
            t["held_back"], t["held_back_names"] = 0, []
            continue
        shown_ids = shown_ids_by_thread.get(proj, set())
        held = [c["name"] for c in by_thread.get(proj, []) if c["id"] not in shown_ids]
        t["held_back"], t["held_back_names"] = len(held), held
    return kept


def build_context(capacity=None, start_time=None, end_time=None, extra=None):
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
    import plan_snapshot_log
    undone_yest = plan_snapshot_log.undone_yesterday()   # rollover candidates: yesterday's uncompleted
    rollover_ids = {u["id"] for u in undone_yest}
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
    # are dropped. With no period this is a calm, stable foreground-first order (no hash — the
    # old date-seeded shuffle was the drift; the LLM re-sequences from here).
    ordered = select_and_order_tasks(tasks, period)
    # "Fun / hobby"-side (self-directed creative/dev) tasks are kept OUT of the daily plan by
    # default (June, 2026-07-11) so they don't crowd out Obligation + Wellbeing work; necessary
    # rest still stays. June toggles this from the overlay Settings panel (dp.include_hobby_block
    # reads settings.json). NB: `wellbeing` var below = the held-out Fun/hobby list (legacy name).
    schedulable, wellbeing = dp.partition_by_side(ordered, projects)
    # Engagement grain gate + one-next-move-per-thread (reconciled selection model 2026-07-11,
    # docs/spec_reconciliation_selection_2026-07-11.md): honor engagement DETERMINISTICALLY (not
    # just as an LLM hint) so the plan is a handful of real next-moves, not the whole pile. The
    # held-back tasks stay in Anytype — this only changes what today's plan shows.
    from surface_log import surfaced_dates
    schedulable = _gate_and_collapse(schedulable, projects, neglected, period, extra=extra,
                                     surface_dates=surfaced_dates(), rollover_ids=rollover_ids)

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
    if undone_yest:
        roll = ("\n\n## Carried over from yesterday (not marked done)\n"
                "These were on yesterday's plan and weren't completed. Decide which GENUINELY should "
                "carry into today — a missed call, an errand that still needs doing — and place those. "
                "Let go the ones that were fine to skip; not everything should roll forward.\n")
        for u in undone_yest:
            roll += f"  - {u['name']}\n"
        context_block += roll
    full_context = context_block + "\n" + schedule_block
    # Return schedulable (not all tasks): wellbeing work is the open block, so it isn't
    # individually accounted / surfaced / ref-tokened downstream (never-pick-her-threads).
    # all_anchors + end_time are handed back so the post-generation re-time pass (_retime_clock_plan)
    # can place the LLM's COMPOSED order in time using the same fixed anchors the suggestion used.
    return full_context, schedulable, start_time, shape, all_anchors, end_time


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
        # Each item is its thread's ONE next move (nearest-due / longest-quiet), picked in the
        # gate. Surface the held-back count so the plan can honestly say "next in X · N more".
        held = t.get("held_back") or 0
        suffix = f"  · {held} more in this thread" if held > 0 else ""
        lines.append(f"  {token} — {t['name']}{suffix}")
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
    """Thread the real Anytype task id onto each plan item, in place. Returns
    (mislabel_count, resolved_count):

      mislabel_count how many resolved items the model had labelled with materially different
                     text than the real (id-resolved) task name — the identity-drift measure.
      resolved_count how many plan items resolved to a real task id at all. This is the
                     resolution-health signal generate_plan reads: a plan where the gated task
                     set is non-empty but resolved_count is ZERO is structurally broken (every
                     row is unactionable), so generate_plan retries/fails on it instead of
                     caching a dead plan. A partial resolution (some > 0) is valid.

    Primary path: the model echoed a `ref` token -> map it back through ref_map.
    Fallback: no/unknown token, but the item's task text matches a real task name exactly
    (normalized) -> use that id. This is deliberately STRICT (exact normalized equality, not
    substring) — a loose match risks marking the WRONG task done, the one error worse than
    no id at all. No match -> the item simply carries no id and shows no done-affordance.

    Identity fields follow the id, not the model's free text: once a ref resolves, the item's
    displayed `task` (and `project`, if the resolved task carries one) is OVERWRITTEN with the
    resolved task's REAL name. The id is what actions key on (mark-done + move chips read
    item["id"] — verified nothing downstream string-matches item["task"]), so a row that READS
    "Check rivets / Leatherworking" but whose id resolves to "Open decision: finish a manuscript"
    (observed live 2026-07-11) would complete a task June never read. That is the one failure this
    surface cannot afford. Overwriting with the full canonical name is correct even when the model
    legitimately shortened it for display — identity beats brevity, and the overlay truncates
    gracefully. Non-task items (Lunch, breaks — ref null, no name match) keep their model text.
    """
    by_name = {_norm(t["name"]): t["id"] for t in tasks}
    context_by_id = {t["id"]: (t.get("context") or "").strip() for t in tasks}
    # Python-owned identity fields, keyed by real id: the canonical task name, and the task's
    # project (first linked project, if any). The overwrite below reads from these.
    name_by_id = {t["id"]: t["name"] for t in tasks}
    proj_by_id = {t["id"]: (t.get("linked_projects") or [None])[0] for t in tasks}
    # Per-thread held-back data (count + names of this thread's not-today items), keyed by the
    # shown task's id. Python owns this map — the LLM only echoes a ref token, never the count —
    # so the honest 'N more' reaches the cached plan JSON without the model rebuilding the pile.
    held_by_id = {t["id"]: (t.get("held_back") or 0) for t in tasks}
    held_names_by_id = {t["id"]: (t.get("held_back_names") or []) for t in tasks}
    mislabels = 0  # resolved items whose model text differed materially from the real name
    resolved = 0   # items that resolved to a real task id (the resolution-health signal)

    def _resolve_item(item):
        nonlocal mislabels, resolved
        ref = item.pop("ref", None)  # consume the token; the overlay only needs the id
        tid = ref_map.get(ref) if ref else None
        if not tid:
            tid = by_name.get(_norm(item.get("task")))
        if tid:
            item["id"] = tid
            resolved += 1
            # Identity fields win over the model's free text now that the id is known. Compare
            # first (normalized) so the drift is measurable — a fallback name match is text-equal
            # by construction and never counts; a real relabel (the trust bug) does.
            real_name = name_by_id.get(tid)
            if real_name:
                if _norm(item.get("task")) != _norm(real_name):
                    mislabels += 1
                item["task"] = real_name
            real_proj = proj_by_id.get(tid)
            if real_proj:
                item["project"] = real_proj
            # Carry the task's stored description (its Context field) onto the item so the
            # overlay can show it on expand. Empty for most tasks until the weed writes one;
            # the overlay only renders the slot when there's text.
            desc = context_by_id.get(tid)
            if desc:
                item["description"] = desc
            # Carry this thread's held-back count + names so the row can label '· N more' and
            # reveal the held items on expand. Only when >0 — a thread with nothing held stays clean.
            held = held_by_id.get(tid, 0)
            if held > 0:
                item["held_back"] = held
                item["held_back_names"] = held_names_by_id.get(tid, [])

    for block in plan.get("blocks", []):        # clock shape
        for item in block.get("items", []):
            _resolve_item(item)
    for item in plan.get("items", []):          # priority shape (flat)
        _resolve_item(item)
    return mislabels, resolved


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


def _retime_clock_plan(plan, tasks, all_anchors, start_time, end_time):
    """Python places the LLM's COMPOSED order in time — the '...Python places it in time
    (determinism)' half of AI_LAYER_SPEC:69, applied AFTER the model composes selection + order.

    Restores the design the build drifted from (structural_diagnosis_2026-07-11): the LLM now owns
    WHICH tasks and IN WHAT ORDER; this pass owns only the clock arithmetic. It reads the model's
    chosen real-task items in the order it wrote them, DROPS the model's echoed anchors/breaks
    (Python re-adds the authoritative meals/appointments/recurring + breaks, at their real fixed
    times, via build_schedule), reruns build_schedule, and rebuilds plan['blocks'] with the true
    times. A task the model deferred simply isn't here — it never gets scheduled, and
    _ensure_all_tasks_accounted has already parked it in still_here. Ends by re-running that
    accounting on the rebuilt blocks: this pass runs AFTER the caller's accounting, so anything
    IT can't place (end_time overflow) must be parked here or it vanishes silently. No-op for
    the priority shape (no clock). Mutates + returns plan."""
    if plan.get("shape") != "clock":
        return plan
    import daily_plan as dp

    _honor_user_meal(plan, all_anchors)   # honor + learn a meal time June set this turn, before placement

    def _match_key(s):
        # Strip parentheticals the model tends to echo ("(~30min)", "(was 09:00)", "(virtual)")
        # so an anchor matches its echo despite decoration; normalize the rest.
        return _norm(re.sub(r"\([^)]*\)", "", s or ""))

    anchor_keys = {k for k in (_match_key(a.get("name")) for a in (all_anchors or [])) if k}

    def _is_anchor_echo(name):
        # Python re-adds every authoritative anchor (meal/appt/recurring) at its real fixed time,
        # so any item the model echoed for one must be dropped — else it double-books (Lunch twice,
        # "Attend X" beside "X"). Match by substring either direction after stripping decoration,
        # because the model renames anchors freely ("Attend SF LGBT…" vs "SF LGBT…").
        k = _match_key(name)
        if not k:
            return False
        return any(k == a or a in k or k in a for a in anchor_keys)

    dur_by_id = {t["id"]: t.get("duration_min") for t in tasks}
    composed = []
    for block in plan.get("blocks", []):
        for it in block.get("items", []):
            name = it.get("task") or it.get("name") or ""
            # JSON rule 3 tells the model to flag ≤15-min REAL tasks interstitial too ("Bring
            # quilt in"), so the flag alone doesn't mean "Python-owned break": only an id-LESS
            # interstitial is the model's own break/filler. An id-carrying one is a captured
            # task — dropping it was the live 2026-07-13 silent-drop (quilt/kitchen/drive-to-SF).
            if it.get("interstitial") and not it.get("id"):
                continue                       # a model-written break — Python recomputes breaks
            # An echo can only be an id-LESS item: a real composed task always resolved to an id via
            # its ref token, while an echoed anchor (Lunch/appt/chore) is ref:null → id-less. Guarding
            # on `id` means the substring match can never silently drop a real task that merely happens
            # to contain an anchor word ("lunch meeting" keeps its id, so it stays).
            if not it.get("id") and _is_anchor_echo(name):
                continue                       # a model-echoed meal/appt/chore — Python re-adds it
            fi = dict(it)                       # carry task/project/why/id/held_back/description through
            fi["name"] = name                   # build_schedule keys on 'name'
            fi["duration_min"] = dur_by_id.get(it.get("id")) or it.get("duration_min")
            fi["_composed"] = True              # tags real items so blocks_from_scheduled can tell them from anchors
            composed.append(fi)
    framing_by_label = {b.get("label"): b.get("framing", "") for b in plan.get("blocks", [])}
    scheduled = dp.build_schedule(composed, all_anchors, start_time, end_time=end_time)
    plan["blocks"] = dp.blocks_from_scheduled(scheduled, framing_by_label)
    # Re-run the accounting net on the REBUILT blocks. build_schedule stops placing flexible
    # items at end_time (an evening run can place NONE), so the rebuilt blocks can hold fewer
    # tasks than the caller's accounting pass saw — and a drop here, after that pass, is
    # exactly the silent vanish the net exists to catch (live 2026-07-13: three real tasks
    # lost from the cached plan). Whatever couldn't be placed lands in still_here instead.
    _ensure_all_tasks_accounted(plan, tasks)
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
    full_context, tasks, start_time, shape, all_anchors, end_time = build_context(capacity=capacity, extra=extra)
    ref_map, task_table = _build_task_refs(tasks)
    prompt = _assemble_prompt(full_context, start_time, capacity=capacity, task_table=task_table,
                              extra=extra, request_kind="generate", shape=shape)
    backend = os.environ.get("CD_BACKEND", "mistral")
    model = _active_model(backend)
    backend_label = f"{backend}/{model}" if model else backend

    # Validity guard (measured live 2026-07-11): if the gated task set is non-empty but ZERO
    # plan items resolve to a real id, the generation is a structural failure, not a plan — every
    # row would be unactionable (no mark-done / move / held-back threading). Retry the LLM once
    # (the fault is intermittent: same prompt, some runs resolve fine), and if the retry is also
    # zero-ref, fail honestly so the caller's fallback fires (morning push -> labelled stale cache
    # with working ids; /api/refresh -> its failure contract) rather than caching a dead plan.
    plan = None
    mislabels = 0
    for attempt in range(1, 3):  # one try + one retry on a zero-ref plan
        t0 = time.monotonic()
        try:
            model_text = generate(prompt)
            plan = parse_plan(model_text)
            mislabels, resolved = _resolve_ids(plan, ref_map, tasks)
            _ensure_all_tasks_accounted(plan, tasks)
        except Exception as e:
            generation_log.log_generation(
                backend=backend_label, duration_s=time.monotonic() - t0,
                success=False, source=source,
                error_type=type(e).__name__, error_msg=str(e),
            )
            raise
        # Only items that CLAIM to be focused work count against resolution health. A plan
        # whose blocks hold nothing but interstitials (breaks, meals) with every gated task
        # honestly in still_here is a legitimate light-day shape — a late evening, or a
        # gentle low-spoon day — not a structural failure (observed live 2026-07-12: the
        # first guard version failed 5/5 evening regenerations for exactly this reason).
        claimed = sum(1 for b in plan.get("blocks", []) for it in b.get("items", [])
                      if not it.get("interstitial"))
        claimed += sum(1 for it in plan.get("items", []) if not it.get("interstitial"))
        if tasks and claimed > 0 and resolved == 0:
            # Zero-ref plan: log the distinct fragility event (keeps it measurable) and retry once;
            # a second zero-ref plan is a real failure, raised so the failure paths fire.
            generation_log.log_generation(
                backend=backend_label, duration_s=time.monotonic() - t0,
                success=False, source=source, error_type="zero_ref_plan",
                error_msg=f"0 plan items resolved to a task id "
                          f"(input had {len(tasks)} gated tasks; attempt {attempt}/2)",
            )
            if attempt < 2:
                continue
            raise ZeroRefPlanError(
                f"plan generation resolved zero of {len(tasks)} gated tasks to ids across 2 attempts")
        break  # a valid plan (some refs resolved, or no gated tasks to resolve)
    # The plan is valid — now Python places the LLM's COMPOSED order in time (AI_LAYER_SPEC:69).
    # Done AFTER the zero-ref guard so the guard reads the model's own interstitial flags (anchors
    # re-added here as non-interstitial rows must not be miscounted as claimed focused work), and
    # BEFORE check_plan/save so the logged + cached blocks carry the authoritative clock times.
    _retime_clock_plan(plan, tasks, all_anchors, start_time, end_time)
    generation_log.log_generation(
        backend=backend_label, duration_s=time.monotonic() - t0,
        success=True, source=source,
        structural=generation_log.check_plan(plan, n_input_tasks=len(tasks),
                                             mislabel_count=mislabels),
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
    # Rollover observability (its own tag): which of yesterday's undone items the model carried into
    # today vs let go — so June can watch how well the LLM judges carry-over before we add manual marks.
    try:
        import rollover_log
        rollover_log.log_rollover(saved)
    except Exception as e:
        print(f"[warn] rollover not logged: {e}", file=sys.stderr)
    # Spec §10 promise: keep the confirmed plan human-readable when the AI layer is down. Mirror
    # it into ONE Anytype object (updated in place, no per-day accumulation — June's decision).
    # BEST-EFFORT: a mirror failure (Anytype closed, API down) must never break or delay a
    # generation, so this runs AFTER the cache write and swallows any error. This is the single
    # seam both the morning push and /api/refresh reach (both call generate_plan), so one call
    # here mirrors both — and it sits after the zero-ref raise, so only VALID plans are mirrored.
    try:
        import plan_mirror
        plan_mirror.mirror_plan_safe(saved)
    except Exception as e:
        print(f"[warn] plan mirror skipped: {e}", file=sys.stderr)  # never break a generation
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
    full_context, tasks, start_time, shape, all_anchors, end_time = build_context(extra=message)
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
        mislabels, _resolved = _resolve_ids(plan, ref_map, tasks)
        _ensure_all_tasks_accounted(plan, tasks)
        # Python re-times June's newly composed order (AI_LAYER_SPEC:69), same as generate_plan.
        _retime_clock_plan(plan, tasks, all_anchors, start_time, end_time)
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
        structural=generation_log.check_plan(plan, n_input_tasks=len(tasks),
                                             mislabel_count=mislabels),
    )
    saved = plan_store.save_plan(plan, source=kind)

    # Snapshot the RENEGOTIATED plan too (not just fresh generations). Without this, undone_yesterday
    # reads the morning snapshot and re-surfaces a task June explicitly dropped in a chat renegotiation
    # — the exact "don't force back what she let go" the rollover design promises. Best-effort.
    try:
        import plan_snapshot_log
        plan_snapshot_log.log_plan_snapshot(saved, source=kind)
    except Exception as e:
        print(f"[warn] plan snapshot not written: {e}", file=sys.stderr)
    try:
        import rollover_log
        rollover_log.log_rollover(saved)
    except Exception as e:
        print(f"[warn] rollover not logged: {e}", file=sys.stderr)

    # Learning loop #1: the correction itself (the richest signal — live negotiation).
    log_correction(kind, before=before, after=saved)
    # Learning loop #2: what surfaced in the renegotiated plan.
    if tasks:
        log_surfaced_batch([{"id": t["id"], "name": t["name"], "type": "task"} for t in tasks])
    # Learning loop #3 (meal timing) now lives inside _retime_clock_plan via _honor_user_meal:
    # when June explicitly moves a meal this turn (model marks it user_set), Python honors her
    # time AND nudges the learned default toward it. Driven by her real placement — not the old
    # closed loop that read Python's own re-placed anchor back to itself (drifted noon -> 12:45).
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


def _honor_user_meal(plan, all_anchors):
    """Honor a meal time June explicitly set this turn, and learn from it — the REAL signal.

    When June moves a meal in a renegotiation ("lunch at 2"), the model places it there and marks
    the item user_set:true (daily_list.md). Python then (a) points the meal ANCHOR at her time so
    today's plan honors it exactly rather than the stored default, and (b) nudges the learned
    default toward it via the 80/20 EMA. This replaces the old loop that read Lunch's time out of
    Python's OWN re-placed anchor and nudged toward itself (drift with no real input from June).

    Best-effort: a meal-learning hiccup must never break a (re)generation.
    """
    import daily_plan as dp
    for block in plan.get("blocks", []):
        for it in block.get("items", []):
            nm = (it.get("task") or it.get("name") or "")
            if not it.get("user_set") or "lunch" not in nm.lower():
                continue
            t = _parse_first_time(it.get("time", ""))
            if not t:
                return
            # (a) point the Lunch anchor at her time so build_schedule places it there today
            for a in (all_anchors or []):
                if "lunch" in (a.get("name") or "").lower() and a.get("fixed_time"):
                    a["fixed_time"] = a["fixed_time"].replace(hour=t.hour, minute=t.minute)
            # (b) nudge the learned default toward her real placement
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
        ctx, tasks, st, _shape, _anchors, _end = build_context(capacity=args.capacity)
        print(ctx)
        print(f"\n[{len(tasks)} tasks would be logged as surfaced]")
    elif args.reorder:
        saved = reorder(args.reorder, kind="freetext")
        print(json.dumps(saved, indent=2))
    else:
        saved = generate_plan(capacity=args.capacity)
        print(json.dumps(saved, indent=2))

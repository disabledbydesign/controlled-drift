#!/usr/bin/env python3
"""Capability comparison — stress-test backends on functions beyond daily plan generation.

Tests:
  renegotiate_quick_wins  — reorder existing plan for quick-wins momentum
  renegotiate_low_energy  — reframe for low capacity / crip-time
  stuck                   — stuck-support: one concrete 5-min step, no questions
  weed                    — weeding gate on a synthetic brain-dump

What to look for (function-specific):

  Renegotiation:
  - Does it explain WHY the new order works? (ordering rationale is load-bearing)
  - Does it hold recurring/household items through the reorder?
  - Does it maintain the time-block structure, or collapse to a list?
  - Low-energy: does it treat rest as valid, or frame as "slimmed-down productivity"?

  Stuck:
  - Does it give ONE step, not a list?
  - Is the step specific to June's actual context, or generic?
  - Does it avoid asking questions? ("Don't ask me to decide anything" is in the prompt)
  - Does it acknowledge the stuckness, or skip straight to advice?

  Weeding:
  - Does the opening sentence name a specific through-line, or give generic encouragement?
  - Are types routed inline within groups, not in a separate list?
  - Does it flag vague items as Needs Clarifying rather than forcing a type?
  - Does it check for existing items before proposing new ones?
  - Does it catch the potential recurring and the strategy-shaped item?
  - Is the SSRC/surgeon flagged with appropriate care (time-sensitive signals)?

  Strategy application (visible in all plan-related tests):
  - Does the model apply the active Strategy "Work for a set time, then wrap up/stop"
    in the ordering framing — or just mention it in passing?

Usage:
  python3 scripts/compare_capabilities.py                       # all tests
  python3 scripts/compare_capabilities.py --tests stuck weed    # specific tests
  python3 scripts/compare_capabilities.py --out path/to/out.md
"""
import sys, os, json, datetime as dt, time

sys.path.insert(0, os.path.dirname(__file__))
import plan_generate as pg
import generation_log as gl
import gsdo_anytype as g
import daily_plan as dp

BACKENDS = [
    ("openrouter", "anthropic/claude-sonnet-4",         "Claude Sonnet 4"),
    ("mistral",    "mistral-small-latest",               "Mistral small"),
    ("mistral",    "mistral-large-latest",               "Mistral large"),
]

WEEDING_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "weeding_gate.md")

# --- synthetic brain-dump for the weeding test --------------------------------
# Calibrated to June's dump style: associative, through-line of avoidance, mixed types,
# one potentially urgent item (surgeon), one vague item, one strategy-shaped item.
SYNTHETIC_BRAIN_DUMP = """
I keep meaning to follow up with the SSRC contacts from the conference but I'm not sure if I
should wait until after I submit the application or just reach out now — and also I need to
actually write the needs statement paragraph, I've been avoiding it. The GRA session from
yesterday had a bunch of decisions I made verbally but didn't capture anywhere, I'll forget
them by tomorrow. I want to start doing a short daily check-in with myself, like 5 minutes,
just to know where I am before diving in — I've been starting cold and it's making everything
harder to start. The surgeon pre-op stuff — I need to call the office about the insurance
authorization, I think there's a deadline soon. I don't know what I want to do about
consulting, it's on my mind but I always push it off. The dishes, again. I've been thinking
about how to structure the daily plan differently — shorter, more breathing room — maybe that's
something to bring to the system, not just for today. Oh and I need to register for the CSS
conference before the early-bird deadline.
"""


# --- prompt builders ----------------------------------------------------------

def _load_alignment_context():
    """Load Goals + Projects + Tasks from Anytype for the weeding gate alignment step."""
    sid = g.get_space_id()
    goals, projects, tasks, strategies, _ = dp.load_active_items(sid)
    lines = ["## Existing Goals, Projects, and Tasks (for alignment and dedup)\n"]
    for goal in goals:
        lines.append(f"GOAL: {goal.get('name', '(unnamed)')}")
        rfor = goal.get("reaching_for", "")
        if rfor:
            lines.append(f"  Reaching for: {rfor}")
    lines.append("")
    for proj in projects:
        lines.append(f"PROJECT: {proj.get('name', '(unnamed)')} [{proj.get('engagement', '')}]")
        ctx = proj.get("context", "")
        if ctx:
            lines.append(f"  Context: {ctx[:100]}")
    lines.append("")
    for task in tasks[:30]:  # cap — the dedup context, not exhaustive
        lines.append(f"TASK: {task.get('name', '(unnamed)')} [{task.get('status', '')}]")
    return "\n".join(lines)


def build_weed_prompt():
    """Weeding gate prompt + alignment context + synthetic brain-dump."""
    with open(WEEDING_PROMPT_PATH) as f:
        template = f.read()
    alignment = _load_alignment_context()
    prompt = (
        template.replace("[June's brain-dump]", "")  # strip placeholder
        + "\n\n---\n\n## EXISTING SPACE CONTEXT (loaded from Anytype)\n\n"
        + alignment
        + "\n\n---\n\n## JUNE'S BRAIN-DUMP\n\n"
        + SYNTHETIC_BRAIN_DUMP.strip()
        + "\n\n---\n\n"
        + "Respond with the weeding output. Remember: read as a web first, find the "
        + "through-line, open with one specific observational sentence, then groups with "
        + "types woven in. No separate type-routing list. This is a validation surface — "
        + "proposals only, June confirms before anything is created."
    )
    return prompt


def build_stuck_prompt():
    """Stuck-support prompt: stopgap payload + current task context for specificity."""
    # Load minimal task context so the model can give a specific step, not a generic one
    sid = g.get_space_id()
    _, _, tasks, _, _ = dp.load_active_items(sid)
    task_lines = "\n".join(
        f"- {t.get('name', '(unnamed)')} [{t.get('project_name', '')}]"
        for t in tasks[:10]
    )
    return (
        "June is stuck and can't start. Her current open tasks include:\n\n"
        + task_lines
        + "\n\n"
        + "She says: I'm stuck and can't start. Offer one very small, concrete first step "
        + "I can take right now — something doable in five minutes. Hold everything else. "
        + "Don't ask me to decide anything.\n\n"
        + "Your response must:\n"
        + "- Name ONE step only — not a list\n"
        + "- Be specific to her actual tasks above, not generic advice\n"
        + "- Acknowledge the stuckness briefly (one sentence max)\n"
        + "- Not ask any questions\n"
        + "- Not give productivity tips or frame this as a system"
    )


def build_renegotiate_prompt(kind):
    """Renegotiation prompt: existing plan context + the preset instruction."""
    payloads = {
        "quick_wins": (
            "Reorder to lead with quick wins — shorter tasks I can finish fast to build "
            "momentum for the harder work later. Explain why this order works for today."
        ),
        "low_energy": (
            "Capacity is low today. Please reframe the plan: shorter sessions, lower-stakes "
            "tasks first, rest built in. Keep the time-block format. Re-explain the ordering "
            "logic for a low-energy day."
        ),
    }
    full_context, tasks, start_time = pg.build_context()
    ref_map, task_table = pg._build_task_refs(tasks)
    prompt = pg._assemble_prompt(
        full_context, start_time,
        extra=payloads[kind],
        task_table=task_table,
    )
    return prompt, tasks, ref_map


# --- running tests ------------------------------------------------------------

def run_test(name, prompt_fn, structural_fn=None, timeout=180):
    """Run one test across all backends. Returns list of result dicts."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)
    results = []
    for backend, model, label in BACKENDS:
        print(f"  → {label}...", end=" ", flush=True)
        t0 = time.monotonic()
        try:
            prompt = prompt_fn() if not isinstance(prompt_fn, str) else prompt_fn
            text = pg.generate(prompt, backend=backend, model=model)
            duration = time.monotonic() - t0
            structural = structural_fn(text) if structural_fn else {}
            print(f"{duration:.1f}s")
            results.append({
                "label": label, "backend": backend, "model": model,
                "duration_s": duration, "success": True,
                "output": text, "structural": structural,
            })
        except Exception as e:
            duration = time.monotonic() - t0
            print(f"{duration:.1f}s  FAILED: {e}")
            results.append({
                "label": label, "backend": backend, "model": model,
                "duration_s": duration, "success": False,
                "error": str(e), "output": None, "structural": {},
            })
    return results


def run_plan_renegotiate(kind, label_suffix):
    """Renegotiation: build prompt once, run all backends."""
    print(f"\n{'='*60}")
    print(f"TEST: renegotiate_{kind}")
    print('='*60)
    print("  Building prompt from Anytype...", flush=True)
    try:
        prompt, tasks, ref_map = build_renegotiate_prompt(kind)
    except Exception as e:
        print(f"  ERROR building prompt: {e}")
        return []
    results = []
    for backend, model, label in BACKENDS:
        print(f"  → {label}...", end=" ", flush=True)
        t0 = time.monotonic()
        try:
            text = pg.generate(prompt, backend=backend, model=model)
            duration = time.monotonic() - t0
            plan = pg.parse_plan(text)
            pg._resolve_ids(plan, ref_map, tasks)
            checks = gl.check_plan(plan, n_input_tasks=len(tasks))
            print(f"{duration:.1f}s  {_summarise(checks)}")
            results.append({
                "label": label, "backend": backend, "model": model,
                "duration_s": duration, "success": True,
                "plan": plan, "checks": checks,
            })
        except Exception as e:
            duration = time.monotonic() - t0
            print(f"{duration:.1f}s  FAILED: {e}")
            results.append({
                "label": label, "backend": backend, "model": model,
                "duration_s": duration, "success": False,
                "error": str(e), "plan": None, "checks": None,
            })
    return results


# --- rendering ----------------------------------------------------------------

def _summarise(checks):
    if not checks:
        return ""
    parts = [f"frame {checks.get('woven_frame_len',0)}ch",
             f"{checks.get('block_count',0)} blocks",
             f"{checks.get('item_count',0)} items"]
    sh = checks.get("still_here_count", 0)
    if sh:
        parts.append(f"{sh} still-here")
    n, r = checks.get("input_task_count"), checks.get("task_refs_resolved", 0)
    if n:
        parts.append(f"{r}/{n} refs")
    return " · ".join(parts)


def _render_plan_section(r):
    if not r["success"]:
        return f"**FAILED:** {r['error']}\n"
    plan = r["plan"]
    lines = []
    frame = (plan.get("woven_frame") or "").strip()
    if frame:
        lines.append(f"> {frame}\n")
    for block in plan.get("blocks", []):
        lines.append(f"### {block.get('label','')}  {block.get('time','')}")
        framing = (block.get("framing") or "").strip()
        if framing:
            lines.append(f"_{framing}_")
        lines.append("")
        for item in block.get("items", []):
            itime = item.get("time", "")
            proj  = item.get("project") or ""
            task  = item.get("task", "")
            why   = item.get("why") or ""
            tid   = item.get("id", "")
            prefix = f"- {itime} | " if itime else "- "
            proj_part = f"**{proj}**: " if proj else ""
            why_part = f"  ↑ _{why}_" if why else ""
            id_note = " `✓`" if tid else ""
            lines.append(f"{prefix}{proj_part}{task}{id_note}{why_part}")
        lines.append("")
    still_here = plan.get("still_here", [])
    if still_here:
        lines.append("### Still here")
        for sh in still_here:
            lines.append(f"- **{sh.get('label','')}** — {sh.get('note','')}")
        lines.append("")
    return "\n".join(lines)


def render_report(all_results, tests_run):
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# Capability Comparison — {now}", ""]
    lines += [
        "## What to look for",
        "",
        "**Renegotiation:** Does it explain WHY the new order works? Does it hold "
        "recurring/household items? Does it maintain time-block structure? "
        "Low-energy: does it treat rest as valid?",
        "",
        "**Stuck:** One step only, not a list. Specific to her actual context. "
        "No questions. Acknowledge the stuckness briefly.",
        "",
        "**Weeding:** Opening sentence names a specific through-line (not generic "
        "encouragement). Types woven inline, not a separate list. Vague items flagged "
        "Needs Clarifying. Surgeon/health item treated as potentially time-sensitive. "
        "Strategy-shaped item routed correctly.",
        "", "---", "",
    ]

    for test_name, results in zip(tests_run, all_results):
        lines.append(f"## {test_name.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Backend | Duration |")
        lines.append("|---|---|")
        for r in results:
            dur = f"{r['duration_s']:.1f}s"
            lines.append(f"| {r['label']} | {dur} |")
        lines.append("")

        for r in results:
            lines.append(f"### {r['label']}  ({r['duration_s']:.1f}s)")
            lines.append("")
            if test_name.startswith("renegotiate"):
                lines.append(_render_plan_section(r))
            else:
                if r["success"]:
                    lines.append(r["output"])
                else:
                    lines.append(f"**FAILED:** {r['error']}")
                lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


# --- main ---------------------------------------------------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Compare backend capabilities beyond plan generation")
    ap.add_argument("--tests", nargs="+",
                    choices=["renegotiate_quick_wins", "renegotiate_low_energy", "stuck", "weed"],
                    default=["renegotiate_quick_wins", "renegotiate_low_energy", "stuck", "weed"],
                    help="which tests to run (default: all)")
    ap.add_argument("--out", default=None,
                    help="output path (default: scripts/data/capabilities_<date>.md)")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    print("Loading Anytype context...", flush=True)
    try:
        g.get_space_id()
    except Exception as e:
        print(f"ERROR: can't reach Anytype — {e}")
        print("Is Anytype running?")
        sys.exit(1)

    all_results = []
    tests_run = []

    for test in args.tests:
        if test == "renegotiate_quick_wins":
            results = run_plan_renegotiate("quick_wins", "Quick Wins")
        elif test == "renegotiate_low_energy":
            results = run_plan_renegotiate("low_energy", "Low Energy")
        elif test == "stuck":
            print(f"\n{'='*60}\nTEST: stuck\n{'='*60}")
            print("  Building stuck prompt...", flush=True)
            prompt = build_stuck_prompt()
            results = run_test("stuck", prompt, timeout=args.timeout)
        elif test == "weed":
            print(f"\n{'='*60}\nTEST: weed\n{'='*60}")
            print("  Building weeding prompt + alignment context...", flush=True)
            try:
                prompt = build_weed_prompt()
            except Exception as e:
                print(f"  ERROR building weeding prompt: {e}")
                continue
            results = run_test("weed", prompt, timeout=args.timeout)

        if results:
            all_results.append(results)
            tests_run.append(test)

    if not all_results:
        print("No results — exiting.")
        sys.exit(1)

    report = render_report(all_results, tests_run)

    out_path = args.out
    if not out_path:
        date_str = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        out_path = os.path.join(data_dir, f"capabilities_{date_str}.md")

    with open(out_path, "w") as f:
        f.write(report)

    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()

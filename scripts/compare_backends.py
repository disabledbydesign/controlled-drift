#!/usr/bin/env python3
"""Backend quality comparison — run the real plan prompt through multiple providers,
print basic structural checks + the full readable plan for June to assess.

This is a read tool, not a scoring system. Structural checks say what's there;
June reads the rendered plans and decides what she actually thinks of the quality.

What to look for when reading each plan:
  - Woven frame: is it specific to your actual situation, or could it be for anyone?
  - Register: does it offer ("you could") or instruct/impose?
  - Ordering: does the sequence make sense for a real day?
  - "Still here": does it actually reassure, or just list?
  - Crip-time warmth: does it treat variable capacity as normal?

Usage:
  python3 scripts/compare_backends.py
  python3 scripts/compare_backends.py --out scripts/data/comparison.md
  python3 scripts/compare_backends.py --timeout 120

Backends tested:
  openrouter / anthropic/claude-sonnet-4   — quality baseline
  openrouter / meta-llama/llama-3.3-70b-instruct — free + open weights
  mistral / mistral-small-latest           — EU/GDPR, no-train, fastest
  mistral / mistral-large-latest           — EU/GDPR, no-train, higher capability

These providers are in June's acceptable privacy tier for plan data (Mistral: EU/GDPR/no-train;
OpenRouter: no-train policy). The prompt contains real task data.
"""
import sys, os, json, datetime as dt

sys.path.insert(0, os.path.dirname(__file__))
import plan_generate as pg
import generation_log as gl

BACKENDS = [
    ("openrouter", "anthropic/claude-sonnet-4",               "Claude Sonnet 4 via OpenRouter"),
    ("openrouter", "meta-llama/llama-3.3-70b-instruct",       "Llama 3.3 70B via OpenRouter (free)"),
    ("mistral",    "mistral-small-latest",                     "Mistral small (EU/GDPR, no-train)"),
    ("mistral",    "mistral-large-latest",                     "Mistral large (EU/GDPR, no-train)"),
]


def _render_plan(plan):
    """Render a parsed plan as readable markdown (not raw JSON)."""
    lines = []
    frame = (plan.get("woven_frame") or "").strip()
    if frame:
        lines.append(f"> {frame}\n")
    for block in plan.get("blocks", []):
        label = block.get("label", "")
        btime = block.get("time", "")
        framing = (block.get("framing") or "").strip()
        lines.append(f"### {label}  {btime}")
        if framing:
            lines.append(f"_{framing}_")
        lines.append("")
        for item in block.get("items", []):
            itime   = item.get("time", "")
            project = item.get("project") or ""
            task    = item.get("task", "")
            why     = item.get("why") or ""
            tid     = item.get("id", "")
            prefix  = f"- {itime} | " if itime else "- "
            proj_part = f"**{project}**: " if project else ""
            why_part  = f"  ↑ _{why}_" if why else ""
            id_note   = " `✓`" if tid else ""
            lines.append(f"{prefix}{proj_part}{task}{id_note}{why_part}")
        lines.append("")
    still_here = plan.get("still_here", [])
    if still_here:
        lines.append("### Still here")
        for sh in still_here:
            label = sh.get("label", "")
            note  = sh.get("note", "")
            lines.append(f"- **{label}** — {note}")
        lines.append("")
    return "\n".join(lines)


def _summarise(checks):
    """One-line summary of structural checks."""
    if not checks:
        return "(no checks — parse failed)"
    parts = []
    fl = checks.get("woven_frame_len", 0)
    parts.append(f"frame {fl}ch")
    parts.append(f"{checks.get('block_count', 0)} blocks")
    parts.append(f"{checks.get('item_count', 0)} items")
    sh = checks.get("still_here_count", 0)
    if sh:
        parts.append(f"{sh} still-here")
    n = checks.get("input_task_count")
    resolved = checks.get("task_refs_resolved", 0)
    if n is not None:
        parts.append(f"{resolved}/{n} refs resolved")
    return " · ".join(parts)


def run_comparison(timeout=None):
    """Build the prompt once, run all backends, return list of result dicts."""
    print("Loading task context from Anytype...", flush=True)
    try:
        prompt, tasks, ref_map = pg.build_prompt()
    except Exception as e:
        print(f"ERROR loading context: {e}")
        print("Is Anytype running? (open the app, then retry)")
        sys.exit(1)

    print(f"Prompt built ({len(prompt)} chars, {len(tasks)} tasks). Running {len(BACKENDS)} backends...\n")

    results = []
    for backend, model, label in BACKENDS:
        print(f"  → {label}...", end=" ", flush=True)
        import time
        t0 = time.monotonic()
        try:
            if timeout:
                old = pg.GEN_TIMEOUT
                pg.GEN_TIMEOUT = timeout
            text = pg.generate(prompt, backend=backend, model=model)
            if timeout:
                pg.GEN_TIMEOUT = old
            duration = time.monotonic() - t0
            plan = pg.parse_plan(text)
            pg._resolve_ids(plan, ref_map, tasks)
            checks = gl.check_plan(plan, n_input_tasks=len(tasks))
            print(f"{duration:.1f}s  {_summarise(checks)}")
            results.append({
                "backend": backend, "model": model, "label": label,
                "duration_s": duration, "success": True,
                "plan": plan, "checks": checks,
            })
        except Exception as e:
            duration = time.monotonic() - t0
            print(f"{duration:.1f}s  FAILED: {e}")
            results.append({
                "backend": backend, "model": model, "label": label,
                "duration_s": duration, "success": False,
                "error": str(e), "plan": None, "checks": None,
            })
    return results


def render_report(results):
    """Render the full comparison as a markdown string."""
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Backend Quality Comparison — {now}",
        "",
        "Read each plan below and note: is the woven frame specific to your actual situation?",
        "Does the register offer or impose? Does the ordering make sense for a real day?",
        "Does \"still here\" actually reassure?",
        "",
        "## Summary",
        "",
        "| Backend | Duration | Structural |",
        "|---|---|---|",
    ]
    for r in results:
        dur = f"{r['duration_s']:.1f}s"
        if r["success"]:
            struct = _summarise(r["checks"])
        else:
            struct = f"FAILED: {r['error'][:80]}"
        lines.append(f"| {r['label']} | {dur} | {struct} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        lines.append(f"## {r['label']}  ({r['duration_s']:.1f}s)")
        lines.append("")
        if not r["success"]:
            lines.append(f"**FAILED:** {r['error']}")
            lines.append("")
        else:
            lines.append(_render_plan(r["plan"]))
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Compare backend quality for the daily plan")
    ap.add_argument("--out", default=None,
                    help="write report to this file (default: scripts/data/comparison_<date>.md)")
    ap.add_argument("--timeout", type=int, default=None,
                    help="per-backend timeout in seconds (default: plan_generate.GEN_TIMEOUT)")
    args = ap.parse_args()

    results = run_comparison(timeout=args.timeout)
    report = render_report(results)

    out_path = args.out
    if not out_path:
        date_str = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        out_path = os.path.join(data_dir, f"comparison_{date_str}.md")

    with open(out_path, "w") as f:
        f.write(report)

    print(f"\nReport written to: {out_path}")
    print("Open it and read through the plans — the structural numbers above are just a first pass.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Backfill estimated, LABELED durations onto existing tasks that carry none.

Why: scheduler.py falls back to a flat DEFAULT_DURATION_MIN=30 for any task with no Duration min,
and today almost every task hits that fallback — so the daily plan treats a 2-hour study block and
a 5-minute call identically. This fills the silence: for each task with no duration, the model
estimates one (using June's stated priors + the task's project), and it's written labeled
'estimated' (Duration source) — never confused with a duration June herself stated, and never
overwriting one. Fidelity-first: a task that already has ANY Duration min is skipped entirely.

Flag discipline mirrors memory_pass.py / status_check.py exactly:
  python3 scripts/duration_backfill.py            dry-run: list sizeless tasks + counts, no LLM
  python3 scripts/duration_backfill.py --preview  LLM estimates, shows what --run would do, no writes
  python3 scripts/duration_backfill.py --run       the real backfill (writes, with read-back)

Idempotent by construction: only sizeless tasks are selected, so once --run gives a task a
duration it drops out of the next run's candidate set. Re-running --preview is side-effect-free.

Reuses, never reinvents: capture_fields (the shared duration seam + June's priors),
plan_generate.generate (the LLM seam), gsdo_objects.update (deterministic write, read-back
proven), generation_log (durable generation record).
"""
import sys, os, re, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import gsdo_objects
import plan_generate
import generation_log
import capture_fields
from anytype_test import call


def _pv(obj, key, field):
    for p in obj.get("properties", []):
        if p.get("key") == key:
            return p.get(field)
    return None


def _project_id_to_name(objs):
    return {o["id"]: o.get("name") for o in objs
            if o.get("type", {}).get("key") == "gsdo_project"}


def load_sizeless_tasks(sid=None):
    """Every Task with NO Duration min (stated or estimated). Skips already-sized tasks so the
    backfill only ever fills silence and re-runs are idempotent. Carries project names + Context
    so the estimator has the same context the capture path gets."""
    sid = sid or g.get_space_id()
    objs = g.fetch_all_objects(sid)
    p_id2name = _project_id_to_name(objs)
    out = []
    for o in objs:
        if o.get("type", {}).get("key") != "task":
            continue
        if _pv(o, "gsdo_duration_min", "number") is not None:
            continue  # already sized — never touch
        status = (_pv(o, "gsdo_task_status", "select") or {}).get("name")
        linked = _pv(o, "linked_projects", "objects") or []
        names = []
        for x in linked:
            pid = x.get("id") if isinstance(x, dict) else x
            nm = p_id2name.get(pid)
            if nm:
                names.append(nm)
        out.append({"id": o["id"], "name": o.get("name"), "status": status,
                    "duration_min": None, "project_names": names,
                    "context": _pv(o, "gsdo_context", "text")})
    return out


def build_prompt(tasks):
    lines = [
        "You are estimating how long each of June's existing tasks actually takes, in MINUTES.",
        "These tasks were captured with no duration, so her daily plan currently treats every one",
        "as a flat 30 minutes — wildly wrong. Give each an honest estimate.",
        "",
        "## DURATION PRIORS",
        "",
        capture_fields.DURATION_PRIORS,
        "",
        "## TASKS TO ESTIMATE",
        "",
    ]
    for t in tasks:
        proj = ", ".join(t["project_names"]) if t["project_names"] else "(no project)"
        ctx = f" | context: {t['context']}" if t.get("context") else ""
        lines.append(f"- id={t['id']} | name: {t['name']} | project: {proj} | status: {t['status']}{ctx}")
    lines += [
        "",
        "## OUTPUT — one fenced ```json block, nothing else",
        "A JSON array, one object per task you can size:",
        '```json',
        '[{"id": "<the id copied exactly>", "estimated_min": <minutes, integer>, '
        '"reasoning": "<one short phrase: why this long>"}]',
        '```',
        "Copy each id EXACTLY. Omit a task only if it is genuinely too vague to size.",
    ]
    return "\n".join(lines)


def parse_estimates(model_text):
    """Extract the estimates array from the model's fenced ```json block. Raises if absent or
    unparseable — a run that produced nothing usable is a failure surfaced, never silent."""
    blocks = re.findall(r"```json\s*(.*?)\s*```", model_text, re.DOTALL)
    if not blocks:
        raise RuntimeError("model output had no ```json block — cannot backfill durations")
    try:
        parsed = json.loads(blocks[-1].strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"model's JSON block did not parse: {e}")
    if not isinstance(parsed, list):
        raise RuntimeError(f"model's JSON block was not a list (got {type(parsed).__name__})")
    return [c for c in parsed if isinstance(c, dict) and c.get("id")]


def preview(sid=None, backend=None):
    """Estimate every sizeless task WITHOUT writing anything. Repeatable, side-effect-free."""
    sid = sid or g.get_space_id()
    tasks = load_sizeless_tasks(sid=sid)
    if not tasks:
        return {"tasks": [], "estimates": [], "by_id": {}}
    prompt = build_prompt(tasks)
    backend_name = backend or os.environ.get("CD_BACKEND", "mistral")
    model = plan_generate._active_model(backend_name)
    backend_label = f"{backend_name}/{model}" if model else backend_name
    t0 = time.monotonic()
    try:
        model_text = plan_generate.generate(prompt, backend=backend)
        estimates = parse_estimates(model_text)
    except Exception as e:
        generation_log.log_generation(
            backend=backend_label, duration_s=time.monotonic() - t0,
            success=False, source="duration_backfill",
            error_type=type(e).__name__, error_msg=str(e))
        raise
    generation_log.log_generation(
        backend=backend_label, duration_s=time.monotonic() - t0,
        success=True, source="duration_backfill",
        structural={"n_tasks": len(tasks), "n_estimates": len(estimates)})
    return {"tasks": tasks, "estimates": estimates,
            "by_id": {t["id"]: t for t in tasks}}


def format_preview(prev):
    tasks, estimates, by_id = prev["tasks"], prev["estimates"], prev["by_id"]
    est_by_id = {e["id"]: e for e in estimates}
    if not tasks:
        return "No duration-less tasks found — nothing to backfill."
    # group by first project name
    groups = {}
    for t in tasks:
        proj = t["project_names"][0] if t["project_names"] else "(no project)"
        groups.setdefault(proj, []).append(t)
    lines = [f"{len(tasks)} duration-less task(s); {len(estimates)} estimated, "
             f"{len(tasks) - len(est_by_id)} left unsized.", ""]
    for proj in sorted(groups):
        lines.append(f"### {proj}")
        for t in groups[proj]:
            e = est_by_id.get(t["id"])
            if e:
                lines.append(f"  - {t['name']}  ~{e.get('estimated_min')} min  — {e.get('reasoning','')}")
            else:
                lines.append(f"  - {t['name']}  (no estimate — too vague to size)")
        lines.append("")
    return "\n".join(lines)


# --- writing (--run only) ----------------------------------------------------

def _duration_source_key():
    """Resolve the Anytype-generated key for 'Duration source' once, by display name (never
    hardcoded — same convention as Engagement/Side)."""
    p = g.find_property("Duration source")
    if p is None:
        raise RuntimeError("'Duration source' property not found — run build_task/build_model first")
    return p.get("key")


_DURATION_SOURCE_KEY = None  # lazily resolved in apply(); module-level so tests can monkeypatch


def _get_task(oid):
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"read-back failed for {oid!r}: {st} {b}")
    return b["object"]


def apply(prev):
    """Write each estimate as a labeled 'estimated' Duration min, read-back proven. Re-fetches
    each task first and skips any that gained a duration since the preview (fidelity: never
    overwrite a value that appeared in the meantime). One task's failure never aborts the rest."""
    global _DURATION_SOURCE_KEY
    if _DURATION_SOURCE_KEY is None:
        _DURATION_SOURCE_KEY = _duration_source_key()
    est_by_id = {e["id"]: e for e in prev["estimates"]}
    result = {"updated": 0, "failed": 0, "skipped_no_estimate": 0}
    for tid, t in prev["by_id"].items():
        e = est_by_id.get(tid)
        if not e:
            result["skipped_no_estimate"] += 1
            continue
        try:
            live = _get_task(tid)
            if _pv(live, "gsdo_duration_min", "number") is not None:
                # gained a duration since preview — never overwrite
                result["skipped_no_estimate"] += 1
                continue
            props = capture_fields.build_optional_props(duration_estimate_min=e.get("estimated_min"))
            if "Duration min" not in props:
                result["skipped_no_estimate"] += 1
                continue
            gsdo_objects.update(tid, properties=props)
            back = _get_task(tid)
            got = _pv(back, "gsdo_duration_min", "number")
            src = (_pv(back, _DURATION_SOURCE_KEY, "select") or {}).get("name")
            if got != props["Duration min"] or src != "estimated":
                raise RuntimeError(f"read-back mismatch for {tid!r}: dur={got} src={src}")
            result["updated"] += 1
        except Exception as ex:
            result["failed"] += 1
            generation_log.log_generation(
                backend="duration_backfill", duration_s=0.0, success=False,
                source="duration_backfill", error_type=type(ex).__name__, error_msg=str(ex))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Backfill estimated durations onto duration-less tasks")
    ap.add_argument("--preview", action="store_true",
                     help="LLM estimates + show what --run would do; writes NOTHING (repeatable)")
    ap.add_argument("--run", action="store_true",
                     help="actually write the estimated durations (with read-back)")
    ap.add_argument("--backend", default=None, help="override CD_BACKEND for this run")
    args = ap.parse_args()
    if args.run and args.preview:
        print("--run and --preview are mutually exclusive", file=sys.stderr); sys.exit(1)

    if args.preview:
        print(format_preview(preview(backend=args.backend)))
    elif args.run:
        prev = preview(backend=args.backend)
        print(format_preview(prev))
        print("\n--- applying ---")
        print(json.dumps(apply(prev), indent=2))
    else:
        tasks = load_sizeless_tasks()
        print(f"duration-less tasks: {len(tasks)}")
        for t in tasks:
            proj = ", ".join(t["project_names"]) or "(no project)"
            print(f"  - {t['name']}  [{t['status']}]  project: {proj}")
        print("\nRun --preview to see estimates, --run to write them.")

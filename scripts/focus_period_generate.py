#!/usr/bin/env python3
"""Headless authoring: structure June's raw words about her week into Focus Period fields.

The backend half of Phase 6 authoring (no overlay UI) — pulled forward so June can author her
real week by feeding her OWN words to the system, not have an instance hand-structure it.
Speak -> structure -> confirm: this does the structure step; June confirms before creation
(focus_period_author.author_focus_period does the create + signal-capture).

Deterministic date anchor: Python computes today's date + weekday and hands it to the LLM, so
the LLM never GUESSES the current date (the thing it can't do reliably) — it only does relative
arithmetic ('Saturday') from a KNOWN anchor. The confirm step is the safety net if it slips.
"""
import sys, os, json, re, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import gsdo_anytype as g
import plan_generate
import daily_plan
import grain
import recurring_active


def _load_authoring_context():
    """Reuses daily_plan.load_active_items — the canonical loader — rather than re-deriving
    engagement/side/workstream logic here. One space fetch.

    Projects: her real project list, minus workstreams (an internal dev/research grouping layer
    she'd never foreground/reference by name directly — same exclusion the daily plan's own grain
    classifier applies). Fun/hobby projects stay IN this list; foregrounding a hobby project on
    its own terms is a legitimate ask.

    Goals: full list, grounding only (foreground/paused can't link to a Goal — only to a Project).

    Tasks: only ones that render as a DISCRETE item in her real daily plan (grain.classify ==
    "task": a Daily-life-side project, or no linked project at all). Everything else either shows
    as a "Work on X" block (already covered by the project name above) or is excluded from the
    plan outright (Fun/hobby, workstreams) — including those task names here would just be
    dev-backlog noise (confirmed live 2026-07-16: 35 of 182 tasks belonged to Build Controlled
    Drift alone, the app's own dev project, which is Side=Fun/hobby).

    As-needed Recurring names are merged in SEPARATELY from the fetch above, regardless of
    current Active state (Task 6 review, 2026-07-17): daily_plan.load_active_items only folds an
    as_needed Recurring into `tasks` when it's "due today" — and for an as_needed item, due IS
    its Active state (datetime_seam.today_fixed_time). So an OFF task — the one June needs to
    NAME to reactivate — was structurally invisible to the authoring prompt's grounding list,
    meaning reactivate_tasks could only ever re-affirm an already-active task, never actually
    reactivate one. A second, targeted fetch avoids reshaping load_active_items' broader "due
    today" contract just for this one grounding need."""
    sid = g.get_space_id()
    goals, projects, tasks, *_rest = daily_plan.load_active_items(sid)
    project_list = [p["name"] for p in projects if p.get("name") and not p.get("is_workstream")]
    goal_list = [go["name"] for go in goals if go.get("name")]
    discrete_ok = {p["name"] for p in projects if grain.classify(p) == "task"}
    task_list = [t["name"] for t in tasks
                 if t.get("name") and (not t.get("linked_projects")
                                        or any(pn in discrete_ok for pn in t["linked_projects"]))]
    all_objects = g.fetch_all_objects(sid)
    for o in recurring_active.as_needed_objects(all_objects):
        if o.get("name") and o["name"] not in task_list:
            task_list.append(o["name"])
    return project_list, goal_list, task_list


def project_names():
    return _load_authoring_context()[0]


def build_authoring_prompt(raw_text, today, names, goals=None, tasks=None, current=None):
    weekday = today.strftime("%A")
    proj_lines = "\n".join("  - " + n for n in names)
    goal_lines = "\n".join("  - " + n for n in goals) if goals else "  (none yet)"
    task_lines = "\n".join("  - " + n for n in tasks) if tasks else "  (none yet)"
    # Edit mode: the LLM REVISES an existing period rather than authoring from scratch. It gets the
    # current fields and must keep everything the change doesn't touch — the diff the reflect-back
    # shows is the safety, so a clobbered field is visible before it writes.
    edit_block = ""
    if current is not None:
        edit_block = f"""
This is an EDIT of an existing period. Here is its CURRENT configuration as JSON:
{json.dumps(current, indent=2)}
Apply ONLY the change her words describe. KEEP every other field exactly as it is above (same dates, foreground, availability, etc. unless she changes them). Output the FULL updated configuration.
"""
    return f"""You structure a person's spoken description of their week into a "Focus Period" configuration for her task system.

TODAY IS {weekday}, {today.isoformat()}. Resolve EVERY relative date ("Saturday", "this week", "next week", "later this week") from THIS anchor. The current date is given — do not guess it; just do the arithmetic from it.
{edit_block}
Her projects (use these EXACT names for foreground/paused; only pick ones she clearly implies — leave empty if unsure):
{proj_lines}

Her Goals (grounding only, not a field you fill — if a phrase in her words is actually the name of one of these, that's what she means; don't substitute your own generic word for it):
{goal_lines}

Her current Tasks/Recurring (grounding only, not a field you fill — if she names something that's already on this list, recognize it as an existing thing rather than reframing or dropping it):
{task_lines}

Her words:
\"\"\"{raw_text}\"\"\"

Output ONLY a JSON object with these keys (use null or [] when she didn't say):
- "name": short label, e.g. "Week of Jun 30 — jobs foreground"
- "start_date", "end_date": ISO dates for the period, resolved from today
- "intent": what this stretch is about, using or inferring based on the person's own words and phrases for framing/priority
- "availability_start", "availability_end": ISO dates of any fragmented/reduced-time stretch (e.g. caregiving), else null
- "availability_note": the situated meaning of that stretch, in her words (what it means for planning)
- "days_off", "days_on": lists of ISO dates she explicitly marks off/on, else []
- "output_format": "Auto" by DEFAULT. Auto = clock schedule on normal days, priority-list only during a fragmented availability window. Only use "Priority list" or "Clock schedule" if she clearly wants that one shape for the WHOLE period.
- "workday_start": "HH:MM" only if she implies the day starts later than usual (slow mornings, "not before 11", a caregiving morning), else null
- "workday_end": "HH:MM" only if she implies working late (a sprint), else null
- "foreground_projects": the FEW projects from HER PROJECT LIST above that she's putting in front this period — match what she said to the closest real project name from that list; don't invent one.
- "paused_projects": ONLY projects she EXPLICITLY says to STOP/drop this period. Default is []. Do NOT pause a project just because it isn't foreground — non-foreground projects stay present (backgrounded), they simply aren't prioritized. Hobby / creative / dev work she frames as low-priority or self-directed goes in NEITHER list — it is open time she chooses herself; say so in "intent".
- "reactivate_tasks": names from HER CURRENT TASKS/RECURRING list above that she says to pick back up / do this period ("keep the dishes going", "I want to get back to cleaning the fridge"). Use the EXACT name from that list; [] if she names none. Only tasks she already has — never invent one.
Output the JSON object only — nothing before or after."""


def parse_fields(model_text):
    """Extract the JSON object the model produced (tolerant of surrounding prose/fences)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", model_text, re.DOTALL)
    raw = m.group(1) if m else None
    if raw is None:
        m = re.search(r"\{.*\}", model_text, re.DOTALL)
        raw = m.group(0) if m else None
    if raw is None:
        raise RuntimeError(f"no JSON object in model output: {model_text[:200]}")
    return json.loads(raw)


def generate_focus_period(raw_text, today=None, names=None, goals=None, tasks=None, current=None):
    """Structure raw_text into proposed Focus Period fields (a dict). Does NOT create anything —
    June confirms first. Python supplies the date anchor; the LLM structures + resolves dates.
    `current` (a fields dict) puts it in EDIT mode: revise that period, keeping untouched fields."""
    today = today or dt.date.today()
    if names is None or goals is None or tasks is None:
        ctx_names, ctx_goals, ctx_tasks = _load_authoring_context()
        names = names if names is not None else ctx_names
        goals = goals if goals is not None else ctx_goals
        tasks = tasks if tasks is not None else ctx_tasks
    prompt = build_authoring_prompt(raw_text, today, names, goals=goals, tasks=tasks, current=current)
    return parse_fields(plan_generate.generate(prompt))

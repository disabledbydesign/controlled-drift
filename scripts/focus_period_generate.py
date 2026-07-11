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


def project_names():
    sid = g.get_space_id()
    return [o["name"] for o in g.fetch_all_objects(sid)
            if isinstance(o.get("type"), dict) and o["type"].get("key") == "gsdo_project"
            and o.get("name")]


def build_authoring_prompt(raw_text, today, names, current=None):
    weekday = today.strftime("%A")
    proj_lines = "\n".join("  - " + n for n in names)
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

Her words:
\"\"\"{raw_text}\"\"\"

Output ONLY a JSON object with these keys (use null or [] when she didn't say):
- "name": short label, e.g. "Week of Jun 30 — jobs foreground"
- "start_date", "end_date": ISO dates for the period, resolved from today
- "intent": her framing in plain words — what this stretch is about, survival-first if she says so
- "availability_start", "availability_end": ISO dates of any fragmented/reduced-time stretch (e.g. caregiving), else null
- "availability_note": the situated meaning of that stretch, in her words (what it means for planning)
- "days_off", "days_on": lists of ISO dates she explicitly marks off/on, else []
- "output_format": "Auto" by DEFAULT. Auto = clock schedule on normal days, priority-list only during a fragmented availability window. Only use "Priority list" or "Clock schedule" if she clearly wants that one shape for the WHOLE period.
- "workday_end": "HH:MM" only if she implies working late (a sprint), else null
- "foreground_projects": the FEW projects she's putting in front this period (e.g. job search when survival is the focus).
- "paused_projects": ONLY projects she EXPLICITLY says to STOP/drop this period. Default is []. Do NOT pause a project just because it isn't foreground — non-foreground projects stay present (backgrounded), they simply aren't prioritized. Hobby / creative / dev work she frames as low-priority or self-directed goes in NEITHER list — it is open time she chooses herself; say so in "intent".
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


def generate_focus_period(raw_text, today=None, names=None, current=None):
    """Structure raw_text into proposed Focus Period fields (a dict). Does NOT create anything —
    June confirms first. Python supplies the date anchor; the LLM structures + resolves dates.
    `current` (a fields dict) puts it in EDIT mode: revise that period, keeping untouched fields."""
    today = today or dt.date.today()
    names = names if names is not None else project_names()
    prompt = build_authoring_prompt(raw_text, today, names, current=current)
    return parse_fields(plan_generate.generate(prompt))

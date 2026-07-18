#!/usr/bin/env python3
"""What each Anytype field MEANS — readable at the moment of writing. Network-free.

WHY THIS EXISTS (2026-07-18). `capture_fields.py` opens by calling itself "the single source
of truth for BOTH write paths." There are THREE. `gsdo_objects.create/update` accept arbitrary
`properties={name: value}` with no content validation, and `cd_mcp_server.py` passes agent input
straight through — so any agent writing directly (including via the global `drift` skill)
bypasses every rule the capture validator enforces.

The observed damage was not a validation failure; it was a KNOWLEDGE failure. Of 14 populated
`Affective` values in June's space, the agent-written ones are status and findings rather than
affect — e.g. "Portal down as of 2026-07-08 — blocked on that, not on June" (that belongs in
`Blocked on`) and "Confirmed 2026-07-02: screen does NOT allow AI tools." (that belongs in
`Context`). Both target fields exist. Nothing routed the text there, because the rules about
what each field means lived ONLY inside the capture prompt, where a direct-writing agent never
sees them. An agent given no guidance picks whichever field sounds closest, reasonably.

So this module is not a validator. **You cannot mechanically decide whether a sentence is
"affect" or "status" — that is a semantic judgment.** This makes the semantics VISIBLE instead:
one definition, several consumers —
  - `scripts/describe_model.py`  — the self-describe seam agents are told to run when orienting
  - `scripts/cd_mcp_server.py`   — the tool descriptions a writing agent reads at the call site
  - `scripts/gsdo_objects.py`    — the low-level write path (points here; enforces only guard #3)

NOTHING HERE IS AUTHORED. Every entry is extracted from the project's own specs and planning
docs and carries a `source` citation, because "we figured all that out" already — the rationale
was written down, just not readable at write time. Where a field has no documented meaning
anywhere it is listed in UNDEFINED (below) and explicitly NOT given one: a fabricated rationale
sitting beside genuine cited ones would be worse than an obvious gap.

TWO LAYERS, RESOLVED (June, 2026-07-18: "if I can see an overall schema of our data structure
and semantics, I can verify it… it should be visible in the UI during the verification flows, so
I can revise it directly. Then our logging system should track it, and we have learning loop
data."). So these are not frozen constants:

  - REPO DEFAULTS — FIELDS/HINTS below. Version-controlled, carry the reasoning + citation.
  - HER OVERRIDES — a JSON file at `cd_paths.data_file(OVERRIDES_FILE)`, revisable through the
    UI. Resolution is override-if-present, else default. An override NEVER overwrites the
    default: `resolved()` returns both, so a later reader can see what was designed AND what she
    changed it to. Every override is logged as a before/after correction (see `set_override`).

TWO GRAINS per field, because the UI needs both (`app/src/components/detail/Field.tsx` renders a
`hint` under each field): a one-line `hint` short enough to sit under a form control, and the
full `means`/`usage`/`source` rationale for an agent or for June's verification pass.

SERIALISABLE: `schema_payload()` returns plain JSON-ready data for the planned `GET /api/schema`
(docs/api_contract_v2.md §1 — "the entire form/picker/chip/dropdown layer is generated from
this"). This module does NOT build the endpoint; `server.py` belongs to another thread.
"""
import os, json, re
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths

# --- the definitions ---------------------------------------------------------
# Keyed by the LIVE display name (what every caller passes to gsdo_objects). Each entry:
#   types      — which of the five types carry this field, per the live schema (describe_model.py)
#   means      — what belongs in it
#   not_this   — what does NOT belong in it (omitted where the spec says nothing)
#   instead    — where misplaced content should go instead
#   usage      — the rules that actually govern a write; quoted or closely paraphrased
#   source     — where to go read the full reasoning
#   observed   — live-data observation; NEVER a silent reconciliation of spec vs. reality

FIELDS = {

    # ---- the four fields the leak was about -------------------------------
    "Affective": {
        "types": ("Task", "Project", "Recurring"),
        "means": "The emotional charge of THIS item, in June's words — affective conditions only. "
                 "The KIND of thing that belongs here: stress, avoidance, dread, hyperfixation, "
                 "flatness, relief, unexpected enthusiasm.",
        "not_this": "Status. Findings. Confirmations. Blockers. Progress notes. Anything about the "
                    "state of the WORK rather than how June feels about it. Never a number or rating.",
        "instead": {"a blocker": "Blocked on", "a finding, confirmation, or origin note": "Context",
                    "an access or executive-function barrier": "Access notes"},
        "usage": [
            "Never a scalar (guard #3). Open text, explicitly marked unstable, capable of holding "
            "multiple distinct signals at once — 'affective weight is a constellation, not a scale.'",
            "Only surfaced when relevant; NEVER asked for tiny tasks.",
            "Each item's affect matches the scope June's words gave it: a feeling about one item "
            "lands on that item; a feeling she states about the whole dump lands on every item.",
            "The AI may offer a rough intensity read purely for filtering, but that read is "
            "low-confidence, always correctable, and never the canonical value — the text is canonical.",
        ],
        "source": "AI_LAYER_SPEC.md §2 (Task/Project tables + 'Affective weight is a constellation'); "
                  "docs/BUILD_DOC.md hazard 'FIELD-SEMANTICS LEAK' (June's field model, 2026-07-18); "
                  "scripts/capture_fields.py docstring",
        "observed": "The leak lives here. Of 14 populated Affective values in the live space, the "
                    "agent-written ones are status/findings, not affect. Spec and observed use "
                    "disagree; the spec is the rule and the data is what needs fixing. "
                    "PARTLY ADDRESSED 2026-07-18, commit e39dd5b — but read the boundary "
                    "carefully, because June's note and the commit are about adjacent things. "
                    "e39dd5b removed `props[\"Context\"] = item[\"reasoning\"]` from "
                    "capture_generate._creation_props, so the gate's own filing rationale no "
                    "longer lands in `Context`; it is now stamped in the write log "
                    "(corrections_log.log_authorship → scripts/data/corrections.jsonl) after "
                    "read-back. That closes the CONTEXT misroute on the capture path. It does NOT "
                    "touch Affective: nothing in that commit changes what goes into this field, "
                    "and the 14 polluted Context values were deliberately left alone (clearing "
                    "them is a data edit on real objects and stays June's call). So the "
                    "status-notes-in-Affective leak is still current, and prose guidance — this "
                    "module, the MCP routing brief, the drift skill — is the whole of what "
                    "prevents it. Separately, docs/structural_diagnosis_2026-07-11.md said "
                    "Affective drove no selection; RE-VERIFIED 2026-07-18, it IS read in the plan "
                    "path now. That half is STALE.",
    },

    "Access notes": {
        "types": ("Task", "Recurring"),
        "means": "Open-text extension of the `Access conditions` tags: what the task needs, or what "
                 "is in the way of STARTING it, for barriers that have no tag yet — unnamed "
                 "executive-function and access barriers (initiation-heavy, context-switch-heavy, "
                 "sensory, social, cognitive-load).",
        "not_this": None,
        "instead": {},
        "usage": [
            "The fixed category list was deliberately NOT pre-enumerated — June's correction: the "
            "four-category body list was overengineered, and the barriers that matter aren't only "
            "about the body. The set GROWS from her real annotations.",
            "Recurring patterns in this note feed the §6 promotion loop: when an unnamed barrier "
            "keeps recurring, the AI surfaces it as a candidate to name as its own tag.",
            "The AI infers and proposes; June never sets it cold; when genuinely ambiguous the AI "
            "leaves it EMPTY rather than guessing.",
        ],
        "source": "AI_LAYER_SPEC.md §2 Task table, `access` row",
        "observed": "Unpopulated across the entire live space (2026-07-18). Per the spec this is "
                    "where unnamed barriers accumulate to feed tag promotion, so nothing is "
                    "currently prompting for it. Recorded as an observation, not asserted as a bug. "
                    "docs/structural_diagnosis_2026-07-11.md also lists access_notes among fields "
                    "nothing reads.",
    },

    "Blocked on": {
        "types": ("Task", "Recurring"),
        "means": "What is being waited for — the concrete blocker.",
        "not_this": "The strategic/decisional 'I don't know how to…' struggle (that is `Barriers`), "
                    "and how June feels about the block (that is `Affective`).",
        "instead": {"a strategic 'I don't know how to…' struggle": "Barriers",
                    "a feeling about the block": "Affective"},
        "usage": [
            "When set, this IS the displayed next item, and it is surfaced positively — the plan "
            "reports what is being waited on and treats 'nothing to do here right now' as the "
            "right answer, not as a gap. Relief, not anxiety.",
            "Free text, not a traversable link (noted as a gap, not a rule).",
        ],
        "source": "AI_LAYER_SPEC.md §2 Task table, `blocked_on` row; "
                  "docs/structural_diagnosis_2026-07-11.md (free text, not a link)",
    },

    "Context": {
        "types": ("Goal", "Project", "Task", "Recurring", "Strategy"),
        "means": "Everything else — findings, confirmations, origin, constraints, what June keeps "
                 "forgetting about this item. The catch-all the AI reads in full.",
        "not_this": None,
        "instead": {},
        "usage": [
            "'The fundamental rule: formal fields exist only for what the AI must query or filter "
            "on. Everything else lives in `context` (free text, always present, always read).'",
            "New patterns emerge in Context BEFORE we know they are patterns; they promote to "
            "formal fields when they have earned it (§6). So writing something here is the correct "
            "default, not a fallback.",
            "On Strategy: origin, lifespan notes, why it was adopted. Heavily used — ~10 of June's "
            "12 real Strategy objects populate it.",
        ],
        "source": "AI_LAYER_SPEC.md §2 ('The fundamental rule') + per-type tables; "
                  "docs/BUILD_DOC.md §8 Strategy decision (live usage across her 12 Strategies)",
    },

    "Access conditions": {
        "types": ("Task", "Recurring", "Project"),
        "means": "Fixed multi-select for the access barriers that are QUERYABLE and load-bearing.",
        "not_this": "Any barrier without a live tag — those go in `Access notes` as open text.",
        "instead": {"a barrier with no matching tag": "Access notes"},
        "usage": [
            "Two tags earn their place because they drive real behavior: Can-be-done-lying-down "
            "(low-capacity filtering) and Involves-leaving-house (errand-batching). "
            "Requires-talking-to-a-person is also live.",
            "Only live option names are ever written — an unknown tag is DROPPED, never created.",
            "The AI infers and proposes; June never sets it cold; ambiguous → leave empty.",
        ],
        "source": "AI_LAYER_SPEC.md §2 Task table `access` row; scripts/capture_fields.py ALLOWED_ACCESS",
        "observed": "Live tags are only the original three. The three additions in backend spec §6 "
                    "(Requires-deep-thinking / Involves-bureaucracy / Induces-pain) are AGREED AND "
                    "PLANNED — June, 2026-07-18: \"We want to build the new tags\" — and are being "
                    "built by another thread. Until they are live, writing them does nothing: an "
                    "unknown tag is dropped. §6 gives behaviour for only one of the three "
                    "(Induces-pain, a capacity signal to weigh on low-capacity days and pair with "
                    "rest); the other two are specified as names with no stated behaviour yet. "
                    "⚠ CORRECTION 2026-07-18, found by running describe_model.py against the live "
                    "space: `Access conditions` IS on the Project type now — another thread added "
                    "it read-back-confirmed the same day, and docs/BUILD_DOC.md Track B §4 already "
                    "records that. This module was the stale one: its type list said "
                    "Task/Recurring, so the field read as having no documented meaning wherever a "
                    "Project was described. Project added. Note per Track B that nothing yet READS "
                    "Project-level access conditions; the reader below is the Task-level one.",
    },

    # ---- duration + provenance --------------------------------------------
    "Duration min": {
        "types": ("Task", "Recurring"),
        "means": "Estimated minutes for the item. The AI proposes a default at cold-start from task "
                 "type and context — never left blank.",
        "not_this": None,
        "instead": {},
        "usage": [
            "June's stated duration is truth and always wins; an LLM estimate fills silence only. "
            "Whichever is written, `Duration source` MUST be written alongside it — a June-stated 90 "
            "and an estimated 90 must never be indistinguishable.",
            "Her calibration: most tasks run 1-2 hours, not 30 minutes; focused-attention work "
            "(job applications) runs 120+ and may need multiple blocks. See DURATION_PRIORS.",
            "A learning loop refines it from actual-vs-estimated.",
        ],
        "source": "AI_LAYER_SPEC.md §2 Task table; scripts/capture_fields.py "
                  "(DURATION_PRIORS + build_optional_props)",
    },

    "Duration source": {
        "types": ("Task",),
        "means": "Provenance label for `Duration min`: 'stated' (June said it) or 'estimated' (the "
                 "LLM filled the silence).",
        "not_this": None,
        "instead": {},
        "usage": ["Written whenever Duration min is written; never on its own.",
                  "Exists so the future duration-bias learning loop can tell the two apart."],
        "source": "scripts/capture_fields.py build_optional_props docstring",
    },

    # ---- the two dates, which are NOT the same ----------------------------
    "Due date": {
        "types": ("Task",),
        "means": "The deadline. Drives urgency and ordering in the plan.",
        "not_this": "The day the plan placed the task — that is `Scheduled`.",
        "instead": {"the day the plan placed this task": "Scheduled"},
        "usage": ["Optional. Only when real.",
                  "Keep separate from Scheduled — do NOT collapse them into one date field."],
        "source": "docs/review_reorganize_backend_spec.md §8 (DECIDED); AI_LAYER_SPEC.md §2 Task table",
        "observed": "docs/structural_diagnosis_2026-07-11.md listed Due date as not even loaded in "
                    "the plan path as of that date." + ' ⚠ RE-VERIFIED 2026-07-18 against current code: this claim is STALE — the field IS read in the plan path now.' + " Read at 3 sites.",
    },

    "Scheduled": {
        "types": ("Task",),
        "means": "The day the plan has actually PLACED the task — set by the scheduler or by June "
                 "moving it. A placement record, not a deadline.",
        "not_this": "A deadline — that is `Due date`.",
        "instead": {"a deadline": "Due date"},
        "usage": ["Keep separate from Due date; the plan reads Due date for urgency."],
        "source": "docs/review_reorganize_backend_spec.md §8 (DECIDED)",
    },

    "Deadline": {
        "types": ("Project",),
        "means": "The project's deadline.",
        "not_this": None,
        "instead": {},
        "usage": ["Optional. Only when real.",
                  "Hard dates that must stay live and drive action are the ONE kind of route "
                  "condition to extract out of prose into a real dated object — the qualitative "
                  "conditions stay as text in Context / Engagement notes."],
        "source": "AI_LAYER_SPEC.md §2 Project table; docs/route_structure_assessment_2026-07-12.md §3",
        "observed": "docs/structural_diagnosis_2026-07-11.md: loaded but never displayed or "
                    "ordered on, as of that date." + ' ⚠ RE-VERIFIED 2026-07-18 against current code: this claim is STALE — the field IS read in the plan path now.' + " Read at 3 sites.",
    },

    # ---- engagement -------------------------------------------------------
    "Engagement": {
        "types": ("Project",),
        "means": "How June is currently engaging with this project — the enduring per-project grain "
                 "gate the daily plan reads deterministically. Steady / Open / Backburner "
                 "(+ Needs Clarifying / Done in the wider live vocabulary).",
        "not_this": "Sprint and Hyperfixation — both RETIRED 2026-07-16. A sprint is a Focus Period "
                    "foreground action; hyperfixation is a qualitative state.",
        "instead": {"a sprint": "Focus Period foreground (not this field)",
                    "hyperfixation or intensity": "Engagement notes / Affective"},
        "usage": [
            "Steady → one normal daily move the plan commits to. Open → available, surfaced gently, "
            "not pushed (the default a new project is born with). Backburner → not surfaced unless a "
            "neglect threshold. Done → excluded, and never a birth value.",
            "An invalid or blank value means Open — the default lives in capture_fields, not in "
            "gsdo_objects (there is deliberately no born-Open chokepoint in the write layer).",
        ],
        "source": "AI_LAYER_SPEC.md §2 Project table + the 2026-07-11 selection reconciliation note; "
                  "scripts/capture_fields.py PROJECT_ENGAGEMENTS",
    },

    "Engagement notes": {
        "types": ("Project",),
        "means": "The situated specifics the Engagement select cannot hold: the threshold that "
                 "would change it, the cadence it implies, a date it turns on, or "
                 "hyperfixation/intensity context.",
        "not_this": None,
        "instead": {},
        "usage": [
            "Canonical, open-schema PAIR for Engagement. The select is filterable; this field is "
            "authoritative about what it means for this project right now.",
            "Route conditions ('Opens when: …', 'Weighed against: …') stay as structured free text "
            "here or in Context — deliberately NOT a condition-field schema, which would flatten "
            "the variety and force provisional conditions into false crispness.",
        ],
        "source": "AI_LAYER_SPEC.md §2 Project table; docs/route_structure_assessment_2026-07-12.md §3",
    },

    "Goal engagement": {
        "types": ("Goal",),
        "means": "The Goal-level analog of a Project's Engagement: is this whole life-area getting "
                 "ongoing baseline attention (Steady), engaged flexibly across many possible "
                 "projects (Open), or set aside (Backburner)?",
        "not_this": "Sprint — a sprint is a Focus Period foreground state on a PROJECT, not a "
                    "property of a whole life area (June, 2026-07-13).",
        "instead": {},
        "usage": ["Feeds the not-yet-built cross-goal balancing / route-prioritization engine (§8d). "
                  "Until that is built this is data worth keeping current, not yet consumed by code."],
        "source": "AI_LAYER_SPEC.md §2 Goal table",
    },

    # ---- statuses ---------------------------------------------------------
    "Task status": {
        "types": ("Task",),
        "means": "Ready / In Design / Parked / Needs Clarifying / Blocked / Done.",
        "not_this": None,
        "instead": {},
        "usage": [
            "Ready = well-specified, executable now. In Design = real committed work that needs a "
            "design conversation first. Parked = captured, no work-stream home yet, intentionally "
            "held — not surfaced in the daily plan or orient map. Needs Clarifying = shape unclear "
            "(the weeding gate's output for vague items). Blocked surfaces `Blocked on`.",
            "Legacy `Active` (pre-rename) is treated identically to Ready in queries.",
        ],
        "source": "AI_LAYER_SPEC.md §2 Task table; docs/review_reorganize_backend_spec.md §12",
    },

    "Goal status": {
        "types": ("Goal",),
        "means": "Active / Parked / Achieved.",
        "not_this": None,
        "instead": {},
        "usage": [],
        "source": "AI_LAYER_SPEC.md §2 Goal table; docs/review_reorganize_backend_spec.md §12",
        "observed": "Also appears on the live Project type, where it is a leak — see "
                    "`Goal status (on Project)` in UNDEFINED. On Goal itself the option list is "
                    "documented but its PURPOSE is not. June's own open question, 2026-07-18, "
                    "recorded as a question and deliberately not promoted into a definition: "
                    "\"im not sure what the goal status is either, other than perhaps a mechanism "
                    "for allowing us to retire goals?\" If that is what it is for, it overlaps "
                    "`Horizon` + `Resolution condition`, which already describe how a goal ends. "
                    "Unresolved; do not write a rationale for it.",
    },

    "Project status": {
        "types": ("Project",),
        "means": "Active / Parked / Inactive.",
        "not_this": None,
        "instead": {"how June is currently engaging with the project": "Engagement"},
        "usage": ["LEGACY — the spec records that `Engagement` REPLACES this field. Prefer Engagement."],
        "source": "AI_LAYER_SPEC.md §2 Project table ('Replaces the old Project status … legacy'); "
                  "docs/review_reorganize_backend_spec.md §12",
    },

    "Strategy status": {
        "types": ("Strategy",),
        "means": "Active / Retired. Queried so the AI applies only currently-active strategies.",
        "not_this": None,
        "instead": {},
        "usage": ["A strategy's lifespan is terminal — retiring one is EXPECTED, not failure."],
        "source": "AI_LAYER_SPEC.md §2 Strategy table",
    },

    # ---- Strategy ---------------------------------------------------------
    "What for": {
        "types": ("Strategy",),
        "means": "When and where to apply the strategy — the point-of-performance trigger (Barkley: "
                 "surface it at the moment the behavior has to happen, not in the abstract).",
        "not_this": None,
        "instead": {},
        "usage": ["Lets the AI know WHEN a strategy is relevant."],
        "source": "AI_LAYER_SPEC.md §2 Strategy table",
        "observed": "In June's 12 real Strategy objects this field carries BOTH the trigger AND the "
                    "instruction — e.g. 'When planning days that involve leaving the house. Weigh "
                    "the cumulative spoon-cost of errands, not just count.' Used on essentially all "
                    "of them (docs/BUILD_DOC.md §8 Strategy decision). Broader than the spec's "
                    "trigger-only definition; reported, not reconciled.",
    },

    "Learning notes": {
        "types": ("Strategy",),
        "means": "The anti-forgetting field: what this strategy needs that it isn't doing yet; "
                 "annotations on whether it is still working.",
        "not_this": None,
        "instead": {},
        "usage": ["A learning loop targets this field so the strategy improves instead of silently "
                  "failing — and so June is reminded the system is revisable, not stuck."],
        "source": "AI_LAYER_SPEC.md §2 Strategy table",
        "observed": "Designed, defined, and unused — not undefined. Unused across her 12 live "
                    "Strategy objects (docs/BUILD_DOC.md §8). June, 2026-07-18: \"useful to build "
                    "on later, although im not sure what the original plan for it was.\" The plan "
                    "IS written down, in AI_LAYER_SPEC.md §2 Strategy, and is quoted in full under "
                    "what-it-does above so it does not have to be hunted for.",
    },

    # ---- the why-fields ---------------------------------------------------
    "Reaching for": {
        "types": ("Goal", "Project"),
        "means": "The WHY — optional but load-bearing when present.",
        "not_this": None,
        "instead": {},
        "usage": [
            "Top-level Goals require HUMAN authorship — drawn from a conversation or document, "
            "never AI-invented. For sub-goals and Projects the AI proposes text June edits.",
            "Fill rate is itself a learning-loop signal: a low fill rate means the field is not "
            "earning its place yet.",
            "Deliberately THIN now, designed to point at PMA's rich version later.",
        ],
        "source": "AI_LAYER_SPEC.md §2 Goal + Project tables; DESIGN_v1_emerging.md §7",
    },

    "Barriers": {
        "types": ("Goal", "Project"),
        "means": "The strategic/decisional 'I don't know how to…' struggle — genuine open QUESTIONS, "
                 "not undone chores. The KIND of thing that belongs here: an unresolved framing "
                 "question, an unknown norm or convention, an audience or format she can't settle.",
        "not_this": "A concrete thing being waited for (that is `Blocked on`) and an access barrier "
                    "(that is `Access conditions` / `Access notes`).",
        "instead": {"something concrete being waited for": "Blocked on",
                    "an access or executive-function barrier": "Access notes"},
        "usage": [
            "Held so June doesn't re-derive it; queryable so the AI can find patterns across "
            "barriers over time (June's stated reason for making it a field).",
            "These must NOT become tasks with done-boxes — the system would quietly score her as "
            "'behind' on things that have no answer yet, which the guards forbid.",
            "The AI proposes it from what June articulates as struggle; optional.",
        ],
        "source": "AI_LAYER_SPEC.md §2 Goal table; docs/route_structure_assessment_2026-07-12.md §5",
        "observed": "Nothing reads it yet, and that is a pending design rather than a dead field — "
                    "June, 2026-07-18: \"Keep this — its pending further design.\" "
                    "docs/route_structure_assessment_2026-07-12.md §5 names 'barriers never "
                    "resurface' as the missing piece: what is unbuilt is the resurfacing, not the "
                    "definition. Keep writing it; the content is what the later design needs.",
    },

    "Horizon": {
        "types": ("Goal",),
        "means": "Chapter / Ongoing / Milestone. Chapter = a life phase ending when a condition is "
                 "met (job search, recovery season). Ongoing = structural, no discrete end (health, "
                 "craft practice). Milestone = a discrete done-state (publish paper, launch tool).",
        "not_this": "The vague Long/Medium/Short-term labels this replaced.",
        "instead": {},
        "usage": ["Feeds Goal ordering; the AI reads it to choose narration register (urgency vs. "
                  "spiral vs. open horizon)."],
        "source": "AI_LAYER_SPEC.md §2 Goal table",
        "observed": "docs/review_reorganize_backend_spec.md §12 lists a wider live option set "
                    "(Chapter · Milestone · Short-term · Medium-term · Long-term · Ongoing).",
    },

    "Resolution condition": {
        "types": ("Goal",),
        "means": "For Chapter goals: what this goal looks like when it stops claiming attention — "
                 "the condition that ends it, stated so it can be recognised when it arrives.",
        "not_this": None,
        "instead": {},
        "usage": ["Optional on Ongoing/Milestone goals, but useful when the done-state needs "
                  "spelling out."],
        "source": "AI_LAYER_SPEC.md §2 Goal table",
    },

    "Description": {
        "types": ("Project",),
        "means": "What this project is and its approach — the WHAT (as distinct from `Reaching for`, "
                 "which is the why).",
        "not_this": None,
        "instead": {"the project's why": "Reaching for"},
        "usage": [],
        "source": "AI_LAYER_SPEC.md §2 Project table",
    },

    # ---- links ------------------------------------------------------------
    "Goal link": {
        "types": ("Project",),
        "means": "The Goal(s) this project serves. The alignment chain.",
        "not_this": "Anything that is not a Goal — a wrong-kind link is dropped by the write layer.",
        "instead": {},
        "usage": ["A Project may serve multiple Goals; storage is a graph, not a tree."],
        "source": "AI_LAYER_SPEC.md §2 Project table",
        "observed": "docs/structural_diagnosis_2026-07-11.md called goal_link 'the alignment chain' and said it was read NOWHERE in the plan path. ⚠ RE-VERIFIED 2026-07-18: STALE — daily_plan.py:147 reads it, fixed 2026-07-14 (the loader used to drop the relation).",
    },

    "Linked Projects": {
        "types": ("Task",),
        "means": "The Project(s) this task belongs to — the anti-drift chain.",
        "not_this": "A Goal. A Task links to Projects only; a wrong-kind link is dropped.",
        "instead": {},
        "usage": ["Optional for bare chores. A Task may link to multiple Projects (many-to-many)."],
        "source": "AI_LAYER_SPEC.md §2 Task table; scripts/gsdo_objects.py _LINK_KIND",
    },

    "Project link": {
        "types": ("Recurring",),
        "means": "The project or goal this recurring item serves. Optional.",
        "not_this": "A Goal — a Recurring links to a Project.",
        "instead": {},
        "usage": [],
        "source": "AI_LAYER_SPEC.md §2 Recurring table; scripts/gsdo_objects.py _LINK_KIND",
    },

    "Parent project": {
        "types": ("Project",),
        "means": "The containing Project. Enables nesting and sub-routes — a work stream is a "
                 "Project under a parent Project; leaf nodes are Tasks.",
        "not_this": None,
        "instead": {},
        "usage": ["Nesting produces 'next tangible item' structure at any level."],
        "source": "AI_LAYER_SPEC.md §2 Project table",
    },

    "Depends on": {
        "types": ("Project",),
        "means": "Hard dependencies ONLY — streams that genuinely cannot start until another is done.",
        "not_this": "Soft ordering or preference. Parallel is the default.",
        "instead": {},
        "usage": ["Leave unset when there is no real dependency. The AI can propose candidates "
                  "from context."],
        "source": "scripts/gsdt_bind.py (the generated per-repo CLAUDE.md binding section)",
    },

    "Arc position rationale": {
        "types": ("Project",),
        "means": "Full plain sentences (not a one-liner) explaining where this stream sits in the "
                 "project arc and why.",
        "not_this": "A terse label or a one-line summary.",
        "instead": {},
        "usage": ["Guard #6: June needs to understand the reasoning, not just see the result. "
                  "Stored so it persists across sessions without being re-derived."],
        "source": "scripts/gsdt_bind.py (the generated per-repo CLAUDE.md binding section)",
    },

    # ---- misc Task/Project ------------------------------------------------
    "Relevant docs": {
        "types": ("Project", "Task", "Recurring"),
        "means": "Filepaths, directory paths, or document locations an agent should read before "
                 "working on this item — a repo path, a folder, a named doc, an external system.",
        "not_this": None,
        "instead": {},
        "usage": ["Populated by the weeding gate when an item references a file or external system; "
                  "the AI reads them before working on the item."],
        "source": "AI_LAYER_SPEC.md §2 Project + Task tables",
        "observed": "RE-VERIFIED 2026-07-18: not read by the plan path — but that is the WRONG "
                    "TEST, same as AI autonomous. Its consumer is agent-facing: an agent working "
                    "the task should open these paths first. June, 2026-07-18: \"Need to be "
                    "fixed.\" What fixed means mechanically is stated under what-it-does above "
                    "(expose it through the MCP read surface, add a read-side rule to the drift "
                    "skill, and populate it at capture). Correction: the usage rule above says the "
                    "weeding gate populates it — no prompt in prompts/ mentions it, so nothing "
                    "does. That rule is intent, not built behaviour.",
    },

    "AI autonomous": {
        "types": ("Task", "Recurring"),
        "means": "Can the AI do this with minimal oversight?",
        "not_this": None,
        "instead": {},
        "usage": ["Lets the system offload work June doesn't need to touch."],
        "source": "AI_LAYER_SPEC.md §2 Task table",
        "observed": "RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST. June: this field is 'useful more in the agent-facing interface' — an agent deciding whether it can just do the task. Checked: cd_mcp_server.py does NOT expose it and the drift skill does not mention it. So it is not dead, it is NEVER CONNECTED TO ITS ACTUAL CONSUMER.",
    },

    "Done": {
        "types": ("Task",),
        "means": "The completion checkbox. Always present on a Task.",
        "not_this": None,
        "instead": {},
        "usage": [
            "A chore is name + Done and nothing else, forever, unless June or the AI adds more "
            "(the bare-task principle). A field existing in the schema never means June fills a form.",
            "Rest and wellbeing are first-class checkable Tasks — checkable rest makes NOT-resting "
            "gently visible; the signal points at under-rest, never at failure.",
        ],
        "source": "AI_LAYER_SPEC.md §2 Task table + 'Rest is first-class and checkable'; "
                  "DESIGN_v1_emerging.md §5",
    },

    "Side": {
        "types": ("Project",),
        "means": "An orthogonal life-domain marker on a project: Obligation / Wellbeing / Fun-hobby "
                 "/ Daily life (Daily life added 2026-07-13, marking the sustainable-daily-life "
                 "subprojects — medical, household, self-care, social).",
        "not_this": "A priority or a ranking. It is applied orthogonally to engagement, never "
                    "overwriting it.",
        "instead": {},
        "usage": [
            "Feeds a display-grain rule: Fun-hobby → excluded from the plan; Daily life → render at "
            "TASK grain (the specific chore); everything else → smallest-subproject grain once "
            "workstreams are filtered out.",
            "Descendants inherit from the nearest ancestor that has it set.",
        ],
        "source": "AI_LAYER_SPEC.md §2 selection-reconciliation note (2026-07-11 / 2026-07-13)",
        "observed": "The rename Obligation → Work (backend spec §12) is DECIDED — June, "
                    "2026-07-18: \"lets rename to work\" — and is another thread's to apply. Not "
                    "live as of 2026-07-18, so `Obligation` is still the only writable name. "
                    "Wellbeing and Obligation are distinguished in the docs but not in any "
                    "selection code; the difference is currently semantic only.",
    },

    "Block chunk min": {
        "types": ("Project",),
        "means": "A durable per-project preference: how many minutes one work chunk on this project "
                 "should be.",
        "not_this": "Ephemeral state such as 'did a chunk today' — that stays in the local "
                    "block_duration_log.jsonl.",
        "instead": {},
        "usage": ["Anytype-is-master: durable preference → Anytype; ephemeral/resetting state → local "
                  "file. An earlier draft put this number in a local file; that was flagged as "
                  "forking the source of truth.",
                  "Its Anytype key is auto-generated (block_chunk_min, no gsdo_ prefix), so it is "
                  "read BY DISPLAY NAME."],
        "source": "docs/display_grain_design.md (revised 2026-07-14, post-swarm); scripts/block_duration.py",
    },

    # ---- Recurring --------------------------------------------------------
    "Interval unit": {
        "types": ("Recurring",),
        "means": "day / week / month / as_needed — the recurrence interval's unit.",
        "not_this": "A Practice-vs-Routine distinction. `Has target` / `Target` were RETIRED "
                    "2026-07-16/17; a recurring item is defined by its interval alone.",
        "instead": {},
        "usage": ["The one axis that stays is scheduled vs. as_needed: whether an item auto-populates "
                  "on a cadence or only when invoked. That is a scheduling choice.",
                  "Replaces the legacy `Frequency` (Daily/Weekly/As-needed) field."],
        "source": "AI_LAYER_SPEC.md §2 Recurring table + the retirement note beneath it",
    },

    "Interval count": {
        "types": ("Recurring",),
        "means": "N in 'every N days/weeks/months'. Default 1. day/1 = daily; day/3 = every 3 days.",
        "not_this": None,
        "instead": {},
        "usage": [],
        "source": "AI_LAYER_SPEC.md §2 Recurring table",
    },

    "Day of week": {
        "types": ("Recurring",),
        "means": "Mon–Sun. The weekly anchor: set only for items pinned to specific day(s), e.g. "
                 "weekly therapy on Tuesday.",
        "not_this": None,
        "instead": {},
        "usage": ["Empty for un-anchored daily routines."],
        "source": "AI_LAYER_SPEC.md §2 Recurring table",
    },

    "Time of day": {
        "types": ("Recurring",),
        "means": "Clock time 'HH:MM'. When set, the deterministic scheduler treats this as a FIXED "
                 "ANCHOR that the day's flexible tasks flow around.",
        "not_this": None,
        "instead": {},
        "usage": ["A Recurring with Day of week + Time of day + Duration min set is a fixed "
                  "appointment placed at its real clock time."],
        "source": "AI_LAYER_SPEC.md §2 Recurring table + 'Fixed recurring appointments'",
    },

    "Fixed appointment": {
        "types": ("Recurring",),
        "means": "Opt-out flag (June's name for it) for the missed-item persistence rule: a fixed "
                 "appointment that is missed returns on its own schedule rather than persisting.",
        "not_this": None,
        "instead": {},
        "usage": ["Checkbox on Recurring; default unset."],
        "source": "docs/task_persistence_design.md",
    },

    "Active": {
        "types": ("Recurring",),
        "means": "The on/off switch for whether this recurring item is currently part of June's "
                 "daily plan. Backend spec §3: \"it is not 'done' (that's per-occurrence); it is "
                 "an on/off 'in my daily plan' toggle.\" Default on. PROMOTED out of UNDEFINED "
                 "2026-07-18: this module previously said no doc defined it, which was wrong — "
                 "§3 defines it and datetime_seam.py reads it.",
        "not_this": "A completion state (a recurring item is never 'done', only done for today), "
                    "and not the legacy `Active` value of Task status, which is a different field.",
        "instead": {"whether today's occurrence is finished": "the per-day completion path, not "
                                                              "this flag"},
        "usage": ["Write it through recurring_active.set_recurring_active, the single writer — "
                  "never by hand. It reads back and logs.",
                  "⚠ It only takes effect on `as_needed` items. On day/week/month items nothing "
                  "consults it, so unticking a weekly recurring does not currently remove it from "
                  "the plan. The scheduler-level skip backend spec §3 asks for is unbuilt."],
        "source": "docs/review_reorganize_backend_spec.md §3; scripts/datetime_seam.py:105-116; "
                  "scripts/recurring_active.py",
        "observed": "June, 2026-07-18, before this was traced: \"probably a tick we use to "
                    "determine whether or not it surfaces in the daily plan.\" That matches §3 "
                    "exactly. The gap is in the build, not in her reading of it.",
    },

    "Day of month": {
        "types": ("Recurring",),
        "means": "The day-of-month anchor for a month-unit recurrence: the day number, 1-31, this "
                 "item is due on. Defined 2026-07-18 from the code that reads it — no spec "
                 "document defines this field.",
        "not_this": "A weekly anchor (that is `Day of week`) and a one-off date (that is `Due "
                    "date` on a Task).",
        "instead": {"a weekly anchor": "Day of week", "a one-off date": "Due date"},
        "usage": ["Required for any Recurring whose `Interval unit` is `month`. ⚠ Leaving it unset "
                  "makes a monthly item NEVER due, and nothing reports that — so an unset value is "
                  "a silent disappearance, not a harmless default.",
                  "A value larger than the current month allows is clamped to that month's last "
                  "day, so 31 fires on Feb 28 or 29.",
                  "⚠ `Interval count` is ignored for month units, so 'every 3 months' currently "
                  "runs every month (datetime_seam.py:22-24 — every-N-months needs a stored start "
                  "anchor the system does not keep yet)."],
        "source": "scripts/datetime_seam.py:131-140 (the only reader); "
                  "scripts/build_recurring.py:14 (schema)",
    },

    "Frequency": {
        "types": ("Recurring",),
        "means": "LEGACY — the v1-prototype field (Daily / Weekly / As-needed).",
        "not_this": None,
        "instead": {"the recurrence cadence": "Interval unit + Interval count"},
        "usage": ["Replaced by the interval model. Ignore it when building; it may still exist in "
                  "the space as a legacy property."],
        "source": "AI_LAYER_SPEC.md §2 Recurring table note",
    },

    # ---- Focus Period -----------------------------------------------------
    # A SIXTH live type, absent from describe_model.py (which filters to the five core types) and
    # therefore missing from this module until 2026-07-18. Its design reasoning was recovered from
    # docs/focus_configuration_addendum.md (session 23, 2026-07-01) + the build plan
    # docs/superpowers/plans/2026-07-02-focus-configuration-layer.md + scripts/build_focus_period.py,
    # and migrated into AI_LAYER_SPEC.md §2. The governing principle for every field here:
    # the STRUCTURED knob is the instruction Python executes; the FREE TEXT is the meaning the LLM
    # reads. Never add a field to capture a feeling or a nuance — that belongs in the free text.
    # `observed` lines below are counted against the 7 live objects on 2026-07-18.

    "Period start": {
        "types": ("Focus Period",),
        "means": "The date this stretch of time begins. Together with `Period end` it defines when "
                 "the period is ACTIVE — the plan loads the period whose range contains today.",
        "not_this": "A narrower free window inside the period — that is `Availability start`.",
        "instead": {"a narrower free window inside the period": "Availability start"},
        "usage": ["Python resolves every calendar fact; the agent must never infer a date or "
                  "weekday. Authoring passes today's date as a deterministic anchor so 'Saturday' "
                  "resolves to a real date."],
        "source": "docs/focus_configuration_addendum.md (Focus Period field table); "
                  "docs/superpowers/plans/2026-07-02-focus-configuration-layer.md Task 1.1; "
                  "AI_LAYER_SPEC.md §2 Focus Period table",
        "observed": "Populated on all 7 live periods. On 4 of the 7 it EQUALS `Period end` — a "
                    "single day — although the design assumes a week-long stretch (one object is "
                    "even named 'Week of Jul 14' with start == end == 2026-07-14). Design and use "
                    "disagree about the grain; reported, not reconciled.",
    },

    "Period end": {
        "types": ("Focus Period",),
        "means": "The date this stretch lapses. Its purpose beyond bounding the range: a lapsed "
                 "period is what triggers the prompt to re-author, so the configuration cannot go "
                 "silently stale — the exact failure this type exists to fix.",
        "not_this": "A deadline for any piece of work.",
        "instead": {"a deadline": "Due date (Task) or Deadline (Project)"},
        "usage": ["Lapsed periods are KEPT, never deleted — history is data for the learning loops "
                  "and a record of how June's phases actually went.",
                  "When no period is active the plan appends a gentle lapse-nudge rather than "
                  "silently planning without a configuration."],
        "source": "docs/focus_configuration_addendum.md ('Gaps the plan must address' — staleness, "
                  "history is a free win); docs/superpowers/plans/"
                  "2026-07-02-focus-configuration-layer.md Task 3.3 / Decision 7",
        "observed": "Populated on all 7 live periods.",
    },

    "Intent": {
        "types": ("Focus Period",),
        "means": "What this stretch of time is about, in June's own words. The primary carrier of "
                 "the period's meaning — read by the planning LLM as framing.",
        "not_this": "Anything the structured fields already hold as an executable instruction "
                    "(which projects are in front, the day's end time, which days are off).",
        "instead": {"which projects are in front": "Foreground projects",
                    "when the day ends": "Workday end",
                    "which days are off or on": "Days off / Days on"},
        "usage": [
            "NEVER reworded by the generator — it is her words (backend spec §17).",
            "This is where the nuance lives, on purpose. The system does not meet June's "
            "variability by predicting circumstances and adding a field for each; the fields are "
            "deliberately minimal and the intelligence is in the READING. If you find yourself "
            "wanting a new field to capture a feeling or a nuance, that is the signal it belongs "
            "here instead.",
            "She authors it by SAYING it — the AI structures it and reflects it back for her to "
            "confirm or edit. She never fills a form.",
        ],
        "source": "docs/focus_configuration_addendum.md ('Where the nuance actually lives', "
                  "'How June inputs it'); docs/review_reorganize_backend_spec.md §17",
        "observed": "Populated on all 7 live periods and consistently rich — several sentences "
                    "carrying capacity, framing and explicit planning instructions (e.g. 'Dev, "
                    "creative, and hobby work is open time June chooses herself - do NOT schedule "
                    "specific hobby tasks'). The most heavily used field on the type.",
    },

    "Availability start": {
        "types": ("Focus Period",),
        "means": "The start of a NARROWER free window inside the period — caregiving days, mornings "
                 "only. Empty means the whole period is available.",
        "not_this": "The period's own bounds — those are `Period start` / `Period end`.",
        "instead": {"the period's own bounds": "Period start / Period end"},
        "usage": ["Structured so Python can test 'is today in the window' deterministically, with "
                  "no natural-language parsing (focus_period.in_availability_window).",
                  "Feeds the output-shape choice: on `Auto`, being inside the window is what makes "
                  "the plan render as a priority list instead of a clock schedule.",
                  "The dates carry only WHEN. What the window MEANS goes in `Availability note`."],
        "source": "docs/focus_configuration_addendum.md (Focus Period field table + 'Reframe'); "
                  "docs/review_reorganize_backend_spec.md §17; scripts/focus_period.py",
        "observed": "Populated on 3 of 7 live periods, always paired with `Availability end`.",
    },

    "Availability end": {
        "types": ("Focus Period",),
        "means": "The end of the narrower free window inside the period.",
        "not_this": "The period's own bounds — those are `Period start` / `Period end`.",
        "instead": {"the period's own bounds": "Period start / Period end"},
        "usage": ["Set together with `Availability start`; the window test needs both."],
        "source": "docs/focus_configuration_addendum.md (Focus Period field table); "
                  "docs/review_reorganize_backend_spec.md §17; scripts/focus_period.py",
        "observed": "Populated on 3 of 7 live periods, always paired with `Availability start`.",
    },

    "Availability note": {
        "types": ("Focus Period",),
        "means": "What the availability window MEANS for planning — how fragmented the time is, "
                 "what kind of work fits it, whether it is wider or narrower than usual. The dates "
                 "say when; this says what to do about it, and this is what the planner reads.",
        "not_this": "A number, a rating, or anything compressed. Never a restatement of the dates.",
        "instead": {},
        "usage": [
            "June: 'this note IS the mechanism… nuance lives here, not in the enum — the "
            "anti-flattening path.' The meaning is never flattened into the dates.",
            "A period may describe as MANY availability shapes as it needs here; the single "
            "structured window exists only for Python's is-today-affected test.",
            "The framing is neutral OVERRIDES, not reductions — a sprint week is MORE availability, "
            "not less. Do not write it as though every period shrinks the day.",
        ],
        "source": "docs/focus_configuration_addendum.md (Focus Period field table, June's note; "
                  "'Reframe: drop the negative reduced framing'); "
                  "docs/review_reorganize_backend_spec.md §17",
        "observed": "Populated on 4 of 7 live periods. All 4 describe REDUCED or fragmented "
                    "availability ('Limited spoon', 'Fragmented or reduced availability due to "
                    "moving assistance'). The 'a period can be MORE' half of the reframe has no "
                    "live use — consistent with `Workday end` being unpopulated on all 7.",
    },

    "Days off": {
        "types": ("Focus Period",),
        "means": "Dates in this period that are forced OFF, overriding the weekly default "
                 "(Sat/Sun, from settings.json). A structured list of ISO dates.",
        "not_this": "Natural language ('the weekend', 'my birthday'). Python must parse it without "
                    "interpreting text.",
        "instead": {"why the day is off, or what it means": "Intent / Availability note"},
        "usage": [
            "Structured, not natural language — deterministically testable, honoring the "
            "regex-burn lesson (no NL scanning anywhere in the calendar path).",
            "Precedence in focus_period.is_day_off: an explicit `Days on` date wins first, then "
            "`Days off`, then the weekly default.",
            "The point is to break the planner's hidden assumption that EVERY day is a full work "
            "day — a wrong default for June.",
            "A malformed list must surface to June, never be silently dropped: a silently-ignored "
            "day off that plans a workday is quietly punitive.",
        ],
        "source": "docs/focus_configuration_addendum.md (Focus Period field table, `days_off` row + "
                  "June's weekly-default recommendation); docs/superpowers/plans/"
                  "2026-07-02-focus-configuration-layer.md Tasks 2.1/2.2 + step 2 of Task 3.3; "
                  "scripts/build_focus_period.py",
        "observed": "UNPOPULATED on all 7 live periods (2026-07-18) — only `Days on` is used. "
                    "Encoding note: the build plan's tests use a JSON array; "
                    "focus_period_adapter._csv writes comma-separated and every live value is "
                    "comma-separated. focus_period._parse_date_list accepts both, so nothing is "
                    "broken, but the plan's stated shape is not the one in the data.",
    },

    "Days on": {
        "types": ("Focus Period",),
        "means": "Dates in this period that are forced to be WORK days, overriding a weekly default "
                 "that would otherwise make them off (e.g. working a Saturday). A structured list "
                 "of ISO dates.",
        "not_this": "Natural language. Same deterministic-parsing constraint as `Days off`.",
        "instead": {"why the day is on, or what it means": "Intent / Availability note"},
        "usage": ["Highest precedence in focus_period.is_day_off — a `Days on` date beats both "
                  "`Days off` and the weekly default.",
                  "Only meaningful for a day the weekly default would otherwise mark off; writing "
                  "an already-working weekday here is harmless but says nothing."],
        "source": "docs/focus_configuration_addendum.md (Focus Period field table, June's "
                  "'overridable both ways per day'); docs/superpowers/plans/"
                  "2026-07-02-focus-configuration-layer.md Task 2.2; scripts/build_focus_period.py",
        "observed": "Populated on 4 of 7 live periods, comma-separated. Only ONE of those 4 carries "
                    "a real override (Sat 2026-07-18); the other 3 list days that are ALREADY work "
                    "days under the Sat/Sun default — redundant, not wrong. Separately: "
                    "docs/review_reorganize_backend_spec.md §17 still calls this field 'stubbed in "
                    "the UI but not yet a committed field — leave OPEN'. That is stale: it is a "
                    "committed field, parsed and populated. Reported, not reconciled.",
    },

    "Output format": {
        "types": ("Focus Period",),
        "means": "The shape the day's plan is rendered in: Auto / Clock schedule / Priority list. "
                 "A per-period override of how the plan looks, not of what is in it.",
        "not_this": "A priority, a capacity level, or how hard June is working.",
        "instead": {"how much capacity this stretch has": "Availability note / Intent"},
        "usage": [
            "A clock-time schedule literally cannot express 'a couple of hours, whenever they "
            "come' — forcing it is an instance of June's own output-format-bias principle, where "
            "the wrong output shape distorts the result. Priority list is the answer to that: a "
            "priority-ordered short list to pull from when a window opens.",
            "The priority-list shape is ADHD-friendly by design — few items, plain language, no "
            "clock pressure, a clear 'when you get a window, do this next.'",
            "`Auto` resolves from STRUCTURED inputs only (focus_period.resolve_output_shape): "
            "priority iff today is inside the availability window. The capacity nuance is the "
            "model's to read from free text, never Python's to scan.",
        ],
        "source": "docs/focus_configuration_addendum.md ('When the day has no fixed shape, the plan "
                  "changes shape too'); docs/review_reorganize_backend_spec.md §17; "
                  "scripts/focus_period.py resolve_output_shape",
        "observed": "Populated on 6 of 7 live periods: Auto x4, Clock schedule x1, Priority list x1.",
    },

    "Workday start": {
        "types": ("Focus Period",),
        "means": "The clock time 'HH:MM' the workday starts for this period. Empty means the "
                 "system default (10:00).",
        "not_this": "A wake-up time, and not a statement about capacity.",
        "instead": {"what this stretch feels like or demands": "Intent / Availability note",
                    "a narrower stretch of DAYS inside the period": "Availability start / end"},
        "usage": ["The companion to `Workday end`, added for backend spec §17 — the day-bounds "
                  "logic was end-only, so a period could say 'work till 22:00 this sprint' but "
                  "not 'don't start me before 11' on a slow-morning stretch.",
                  "It moves the FLOOR only. A plan generated after this time still starts now — "
                  "the field never schedules work into the past.",
                  "Distinct from Availability start, which is a DATE bounding which days are "
                  "free; this is a CLOCK time bounding the hours within a day."],
        "source": "docs/review_reorganize_backend_spec.md §17 (flagged NEW there); "
                  "scripts/plan_generate.py day-bounds; scripts/build_focus_period.py",
        "observed": "NOT YET ON THE LIVE TYPE (2026-07-18). The builder was edited to add it but "
                    "deliberately not run — schema writes to June's space are human-gated "
                    "(docs/BUILD_DOC.md §2). Every reader/writer is wired and inert until then.",
    },

    "Workday end": {
        "types": ("Focus Period",),
        "means": "The clock time 'HH:MM' the workday ends for this period. Empty means the system "
                 "default (18:00).",
        "not_this": "A deadline, and not a statement about capacity.",
        "instead": {"what this stretch feels like or demands": "Intent / Availability note"},
        "usage": ["Designed to be pushed WIDER for a sprint (working till 10, 11, midnight) or "
                  "narrower for a gentle week — June asked for this explicitly. It is the field "
                  "that carries the 'a period can be MORE, not less' half of the design.",
                  "Wired into the scheduler's end time, overriding the hardcoded default."],
        "source": "docs/focus_configuration_addendum.md ('Workday bounds' under the overrides "
                  "list); docs/superpowers/plans/2026-07-02-focus-configuration-layer.md Task 3.3",
        "observed": "UNPOPULATED on all 7 live periods (2026-07-18) — the widening case the field "
                    "was built for has never been used. Separately, "
                    "the companion `Workday start` (backend spec §17) is now BUILT in code — "
                    "the day-bounds logic reads both ends — but its schema write is still "
                    "pending June's approval; see that field's entry.",
    },

    "Foreground projects": {
        "types": ("Focus Period",),
        "means": "The projects June has put IN FRONT for this stretch — overriding their enduring "
                 "per-project `Engagement` while the period is active.",
        "not_this": "A permanent change to how she engages the project. When the period lapses the "
                    "project's own Engagement returns.",
        "instead": {"a lasting change to how she engages a project": "Engagement",
                    "the specifics of what that engagement means": "Engagement notes"},
        "usage": [
            "This is the short-term layer of a two-layer model: the Project holds the enduring "
            "default, the period overrides it while active, and when the two contradict THE PERIOD "
            "WINS (June's decision).",
            "Drives REAL selection by object id — not a prose hint handed to the LLM.",
            "A sprint is expressed here, as a foreground action for a period. It is deliberately "
            "NOT a stored Engagement value (`Sprint` was retired 2026-07-16) and never a Goal-level "
            "state.",
        ],
        "source": "docs/focus_configuration_addendum.md ('Two layers' + precedence + 'Foreground "
                  "overrides'); docs/superpowers/plans/2026-07-02-focus-configuration-layer.md "
                  "Task 3.2; AI_LAYER_SPEC.md §2 Project `engagement` retirement note",
        "observed": "Populated on all 7 live periods (1-4 projects each) — with `Intent`, the most "
                    "used field on the type. NOTE: a field with this same display name also exists "
                    "on the live Goal type, where no doc explains what it means; that one stays in "
                    "UNDEFINED as 'Foreground projects (on Goal)'.",
    },

    "Paused projects": {
        "types": ("Focus Period",),
        "means": "Projects held OUT of plan generation entirely while this period is active — an "
                 "explicit stop, not a de-prioritization.",
        "not_this": "Everything that is merely not foreground. Non-foreground is NOT paused: those "
                    "projects stay present and are simply scheduled after the foreground ones.",
        "instead": {"a project that is just not in front right now": "leave it out of both lists"},
        "usage": [
            "Pausing must be RARE — explicit-stop only. Default is an empty list. It requires June "
            "having said something like 'stop X this period'.",
            "The first LLM authoring run over-paused, pausing every non-foreground project, which "
            "DROPS their tasks from the plan. The authoring prompt was tuned to require an "
            "explicit stop; that correction is the reason this rule exists.",
            "Pickers filter to 'pausable' projects — only those that would normally populate the "
            "plan (not Backburner/Done engagement, not Parked/Inactive status).",
        ],
        "source": "docs/superpowers/plans/2026-07-02-focus-configuration-layer.md "
                  "('Learned from first real use', commit 2a85dbd); "
                  "docs/review_reorganize_backend_spec.md §17",
        "observed": "UNPOPULATED on all 7 live periods (2026-07-18) — consistent with the "
                    "pause-is-rare rule holding in practice after the prompt was tuned.",
    },
}


# --- the short grain: one line, sits under a form control --------------------
# Kept as ONE dict rather than a key inside each entry on purpose: these are exactly the strings
# June sees in the UI, so they need to be reviewable as a SET — scannable end-to-end in one pass
# when she verifies or revises them. Each one compresses its FIELDS entry; it adds no new claim.
# A field with an entry but no hint here falls back to the first sentence of `means`.

HINTS = {
    "Affective": "How June feels about this, in her words — not status or findings. Never a number.",
    "Access notes": "What's in the way of starting it, when no tag fits. Left empty if unsure.",
    "Blocked on": "What is concretely being waited for.",
    "Context": "Findings, confirmations, origin — everything else. The catch-all, and the safe default.",
    "Access conditions": "The queryable access tags only; anything else goes in Access notes.",
    "Duration min": "Estimated minutes. Write Duration source alongside it.",
    "Duration source": "Where the duration came from: June stated it, or the AI estimated it.",
    "Deadline": "The project's deadline. Only when it's real.",
    "Due date": "The deadline. Not the day it's planned for.",
    "Scheduled": "The day the plan placed this. Not a deadline.",
    "Engagement": "How June is engaging with this project now. Steady / Open / Backburner.",
    "Engagement notes": "The specifics the dropdown can't hold — cadence, thresholds, a deadline.",
    "Goal engagement": "Whether this whole life area is getting attention now.",
    "Task status": "Ready / In Design / Parked / Needs Clarifying / Blocked / Done.",
    "Goal status": "Active / Parked / Achieved.",
    "Project status": "Legacy — use Engagement instead.",
    "Strategy status": "Active or Retired. Retiring one is expected, not failure.",
    "What for": "When and where to apply this strategy.",
    "Learning notes": "What this strategy needs that it isn't doing yet.",
    "Reaching for": "The why. June authors it for top-level goals; the AI proposes elsewhere.",
    "Barriers": "The 'I don't know how to…' open question. Never turned into a task.",
    "Horizon": "Chapter (ends when a condition is met) / Ongoing / Milestone.",
    "Resolution condition": "What this goal looks like when it stops claiming attention.",
    "Description": "What this project is and how it's approached.",
    "Goal link": "The Goal(s) this project serves.",
    "Linked Projects": "The Project(s) this task belongs to.",
    "Project link": "The project this recurring item serves.",
    "Parent project": "The project this one sits under.",
    "Depends on": "Hard dependencies only — can't start until that's done. Parallel is the default.",
    "Arc position rationale": "Full sentences: where this sits in the project arc, and why.",
    "Relevant docs": "Files or folders the AI should read before working on this.",
    "AI autonomous": "Can the AI do this with minimal oversight?",
    "Done": "The completion checkbox. Rest counts as a real, checkable task.",
    "Side": "Life domain: Obligation / Wellbeing / Fun-hobby / Daily life. Not a priority.",
    "Block chunk min": "How many minutes one work chunk on this project should be.",
    "Interval unit": "day / week / month / as_needed.",
    "Interval count": "The N in 'every N days/weeks/months'.",
    "Day of week": "Only for items pinned to specific days. Empty for un-anchored routines.",
    "Time of day": "HH:MM. When set, this is a fixed anchor the day flows around.",
    "Fixed appointment": "A missed one returns on its own schedule instead of persisting.",
    "Active": "On/off for whether this recurring item is in the daily plan. Only takes effect on as-needed.",
    "Day of month": "The day number a monthly item is due on. Unset means it is never due.",
    "Frequency": "Legacy — use Interval unit and Interval count.",
    "Period start": "The day this stretch of time begins.",
    "Period end": "The day it lapses. Lapsing is what prompts June to write the next one.",
    "Intent": "What this stretch is about, in June's words. The nuance goes here, not in new fields.",
    "Availability start": "Start of a narrower free window inside the period. Empty = the whole period.",
    "Availability end": "End of that narrower free window.",
    "Availability note": "What the window means for planning — the part the planner actually reads.",
    "Days off": "Dates forced off, overriding the weekly default. ISO dates, never words.",
    "Days on": "Dates forced to be work days, overriding the weekly default. ISO dates, never words.",
    "Output format": "The plan's shape: Auto, a clock schedule, or a priority list to pull from.",
    "Workday start": "HH:MM the day starts. Push it later for a period of slow mornings.",
    "Workday end": "HH:MM the day ends. Push it later for a sprint, earlier for a gentle week.",
    "Foreground projects": "Projects in front this period. Overrides their Engagement while it's active.",
    "Paused projects": "Projects stopped this period. Rare — only when June explicitly says to stop one.",
}


# --- illustrations, deliberately plural --------------------------------------
# WHY THIS SHAPE (June, 2026-07-18): "if you give one specific example, the model may replicate
# your example in its output for the text fields. which is tricky because your example is
# clarifying." She is right, and it is a real hazard: a single quoted specimen sitting inside a
# definition an LLM reads right before writing teaches the SHAPE and hands over a PHRASE, and the
# phrase is what ends up in her data.
#
# The fix, applied to every free-text field with no exceptions:
#   1. `means` names the KIND of thing, never a specimen. Specimens are out of the definition.
#   2. Illustrations live HERE, always THREE OR MORE, deliberately varied in length, register and
#      grammar so there is no single dominant pattern to copy.
#   3. They are rendered under an explicit do-not-reuse banner wherever they are shown.
# One example is a template. Several dissimilar ones can only be read as a range.

EXAMPLES_BANNER = ("Illustrations of the KIND of content only — NOT a template and NOT a "
                   "vocabulary. Write what is actually true of this item, in June's words. Do "
                   "not reuse, adapt, or echo the wording below.")

# Every field here is free text an agent might compose. The list is the test's subject too:
# a free-text field with fewer than three illustrations fails `tests/test_field_semantics.py`.
FREE_TEXT_FIELDS = (
    "Affective", "Access notes", "Blocked on", "Context", "Barriers", "Engagement notes",
    "Reaching for", "Resolution condition", "Description", "Arc position rationale",
    "Learning notes", "What for", "Relevant docs", "Intent", "Availability note",
)

EXAMPLES = {
    "Affective": ("dreading it", "keeps sliding — I think I'm avoiding it",
                  "actually excited about this one, first time in weeks",
                  "not scared of it, just flat about it"),
    "Access notes": ("hard to start cold; needs someone to sit with me for the first ten minutes",
                     "phone call — I put these off for weeks",
                     "too many open tabs of decision before anything can be typed",
                     "fine lying down, impossible at a desk"),
    "Blocked on": ("waiting on the landlord's reply", "the portal is down",
                   "needs Julia's spec before anything can be drafted",
                   "insurance card hasn't arrived"),
    "Context": ("confirmed 2026-07-02: the screen does not allow AI tools",
                "came out of the Tuesday conversation with M.",
                "there are two versions of this file and the newer one is in Drive, not the repo",
                "she has asked twice; the second ask was more urgent than the first"),
    "Barriers": ("as a PhD I'm overqualified and never know how to handle that in a cover letter",
                 "don't know whether to pitch this as a paper or a tool",
                 "no idea what a reasonable rate would be to ask for",
                 "unclear who the audience even is"),
    "Engagement notes": ("Steady: about half an hour a day, mornings",
                         "Backburner until after the surgery recovery",
                         "opens up once the grant decision lands",
                         "weighed against the article — whichever has the nearer date"),
    "Reaching for": ("income that covers rent without contract work",
                     "being able to work without pain by the autumn",
                     "a practice that keeps going when the job situation changes",
                     "staying in touch with the people who matter"),
    "Resolution condition": ("until income covers basic needs and the GA decision is made",
                             "when the manuscript is accepted somewhere",
                             "when the move is finished and the boxes are gone",
                             "when I no longer need the brace"),
    "Description": ("a short article for a general audience, drafted then workshopped",
                    "the household admin that keeps the flat running",
                    "rebuilding the tool's front end so it works on a phone",
                    "physiotherapy and the appointments around it"),
    "Arc position rationale": (
        "This sits early in the arc because everything downstream reads the schema it defines, so "
        "changing it later would mean redoing the work that depends on it.",
        "This comes last on purpose. It is polish, and doing it before the shape is settled would "
        "mean polishing something that is about to change.",
        "This runs in parallel with the drafting rather than after it, because the two inform each "
        "other and doing them in sequence loses that.",
    ),
    "Learning notes": ("this one only fires when I'm already calm — needs a version for bad days",
                       "worked in June, stopped working once the schedule got fragmented",
                       "too abstract to act on; needs a concrete first move attached",
                       "still good, no change needed as of this month"),
    "What for": ("When planning a day that involves leaving the house.",
                 "At the point of sitting down to write, before opening anything else.",
                 "Whenever a task has been carried over three days running.",
                 "When the plan has more than four items on it."),
    "Relevant docs": ("~/Documents/papers/anthro-article/",
                      "the shared Drive folder for the grant, plus the PDF of the call",
                      "docs/api_contract_v2.md",
                      "the email thread with the clinic, in Mail"),
    "Intent": ("A slow week. Recovery is the point; anything else is a bonus.",
               "Sprint on the application. Everything else waits until it is sent.",
               "Caregiving most days. Short windows only, and I don't know when they'll come.",
               "Back to normal after the move. Ease in rather than starting at full speed."),
    "Availability note": ("caregiving; fragmented time; no deep-focus blocks",
                          "mornings only, and the mornings are good ones",
                          "more time than usual this week, not less — evenings are free",
                          "in and out of appointments; assume interruptions"),
}


# --- WHAT THE FIELD DOES -----------------------------------------------------
# `means` says what belongs in a field. This says what HAPPENS when it is set — June, 2026-07-18:
# "we want to make sure the semantic explanations help the LLM actually navigate the system and
# how it works correctly." A model filling in a field should know the consequence, not only the
# definition, because the consequence is what makes a wrong value expensive.
#
# THREE STATUSES, and the distinction is load-bearing. Several of these fields are waiting on
# design that has not happened yet. That is a normal state for a system still being built, NOT a
# defect, and it must not be written as one:
#
#   live       — something actually reads or writes it now. Says what, and what changes.
#   planned    — designed, not built. Says where the design is, so it can be read.
#   undesigned — it exists, nothing reads or writes it, and no plan was found. Stated once,
#                plainly, with no editorial. An undesigned field is not a broken field.
#
# Kept as its own dict, like HINTS, so the runtime picture is reviewable as a SET — and so the
# ONE thing most likely to go stale sits in ONE place. See docs/BUILD_DOC.md §3 clause 5: a build
# that changes what reads or writes a field updates that field's entry here, in the same commit.
#
# `written_by` answers a question June asked directly of `Last surfaced` — "the llm wouldn't write
# to this path, right? That would be updated by python?" — which is exactly the kind of thing an
# agent needs and could not previously find anywhere.

DOES_STATUSES = ("live", "planned", "undesigned")

DOES = {

    # ---- the free-text routing group --------------------------------------
    "Affective": {
        "status": "live",
        "written_by": "The capture path (capture_generate.py) and ANY agent writing directly "
                      "through gsdo_objects / the MCP server. There is no validator on the "
                      "content — the only mechanical check is guard #3, which refuses a bare "
                      "number. Everything else about whether the text is affect is your judgment.",
        "read_by": "daily_plan.py loads it and passes it into the planning prompt, so what you "
                   "write here is read back to June as part of how her day is described. A status "
                   "note written here becomes the plan's account of how she FEELS about the item.",
    },
    "Access notes": {
        "status": "planned",
        "written_by": "Nothing writes it today; the live space is empty of it. The intended "
                      "writer is the AI at capture/weeding time, proposing from what June says. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "No code reads it yet. It is designed as the place unnamed barriers accumulate "
                   "so recurring ones can be promoted to real tags — AI_LAYER_SPEC.md §2 Task "
                   "`access` row + the §6 promotion loop. June, 2026-07-18: surfacing the field "
                   "and its purpose is the intended remedy for its emptiness.",
    },
    "Blocked on": {
        "status": "live",
        "written_by": "The capture path and direct agent writes.",
        "read_by": "daily_plan.py; prompts/daily_list.md and prompts/daily_memory_pass.md instruct "
                   "the planner on it. When set it becomes the item's displayed line — the plan "
                   "shows what is being waited for instead of asking her to act.",
    },
    "Context": {
        "status": "live",
        "written_by": "Every write path: capture, the weeding gate (prompts/weeding_gate.md), the "
                      "MCP server, the app, direct agent writes.",
        "read_by": "The most widely read text field in the system — daily_plan.py, plan_generate.py, "
                   "status_check.py, focus_period_generate.py all load it in full into the model's "
                   "context, and the app renders it. ⚠ Do NOT write your own filing rationale here: "
                   "an agent's reasoning about WHY it filed something belongs in the write log, not "
                   "in a field June reads. That misroute was real and was closed in commit e39dd5b.",
    },
    "Access conditions": {
        "status": "live",
        "written_by": "The capture path (capture_fields.ALLOWED_ACCESS) and the app's detail pane. "
                      "An unknown tag name is dropped, never created.",
        "read_by": "daily_plan.py reads it ON A TASK, for low-capacity filtering and errand "
                   "batching. On a PROJECT it is live in the schema but nothing reads it yet "
                   "(docs/BUILD_DOC.md Track B §4), so a tag set there does not currently reach "
                   "the plan. PLANNED ADDITION: docs/review_reorganize_backend_spec.md §6 adds "
                   "`Requires-deep-thinking`, `Involves-bureaucracy` and `Induces-pain` (§6 gives "
                   "behaviour only for Induces-pain: a capacity signal the scheduler and model "
                   "weigh, deprioritised on low-capacity days and paired with rest, kept as a tag "
                   "and never a number). Another thread is building these; until they exist, "
                   "writing them does nothing because unknown tags are dropped.",
    },

    # ---- durations, dates -------------------------------------------------
    "Duration min": {
        "status": "live",
        "written_by": "The capture path, and the app.",
        "read_by": "scheduler.py places the day around it, grain.py sizes work blocks from it, "
                   "daily_plan.py and plan_generate.py both read it. It is the single number that "
                   "decides how much of June's day an item is allowed to claim — a wrong estimate "
                   "here shows up as a day that does not fit.",
    },
    "Duration source": {
        "status": "planned",
        "written_by": "The capture path, always alongside Duration min.",
        "read_by": "Nothing reads it yet. It exists so the duration-bias learning loop can "
                   "separate June's own numbers from the model's guesses "
                   "(scripts/capture_fields.py build_optional_props). Recording it now is what "
                   "makes that loop possible later; the data cannot be reconstructed after the fact.",
    },
    "Due date": {
        "status": "live",
        "written_by": "Not written by any Python path — set by June in the app or in Anytype. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "daily_plan.py and plan_generate.py: it drives urgency and ordering, and the "
                   "within-thread pick uses the nearest deadline to choose what surfaces.",
    },
    "Scheduled": {
        "status": "live",
        "written_by": "plan generation (capture_generate.py, server.py) — it records a placement "
                      "the system made, or June moving an item.",
        "read_by": "daily_plan.py, plan_generate.py, grain.py, block_duration.py, status_check.py, "
                   "and the app's plan view. A future-dated Scheduled keeps an item out of today.",
    },
    "Deadline": {
        "status": "live",
        "written_by": "The capture path; the app's detail pane.",
        "read_by": "daily_plan.py and plan_generate.py load it into the planning context.",
    },

    # ---- engagement -------------------------------------------------------
    "Engagement": {
        "status": "live",
        "written_by": "The capture path (default Open for a new project), the weeding gate, "
                      "server.py, and the app.",
        "read_by": "The most consequential select on Project. daily_plan.py, plan_generate.py, "
                   "grain.py, neglect.py, block_duration.py, status_check.py and "
                   "focus_period_generate.py all gate on it, and the app shows it as a chip. "
                   "Setting Backburner removes a project from the daily plan until a neglect "
                   "threshold; Done removes it entirely. This value decides whether June sees the "
                   "project at all.",
    },
    "Engagement notes": {
        "status": "live",
        "written_by": "The capture path and the weeding gate.",
        "read_by": "daily_plan.py passes it to the planner as the authoritative statement of what "
                   "the Engagement value MEANS for this project right now.",
    },
    "Goal engagement": {
        "status": "live",
        "written_by": "Nothing writes it — June sets it in the app or in Anytype. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "daily_plan.py:114 loads it and daily_plan.py:415 prints it on the goal's line "
                   "in the planning prompt, with the instruction that Steady reads as normal and "
                   "Backburner is noted but de-emphasised. ⚠ CORRECTION 2026-07-18: this entry "
                   "previously said the field was 'not yet consumed by code'. It is consumed, as "
                   "framing for the model. The cross-goal balancing engine (§8d) that would use it "
                   "for real prioritisation is still unbuilt.",
    },

    # ---- statuses ---------------------------------------------------------
    "Task status": {
        "status": "live",
        "written_by": "The capture path, the weeding gate, the MCP server, server.py, the app.",
        "read_by": "daily_plan.py, grain.py, neglect.py. Parked takes a task out of the daily plan "
                   "and the orient map; Blocked makes the plan display `Blocked on` instead of an "
                   "action. Legacy `Active` is treated as Ready.",
    },
    "Goal status": {
        "status": "live",
        "written_by": "Nothing writes it — set by June. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "daily_plan.py:104-105, and only when the object's type key is `gsdo_goal`. "
                   "OPEN QUESTION, June's own, recorded as a question and not answered here: "
                   "\"im not sure what the goal status is either, other than perhaps a mechanism "
                   "for allowing us to retire goals?\" That is her speculation about the field's "
                   "purpose, not a decision, and no doc settles it.",
    },
    "Project status": {
        "status": "undesigned",
        "written_by": "Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "Nothing in scripts/ reads it; the app's detail pane still displays it. "
                   "Superseded by Engagement, which is what the plan actually gates on.",
    },
    "Strategy status": {
        "status": "live",
        "written_by": "capture_generate.py:392 sets it to Active when a strategy is adopted.",
        "read_by": "daily_plan.py:252-253 filters the strategy set on it — only Active (or unset) "
                   "strategies are loaded into the planning prompt. Setting Retired takes a "
                   "strategy out of every plan from that point on.",
    },

    # ---- Strategy ---------------------------------------------------------
    "What for": {
        "status": "live",
        "written_by": "Nothing writes it — June writes it, in the app or in Anytype. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "daily_plan.py:258 loads it and it is printed under 'Active strategies' in the "
                   "planning prompt, so it is read by the model on every plan.",
    },
    "Learning notes": {
        "status": "planned",
        "written_by": "Nothing writes it; unused across her 12 live Strategy objects.",
        "read_by": "No code reads it. The app displays it (strategyFields.ts). It IS defined in "
                   "the spec — AI_LAYER_SPEC.md §2 Strategy calls it \"the anti-forgetting field: "
                   "what this strategy needs that it isn't doing yet; annotations on whether it's "
                   "still working. A learning loop targets this field so the strategy improves "
                   "instead of silently failing — and so June is reminded the system is revisable, "
                   "not stuck.\" AI_LAYER_SPEC.md:505 lists that loop as still open, to be designed "
                   "once strategies have accumulated real annotations.",
    },

    # ---- the why-fields ---------------------------------------------------
    "Reaching for": {
        "status": "live",
        "written_by": "The weeding gate proposes it for sub-goals and Projects; top-level Goals "
                      "are June's to author.",
        "read_by": "daily_plan.py:417 and plan_generate.py print it on the goal's line, so it "
                   "reaches the model as the reason the goal exists.",
    },
    "Barriers": {
        "status": "planned",
        "written_by": "Nothing writes it in code; the weeding-gate example set references it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "No code reads it. June, 2026-07-18: \"Keep this — its pending further design.\" "
                   "docs/route_structure_assessment_2026-07-12.md §5 names 'barriers never "
                   "resurface' as the missing piece — the resurfacing, not the definition.",
    },
    "Horizon": {
        "status": "undesigned",
        "written_by": "Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "Nothing reads it. ⚠ CORRECTION 2026-07-18: this entry previously said it "
                   "'feeds Goal ordering' and that the AI reads it to choose narration register. "
                   "That is the spec's intent (AI_LAYER_SPEC.md §2 Goal), not built behaviour — no "
                   "ordering or register code reads Horizon. The app uses it for chips and tabs.",
    },
    "Resolution condition": {
        "status": "live",
        "written_by": "Nothing writes it — June's, via the app or the weeding gate's proposal. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "daily_plan.py:113 loads it and :420 prints it as 'resolved when: …' on the "
                   "goal's line in the planning prompt.",
    },
    "Description": {
        "status": "live",
        "written_by": "The capture path, the MCP server, server.py, the app.",
        "read_by": "daily_plan.py, plan_generate.py, status_check.py and the app's plan view.",
    },

    # ---- links ------------------------------------------------------------
    "Goal link": {
        "status": "live",
        "written_by": "The capture path, the MCP server, gsdo_objects (which drops a wrong-kind "
                      "link rather than writing it).",
        "read_by": "daily_plan.py:147 — the alignment chain the plan uses to say which goal a "
                   "piece of work serves. (Read nowhere before the 2026-07-14 loader fix.)",
    },
    "Linked Projects": {
        "status": "live",
        "written_by": "The capture path, the MCP server, gsdo_objects, api_write.move_object. "
                      "Also api_write.convert_type (backend spec §5): a type conversion RELINKS the parent onto whichever of these properties the new type uses, and clears the one it converted away from, so the tree never reaches the object two ways.",
        "read_by": "daily_plan.py, plan_generate.py, grain.py, neglect.py, "
                   "focus_period_generate.py. It is how a task inherits its project's engagement, "
                   "Side and grain — an unlinked task is a bare chore with no inheritance.",
    },
    "Project link": {
        "status": "live",
        "written_by": "The capture path, the MCP server, gsdo_objects, api_write.move_object. "
                      "Also api_write.convert_type (backend spec §5): a type conversion RELINKS the parent onto whichever of these properties the new type uses, and clears the one it converted away from, so the tree never reaches the object two ways.",
        "read_by": "daily_plan.py, for the recurring item's project association.",
    },
    "Parent project": {
        "status": "live",
        "written_by": "server.py (the move operation), api_write.move_object. "
                      "Also api_write.convert_type (backend spec §5): a type conversion RELINKS the parent onto whichever of these properties the new type uses, and clears the one it converted away from, so the tree never reaches the object two ways.",
        "read_by": "daily_plan.py:170-180 walks it upward to inherit Side, and the app's map "
                   "renders the nesting. This is the edge that makes work streams work.",
    },
    "Depends on": {
        "status": "undesigned",
        "written_by": "Nothing writes it.",
        "read_by": "Nothing reads it. Documented in the per-repo binding scripts/gsdt_bind.py "
                   "generates; no ordering code consumes it and no plan for one was found.",
    },
    "Arc position rationale": {
        "status": "live",
        "written_by": "An agent working on the repo, through the binding protocol in "
                      "scripts/gsdt_bind.py.",
        "read_by": "No Python path reads it. Its reader is a PERSON or an AGENT opening the "
                   "object — it exists so the reasoning survives across sessions instead of being "
                   "re-derived (guard #6). Agent-facing by design, so 'the plan path does not read "
                   "it' is not the right test of whether it works.",
    },

    # ---- misc Task/Project ------------------------------------------------
    "Relevant docs": {
        "status": "planned",
        "written_by": "Nothing writes it. field_semantics previously said the weeding gate "
                      "populates it; no prompt in prompts/ mentions it, so that was not accurate. "
                      "June can set it by hand in the review surface (review_surface.py:43). ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "Nothing reads it, and the plan path is the wrong place to look — its consumer "
                   "is an AGENT about to work the item. June, 2026-07-18: \"Need to be fixed.\" "
                   "Concretely, fixed means three things: (1) the MCP server exposes it — "
                   "cd_mcp_server.list_tasks returns only id/name/status and there is no "
                   "get_task(id) tool at all, so a full-field read tool is the missing seam; "
                   "(2) the drift skill gains a READ-side rule to match its write-routing table, "
                   "telling an agent to open these paths before starting; (3) something populates "
                   "it — capture should set it when an item names a file or an external system.",
    },
    "AI autonomous": {
        "status": "planned",
        "written_by": "Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "Nothing reads it, and again the plan path is the wrong test. June: it is "
                   "\"useful more in the agent-facing interface\" — an agent deciding whether it "
                   "can just do the task. Same missing seam as Relevant docs: not returned by any "
                   "MCP tool, not mentioned in the drift skill.",
    },
    "Done": {
        "status": "live",
        "written_by": "Everything: check-off in the app, the MCP server's complete_task, "
                      "server.py, the capture path.",
        "read_by": "Everything: daily_plan.py, plan_generate.py, grain.py, neglect.py, "
                   "status_check.py, and roughly twenty app components. Checking it removes the "
                   "item from the plan and feeds the completion record.",
    },
    "Side": {
        "status": "live",
        "written_by": "The capture path, the weeding gate, server.py, focus_period_author.py, and "
                      "the app's detail pane (on Project and sub-project only — not on work "
                      "streams, goals or tasks). ⚠ A RENAME IS AGREED: June, 2026-07-18, "
                      "\"lets rename to work\" — Obligation becomes Work per "
                      "docs/review_reorganize_backend_spec.md §12. Another thread is applying it; "
                      "until then the live option is still `Obligation`, and only live option "
                      "names may be written.",
        "read_by": "This is the field with the widest visible consequence, so what it does is "
                   "worth knowing precisely. BACKEND — grain.py:21-40 is the whole rule, and it "
                   "runs on every plan (daily_plan.py, plan_generate.py, "
                   "focus_period_generate.py). `Fun / hobby` → the project is EXCLUDED from the "
                   "plan; its tasks are pulled out (daily_plan.partition_by_side) and replaced by "
                   "one open self-directed block, so the time is protected but June picks what "
                   "goes in it. `Daily life` → rendered at TASK grain: the specific chore appears "
                   "by name. `Obligation` / `Wellbeing` → rendered as a work block (\"work on X\"); "
                   "no code distinguishes the two in selection. Side is also printed on the "
                   "project's line in the planning prompt. Descendants inherit it from the nearest "
                   "ancestor that sets it (daily_plan.py:170-180; app/src/model/fields.ts sideOf). "
                   "FRONTEND — it renders as a labelled chip on the project row (one uniform "
                   "colour: the chip says WHICH side by its word, never by hue), and it is the "
                   "Map's filter axis (FilterMenu.tsx → MapScreen.tsx), so setting it decides "
                   "which subtrees are reachable when June filters. A node with no Side anywhere "
                   "in its chain fails every specific filter and disappears from a filtered map. "
                   "The Routines tab deliberately ignores the Side filter.",
    },
    "Block chunk min": {
        "status": "live",
        "written_by": "Nothing writes it — June's durable preference, set on the project. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "block_duration.py and daily_plan.py, to size one work chunk on this project. "
                   "Read by DISPLAY NAME, because its Anytype key is auto-generated.",
    },

    # ---- Recurring --------------------------------------------------------
    "Interval unit": {
        "status": "live",
        "written_by": "The capture path.",
        "read_by": "datetime_seam.py:105-141 — it selects the whole due-today branch. It also "
                   "decides whether `Active` means anything: on `as_needed` the Active checkbox IS "
                   "the due-today answer; on day/week/month Active is never consulted.",
    },
    "Interval count": {
        "status": "live",
        "written_by": "Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "datetime_seam.py, for day and week units. ⚠ It is IGNORED for `month`: "
                   "datetime_seam.py:22-24 records that v1 fires monthly regardless of N, because "
                   "every-N-months needs a stored start anchor the system does not keep. So "
                   "'every 3 months' currently runs every month.",
    },
    "Day of week": {
        "status": "live",
        "written_by": "Nothing writes it; the app's recurrence card edits it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "datetime_seam.py, for week-unit items. Empty means un-anchored.",
    },
    "Time of day": {
        "status": "live",
        "written_by": "Nothing writes it; the app's recurrence card edits it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "datetime_seam.py and daily_plan.py — it makes the item a fixed anchor the "
                   "day's flexible work is arranged around, rather than something the scheduler "
                   "may move.",
    },
    "Fixed appointment": {
        "status": "live",
        "written_by": "Nothing writes it; a checkbox June sets.",
        "read_by": "plan_generate.py:621,643 — a missed Fixed-appointment recurring is SKIPPED by "
                   "the persistence rule and waits for its next cadence instead of carrying "
                   "forward.",
    },
    "Frequency": {
        "status": "undesigned",
        "written_by": "Nothing writes it.",
        "read_by": "Nothing reads it. Legacy from the v1 prototype, replaced by Interval unit + "
                   "Interval count. It may still exist in the space; ignore it.",
    },

    # ---- Focus Period -----------------------------------------------------
    "Period start": {
        "status": "live",
        "written_by": "focus_period_author.py, from June speaking the period aloud. Python anchors "
                      "the date; the model never resolves a weekday itself.",
        "read_by": "focus_period.py — with Period end it decides WHICH period is active, and the "
                   "active period is what the whole plan is generated under.",
    },
    "Period end": {
        "status": "live",
        "written_by": "focus_period_author.py.",
        "read_by": "focus_period.py. When today is past it, no period is active and the plan "
                   "appends a gentle prompt to write a new one rather than planning without a "
                   "configuration. Lapsed periods are kept, never deleted.",
    },
    "Intent": {
        "status": "live",
        "written_by": "focus_period_author.py, in June's own words, NEVER reworded by the "
                      "generator (backend spec §17).",
        "read_by": "daily_plan.py, plan_generate.py, focus_period_generate.py — it goes into the "
                   "planning prompt as framing, and it is the most heavily used field on the type. "
                   "This is where a nuance goes when you are tempted to invent a field for it.",
    },
    "Availability start": {
        "status": "live",
        "written_by": "focus_period_author.py.",
        "read_by": "focus_period.in_availability_window, deterministically. On `Auto`, being "
                   "inside this window is what makes the plan render as a priority list rather "
                   "than a clock schedule.",
    },
    "Availability end": {
        "status": "live",
        "written_by": "focus_period_author.py.",
        "read_by": "focus_period.in_availability_window; the test needs both ends.",
    },
    "Availability note": {
        "status": "live",
        "written_by": "focus_period_author.py.",
        "read_by": "daily_plan.py and focus_period_generate.py pass it to the planner. The dates "
                   "say when the window is; this says what to do about it, and this is the half "
                   "the planner actually acts on.",
    },
    "Days off": {
        "status": "live",
        "written_by": "focus_period_author.py, as a parsed list of ISO dates.",
        "read_by": "focus_period.is_day_off, second in precedence after Days on and ahead of the "
                   "weekly default. A day marked off is not planned as a work day.",
    },
    "Days on": {
        "status": "live",
        "written_by": "focus_period_author.py.",
        "read_by": "focus_period.is_day_off, HIGHEST precedence — it beats Days off and the weekly "
                   "Sat/Sun default.",
    },
    "Output format": {
        "status": "live",
        "written_by": "focus_period_author.py.",
        "read_by": "focus_period.resolve_output_shape. It changes the SHAPE the day is rendered "
                   "in, not what is in it: a clock schedule, or a short priority-ordered list to "
                   "pull from when a window opens. On `Auto` the shape resolves from the "
                   "availability window alone — structured inputs only, never a text scan.",
    },
    "Workday start": {
        "status": "planned",
        "written_by": "focus_period_author.py, via focus_period_adapter's authoring payload.",
        "read_by": "plan_generate.py's day-bounds, replacing the hardcoded 10:00 start. Wired "
                   "end to end, but the property does not exist on the live Focus Period type "
                   "yet — build_focus_period.py adds it and has NOT been run (human-gated). "
                   "Until June approves that write, reads return None and the default applies.",
    },
    "Workday end": {
        "status": "live",
        "written_by": "focus_period_author.py.",
        "read_by": "plan_generate.py and focus_period.py override the hardcoded 18:00 with it. "
                   "Unpopulated on all 7 live periods, so the widening case it was built for "
                   "(working later during a sprint) has never actually run. A companion "
                   "`Workday start` is specified in backend spec §17 and does not exist yet.",
    },
    "Foreground projects": {
        "status": "live",
        "written_by": "focus_period_author.py, as real object ids — and only after June confirms "
                      "the reflect-back.",
        "read_by": "daily_plan.py:437 and plan_generate.py:409 drive real SELECTION from it, by "
                   "id, not as a prose hint. While the period is active these projects override "
                   "their own Engagement; when it lapses the project's Engagement returns.",
    },
    "Paused projects": {
        "status": "live",
        "written_by": "focus_period_author.py — and rarely. The first authoring run over-paused "
                      "every non-foreground project, which silently dropped their tasks from the "
                      "plan; the prompt now requires an explicit stop from June.",
        "read_by": "focus_period_generate.py and the plan path: a paused project is held out of "
                   "generation entirely. Not-foreground is NOT paused.",
    },

    # ---- fields with no documented MEANING, which still have a runtime story --
    # An undefined meaning and an undefined function are different gaps. Several of the fields in
    # UNDEFINED below do something quite specific at runtime; saying so is not inventing a
    # rationale, it is reporting the code.
    "Needs clarifying": {
        "status": "undesigned",
        "written_by": "Nothing writes the checkbox; the app's detail pane can toggle it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "No code reads the checkbox. (`Needs Clarifying` the STATUS value is a "
                   "different thing and is read.) June, 2026-07-18, on what it is for — the "
                   "clearest statement anyone has written down: it belongs to the same family as "
                   "`AI autonomous`, \"essentially telling agents, 'dont act on this, it can be "
                   "raised, but it needs clarifying or design or something'\". Both are "
                   "agent-facing control flags rather than content. She also said it needs more "
                   "usage data before deciding; backend spec §13 keeps it open.",
    },
    "Last surfaced": {
        "status": "undesigned",
        "written_by": "PYTHON ONLY, and never an LLM. daily_plan.update_last_surfaced is the sole "
                      "writer and it sits behind an interactive terminal confirmation June does "
                      "not use. No MCP tool can set it; there is no generic property setter. "
                      "June asked exactly this and was right: an agent should not write here.",
        "read_by": "status_check.py and neglect.py read it, but only as a FALLBACK — the live "
                   "staleness signal is the append-only surface log (surface_log.py), because this "
                   "field is a single overwriting date. 5 of 137 tasks carry a value, none newer "
                   "than 2026-06-18.",
    },
    "Active": {
        "status": "live",
        "written_by": "recurring_active.set_recurring_active is the single writer (server.py's "
                      "complete/uncomplete/toggle endpoints and capture_generate.py call it). "
                      "It reads back and logs.",
        "read_by": "datetime_seam.py:112-116, and ONLY inside the `as_needed` branch. June's read "
                   "of it — \"probably a tick we use to determine whether or not it surfaces in "
                   "the daily plan\" — matches what the spec asks for: "
                   "docs/review_reorganize_backend_spec.md §3 says \"it is not 'done' (that's "
                   "per-occurrence); it is an on/off 'in my daily plan' toggle\" and \"Add `active` "
                   "… Default active. `daily_plan`/scheduler skip recurring anchors that are not "
                   "active.\" ⚠ Built only halfway: for an as-needed item Active IS the "
                   "surfaces-today answer, but day/week/month items ignore it entirely, so "
                   "unticking a weekly recurring currently does nothing. The scheduler-level skip "
                   "§3 describes is unbuilt.",
    },
    "Day of month": {
        "status": "live",
        "written_by": "Nothing writes it; the app's recurrence card and the review surface edit it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "datetime_seam.py:131-140, the month branch: due when today's day number equals "
                   "it, clamped to the month's last day so 31 fires on Feb 28/29. Two "
                   "consequences worth knowing — a month-unit recurring with this UNSET is never "
                   "due, silently; and Interval count is ignored for months, so every-N-months "
                   "runs monthly. Semantics are from the code; no spec defines this field.",
    },
    "Foreground projects (on Goal)": {
        "status": "undesigned",
        "written_by": "Nothing. Every writer targets Focus Period.",
        "read_by": "Nothing. Investigated 2026-07-18 at June's request: no build script attaches "
                   "this property to Goal — build_focus_period.py:30-34 creates and links it to "
                   "Focus Period alone, and build_goal.py does not list it. It appears on Goal "
                   "because Anytype properties are space-global and were linked there by hand, and "
                   "ensure_type only ever adds. So it is a leak with zero runtime effect, not a "
                   "feature. Goal-level foreground is also explicitly rejected in the design "
                   "(build_goal.py:17-19, June 2026-07-13: a sprint is a Focus Period foreground "
                   "state on a PROJECT, never a property of a life area).",
    },
    "Applies when": {
        "status": "live",
        "written_by": "Nothing in scripts/ writes it; June sets it in the app or in Anytype. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.",
        "read_by": "daily_plan.py:254-261 loads it by display name and :388-390 splits the "
                   "strategy set with it: `Always` strategies are listed every day, and a strategy "
                   "whose state matches today's capacity is injected as a FIRM directive on the "
                   "whole plan. This is close to what June described as the intent — \"should "
                   "trigger in specific coded conditions — when I click this button in the UI, "
                   "here's what you should do\" — recorded as HER INTENT, not as built behaviour, "
                   "because only part of it is built: daily_plan._APPLIES_TO_LEVEL maps only "
                   "`Low energy`, and build_strategy.py mints only `Always` and `Low energy`, so "
                   "`Overwhelmed` / `Sprint` / `Stuck` are inert and cannot even be selected.",
    },
    "Goal status (on Project)": {
        "status": "undesigned",
        "written_by": "Nothing writes it on a Project.",
        "read_by": "Nothing reads it on a Project. Checked 2026-07-18 at June's request (\"Is it "
                   "in the mockup? I think this might be leak\") — she is right on all three "
                   "checks: the mockup assigns Goal status to GOAL only "
                   "(design/mockups/review-reorganize-mobile-v4.html:106-108), "
                   "app/src/fixtures/schema.ts gives Project Engagement / Project status / Side / "
                   "Deadline / Typical block / Access conditions and not this, build_goal.py links "
                   "the property to Goal alone, and daily_plan.py:104-105 reads it only when the "
                   "type key is `gsdo_goal`. A leak, inert.",
    },
}


# --- fields with NO documented meaning ---------------------------------------
# Deliberately NOT given definitions. A fabricated rationale sitting beside cited ones would be
# worse than an obvious gap. Each value states what was searched and what was (not) found.

UNDEFINED = {
    "Needs clarifying": "A checkbox on Task and Recurring. `Needs Clarifying` exists as a STATUS "
                        "value with a documented meaning, but no doc explains what the separate "
                        "checkbox means or how it relates to the status; backend spec §13 has it "
                        "as an OPEN question. The nearest thing to a purpose anyone has written "
                        "down is June's, 2026-07-18, and it is a family resemblance rather than a "
                        "definition: it belongs with `AI autonomous` as an agent-facing control "
                        "flag — \"essentially telling agents, 'dont act on this, it can be "
                        "raised, but it needs clarifying or design or something'\". She also said "
                        "it needs more usage data before deciding, so that stays her framing of "
                        "the question, not a settled meaning.",
    "Last surfaced": "A date on Task. docs/orchestrator_flags_2026-07-11.md describes it as the "
                     "neglect/staleness input and reports it non-functional end to end. Its "
                     "intended semantics were never written down as a field definition, so none is "
                     "given here — but what it DOES is now recorded (see the what-it-does entry): "
                     "it is SYSTEM-MAINTAINED and must never be written by an LLM. Python is its "
                     "only writer, and no agent-facing tool can set it.",
    "Foreground projects (on Goal)": "An objects field of this name also exists on the live Goal "
                                     "type. On Focus Period it is defined (see FIELDS); ON A GOAL "
                                     "no doc found explains what it means, and re-searched "
                                     "2026-07-18 during the Focus Period recovery. Not defined "
                                     "here. Same shape as `Goal status (on Project)` below.",
    "Applies when": "A select on Strategy (Always / Low energy / Overwhelmed / Sprint / Stuck). Its "
                    "options are documented (backend spec §12) but its MEANING is not settled: "
                    "docs/BUILD_DOC.md §8 records that it is barely used (1 of 12) and nominally "
                    "overlaps `What for`, with the redundancy explicitly unresolved. June's stated "
                    "INTENT for it, 2026-07-18 — recorded as intent, not as built behaviour: it "
                    "\"should trigger in specific coded conditions — when I click this button in "
                    "the UI, here's what you should do.\" Part of that shape is already built (see "
                    "the what-it-does entry: one option is wired to the low-capacity signal), but "
                    "whether the field should be the machine-matchable trigger layer, and what the "
                    "other options should do, is undecided.",
    "Goal status (on Project)": "The live Project type carries a `Goal status` select. The specs "
                                "define Goal status only for Goal. Whether this is intentional or "
                                "a schema leak is not documented.",
}


# --- API ---------------------------------------------------------------------

_BY_LOWER = {k.lower(): k for k in FIELDS}


def canonical(name):
    """The canonical display name for `name` (case-insensitive, whitespace-trimmed), or None."""
    if not isinstance(name, str):
        return None
    return _BY_LOWER.get(name.strip().lower())


def lookup(name):
    """The semantics entry for a field by display name, or None if it has none defined here.

    None means one of two things — use `is_undefined` to tell them apart: the field is known to
    have no documented meaning (in UNDEFINED), or it is simply not covered by this module.
    """
    key = canonical(name)
    return FIELDS[key] if key else None


def is_undefined(name):
    """True if this field is KNOWN to have no documented meaning (listed in UNDEFINED)."""
    if not isinstance(name, str):
        return False
    n = name.strip().lower()
    return any(n == k.lower() for k in UNDEFINED)


def does(name):
    """What HAPPENS when this field is set: {status, written_by, read_by}, or None if unrecorded.

    Covers FIELDS and UNDEFINED alike — a field can have no documented MEANING and still have a
    precise runtime story, and those are different gaps. `status` is one of DOES_STATUSES.
    """
    key = canonical(name)
    if key:
        return DOES.get(key)
    if not isinstance(name, str):
        return None
    n = name.strip().lower()
    for k in UNDEFINED:
        if n == k.lower():
            return DOES.get(k)
    return None


def does_line(name, type_name=None):
    """One compact line of what-it-does, for describe_model's per-field output. None if unrecorded.

    Deliberately lossy: it carries the STATUS and the reader, because those are what change how an
    agent should treat the field. `field_semantics.describe(name)` has the full text.

    `type_name` scopes the answer exactly as `one_line` does, and for the same reason — with more
    at stake here. A field name can be live on two types with completely different runtime stories:
    `Foreground projects` drives real selection on a Focus Period and does NOTHING on a Goal.
    Printing the Focus Period story under the Goal's field would tell an agent that writing there
    changes the plan. It does not. So a type mismatch looks for a disambiguated entry
    ("<field> (on <type>)") and, failing that, returns None rather than the other type's answer.
    """
    d = does(name)
    key = canonical(name)
    if type_name and key and type_name not in FIELDS[key]["types"]:
        d = does(f"{name} (on {type_name})")
    if not d:
        return None
    read = " ".join(str(d.get("read_by") or "").split())
    if len(read) > 150:
        read = read[:149].rsplit(" ", 1)[0] + "…"
    return f"[{d.get('status', '?')}] {read}"


def examples(name):
    """Varied illustrations for a free-text field, as a tuple. Empty when the field has none.

    Always three or more where present, and never a template — see EXAMPLES_BANNER, which must be
    shown with them anywhere they are rendered.
    """
    key = canonical(name)
    return tuple(EXAMPLES.get(key) or ()) if key else ()


def undefined_reason(name):
    """Why a field is listed as undefined, or None."""
    if not isinstance(name, str):
        return None
    n = name.strip().lower()
    for k, v in UNDEFINED.items():
        if n == k.lower():
            return v
    return None


# --- her overrides: a layer she can revise, resolved over the repo defaults --

OVERRIDES_FILE = "field_semantics_overrides.json"

# Only these keys may be overridden. `source` and `observed` are NOT overridable: the citation is
# the thing that lets a later reader go check the original reasoning, and an observation about
# live data is a finding, not a definition. Her revision changes the MEANING, not its provenance.
OVERRIDABLE = ("hint", "means", "not_this", "usage")


def _overrides_path(path=None):
    return path or cd_paths.data_file(OVERRIDES_FILE)


def read_overrides(path=None):
    """June's overrides as {field_name: {key: value}}. Missing file = no overrides, not an error."""
    try:
        with open(_overrides_path(path)) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{_overrides_path(path)}: expected a JSON object of "
                         f"{{field: {{key: value}}}}, got {type(data).__name__}")
    return data


def _write_overrides(data, path=None):
    p = _overrides_path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def default_entry(name):
    """The repo default for a field, hint included, or None. Never reflects an override."""
    key = canonical(name)
    if not key:
        return None
    e = dict(FIELDS[key])
    e["field"] = key
    e["hint"] = HINTS.get(key) or _first_sentence(e["means"])
    e["does"] = DOES.get(key)
    e["examples"] = list(EXAMPLES.get(key) or ())
    return e


def _first_sentence(text):
    t = " ".join((text or "").split())
    cut = t.find(". ")
    return t[:cut + 1] if cut != -1 else t


def resolved(name, path=None):
    """A field's semantics with June's override applied, or None if the field isn't covered.

    The default SURVIVES: the returned entry carries `overridden` (the list of keys she changed)
    and `default` (the untouched repo values for those keys), so a reader can always see both
    what was designed and what she changed it to.
    """
    e = default_entry(name)
    if e is None:
        return None
    ov = read_overrides(path).get(e["field"]) or {}
    changed, before = [], {}
    for k in OVERRIDABLE:
        if k in ov and ov[k] != e.get(k):
            before[k] = e.get(k)
            e[k] = ov[k]
            changed.append(k)
    e["overridden"] = changed
    e["default"] = before
    return e


def set_override(name, values, path=None, log=True):
    """Record June's revision of a field's semantics. Returns the newly-resolved entry.

    Only OVERRIDABLE keys are accepted; anything else raises rather than being silently dropped
    (repo constraint §5.1 — no silent failures). Her edit is written to the overrides file, never
    into FIELDS, and is appended to the corrections log as a before/after record so the revision
    is learning-loop material rather than an untracked change.
    """
    key = canonical(name)
    if not key:
        raise ValueError(f"set_override: no field semantics entry for {name!r}")
    if not isinstance(values, dict) or not values:
        raise ValueError("set_override: values must be a non-empty {key: value} dict")
    bad = [k for k in values if k not in OVERRIDABLE]
    if bad:
        raise ValueError(f"set_override: {bad} not overridable (allowed: {list(OVERRIDABLE)}). "
                         f"`source` and `observed` stay as written — the citation is what lets a "
                         f"later reader check the original reasoning.")
    before = {k: resolved(key, path).get(k) for k in values}
    data = read_overrides(path)
    entry = dict(data.get(key) or {})
    entry.update(values)
    data[key] = entry
    _write_overrides(data, path)
    after = {k: values[k] for k in values}
    if log and before != after:
        _log_revision(key, before, after)
    return resolved(key, path)


def clear_override(name, path=None):
    """Drop June's override for a field, restoring the repo default. Logged the same way."""
    key = canonical(name)
    if not key:
        raise ValueError(f"clear_override: no field semantics entry for {name!r}")
    data = read_overrides(path)
    if key not in data:
        return resolved(key, path)
    before = {k: v for k, v in data.pop(key).items()}
    _write_overrides(data, path)
    _log_revision(key, before, {k: default_entry(key).get(k) for k in before})
    return resolved(key, path)


def _log_revision(field, before, after):
    """Route the revision through the EXISTING corrections log — no thirteenth log module.

    `corrections_log.log_correction(kind, before, after)` is the repo's generic
    before/after correction record and is the only existing log whose shape matches an edit with
    a before and an after. ⚠ Its file is named for PLAN corrections, so a schema-semantics
    revision is a widening of its scope, not a natural fit — flagged for June rather than
    resolved by adding a new log (backend spec §11 / repo rule: never invent a new log).
    """
    import corrections_log
    corrections_log.log_correction("field_semantics",
                                        {"field": field, **before},
                                        {"field": field, **after})


# --- serialisable payload for the planned GET /api/schema --------------------

def schema_payload(path=None):
    """All field semantics as plain JSON-ready data, overrides resolved.

    Shape: {"fields": {name: entry}, "undefined": {name: reason}, "routing_brief": str}. Each
    entry carries both grains — `hint` (one line, for the UI's per-field hint slot) and the full
    `means`/`not_this`/`instead`/`usage`/`observed`/`source` — plus `overridden` and `default`
    so June can see what she changed. Nothing here touches Anytype or the network.
    """
    return {
        "fields": {name: resolved(name, path) for name in FIELDS},
        "undefined": {name: {"reason": why, "does": DOES.get(name)}
                      for name, why in UNDEFINED.items()},
        "routing_brief": routing_brief(),
        "examples_banner": EXAMPLES_BANNER,
        "does_statuses": list(DOES_STATUSES),
    }


def one_line(name, type_name=None, path=None):
    """The short grain: one line, for inline display next to a field name. None if not covered.

    Returns the RESOLVED hint (June's override wins). Used by describe_model.py, which prints one
    line per field, and by the UI's per-field hint slot — so it must stay ONE line.

    `type_name` scopes the answer to the type being displayed. A field can be live on a type the
    specs never documented it for (the live Project type carries `Goal status`, which the specs
    define only for Goal); showing the other type's definition there would assert a meaning
    nobody wrote down. So a type mismatch returns None rather than the wrong meaning.
    """
    e = resolved(name, path)
    if not e:
        return None
    if type_name and type_name not in e["types"]:
        return None
    return " ".join(str(e["hint"]).split())


def describe(name, path=None):
    """A full, human/agent-readable rendering of one field's semantics, overrides resolved.

    Raises if the field is neither defined nor listed as undefined.
    """
    key = canonical(name)
    if not key:
        reason = undefined_reason(name)
        if reason:
            out = [f"{name}", "  UNDEFINED — no documented meaning.", f"  {reason}"]
            out += _does_lines(does(name))
            return "\n".join(out)
        raise KeyError(f"field_semantics.describe: no entry for {name!r} "
                       f"(not in FIELDS and not in UNDEFINED)")
    e = resolved(key, path)
    lines = [f"{key}  (on {', '.join(e['types'])})",
             f"  HINT:     {e['hint']}",
             f"  MEANS:    {e['means']}"]
    if e.get("not_this"):
        lines.append(f"  NOT:      {e['not_this']}")
    for what, where in (e.get("instead") or {}).items():
        lines.append(f"  INSTEAD:  {what} -> {where}")
    for rule in e.get("usage") or []:
        lines.append(f"  RULE:     {rule}")
    lines += _does_lines(e.get("does"))
    if e.get("examples"):
        lines.append(f"  EXAMPLES: ({EXAMPLES_BANNER})")
        for ex in e["examples"]:
            lines.append(f"            · {ex}")
    if e.get("observed"):
        lines.append(f"  OBSERVED: {e['observed']}")
    lines.append(f"  SOURCE:   {e['source']}")
    if e.get("overridden"):
        for k in e["overridden"]:
            lines.append(f"  REVISED BY JUNE: {k} — repo default was: {e['default'].get(k)!r}")
    return "\n".join(lines)


def _does_lines(d):
    """Render a what-it-does record. Empty list when a field has none — never a fabricated one."""
    if not d:
        return []
    out = [f"  DOES:     [{d.get('status', '?')}]"]
    if d.get("written_by"):
        out.append(f"    written by:  {d['written_by']}")
    if d.get("read_by"):
        out.append(f"    read by:     {d['read_by']}")
    return out


def describe_many(names):
    """Full renderings for several fields, in the order given. Unknown names are skipped."""
    out = []
    for n in names:
        if canonical(n) or is_undefined(n):
            out.append(describe(n))
    return "\n\n".join(out)


# The fields an agent writing free text is most likely to mis-route — the leak's actual shape.
FREE_TEXT_ROUTING = ("Affective", "Blocked on", "Context", "Access notes", "Barriers")


def routing_brief():
    """Compact 'which free-text field does this belong in' guide, for a tool description.

    Short by design: it is read at the call site, where a long block would be ignored.
    """
    return (
        "WHICH FIELD DOES THIS TEXT BELONG IN? (scripts/field_semantics.py has the full rules, "
        "plus what each field DOES at runtime and several varied illustrations per field — those "
        "illustrations show the range, they are never a template to copy)\n"
        "  Affective   — ONLY how June feels about the item, in her words: dread, avoidance, "
        "hyperfixation, flatness, relief. Never status, findings, confirmations, blockers. "
        "Never a number.\n"
        "  Blocked on  — what is concretely being waited for.\n"
        "  Barriers    — the strategic 'I don't know how to...' open question (Goal/Project only).\n"
        "  Access notes— what is in the way of STARTING it (executive-function/sensory/access).\n"
        "  Context     — findings, confirmations, origin, everything else. The catch-all, and the "
        "correct default when unsure."
    )


# --- the ONE mechanical check that is not a semantic judgment ----------------
# Guard #3: an affect field is free text, never a scalar. Whether a sentence is 'affect' or
# 'status' cannot be decided mechanically — but a bare number or bare rating objectively is not
# an affect note, in any reading. That is the only content check made anywhere in the write path.
#
# capture_fields._text_prop already rejects a non-string, so an int 3 is dropped there — but the
# STRING form "3" passes it (verified by reading the code, 2026-07-18). Nothing checked the
# direct write paths at all.

SCALAR_FIELDS = ("Affective",)

_BARE_SCALAR = re.compile(
    r"""^\s*
        \d+(?:\.\d+)?                       # 3 or 3.5
        \s*(?:
            /\s*\d+(?:\.\d+)?               # 3/5
          | \s*out\s+of\s+\d+(?:\.\d+)?     # 3 out of 5
        )?
        \s*$""",
    re.VERBOSE | re.IGNORECASE,
)


def scalar_affect_problem(field_name, value):
    """Reason string if `value` is an objectively-invalid SCALAR for an affect field, else None.

    Only the unambiguous case: a numeric/boolean value, or a string that is nothing but a number
    or a rating ("3", "3/5", "3 out of 5"). Any real sentence passes — this makes NO judgment
    about whether the sentence is affect or status. That judgment is the reader's, which is why
    the semantics above exist rather than a validator.
    """
    if canonical(field_name) not in SCALAR_FIELDS:
        return None
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return (f"{field_name} is free text, never a scalar (guard #3): got {value!r}. "
                f"Affective holds how June feels about the item, in her own words — a sentence, "
                f"not a rating.")
    if isinstance(value, str) and _BARE_SCALAR.match(value):
        return (f"{field_name} is free text, never a scalar (guard #3): got the bare rating "
                f"{value!r}. Affective holds how June feels about the item, in her own words — a "
                f"sentence, not a rating.")
    return None


def check_scalar_affect(properties):
    """Raise ValueError if any affect field in a {display_name: value} dict holds a bare scalar.

    Fails loudly and never silently drops (repo constraint §5.1 — no silent failures). Called by
    the shared write layer so every write path inherits it.
    """
    for name, value in (properties or {}).items():
        problem = scalar_affect_problem(name, value)
        if problem:
            raise ValueError(problem)


if __name__ == "__main__":
    print(__doc__.strip())
    print()
    for name in sorted(FIELDS):
        print(describe(name))
        print()
    print("=" * 60)
    print("FIELDS WITH NO DOCUMENTED MEANING (deliberately not defined):")
    for name, why in sorted(UNDEFINED.items()):
        print(f"\n{name}\n  {why}")

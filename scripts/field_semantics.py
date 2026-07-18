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
                 "'I'm stressed about this', 'I'm putting it off', 'I'm hyperfixated', 'dreading it'.",
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
                    "disagree; the spec is the rule and the data is what needs fixing. Separately, "
                    "docs/structural_diagnosis_2026-07-11.md noted Affective drove no selection as of that "
                    "date; RE-VERIFIED 2026-07-18, it IS read in the plan path now (2 refs). "
                    "That half of the claim is STALE; the leak above is current.",
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
            "When set, this IS the displayed next item, surfaced positively: 'Waiting: Julia's spec. "
            "Job Search is healthy — nothing to do here right now is the right answer.' Relief, not "
            "anxiety.",
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
        "types": ("Task", "Recurring"),
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
        "observed": "Live tags are only the original three. docs/BUILD_DOC.md Track B records "
                    "backend-spec §6's Requires-deep-thinking / Involves-bureaucracy / Induces-pain "
                    "as NOT DONE. Also: `Access conditions` is missing on Project.",
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
        "means": "The situated specifics the Engagement select cannot hold: thresholds ('Backburner: "
                 "revisit after surgery recovery'), cadence ('Steady: ~30min daily'), a deadline "
                 "('due July 1'), or hyperfixation/intensity context.",
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
        "observed": "Also appears on the live Project type. The specs define it only for Goal; no "
                    "documented meaning for a Project's Goal status was found. See UNDEFINED.",
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
        "observed": "Appears unused across her 12 live Strategy objects (docs/BUILD_DOC.md §8).",
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
                 "not undone chores. 'As a PhD I'm overqualified — never know how to handle it.'",
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
        "observed": "docs/structural_diagnosis_2026-07-11.md lists Barriers among fields nothing "
                    "reads; the route assessment names 'barriers never resurface' as the missing "
                    "piece — the field, not the definition.",
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
        "means": "For Chapter goals: what this goal looks like when it stops claiming attention. "
                 "'Until income covers basic needs and the GA decision is made.'",
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
        "means": "Filepaths, directory paths, or document locations the AI should read when working "
                 "on this item. E.g. /Users/june/Documents/papers/anthro-article/.",
        "not_this": None,
        "instead": {},
        "usage": ["Populated by the weeding gate when an item references a file or external system; "
                  "the AI reads them before working on the item."],
        "source": "AI_LAYER_SPEC.md §2 Project + Task tables",
        "observed": "RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST, same as AI autonomous. June: agent-facing. An agent working the task should read these paths first. Checked: not exposed by cd_mcp_server.py, not mentioned in the drift skill. Never connected to its consumer.",
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
        "observed": "docs/review_reorganize_backend_spec.md §12 proposes renaming Obligation → Work; "
                    "not applied live as of 2026-07-18.",
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

    "Frequency": {
        "types": ("Recurring",),
        "means": "LEGACY — the v1-prototype field (Daily / Weekly / As-needed).",
        "not_this": None,
        "instead": {"the recurrence cadence": "Interval unit + Interval count"},
        "usage": ["Replaced by the interval model. Ignore it when building; it may still exist in "
                  "the space as a legacy property."],
        "source": "AI_LAYER_SPEC.md §2 Recurring table note",
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
    "Frequency": "Legacy — use Interval unit and Interval count.",
}


# --- fields with NO documented meaning ---------------------------------------
# Deliberately NOT given definitions. A fabricated rationale sitting beside cited ones would be
# worse than an obvious gap. Each value states what was searched and what was (not) found.

UNDEFINED = {
    "Needs clarifying": "A checkbox on Task and Recurring. `Needs Clarifying` exists as a STATUS "
                        "value with a documented meaning, but no doc found explains what the "
                        "separate checkbox means or how it relates to the status. "
                        "docs/review_reorganize_backend_spec.md §13 has it as an OPEN question "
                        "('reconsider whether it earns its place').",
    "Last surfaced": "A date on Task. docs/orchestrator_flags_2026-07-11.md describes it as the "
                     "neglect/staleness input, and reports it NON-FUNCTIONAL end to end (written "
                     "only by an interactive CLI path June doesn't use; 5 of 137 tasks had it, none "
                     "newer than 2026-06-18). Its intended semantics were never written down as a "
                     "field definition, so none is given here.",
    "Active": "A checkbox on Recurring created by scripts/build_recurring.py. No spec or design doc "
              "found defining what it means or what reads it.",
    "Day of month": "A number on Recurring. The interval model in AI_LAYER_SPEC.md §2 does not "
                    "mention it; no other doc found defines it.",
    "Foreground projects": "An objects field on Goal. The name matches Focus Period's foreground "
                           "concept, and the Focus Period adapter writes a field of this name — but "
                           "no doc found explains what it means ON A GOAL. Not defined here.",
    "Applies when": "A select on Strategy (Always / Low energy / Overwhelmed / Sprint / Stuck). It "
                    "exists and its options are documented "
                    "(docs/review_reorganize_backend_spec.md §12), but docs/BUILD_DOC.md §8 records "
                    "that it is barely used (1 of 12 Strategies) and NOMINALLY OVERLAPS `What for`, "
                    "with the redundancy explicitly unresolved. No settled meaning to state.",
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

    `plan_corrections_log.log_correction(kind, before, after)` is the repo's generic
    before/after correction record and is the only existing log whose shape matches an edit with
    a before and an after. ⚠ Its file is named for PLAN corrections, so a schema-semantics
    revision is a widening of its scope, not a natural fit — flagged for June rather than
    resolved by adding a new log (backend spec §11 / repo rule: never invent a new log).
    """
    import plan_corrections_log
    plan_corrections_log.log_correction("field_semantics",
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
        "undefined": dict(UNDEFINED),
        "routing_brief": routing_brief(),
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
            return f"{name}\n  UNDEFINED — no documented meaning.\n  {reason}"
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
    if e.get("observed"):
        lines.append(f"  OBSERVED: {e['observed']}")
    lines.append(f"  SOURCE:   {e['source']}")
    if e.get("overridden"):
        for k in e["overridden"]:
            lines.append(f"  REVISED BY JUNE: {k} — repo default was: {e['default'].get(k)!r}")
    return "\n".join(lines)


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
        "WHICH FIELD DOES THIS TEXT BELONG IN? (scripts/field_semantics.py has the full rules)\n"
        "  Affective   — ONLY how June feels about the item, in her words ('I'm dreading this', "
        "'I'm putting it off'). Never status, findings, confirmations, blockers. Never a number.\n"
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
                f"Affective holds how June feels in her words, e.g. 'dreading it'.")
    if isinstance(value, str) and _BARE_SCALAR.match(value):
        return (f"{field_name} is free text, never a scalar (guard #3): got the bare rating "
                f"{value!r}. Affective holds how June feels in her words, e.g. 'dreading it'.")
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

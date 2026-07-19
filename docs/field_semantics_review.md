# What each field means — for checking

This is what the system now tells an AI about how to fill in your fields. It was pulled
out of your own specs and planning docs, not written fresh — each block says where it came
from, so you can go read the full reasoning if a summary looks wrong.

**What to do with this:** skim for anything that doesn't match how you actually use the
field. Tick the ones that are right, write a correction under the ones that aren't. Two
sections are worth your attention most — the flagged mismatches, and the fields with no
documented meaning at all.

There's no validator. Nothing here blocks a write. This is what the AI *reads* before
writing, so getting it right is how the fields stay clean.

---

## ⚠️ Where the written meaning and your real use disagree

These are the ones to look at first. Nothing was silently reconciled — both readings are
recorded, and which one is right is your call.

**AI autonomous** — RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST. June: this field is 'useful more in the agent-facing interface' — an agent deciding whether it can just do the task. Checked: cd_mcp_server.py does NOT expose it and the drift skill does not mention it. So it is not dead, it is NEVER CONNECTED TO ITS ACTUAL CONSUMER.

**Access conditions** — Live tags are only the original three. docs/BUILD_DOC.md Track B records backend-spec §6's Requires-deep-thinking / Involves-bureaucracy / Induces-pain as NOT DONE. Also: `Access conditions` is missing on Project.

>> June: We want to build the new tags.

**Access notes** — Unpopulated across the entire live space (2026-07-18). Per the spec this is where unnamed barriers accumulate to feed tag promotion, so nothing is currently prompting for it. Recorded as an observation, not asserted as a bug. docs/structural_diagnosis_2026-07-11.md also lists access_notes among fields nothing reads.

>> June: Keep this - hopefully surfacing the fields and their semantic purpose will help with this. 

**Affective** — The leak lives here. Of 14 populated Affective values in the live space, the agent-written ones are status/findings, not affect. Spec and observed use disagree; the spec is the rule and the data is what needs fixing. Separately, docs/structural_diagnosis_2026-07-11.md noted Affective drove no selection as of that date; RE-VERIFIED 2026-07-18, it IS read in the plan path now (2 refs). That half of the claim is STALE; the leak above is current.

>> June: We want to fix this - it sounds like the problem was that the python puts the LLM's reasoning output into the context field, whereas the reasoning field should land in the write log

**Barriers** — docs/structural_diagnosis_2026-07-11.md lists Barriers among fields nothing reads; the route assessment names 'barriers never resurface' as the missing piece — the field, not the definition.

>> June: Keep this - its pending further design

**Deadline** — docs/structural_diagnosis_2026-07-11.md: loaded but never displayed or ordered on, as of that date. ⚠ RE-VERIFIED 2026-07-18 against current code: this claim is STALE — the field IS read in the plan path now. Read at 3 sites.

**Due date** — docs/structural_diagnosis_2026-07-11.md listed Due date as not even loaded in the plan path as of that date. ⚠ RE-VERIFIED 2026-07-18 against current code: this claim is STALE — the field IS read in the plan path now. Read at 3 sites.

**Goal link** — docs/structural_diagnosis_2026-07-11.md called goal_link 'the alignment chain' and said it was read NOWHERE in the plan path. ⚠ RE-VERIFIED 2026-07-18: STALE — daily_plan.py:147 reads it, fixed 2026-07-14 (the loader used to drop the relation).

**Goal status** — Also appears on the live Project type. The specs define it only for Goal; no documented meaning for a Project's Goal status was found. See UNDEFINED.

>> June: Yes, im not sure what the goal status is either, other than perhaps a mechanism for allowing us to retire goals?

**Horizon** — docs/review_reorganize_backend_spec.md §12 lists a wider live option set (Chapter · Milestone · Short-term · Medium-term · Long-term · Ongoing).

**Learning notes** — Appears unused across her 12 live Strategy objects (docs/BUILD_DOC.md §8).

>> June: This seems like it would be useful to build on later, although im not sure what the original plan for it was. 

**Relevant docs** — RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST, same as AI autonomous. June: agent-facing. An agent working the task should read these paths first. Checked: not exposed by cd_mcp_server.py, not mentioned in the drift skill. Never connected to its consumer.

>> June: Need to be fixed

**Side** — docs/review_reorganize_backend_spec.md §12 proposes renaming Obligation → Work; not applied live as of 2026-07-18.

>> June: Yes, lets rename to work. And let's also make sure that the LLM-facing semantic explination includes what these do in terms of the UI/UX.

**What for** — In June's 12 real Strategy objects this field carries BOTH the trigger AND the instruction — e.g. 'When planning days that involve leaving the house. Weigh the cumulative spoon-cost of errands, not just count.' Used on essentially all of them (docs/BUILD_DOC.md §8 Strategy decision). Broader than the spec's trigger-only definition; reported, not reconciled.

---

## Fields with no documented meaning

Nothing was invented for these. A made-up rationale sitting next to real ones would be
worse than an obvious gap, because it would look just as authoritative.

- **Active** — A checkbox on Recurring created by scripts/build_recurring.py. No spec or design doc found defining what it means or what reads it.

>> June: Recurring as needed, scheduled, or both? It is probably a tick we use to determine whether or not it surfaces in the daily plan or not. 

- **Applies when** — A select on Strategy (Always / Low energy / Overwhelmed / Sprint / Stuck). It exists and its options are documented (docs/review_reorganize_backend_spec.md §12), but docs/BUILD_DOC.md §8 records that it is barely used (1 of 12 Strategies) and NOMINALLY OVERLAPS `What for`, with the redundancy explicitly unresolved. No settled meaning to state.

>> June: Applies when should trigger in specific coded conditions - when I click this button in the UI, here's what you should do. Or something like that? 

- **Day of month** — A number on Recurring. The interval model in AI_LAYER_SPEC.md §2 does not mention it; no other doc found defines it.

>> June: Should be straightforward for an agent.

- **Foreground projects** — An objects field on Goal. The name matches Focus Period's foreground concept, and the Focus Period adapter writes a field of this name — but no doc found explains what it means ON A GOAL. Not defined here.

>> June: Answer these questions by looking at focus period's interactions in the UI/UX - what does the field *do* - then draft semantic explinations for the field based on that, in terms of what the LLM needs to know to use this field correctly. 

- **Goal status (on Project)** — The live Project type carries a `Goal status` select. The specs define Goal status only for Goal. Whether this is intentional or a schema leak is not documented.

>> June: Is it in the mockup? I think this might be leak.

- **Last surfaced** — A date on Task. docs/orchestrator_flags_2026-07-11.md describes it as the neglect/staleness input, and reports it NON-FUNCTIONAL end to end (written only by an interactive CLI path June doesn't use; 5 of 137 tasks had it, none newer than 2026-06-18). Its intended semantics were never written down as a field definition, so none is given here.

>> June: if this is a valuable field, we can update the system to keep updating it outside the CLI path. But the llm wouldn't write to this path, right? That would be updated by python?

- **Needs clarifying** — A checkbox on Task and Recurring. `Needs Clarifying` exists as a STATUS value with a documented meaning, but no doc found explains what the separate checkbox means or how it relates to the status. docs/review_reorganize_backend_spec.md §13 has it as an OPEN question ('reconsider whether it earns its place').

>> June: Yeah, this may be relevent for the agent-facing interface. Need more usage data to know for sure. But it belongs in the same family of considerations as AI autonomous - essentially telling agents, "dont act on this, it can be raised, but it needs clarifying or design or something"

---

## Goal

### Barriers

The strategic/decisional 'I don't know how to…' struggle — genuine open QUESTIONS, not undone chores. 'As a PhD I'm overqualified — never know how to handle it.'

>> June: A note on LLM facing langauge - if you give one specific example, the model may replicate your example in its output for the text fields. which is tricky because your example is clarifying. 

**Not this:** A concrete thing being waited for (that is `Blocked on`) and an access barrier (that is `Access conditions` / `Access notes`).

**If it's actually…**

- something concrete being waited for → `Blocked on`
- an access or executive-function barrier → `Access notes`

**Rules that govern a write:**

- Held so June doesn't re-derive it; queryable so the AI can find patterns across barriers over time (June's stated reason for making it a field).
- These must NOT become tasks with done-boxes — the system would quietly score her as 'behind' on things that have no answer yet, which the guards forbid.
- The AI proposes it from what June articulates as struggle; optional.

⚠️ **Observed use differs:** docs/structural_diagnosis_2026-07-11.md lists Barriers among fields nothing reads; the route assessment names 'barriers never resurface' as the missing piece — the field, not the definition.

<sub>from AI_LAYER_SPEC.md §2 Goal table; docs/route_structure_assessment_2026-07-12.md §5</sub>

- [ ] this is right
- Change it to:

---

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**Rules that govern a write:**

- 'The fundamental rule: formal fields exist only for what the AI must query or filter on. Everything else lives in `context` (free text, always present, always read).'
- New patterns emerge in Context BEFORE we know they are patterns; they promote to formal fields when they have earned it (§6). So writing something here is the correct default, not a fallback.
- On Strategy: origin, lifespan notes, why it was adopted. Heavily used — ~10 of June's 12 real Strategy objects populate it.

<sub>from AI_LAYER_SPEC.md §2 ('The fundamental rule') + per-type tables; docs/BUILD_DOC.md §8 Strategy decision (live usage across her 12 Strategies)</sub>

- [ ] this is right
- Change it to:

---

### Goal engagement

The Goal-level analog of a Project's Engagement: is this whole life-area getting ongoing baseline attention (Steady), engaged flexibly across many possible projects (Open), or set aside (Backburner)?

**Not this:** Sprint — a sprint is a Focus Period foreground state on a PROJECT, not a property of a whole life area (June, 2026-07-13).

**Rules that govern a write:**

- Feeds the not-yet-built cross-goal balancing / route-prioritization engine (§8d). Until that is built this is data worth keeping current, not yet consumed by code.

<sub>from AI_LAYER_SPEC.md §2 Goal table</sub>

- [ ] this is right
- Change it to:

---

### Goal status

Active / Parked / Achieved.

⚠️ **Observed use differs:** Also appears on the live Project type. The specs define it only for Goal; no documented meaning for a Project's Goal status was found. See UNDEFINED.

<sub>from AI_LAYER_SPEC.md §2 Goal table; docs/review_reorganize_backend_spec.md §12</sub>

- [ ] this is right
- Change it to:

---

### Horizon

Chapter / Ongoing / Milestone. Chapter = a life phase ending when a condition is met (job search, recovery season). Ongoing = structural, no discrete end (health, craft practice). Milestone = a discrete done-state (publish paper, launch tool).

**Not this:** The vague Long/Medium/Short-term labels this replaced.

**Rules that govern a write:**

- Feeds Goal ordering; the AI reads it to choose narration register (urgency vs. spiral vs. open horizon).

⚠️ **Observed use differs:** docs/review_reorganize_backend_spec.md §12 lists a wider live option set (Chapter · Milestone · Short-term · Medium-term · Long-term · Ongoing).

<sub>from AI_LAYER_SPEC.md §2 Goal table</sub>

- [ ] this is right
- Change it to:

---

### Reaching for

The WHY — optional but load-bearing when present.

**Rules that govern a write:**

- Top-level Goals require HUMAN authorship — drawn from a conversation or document, never AI-invented. For sub-goals and Projects the AI proposes text June edits.
- Fill rate is itself a learning-loop signal: a low fill rate means the field is not earning its place yet.
- Deliberately THIN now, designed to point at PMA's rich version later.

<sub>from AI_LAYER_SPEC.md §2 Goal + Project tables; DESIGN_v1_emerging.md §7</sub>

- [ ] this is right
- Change it to:

---

### Resolution condition

For Chapter goals: what this goal looks like when it stops claiming attention. 'Until income covers basic needs and the GA decision is made.'

**Rules that govern a write:**

- Optional on Ongoing/Milestone goals, but useful when the done-state needs spelling out.

<sub>from AI_LAYER_SPEC.md §2 Goal table</sub>

- [ ] this is right
- Change it to:

---

## Project

### Affective

The emotional charge of THIS item, in June's words — affective conditions only. 'I'm stressed about this', 'I'm putting it off', 'I'm hyperfixated', 'dreading it'.

**Not this:** Status. Findings. Confirmations. Blockers. Progress notes. Anything about the state of the WORK rather than how June feels about it. Never a number or rating.

**If it's actually…**

- a blocker → `Blocked on`
- a finding, confirmation, or origin note → `Context`
- an access or executive-function barrier → `Access notes`

**Rules that govern a write:**

- Never a scalar (guard #3). Open text, explicitly marked unstable, capable of holding multiple distinct signals at once — 'affective weight is a constellation, not a scale.'
- Only surfaced when relevant; NEVER asked for tiny tasks.
- Each item's affect matches the scope June's words gave it: a feeling about one item lands on that item; a feeling she states about the whole dump lands on every item.
- The AI may offer a rough intensity read purely for filtering, but that read is low-confidence, always correctable, and never the canonical value — the text is canonical.

⚠️ **Observed use differs:** The leak lives here. Of 14 populated Affective values in the live space, the agent-written ones are status/findings, not affect. Spec and observed use disagree; the spec is the rule and the data is what needs fixing. Separately, docs/structural_diagnosis_2026-07-11.md noted Affective drove no selection as of that date; RE-VERIFIED 2026-07-18, it IS read in the plan path now (2 refs). That half of the claim is STALE; the leak above is current.

<sub>from AI_LAYER_SPEC.md §2 (Task/Project tables + 'Affective weight is a constellation'); docs/BUILD_DOC.md hazard 'FIELD-SEMANTICS LEAK' (June's field model, 2026-07-18); scripts/capture_fields.py docstring</sub>

- [ ] this is right
- Change it to:

---

### Arc position rationale

Full plain sentences (not a one-liner) explaining where this stream sits in the project arc and why.

**Not this:** A terse label or a one-line summary.

**Rules that govern a write:**

- Guard #6: June needs to understand the reasoning, not just see the result. Stored so it persists across sessions without being re-derived.

<sub>from scripts/gsdt_bind.py (the generated per-repo CLAUDE.md binding section)</sub>

- [ ] this is right
- Change it to:

---

### Barriers

The strategic/decisional 'I don't know how to…' struggle — genuine open QUESTIONS, not undone chores. 'As a PhD I'm overqualified — never know how to handle it.'

**Not this:** A concrete thing being waited for (that is `Blocked on`) and an access barrier (that is `Access conditions` / `Access notes`).

**If it's actually…**

- something concrete being waited for → `Blocked on`
- an access or executive-function barrier → `Access notes`

**Rules that govern a write:**

- Held so June doesn't re-derive it; queryable so the AI can find patterns across barriers over time (June's stated reason for making it a field).
- These must NOT become tasks with done-boxes — the system would quietly score her as 'behind' on things that have no answer yet, which the guards forbid.
- The AI proposes it from what June articulates as struggle; optional.

⚠️ **Observed use differs:** docs/structural_diagnosis_2026-07-11.md lists Barriers among fields nothing reads; the route assessment names 'barriers never resurface' as the missing piece — the field, not the definition.

<sub>from AI_LAYER_SPEC.md §2 Goal table; docs/route_structure_assessment_2026-07-12.md §5</sub>

- [ ] this is right
- Change it to:

---

### Block chunk min

A durable per-project preference: how many minutes one work chunk on this project should be.

**Not this:** Ephemeral state such as 'did a chunk today' — that stays in the local block_duration_log.jsonl.

**Rules that govern a write:**

- Anytype-is-master: durable preference → Anytype; ephemeral/resetting state → local file. An earlier draft put this number in a local file; that was flagged as forking the source of truth.
- Its Anytype key is auto-generated (block_chunk_min, no gsdo_ prefix), so it is read BY DISPLAY NAME.

<sub>from docs/display_grain_design.md (revised 2026-07-14, post-swarm); scripts/block_duration.py</sub>

- [ ] this is right
- Change it to:

---

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**Rules that govern a write:**

- 'The fundamental rule: formal fields exist only for what the AI must query or filter on. Everything else lives in `context` (free text, always present, always read).'
- New patterns emerge in Context BEFORE we know they are patterns; they promote to formal fields when they have earned it (§6). So writing something here is the correct default, not a fallback.
- On Strategy: origin, lifespan notes, why it was adopted. Heavily used — ~10 of June's 12 real Strategy objects populate it.

<sub>from AI_LAYER_SPEC.md §2 ('The fundamental rule') + per-type tables; docs/BUILD_DOC.md §8 Strategy decision (live usage across her 12 Strategies)</sub>

- [ ] this is right
- Change it to:

---

### Deadline

The project's deadline.

**Rules that govern a write:**

- Optional. Only when real.
- Hard dates that must stay live and drive action are the ONE kind of route condition to extract out of prose into a real dated object — the qualitative conditions stay as text in Context / Engagement notes.

⚠️ **Observed use differs:** docs/structural_diagnosis_2026-07-11.md: loaded but never displayed or ordered on, as of that date. ⚠ RE-VERIFIED 2026-07-18 against current code: this claim is STALE — the field IS read in the plan path now. Read at 3 sites.

<sub>from AI_LAYER_SPEC.md §2 Project table; docs/route_structure_assessment_2026-07-12.md §3</sub>

- [ ] this is right
- Change it to:

---

### Depends on

Hard dependencies ONLY — streams that genuinely cannot start until another is done.

**Not this:** Soft ordering or preference. Parallel is the default.

**Rules that govern a write:**

- Leave unset when there is no real dependency. The AI can propose candidates from context.

<sub>from scripts/gsdt_bind.py (the generated per-repo CLAUDE.md binding section)</sub>

- [ ] this is right
- Change it to:

---

### Description

What this project is and its approach — the WHAT (as distinct from `Reaching for`, which is the why).

**If it's actually…**

- the project's why → `Reaching for`

<sub>from AI_LAYER_SPEC.md §2 Project table</sub>

- [ ] this is right
- Change it to:

---

### Engagement

How June is currently engaging with this project — the enduring per-project grain gate the daily plan reads deterministically. Steady / Open / Backburner (+ Needs Clarifying / Done in the wider live vocabulary).

**Not this:** Sprint and Hyperfixation — both RETIRED 2026-07-16. A sprint is a Focus Period foreground action; hyperfixation is a qualitative state.

**If it's actually…**

- a sprint → `Focus Period foreground (not this field)`
- hyperfixation or intensity → `Engagement notes / Affective`

**Rules that govern a write:**

- Steady → one normal daily move the plan commits to. Open → available, surfaced gently, not pushed (the default a new project is born with). Backburner → not surfaced unless a neglect threshold. Done → excluded, and never a birth value.
- An invalid or blank value means Open — the default lives in capture_fields, not in gsdo_objects (there is deliberately no born-Open chokepoint in the write layer).

<sub>from AI_LAYER_SPEC.md §2 Project table + the 2026-07-11 selection reconciliation note; scripts/capture_fields.py PROJECT_ENGAGEMENTS</sub>

- [ ] this is right
- Change it to:

---

### Engagement notes

The situated specifics the Engagement select cannot hold: thresholds ('Backburner: revisit after surgery recovery'), cadence ('Steady: ~30min daily'), a deadline ('due July 1'), or hyperfixation/intensity context.

**Rules that govern a write:**

- Canonical, open-schema PAIR for Engagement. The select is filterable; this field is authoritative about what it means for this project right now.
- Route conditions ('Opens when: …', 'Weighed against: …') stay as structured free text here or in Context — deliberately NOT a condition-field schema, which would flatten the variety and force provisional conditions into false crispness.

<sub>from AI_LAYER_SPEC.md §2 Project table; docs/route_structure_assessment_2026-07-12.md §3</sub>

- [ ] this is right
- Change it to:

---

### Goal link

The Goal(s) this project serves. The alignment chain.

**Not this:** Anything that is not a Goal — a wrong-kind link is dropped by the write layer.

**Rules that govern a write:**

- A Project may serve multiple Goals; storage is a graph, not a tree.

⚠️ **Observed use differs:** docs/structural_diagnosis_2026-07-11.md called goal_link 'the alignment chain' and said it was read NOWHERE in the plan path. ⚠ RE-VERIFIED 2026-07-18: STALE — daily_plan.py:147 reads it, fixed 2026-07-14 (the loader used to drop the relation).

<sub>from AI_LAYER_SPEC.md §2 Project table</sub>

- [ ] this is right
- Change it to:

---

### Parent project

The containing Project. Enables nesting and sub-routes — a work stream is a Project under a parent Project; leaf nodes are Tasks.

**Rules that govern a write:**

- Nesting produces 'next tangible item' structure at any level.

<sub>from AI_LAYER_SPEC.md §2 Project table</sub>

- [ ] this is right
- Change it to:

---

### Project status

Active / Parked / Inactive.

**If it's actually…**

- how June is currently engaging with the project → `Engagement`

**Rules that govern a write:**

- LEGACY — the spec records that `Engagement` REPLACES this field. Prefer Engagement.

<sub>from AI_LAYER_SPEC.md §2 Project table ('Replaces the old Project status … legacy'); docs/review_reorganize_backend_spec.md §12</sub>

- [ ] this is right
- Change it to:

---

### Reaching for

The WHY — optional but load-bearing when present.

**Rules that govern a write:**

- Top-level Goals require HUMAN authorship — drawn from a conversation or document, never AI-invented. For sub-goals and Projects the AI proposes text June edits.
- Fill rate is itself a learning-loop signal: a low fill rate means the field is not earning its place yet.
- Deliberately THIN now, designed to point at PMA's rich version later.

<sub>from AI_LAYER_SPEC.md §2 Goal + Project tables; DESIGN_v1_emerging.md §7</sub>

- [ ] this is right
- Change it to:

---

### Relevant docs

Filepaths, directory paths, or document locations the AI should read when working on this item. E.g. /Users/june/Documents/papers/anthro-article/.

**Rules that govern a write:**

- Populated by the weeding gate when an item references a file or external system; the AI reads them before working on the item.

⚠️ **Observed use differs:** RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST, same as AI autonomous. June: agent-facing. An agent working the task should read these paths first. Checked: not exposed by cd_mcp_server.py, not mentioned in the drift skill. Never connected to its consumer.

<sub>from AI_LAYER_SPEC.md §2 Project + Task tables</sub>

- [ ] this is right
- Change it to:

---

### Side

An orthogonal life-domain marker on a project: Obligation / Wellbeing / Fun-hobby / Daily life (Daily life added 2026-07-13, marking the sustainable-daily-life subprojects — medical, household, self-care, social).

**Not this:** A priority or a ranking. It is applied orthogonally to engagement, never overwriting it.

**Rules that govern a write:**

- Feeds a display-grain rule: Fun-hobby → excluded from the plan; Daily life → render at TASK grain (the specific chore); everything else → smallest-subproject grain once workstreams are filtered out.
- Descendants inherit from the nearest ancestor that has it set.

⚠️ **Observed use differs:** docs/review_reorganize_backend_spec.md §12 proposes renaming Obligation → Work; not applied live as of 2026-07-18.

<sub>from AI_LAYER_SPEC.md §2 selection-reconciliation note (2026-07-11 / 2026-07-13)</sub>

- [ ] this is right
- Change it to:

---

## Task

### AI autonomous

Can the AI do this with minimal oversight?

**Rules that govern a write:**

- Lets the system offload work June doesn't need to touch.

⚠️ **Observed use differs:** RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST. June: this field is 'useful more in the agent-facing interface' — an agent deciding whether it can just do the task. Checked: cd_mcp_server.py does NOT expose it and the drift skill does not mention it. So it is not dead, it is NEVER CONNECTED TO ITS ACTUAL CONSUMER.

<sub>from AI_LAYER_SPEC.md §2 Task table</sub>

- [ ] this is right
- Change it to:

---

### Access conditions

Fixed multi-select for the access barriers that are QUERYABLE and load-bearing.

**Not this:** Any barrier without a live tag — those go in `Access notes` as open text.

**If it's actually…**

- a barrier with no matching tag → `Access notes`

**Rules that govern a write:**

- Two tags earn their place because they drive real behavior: Can-be-done-lying-down (low-capacity filtering) and Involves-leaving-house (errand-batching). Requires-talking-to-a-person is also live.
- Only live option names are ever written — an unknown tag is DROPPED, never created.
- The AI infers and proposes; June never sets it cold; ambiguous → leave empty.

⚠️ **Observed use differs:** Live tags are only the original three. docs/BUILD_DOC.md Track B records backend-spec §6's Requires-deep-thinking / Involves-bureaucracy / Induces-pain as NOT DONE. Also: `Access conditions` is missing on Project.

<sub>from AI_LAYER_SPEC.md §2 Task table `access` row; scripts/capture_fields.py ALLOWED_ACCESS</sub>

- [ ] this is right
- Change it to:

---

### Access notes

Open-text extension of the `Access conditions` tags: what the task needs, or what is in the way of STARTING it, for barriers that have no tag yet — unnamed executive-function and access barriers (initiation-heavy, context-switch-heavy, sensory, social, cognitive-load).

**Rules that govern a write:**

- The fixed category list was deliberately NOT pre-enumerated — June's correction: the four-category body list was overengineered, and the barriers that matter aren't only about the body. The set GROWS from her real annotations.
- Recurring patterns in this note feed the §6 promotion loop: when an unnamed barrier keeps recurring, the AI surfaces it as a candidate to name as its own tag.
- The AI infers and proposes; June never sets it cold; when genuinely ambiguous the AI leaves it EMPTY rather than guessing.

⚠️ **Observed use differs:** Unpopulated across the entire live space (2026-07-18). Per the spec this is where unnamed barriers accumulate to feed tag promotion, so nothing is currently prompting for it. Recorded as an observation, not asserted as a bug. docs/structural_diagnosis_2026-07-11.md also lists access_notes among fields nothing reads.

<sub>from AI_LAYER_SPEC.md §2 Task table, `access` row</sub>

- [ ] this is right
- Change it to:

---

### Affective

The emotional charge of THIS item, in June's words — affective conditions only. 'I'm stressed about this', 'I'm putting it off', 'I'm hyperfixated', 'dreading it'.

**Not this:** Status. Findings. Confirmations. Blockers. Progress notes. Anything about the state of the WORK rather than how June feels about it. Never a number or rating.

**If it's actually…**

- a blocker → `Blocked on`
- a finding, confirmation, or origin note → `Context`
- an access or executive-function barrier → `Access notes`

**Rules that govern a write:**

- Never a scalar (guard #3). Open text, explicitly marked unstable, capable of holding multiple distinct signals at once — 'affective weight is a constellation, not a scale.'
- Only surfaced when relevant; NEVER asked for tiny tasks.
- Each item's affect matches the scope June's words gave it: a feeling about one item lands on that item; a feeling she states about the whole dump lands on every item.
- The AI may offer a rough intensity read purely for filtering, but that read is low-confidence, always correctable, and never the canonical value — the text is canonical.

⚠️ **Observed use differs:** The leak lives here. Of 14 populated Affective values in the live space, the agent-written ones are status/findings, not affect. Spec and observed use disagree; the spec is the rule and the data is what needs fixing. Separately, docs/structural_diagnosis_2026-07-11.md noted Affective drove no selection as of that date; RE-VERIFIED 2026-07-18, it IS read in the plan path now (2 refs). That half of the claim is STALE; the leak above is current.

<sub>from AI_LAYER_SPEC.md §2 (Task/Project tables + 'Affective weight is a constellation'); docs/BUILD_DOC.md hazard 'FIELD-SEMANTICS LEAK' (June's field model, 2026-07-18); scripts/capture_fields.py docstring</sub>

- [ ] this is right
- Change it to:

---

### Blocked on

What is being waited for — the concrete blocker.

**Not this:** The strategic/decisional 'I don't know how to…' struggle (that is `Barriers`), and how June feels about the block (that is `Affective`).

**If it's actually…**

- a strategic 'I don't know how to…' struggle → `Barriers`
- a feeling about the block → `Affective`

**Rules that govern a write:**

- When set, this IS the displayed next item, surfaced positively: 'Waiting: Julia's spec. Job Search is healthy — nothing to do here right now is the right answer.' Relief, not anxiety.
- Free text, not a traversable link (noted as a gap, not a rule).

<sub>from AI_LAYER_SPEC.md §2 Task table, `blocked_on` row; docs/structural_diagnosis_2026-07-11.md (free text, not a link)</sub>

- [ ] this is right
- Change it to:

---

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**Rules that govern a write:**

- 'The fundamental rule: formal fields exist only for what the AI must query or filter on. Everything else lives in `context` (free text, always present, always read).'
- New patterns emerge in Context BEFORE we know they are patterns; they promote to formal fields when they have earned it (§6). So writing something here is the correct default, not a fallback.
- On Strategy: origin, lifespan notes, why it was adopted. Heavily used — ~10 of June's 12 real Strategy objects populate it.

<sub>from AI_LAYER_SPEC.md §2 ('The fundamental rule') + per-type tables; docs/BUILD_DOC.md §8 Strategy decision (live usage across her 12 Strategies)</sub>

- [ ] this is right
- Change it to:

---

### Done

The completion checkbox. Always present on a Task.

**Rules that govern a write:**

- A chore is name + Done and nothing else, forever, unless June or the AI adds more (the bare-task principle). A field existing in the schema never means June fills a form.
- Rest and wellbeing are first-class checkable Tasks — checkable rest makes NOT-resting gently visible; the signal points at under-rest, never at failure.

<sub>from AI_LAYER_SPEC.md §2 Task table + 'Rest is first-class and checkable'; DESIGN_v1_emerging.md §5</sub>

- [ ] this is right
- Change it to:

---

### Due date

The deadline. Drives urgency and ordering in the plan.

**Not this:** The day the plan placed the task — that is `Scheduled`.

**If it's actually…**

- the day the plan placed this task → `Scheduled`

**Rules that govern a write:**

- Optional. Only when real.
- Keep separate from Scheduled — do NOT collapse them into one date field.

⚠️ **Observed use differs:** docs/structural_diagnosis_2026-07-11.md listed Due date as not even loaded in the plan path as of that date. ⚠ RE-VERIFIED 2026-07-18 against current code: this claim is STALE — the field IS read in the plan path now. Read at 3 sites.

<sub>from docs/review_reorganize_backend_spec.md §8 (DECIDED); AI_LAYER_SPEC.md §2 Task table</sub>

- [ ] this is right
- Change it to:

---

### Duration min

Estimated minutes for the item. The AI proposes a default at cold-start from task type and context — never left blank.

**Rules that govern a write:**

- June's stated duration is truth and always wins; an LLM estimate fills silence only. Whichever is written, `Duration source` MUST be written alongside it — a June-stated 90 and an estimated 90 must never be indistinguishable.
- Her calibration: most tasks run 1-2 hours, not 30 minutes; focused-attention work (job applications) runs 120+ and may need multiple blocks. See DURATION_PRIORS.
- A learning loop refines it from actual-vs-estimated.

<sub>from AI_LAYER_SPEC.md §2 Task table; scripts/capture_fields.py (DURATION_PRIORS + build_optional_props)</sub>

- [ ] this is right
- Change it to:

---

### Duration source

Provenance label for `Duration min`: 'stated' (June said it) or 'estimated' (the LLM filled the silence).

**Rules that govern a write:**

- Written whenever Duration min is written; never on its own.
- Exists so the future duration-bias learning loop can tell the two apart.

<sub>from scripts/capture_fields.py build_optional_props docstring</sub>

- [ ] this is right
- Change it to:

---

### Linked Projects

The Project(s) this task belongs to — the anti-drift chain.

**Not this:** A Goal. A Task links to Projects only; a wrong-kind link is dropped.

**Rules that govern a write:**

- Optional for bare chores. A Task may link to multiple Projects (many-to-many).

<sub>from AI_LAYER_SPEC.md §2 Task table; scripts/gsdo_objects.py _LINK_KIND</sub>

- [ ] this is right
- Change it to:

---

### Relevant docs

Filepaths, directory paths, or document locations the AI should read when working on this item. E.g. /Users/june/Documents/papers/anthro-article/.

**Rules that govern a write:**

- Populated by the weeding gate when an item references a file or external system; the AI reads them before working on the item.

⚠️ **Observed use differs:** RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST, same as AI autonomous. June: agent-facing. An agent working the task should read these paths first. Checked: not exposed by cd_mcp_server.py, not mentioned in the drift skill. Never connected to its consumer.

<sub>from AI_LAYER_SPEC.md §2 Project + Task tables</sub>

- [ ] this is right
- Change it to:

---

### Scheduled

The day the plan has actually PLACED the task — set by the scheduler or by June moving it. A placement record, not a deadline.

**Not this:** A deadline — that is `Due date`.

**If it's actually…**

- a deadline → `Due date`

**Rules that govern a write:**

- Keep separate from Due date; the plan reads Due date for urgency.

<sub>from docs/review_reorganize_backend_spec.md §8 (DECIDED)</sub>

- [ ] this is right
- Change it to:

---

### Task status

Ready / In Design / Parked / Needs Clarifying / Blocked / Done.

**Rules that govern a write:**

- Ready = well-specified, executable now. In Design = real committed work that needs a design conversation first. Parked = captured, no work-stream home yet, intentionally held — not surfaced in the daily plan or orient map. Needs Clarifying = shape unclear (the weeding gate's output for vague items). Blocked surfaces `Blocked on`.
- Legacy `Active` (pre-rename) is treated identically to Ready in queries.

<sub>from AI_LAYER_SPEC.md §2 Task table; docs/review_reorganize_backend_spec.md §12</sub>

- [ ] this is right
- Change it to:

---

## Recurring

### AI autonomous

Can the AI do this with minimal oversight?

**Rules that govern a write:**

- Lets the system offload work June doesn't need to touch.

⚠️ **Observed use differs:** RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST. June: this field is 'useful more in the agent-facing interface' — an agent deciding whether it can just do the task. Checked: cd_mcp_server.py does NOT expose it and the drift skill does not mention it. So it is not dead, it is NEVER CONNECTED TO ITS ACTUAL CONSUMER.

<sub>from AI_LAYER_SPEC.md §2 Task table</sub>

- [ ] this is right
- Change it to:

---

### Access conditions

Fixed multi-select for the access barriers that are QUERYABLE and load-bearing.

**Not this:** Any barrier without a live tag — those go in `Access notes` as open text.

**If it's actually…**

- a barrier with no matching tag → `Access notes`

**Rules that govern a write:**

- Two tags earn their place because they drive real behavior: Can-be-done-lying-down (low-capacity filtering) and Involves-leaving-house (errand-batching). Requires-talking-to-a-person is also live.
- Only live option names are ever written — an unknown tag is DROPPED, never created.
- The AI infers and proposes; June never sets it cold; ambiguous → leave empty.

⚠️ **Observed use differs:** Live tags are only the original three. docs/BUILD_DOC.md Track B records backend-spec §6's Requires-deep-thinking / Involves-bureaucracy / Induces-pain as NOT DONE. Also: `Access conditions` is missing on Project.

<sub>from AI_LAYER_SPEC.md §2 Task table `access` row; scripts/capture_fields.py ALLOWED_ACCESS</sub>

- [ ] this is right
- Change it to:

---

### Access notes

Open-text extension of the `Access conditions` tags: what the task needs, or what is in the way of STARTING it, for barriers that have no tag yet — unnamed executive-function and access barriers (initiation-heavy, context-switch-heavy, sensory, social, cognitive-load).

**Rules that govern a write:**

- The fixed category list was deliberately NOT pre-enumerated — June's correction: the four-category body list was overengineered, and the barriers that matter aren't only about the body. The set GROWS from her real annotations.
- Recurring patterns in this note feed the §6 promotion loop: when an unnamed barrier keeps recurring, the AI surfaces it as a candidate to name as its own tag.
- The AI infers and proposes; June never sets it cold; when genuinely ambiguous the AI leaves it EMPTY rather than guessing.

⚠️ **Observed use differs:** Unpopulated across the entire live space (2026-07-18). Per the spec this is where unnamed barriers accumulate to feed tag promotion, so nothing is currently prompting for it. Recorded as an observation, not asserted as a bug. docs/structural_diagnosis_2026-07-11.md also lists access_notes among fields nothing reads.

<sub>from AI_LAYER_SPEC.md §2 Task table, `access` row</sub>

- [ ] this is right
- Change it to:

---

### Affective

The emotional charge of THIS item, in June's words — affective conditions only. 'I'm stressed about this', 'I'm putting it off', 'I'm hyperfixated', 'dreading it'.

**Not this:** Status. Findings. Confirmations. Blockers. Progress notes. Anything about the state of the WORK rather than how June feels about it. Never a number or rating.

**If it's actually…**

- a blocker → `Blocked on`
- a finding, confirmation, or origin note → `Context`
- an access or executive-function barrier → `Access notes`

**Rules that govern a write:**

- Never a scalar (guard #3). Open text, explicitly marked unstable, capable of holding multiple distinct signals at once — 'affective weight is a constellation, not a scale.'
- Only surfaced when relevant; NEVER asked for tiny tasks.
- Each item's affect matches the scope June's words gave it: a feeling about one item lands on that item; a feeling she states about the whole dump lands on every item.
- The AI may offer a rough intensity read purely for filtering, but that read is low-confidence, always correctable, and never the canonical value — the text is canonical.

⚠️ **Observed use differs:** The leak lives here. Of 14 populated Affective values in the live space, the agent-written ones are status/findings, not affect. Spec and observed use disagree; the spec is the rule and the data is what needs fixing. Separately, docs/structural_diagnosis_2026-07-11.md noted Affective drove no selection as of that date; RE-VERIFIED 2026-07-18, it IS read in the plan path now (2 refs). That half of the claim is STALE; the leak above is current.

<sub>from AI_LAYER_SPEC.md §2 (Task/Project tables + 'Affective weight is a constellation'); docs/BUILD_DOC.md hazard 'FIELD-SEMANTICS LEAK' (June's field model, 2026-07-18); scripts/capture_fields.py docstring</sub>

- [ ] this is right
- Change it to:

---

### Blocked on

What is being waited for — the concrete blocker.

**Not this:** The strategic/decisional 'I don't know how to…' struggle (that is `Barriers`), and how June feels about the block (that is `Affective`).

**If it's actually…**

- a strategic 'I don't know how to…' struggle → `Barriers`
- a feeling about the block → `Affective`

**Rules that govern a write:**

- When set, this IS the displayed next item, surfaced positively: 'Waiting: Julia's spec. Job Search is healthy — nothing to do here right now is the right answer.' Relief, not anxiety.
- Free text, not a traversable link (noted as a gap, not a rule).

<sub>from AI_LAYER_SPEC.md §2 Task table, `blocked_on` row; docs/structural_diagnosis_2026-07-11.md (free text, not a link)</sub>

- [ ] this is right
- Change it to:

---

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**Rules that govern a write:**

- 'The fundamental rule: formal fields exist only for what the AI must query or filter on. Everything else lives in `context` (free text, always present, always read).'
- New patterns emerge in Context BEFORE we know they are patterns; they promote to formal fields when they have earned it (§6). So writing something here is the correct default, not a fallback.
- On Strategy: origin, lifespan notes, why it was adopted. Heavily used — ~10 of June's 12 real Strategy objects populate it.

<sub>from AI_LAYER_SPEC.md §2 ('The fundamental rule') + per-type tables; docs/BUILD_DOC.md §8 Strategy decision (live usage across her 12 Strategies)</sub>

- [ ] this is right
- Change it to:

---

### Day of week

Mon–Sun. The weekly anchor: set only for items pinned to specific day(s), e.g. weekly therapy on Tuesday.

**Rules that govern a write:**

- Empty for un-anchored daily routines.

<sub>from AI_LAYER_SPEC.md §2 Recurring table</sub>

- [ ] this is right
- Change it to:

---

### Duration min

Estimated minutes for the item. The AI proposes a default at cold-start from task type and context — never left blank.

**Rules that govern a write:**

- June's stated duration is truth and always wins; an LLM estimate fills silence only. Whichever is written, `Duration source` MUST be written alongside it — a June-stated 90 and an estimated 90 must never be indistinguishable.
- Her calibration: most tasks run 1-2 hours, not 30 minutes; focused-attention work (job applications) runs 120+ and may need multiple blocks. See DURATION_PRIORS.
- A learning loop refines it from actual-vs-estimated.

<sub>from AI_LAYER_SPEC.md §2 Task table; scripts/capture_fields.py (DURATION_PRIORS + build_optional_props)</sub>

- [ ] this is right
- Change it to:

---

### Fixed appointment

Opt-out flag (June's name for it) for the missed-item persistence rule: a fixed appointment that is missed returns on its own schedule rather than persisting.

**Rules that govern a write:**

- Checkbox on Recurring; default unset.

<sub>from docs/task_persistence_design.md</sub>

- [ ] this is right
- Change it to:

---

### Frequency

LEGACY — the v1-prototype field (Daily / Weekly / As-needed).

**If it's actually…**

- the recurrence cadence → `Interval unit + Interval count`

**Rules that govern a write:**

- Replaced by the interval model. Ignore it when building; it may still exist in the space as a legacy property.

<sub>from AI_LAYER_SPEC.md §2 Recurring table note</sub>

- [ ] this is right
- Change it to:

---

### Interval count

N in 'every N days/weeks/months'. Default 1. day/1 = daily; day/3 = every 3 days.

<sub>from AI_LAYER_SPEC.md §2 Recurring table</sub>

- [ ] this is right
- Change it to:

---

### Interval unit

day / week / month / as_needed — the recurrence interval's unit.

**Not this:** A Practice-vs-Routine distinction. `Has target` / `Target` were RETIRED 2026-07-16/17; a recurring item is defined by its interval alone.

**Rules that govern a write:**

- The one axis that stays is scheduled vs. as_needed: whether an item auto-populates on a cadence or only when invoked. That is a scheduling choice.
- Replaces the legacy `Frequency` (Daily/Weekly/As-needed) field.

<sub>from AI_LAYER_SPEC.md §2 Recurring table + the retirement note beneath it</sub>

- [ ] this is right
- Change it to:

---

### Project link

The project or goal this recurring item serves. Optional.

**Not this:** A Goal — a Recurring links to a Project.

<sub>from AI_LAYER_SPEC.md §2 Recurring table; scripts/gsdo_objects.py _LINK_KIND</sub>

- [ ] this is right
- Change it to:

---

### Relevant docs

Filepaths, directory paths, or document locations the AI should read when working on this item. E.g. /Users/june/Documents/papers/anthro-article/.

**Rules that govern a write:**

- Populated by the weeding gate when an item references a file or external system; the AI reads them before working on the item.

⚠️ **Observed use differs:** RE-VERIFIED 2026-07-18: still not read by the plan path — but that is the WRONG TEST, same as AI autonomous. June: agent-facing. An agent working the task should read these paths first. Checked: not exposed by cd_mcp_server.py, not mentioned in the drift skill. Never connected to its consumer.

<sub>from AI_LAYER_SPEC.md §2 Project + Task tables</sub>

- [ ] this is right
- Change it to:

---

### Time of day

Clock time 'HH:MM'. When set, the deterministic scheduler treats this as a FIXED ANCHOR that the day's flexible tasks flow around.

**Rules that govern a write:**

- A Recurring with Day of week + Time of day + Duration min set is a fixed appointment placed at its real clock time.

<sub>from AI_LAYER_SPEC.md §2 Recurring table + 'Fixed recurring appointments'</sub>

- [ ] this is right
- Change it to:

---

## Strategy

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**Rules that govern a write:**

- 'The fundamental rule: formal fields exist only for what the AI must query or filter on. Everything else lives in `context` (free text, always present, always read).'
- New patterns emerge in Context BEFORE we know they are patterns; they promote to formal fields when they have earned it (§6). So writing something here is the correct default, not a fallback.
- On Strategy: origin, lifespan notes, why it was adopted. Heavily used — ~10 of June's 12 real Strategy objects populate it.

<sub>from AI_LAYER_SPEC.md §2 ('The fundamental rule') + per-type tables; docs/BUILD_DOC.md §8 Strategy decision (live usage across her 12 Strategies)</sub>

- [ ] this is right
- Change it to:

---

### Learning notes

The anti-forgetting field: what this strategy needs that it isn't doing yet; annotations on whether it is still working.

**Rules that govern a write:**

- A learning loop targets this field so the strategy improves instead of silently failing — and so June is reminded the system is revisable, not stuck.

⚠️ **Observed use differs:** Appears unused across her 12 live Strategy objects (docs/BUILD_DOC.md §8).

<sub>from AI_LAYER_SPEC.md §2 Strategy table</sub>

- [ ] this is right
- Change it to:

---

### Strategy status

Active / Retired. Queried so the AI applies only currently-active strategies.

**Rules that govern a write:**

- A strategy's lifespan is terminal — retiring one is EXPECTED, not failure.

<sub>from AI_LAYER_SPEC.md §2 Strategy table</sub>

- [ ] this is right
- Change it to:

---

### What for

When and where to apply the strategy — the point-of-performance trigger (Barkley: surface it at the moment the behavior has to happen, not in the abstract).

**Rules that govern a write:**

- Lets the AI know WHEN a strategy is relevant.

⚠️ **Observed use differs:** In June's 12 real Strategy objects this field carries BOTH the trigger AND the instruction — e.g. 'When planning days that involve leaving the house. Weigh the cumulative spoon-cost of errands, not just count.' Used on essentially all of them (docs/BUILD_DOC.md §8 Strategy decision). Broader than the spec's trigger-only definition; reported, not reconciled.

<sub>from AI_LAYER_SPEC.md §2 Strategy table</sub>

- [ ] this is right
- Change it to:

---

## Focus Period

*No fields documented for this type yet.*

---


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

**Access conditions** — Live tags are only the original three. The three additions in backend spec §6 (Requires-deep-thinking / Involves-bureaucracy / Induces-pain) are AGREED AND PLANNED — June, 2026-07-18: "We want to build the new tags" — and are being built by another thread. Until they are live, writing them does nothing: an unknown tag is dropped. §6 gives behaviour for only one of the three (Induces-pain, a capacity signal to weigh on low-capacity days and pair with rest); the other two are specified as names with no stated behaviour yet. ⚠ CORRECTION 2026-07-18, found by running describe_model.py against the live space: `Access conditions` IS on the Project type now — another thread added it read-back-confirmed the same day, and docs/BUILD_DOC.md Track B §4 already records that. This module was the stale one: its type list said Task/Recurring, so the field read as having no documented meaning wherever a Project was described. Project added. Note per Track B that nothing yet READS Project-level access conditions; the reader below is the Task-level one.

**Access notes** — Unpopulated across the entire live space (2026-07-18). Per the spec this is where unnamed barriers accumulate to feed tag promotion, so nothing is currently prompting for it. Recorded as an observation, not asserted as a bug. docs/structural_diagnosis_2026-07-11.md also lists access_notes among fields nothing reads.

**Active** — June, 2026-07-18, before this was traced: "probably a tick we use to determine whether or not it surfaces in the daily plan." That matches §3 exactly. The gap is in the build, not in her reading of it.

**Affective** — The leak lives here. Of 14 populated Affective values in the live space, the agent-written ones are status/findings, not affect. Spec and observed use disagree; the spec is the rule and the data is what needs fixing. PARTLY ADDRESSED 2026-07-18, commit e39dd5b — but read the boundary carefully, because June's note and the commit are about adjacent things. e39dd5b removed `props["Context"] = item["reasoning"]` from capture_generate._creation_props, so the gate's own filing rationale no longer lands in `Context`; it is now stamped in the write log (corrections_log.log_authorship → scripts/data/corrections.jsonl) after read-back. That closes the CONTEXT misroute on the capture path. It does NOT touch Affective: nothing in that commit changes what goes into this field, and the 14 polluted Context values were deliberately left alone (clearing them is a data edit on real objects and stays June's call). So the status-notes-in-Affective leak is still current, and prose guidance — this module, the MCP routing brief, the drift skill — is the whole of what prevents it. Separately, docs/structural_diagnosis_2026-07-11.md said Affective drove no selection; RE-VERIFIED 2026-07-18, it IS read in the plan path now. That half is STALE.

**Availability end** — Populated on 3 of 7 live periods, always paired with `Availability start`.

**Availability note** — Populated on 4 of 7 live periods. All 4 describe REDUCED or fragmented availability ('Limited spoon', 'Fragmented or reduced availability due to moving assistance'). The 'a period can be MORE' half of the reframe has no live use — consistent with `Workday end` being unpopulated on all 7.

**Availability start** — Populated on 3 of 7 live periods, always paired with `Availability end`.

**Barriers** — Nothing reads it yet, and that is a pending design rather than a dead field — June, 2026-07-18: "Keep this — its pending further design." docs/route_structure_assessment_2026-07-12.md §5 names 'barriers never resurface' as the missing piece: what is unbuilt is the resurfacing, not the definition. Keep writing it; the content is what the later design needs.

**Days off** — UNPOPULATED on all 7 live periods (2026-07-18) — only `Days on` is used. Encoding note: the build plan's tests use a JSON array; focus_period_adapter._csv writes comma-separated and every live value is comma-separated. focus_period._parse_date_list accepts both, so nothing is broken, but the plan's stated shape is not the one in the data.

**Days on** — Populated on 4 of 7 live periods, comma-separated. Only ONE of those 4 carries a real override (Sat 2026-07-18); the other 3 list days that are ALREADY work days under the Sat/Sun default — redundant, not wrong. Separately: docs/review_reorganize_backend_spec.md §17 still calls this field 'stubbed in the UI but not yet a committed field — leave OPEN'. That is stale: it is a committed field, parsed and populated. Reported, not reconciled.

**Deadline** — docs/structural_diagnosis_2026-07-11.md: loaded but never displayed or ordered on, as of that date. ⚠ RE-VERIFIED 2026-07-18 against current code: this claim is STALE — the field IS read in the plan path now. Read at 3 sites.

**Due date** — docs/structural_diagnosis_2026-07-11.md listed Due date as not even loaded in the plan path as of that date. ⚠ RE-VERIFIED 2026-07-18 against current code: this claim is STALE — the field IS read in the plan path now. Read at 3 sites.

**Foreground projects** — Populated on all 7 live periods (1-4 projects each) — with `Intent`, the most used field on the type. NOTE: a field with this same display name also exists on the live Goal type, where no doc explains what it means; that one stays in UNDEFINED as 'Foreground projects (on Goal)'.

**Goal link** — docs/structural_diagnosis_2026-07-11.md called goal_link 'the alignment chain' and said it was read NOWHERE in the plan path. ⚠ RE-VERIFIED 2026-07-18: STALE — daily_plan.py:147 reads it, fixed 2026-07-14 (the loader used to drop the relation).

**Goal status** — Also appears on the live Project type, where it is a leak — see `Goal status (on Project)` in UNDEFINED. On Goal itself the option list is documented but its PURPOSE is not. June's own open question, 2026-07-18, recorded as a question and deliberately not promoted into a definition: "im not sure what the goal status is either, other than perhaps a mechanism for allowing us to retire goals?" If that is what it is for, it overlaps `Horizon` + `Resolution condition`, which already describe how a goal ends. Unresolved; do not write a rationale for it.

**Horizon** — docs/review_reorganize_backend_spec.md §12 lists a wider live option set (Chapter · Milestone · Short-term · Medium-term · Long-term · Ongoing).

**Intent** — Populated on all 7 live periods and consistently rich — several sentences carrying capacity, framing and explicit planning instructions (e.g. 'Dev, creative, and hobby work is open time June chooses herself - do NOT schedule specific hobby tasks'). The most heavily used field on the type.

**Intentionally none** — Added 2026-07-19 after June hit the failure it fixes: pressing Custom on a field with nothing to inherit wrote an empty value, which deleted the property, so the save failed its own read-back and she got an error for pressing a button. She confirmed overriding to empty is a real need — a task under dev work whose inherited conditions genuinely do not apply.

**Learning notes** — Designed, defined, and unused — not undefined. Unused across her 12 live Strategy objects (docs/BUILD_DOC.md §8). June, 2026-07-18: "useful to build on later, although im not sure what the original plan for it was." The plan IS written down, in AI_LAYER_SPEC.md §2 Strategy, and is quoted in full under what-it-does above so it does not have to be hunted for.

**Output format** — Populated on 6 of 7 live periods: Auto x4, Clock schedule x1, Priority list x1.

**Paused projects** — UNPOPULATED on all 7 live periods (2026-07-18) — consistent with the pause-is-rare rule holding in practice after the prompt was tuned.

**Period end** — Populated on all 7 live periods.

**Period start** — Populated on all 7 live periods. On 4 of the 7 it EQUALS `Period end` — a single day — although the design assumes a week-long stretch (one object is even named 'Week of Jul 14' with start == end == 2026-07-14). Design and use disagree about the grain; reported, not reconciled.

**Relevant docs** — RE-VERIFIED 2026-07-18: not read by the plan path — but that is the WRONG TEST, same as AI autonomous. Its consumer is agent-facing: an agent working the task should open these paths first. June, 2026-07-18: "Need to be fixed." What fixed means mechanically is stated under what-it-does above (expose it through the MCP read surface, add a read-side rule to the drift skill, and populate it at capture). Correction: the usage rule above says the weeding gate populates it — no prompt in prompts/ mentions it, so nothing does. That rule is intent, not built behaviour.

**Side** — The rename Obligation → Work (backend spec §12) is DECIDED — June, 2026-07-18: "lets rename to work" — and is another thread's to apply. Not live as of 2026-07-18, so `Obligation` is still the only writable name. Wellbeing and Obligation are distinguished in the docs but not in any selection code; the difference is currently semantic only.

**What for** — In June's 12 real Strategy objects this field carries BOTH the trigger AND the instruction — e.g. 'When planning days that involve leaving the house. Weigh the cumulative spoon-cost of errands, not just count.' Used on essentially all of them (docs/BUILD_DOC.md §8 Strategy decision). Broader than the spec's trigger-only definition; reported, not reconciled.

**Workday end** — UNPOPULATED on all 7 live periods (2026-07-18) — the widening case the field was built for has never been used. Separately, the companion `Workday start` (backend spec §17) is now BUILT in code — the day-bounds logic reads both ends — but its schema write is still pending June's approval; see that field's entry.

**Workday start** — NOT YET ON THE LIVE TYPE (2026-07-18). The builder was edited to add it but deliberately not run — schema writes to June's space are human-gated (docs/BUILD_DOC.md §2). Every reader/writer is wired and inert until then.

---

## Fields with no documented meaning

Nothing was invented for these. A made-up rationale sitting next to real ones would be
worse than an obvious gap, because it would look just as authoritative.

- **Applies when** — A select on Strategy (Always / Low energy / Overwhelmed / Sprint / Stuck). Its options are documented (backend spec §12) but its MEANING is not settled: docs/BUILD_DOC.md §8 records that it is barely used (1 of 12) and nominally overlaps `What for`, with the redundancy explicitly unresolved. June's stated INTENT for it, 2026-07-18 — recorded as intent, not as built behaviour: it "should trigger in specific coded conditions — when I click this button in the UI, here's what you should do." Part of that shape is already built (see the what-it-does entry: one option is wired to the low-capacity signal), but whether the field should be the machine-matchable trigger layer, and what the other options should do, is undecided.

  **What it does — Working now**

  - *What writes it:* Nothing in scripts/ writes it; June sets it in the app or in Anytype. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
  - *What reads it, and what changes:* daily_plan.py:254-261 loads it by display name and :388-390 splits the strategy set with it: `Always` strategies are listed every day, and a strategy whose state matches today's capacity is injected as a FIRM directive on the whole plan. This is close to what June described as the intent — "should trigger in specific coded conditions — when I click this button in the UI, here's what you should do" — recorded as HER INTENT, not as built behaviour, because only part of it is built: daily_plan._APPLIES_TO_LEVEL maps only `Low energy`, and build_strategy.py mints only `Always` and `Low energy`, so `Overwhelmed` / `Sprint` / `Stuck` are inert and cannot even be selected.

- **Foreground projects (on Goal)** — An objects field of this name also exists on the live Goal type. On Focus Period it is defined (see FIELDS); ON A GOAL no doc found explains what it means, and re-searched 2026-07-18 during the Focus Period recovery. Not defined here. Same shape as `Goal status (on Project)` below.

  **What it does — Nothing uses it yet, and no design was found**

  - *What writes it:* Nothing. Every writer targets Focus Period.
  - *What reads it, and what changes:* Nothing. Investigated 2026-07-18 at June's request: no build script attaches this property to Goal — build_focus_period.py:30-34 creates and links it to Focus Period alone, and build_goal.py does not list it. It appears on Goal because Anytype properties are space-global and were linked there by hand, and ensure_type only ever adds. So it is a leak with zero runtime effect, not a feature. Goal-level foreground is also explicitly rejected in the design (build_goal.py:17-19, June 2026-07-13: a sprint is a Focus Period foreground state on a PROJECT, never a property of a life area).

- **Goal status (on Project)** — The live Project type carries a `Goal status` select. The specs define Goal status only for Goal. Whether this is intentional or a schema leak is not documented.

  **What it does — Nothing uses it yet, and no design was found**

  - *What writes it:* Nothing writes it on a Project.
  - *What reads it, and what changes:* Nothing reads it on a Project. Checked 2026-07-18 at June's request ("Is it in the mockup? I think this might be leak") — she is right on all three checks: the mockup assigns Goal status to GOAL only (design/mockups/review-reorganize-mobile-v4.html:106-108), app/src/fixtures/schema.ts gives Project Engagement / Project status / Side / Deadline / Typical block / Access conditions and not this, build_goal.py links the property to Goal alone, and daily_plan.py:104-105 reads it only when the type key is `gsdo_goal`. A leak, inert.

- **Last surfaced** — A date on Task. docs/orchestrator_flags_2026-07-11.md describes it as the neglect/staleness input and reports it non-functional end to end. Its intended semantics were never written down as a field definition, so none is given here — but what it DOES is now recorded (see the what-it-does entry): it is SYSTEM-MAINTAINED and must never be written by an LLM. Python is its only writer, and no agent-facing tool can set it.

  **What it does — Nothing uses it yet, and no design was found**

  - *What writes it:* PYTHON ONLY, and never an LLM. daily_plan.update_last_surfaced is the sole writer and it sits behind an interactive terminal confirmation June does not use. No MCP tool can set it; there is no generic property setter. June asked exactly this and was right: an agent should not write here.
  - *What reads it, and what changes:* status_check.py and neglect.py read it, but only as a FALLBACK — the live staleness signal is the append-only surface log (surface_log.py), because this field is a single overwriting date. 5 of 137 tasks carry a value, none newer than 2026-06-18.

- **Needs clarifying** — A checkbox on Task and Recurring. `Needs Clarifying` exists as a STATUS value with a documented meaning, but no doc explains what the separate checkbox means or how it relates to the status; backend spec §13 has it as an OPEN question. The nearest thing to a purpose anyone has written down is June's, 2026-07-18, and it is a family resemblance rather than a definition: it belongs with `AI autonomous` as an agent-facing control flag — "essentially telling agents, 'dont act on this, it can be raised, but it needs clarifying or design or something'". She also said it needs more usage data before deciding, so that stays her framing of the question, not a settled meaning.

  **What it does — Nothing uses it yet, and no design was found**

  - *What writes it:* Nothing writes the checkbox; the app's detail pane can toggle it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
  - *What reads it, and what changes:* No code reads the checkbox. (`Needs Clarifying` the STATUS value is a different thing and is read.) June, 2026-07-18, on what it is for — the clearest statement anyone has written down: it belongs to the same family as `AI autonomous`, "essentially telling agents, 'dont act on this, it can be raised, but it needs clarifying or design or something'". Both are agent-facing control flags rather than content. She also said it needs more usage data before deciding; backend spec §13 keeps it open.


---

## Goal

### Barriers

The strategic/decisional 'I don't know how to…' struggle — genuine open QUESTIONS, not undone chores. The KIND of thing that belongs here: an unresolved framing question, an unknown norm or convention, an audience or format she can't settle.

**Not this:** A concrete thing being waited for (that is `Blocked on`) and an access barrier (that is `Access conditions` / `Access notes`).

**If it's actually…**

- something concrete being waited for → `Blocked on`
- an access or executive-function barrier → `Access notes`

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it in code; the weeding-gate example set references it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* No code reads it. June, 2026-07-18: "Keep this — its pending further design." docs/route_structure_assessment_2026-07-12.md §5 names 'barriers never resurface' as the missing piece — the resurfacing, not the definition.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- as a PhD I'm overqualified and never know how to handle that in a cover letter
- don't know whether to pitch this as a paper or a tool
- no idea what a reasonable rate would be to ask for
- unclear who the audience even is

**Rules that govern a write:**

- Held so June doesn't re-derive it; queryable so the AI can find patterns across barriers over time (June's stated reason for making it a field).
- These must NOT become tasks with done-boxes — the system would quietly score her as 'behind' on things that have no answer yet, which the guards forbid.
- The AI proposes it from what June articulates as struggle; optional.

⚠️ **Observed use differs:** Nothing reads it yet, and that is a pending design rather than a dead field — June, 2026-07-18: "Keep this — its pending further design." docs/route_structure_assessment_2026-07-12.md §5 names 'barriers never resurface' as the missing piece: what is unbuilt is the resurfacing, not the definition. Keep writing it; the content is what the later design needs.

<sub>from AI_LAYER_SPEC.md §2 Goal table; docs/route_structure_assessment_2026-07-12.md §5</sub>

- [ ] this is right
- Change it to:

---

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**What it does — Working now**

- *What writes it:* Every write path: capture, the weeding gate (prompts/weeding_gate.md), the MCP server, the app, direct agent writes.
- *What reads it, and what changes:* The most widely read text field in the system — daily_plan.py, plan_generate.py, status_check.py, focus_period_generate.py all load it in full into the model's context, and the app renders it. ⚠ Do NOT write your own filing rationale here: an agent's reasoning about WHY it filed something belongs in the write log, not in a field June reads. That misroute was real and was closed in commit e39dd5b.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- confirmed 2026-07-02: the screen does not allow AI tools
- came out of the Tuesday conversation with M.
- there are two versions of this file and the newer one is in Drive, not the repo
- she has asked twice; the second ask was more urgent than the first

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

**What it does — Working now**

- *What writes it:* Nothing writes it — June sets it in the app or in Anytype. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* daily_plan.py:114 loads it and daily_plan.py:415 prints it on the goal's line in the planning prompt, with the instruction that Steady reads as normal and Backburner is noted but de-emphasised. ⚠ CORRECTION 2026-07-18: this entry previously said the field was 'not yet consumed by code'. It is consumed, as framing for the model. The cross-goal balancing engine (§8d) that would use it for real prioritisation is still unbuilt.

**Rules that govern a write:**

- Feeds the not-yet-built cross-goal balancing / route-prioritization engine (§8d). Until that is built this is data worth keeping current, not yet consumed by code.

<sub>from AI_LAYER_SPEC.md §2 Goal table</sub>

- [ ] this is right
- Change it to:

---

### Goal status

Active / Parked / Achieved.

**What it does — Working now**

- *What writes it:* Nothing writes it — set by June. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* daily_plan.py:104-105, and only when the object's type key is `gsdo_goal`. OPEN QUESTION, June's own, recorded as a question and not answered here: "im not sure what the goal status is either, other than perhaps a mechanism for allowing us to retire goals?" That is her speculation about the field's purpose, not a decision, and no doc settles it.

⚠️ **Observed use differs:** Also appears on the live Project type, where it is a leak — see `Goal status (on Project)` in UNDEFINED. On Goal itself the option list is documented but its PURPOSE is not. June's own open question, 2026-07-18, recorded as a question and deliberately not promoted into a definition: "im not sure what the goal status is either, other than perhaps a mechanism for allowing us to retire goals?" If that is what it is for, it overlaps `Horizon` + `Resolution condition`, which already describe how a goal ends. Unresolved; do not write a rationale for it.

<sub>from AI_LAYER_SPEC.md §2 Goal table; docs/review_reorganize_backend_spec.md §12</sub>

- [ ] this is right
- Change it to:

---

### Horizon

Chapter / Ongoing / Milestone. Chapter = a life phase ending when a condition is met (job search, recovery season). Ongoing = structural, no discrete end (health, craft practice). Milestone = a discrete done-state (publish paper, launch tool).

**Not this:** The vague Long/Medium/Short-term labels this replaced.

**What it does — Nothing uses it yet, and no design was found**

- *What writes it:* Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* Nothing reads it. ⚠ CORRECTION 2026-07-18: this entry previously said it 'feeds Goal ordering' and that the AI reads it to choose narration register. That is the spec's intent (AI_LAYER_SPEC.md §2 Goal), not built behaviour — no ordering or register code reads Horizon. The app uses it for chips and tabs.

**Rules that govern a write:**

- Feeds Goal ordering; the AI reads it to choose narration register (urgency vs. spiral vs. open horizon).

⚠️ **Observed use differs:** docs/review_reorganize_backend_spec.md §12 lists a wider live option set (Chapter · Milestone · Short-term · Medium-term · Long-term · Ongoing).

<sub>from AI_LAYER_SPEC.md §2 Goal table</sub>

- [ ] this is right
- Change it to:

---

### Reaching for

The WHY — optional but load-bearing when present.

**What it does — Working now**

- *What writes it:* The weeding gate proposes it for sub-goals and Projects; top-level Goals are June's to author.
- *What reads it, and what changes:* daily_plan.py:417 and plan_generate.py print it on the goal's line, so it reaches the model as the reason the goal exists.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- income that covers rent without contract work
- being able to work without pain by the autumn
- a practice that keeps going when the job situation changes
- staying in touch with the people who matter

**Rules that govern a write:**

- Top-level Goals require HUMAN authorship — drawn from a conversation or document, never AI-invented. For sub-goals and Projects the AI proposes text June edits.
- Fill rate is itself a learning-loop signal: a low fill rate means the field is not earning its place yet.
- Deliberately THIN now, designed to point at PMA's rich version later.

<sub>from AI_LAYER_SPEC.md §2 Goal + Project tables; DESIGN_v1_emerging.md §7</sub>

- [ ] this is right
- Change it to:

---

### Resolution condition

For Chapter goals: what this goal looks like when it stops claiming attention — the condition that ends it, stated so it can be recognised when it arrives.

**What it does — Working now**

- *What writes it:* Nothing writes it — June's, via the app or the weeding gate's proposal. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* daily_plan.py:113 loads it and :420 prints it as 'resolved when: …' on the goal's line in the planning prompt.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- until income covers basic needs and the GA decision is made
- when the manuscript is accepted somewhere
- when the move is finished and the boxes are gone
- when I no longer need the brace

**Rules that govern a write:**

- Optional on Ongoing/Milestone goals, but useful when the done-state needs spelling out.

<sub>from AI_LAYER_SPEC.md §2 Goal table</sub>

- [ ] this is right
- Change it to:

---

## Project

### Access conditions

Fixed multi-select for the access barriers that are QUERYABLE and load-bearing.

**Not this:** Any barrier without a live tag — those go in `Access notes` as open text.

**If it's actually…**

- a barrier with no matching tag → `Access notes`
- deliberately NO barriers, overriding what would be inherited → `Intentionally none`

**What it does — Working now**

- *What writes it:* The capture path (capture_fields.ALLOWED_ACCESS) and the app's detail pane. An unknown tag name is dropped, never created.
- *What reads it, and what changes:* daily_plan.py reads it ON A TASK, for low-capacity filtering and errand batching. On a PROJECT it is live in the schema but nothing reads it yet (docs/BUILD_DOC.md Track B §4), so a tag set there does not currently reach the plan. PLANNED ADDITION: docs/review_reorganize_backend_spec.md §6 adds `Requires-deep-thinking`, `Involves-bureaucracy` and `Induces-pain` (§6 gives behaviour only for Induces-pain: a capacity signal the scheduler and model weigh, deprioritised on low-capacity days and paired with rest, kept as a tag and never a number). Another thread is building these; until they exist, writing them does nothing because unknown tags are dropped.

**Rules that govern a write:**

- Two tags earn their place because they drive real behavior: Can-be-done-lying-down (low-capacity filtering) and Involves-leaving-house (errand-batching). Requires-talking-to-a-person is also live.
- Only live option names are ever written — an unknown tag is DROPPED, never created.
- The AI infers and proposes; June never sets it cold; ambiguous → leave empty.

⚠️ **Observed use differs:** Live tags are only the original three. The three additions in backend spec §6 (Requires-deep-thinking / Involves-bureaucracy / Induces-pain) are AGREED AND PLANNED — June, 2026-07-18: "We want to build the new tags" — and are being built by another thread. Until they are live, writing them does nothing: an unknown tag is dropped. §6 gives behaviour for only one of the three (Induces-pain, a capacity signal to weigh on low-capacity days and pair with rest); the other two are specified as names with no stated behaviour yet. ⚠ CORRECTION 2026-07-18, found by running describe_model.py against the live space: `Access conditions` IS on the Project type now — another thread added it read-back-confirmed the same day, and docs/BUILD_DOC.md Track B §4 already records that. This module was the stale one: its type list said Task/Recurring, so the field read as having no documented meaning wherever a Project was described. Project added. Note per Track B that nothing yet READS Project-level access conditions; the reader below is the Task-level one.

<sub>from AI_LAYER_SPEC.md §2 Task table `access` row; scripts/capture_fields.py ALLOWED_ACCESS</sub>

- [ ] this is right
- Change it to:

---

### Affective

The emotional charge of THIS item, in June's words — affective conditions only. The KIND of thing that belongs here: stress, avoidance, dread, hyperfixation, flatness, relief, unexpected enthusiasm.

**Not this:** Status. Findings. Confirmations. Blockers. Progress notes. Anything about the state of the WORK rather than how June feels about it. Never a number or rating.

**If it's actually…**

- a blocker → `Blocked on`
- a finding, confirmation, or origin note → `Context`
- an access or executive-function barrier → `Access notes`

**What it does — Working now**

- *What writes it:* The capture path (capture_generate.py) and ANY agent writing directly through gsdo_objects / the MCP server. There is no validator on the content — the only mechanical check is guard #3, which refuses a bare number. Everything else about whether the text is affect is your judgment.
- *What reads it, and what changes:* daily_plan.py loads it and passes it into the planning prompt, so what you write here is read back to June as part of how her day is described. A status note written here becomes the plan's account of how she FEELS about the item.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- dreading it
- keeps sliding — I think I'm avoiding it
- actually excited about this one, first time in weeks
- not scared of it, just flat about it

**Rules that govern a write:**

- Never a scalar (guard #3). Open text, explicitly marked unstable, capable of holding multiple distinct signals at once — 'affective weight is a constellation, not a scale.'
- Only surfaced when relevant; NEVER asked for tiny tasks.
- Each item's affect matches the scope June's words gave it: a feeling about one item lands on that item; a feeling she states about the whole dump lands on every item.
- The AI may offer a rough intensity read purely for filtering, but that read is low-confidence, always correctable, and never the canonical value — the text is canonical.

⚠️ **Observed use differs:** The leak lives here. Of 14 populated Affective values in the live space, the agent-written ones are status/findings, not affect. Spec and observed use disagree; the spec is the rule and the data is what needs fixing. PARTLY ADDRESSED 2026-07-18, commit e39dd5b — but read the boundary carefully, because June's note and the commit are about adjacent things. e39dd5b removed `props["Context"] = item["reasoning"]` from capture_generate._creation_props, so the gate's own filing rationale no longer lands in `Context`; it is now stamped in the write log (corrections_log.log_authorship → scripts/data/corrections.jsonl) after read-back. That closes the CONTEXT misroute on the capture path. It does NOT touch Affective: nothing in that commit changes what goes into this field, and the 14 polluted Context values were deliberately left alone (clearing them is a data edit on real objects and stays June's call). So the status-notes-in-Affective leak is still current, and prose guidance — this module, the MCP routing brief, the drift skill — is the whole of what prevents it. Separately, docs/structural_diagnosis_2026-07-11.md said Affective drove no selection; RE-VERIFIED 2026-07-18, it IS read in the plan path now. That half is STALE.

<sub>from AI_LAYER_SPEC.md §2 (Task/Project tables + 'Affective weight is a constellation'); docs/BUILD_DOC.md hazard 'FIELD-SEMANTICS LEAK' (June's field model, 2026-07-18); scripts/capture_fields.py docstring</sub>

- [ ] this is right
- Change it to:

---

### Arc position rationale

Full plain sentences (not a one-liner) explaining where this stream sits in the project arc and why.

**Not this:** A terse label or a one-line summary.

**What it does — Working now**

- *What writes it:* An agent working on the repo, through the binding protocol in scripts/gsdt_bind.py.
- *What reads it, and what changes:* No Python path reads it. Its reader is a PERSON or an AGENT opening the object — it exists so the reasoning survives across sessions instead of being re-derived (guard #6). Agent-facing by design, so 'the plan path does not read it' is not the right test of whether it works.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- This sits early in the arc because everything downstream reads the schema it defines, so changing it later would mean redoing the work that depends on it.
- This comes last on purpose. It is polish, and doing it before the shape is settled would mean polishing something that is about to change.
- This runs in parallel with the drafting rather than after it, because the two inform each other and doing them in sequence loses that.

**Rules that govern a write:**

- Guard #6: June needs to understand the reasoning, not just see the result. Stored so it persists across sessions without being re-derived.

<sub>from scripts/gsdt_bind.py (the generated per-repo CLAUDE.md binding section)</sub>

- [ ] this is right
- Change it to:

---

### Barriers

The strategic/decisional 'I don't know how to…' struggle — genuine open QUESTIONS, not undone chores. The KIND of thing that belongs here: an unresolved framing question, an unknown norm or convention, an audience or format she can't settle.

**Not this:** A concrete thing being waited for (that is `Blocked on`) and an access barrier (that is `Access conditions` / `Access notes`).

**If it's actually…**

- something concrete being waited for → `Blocked on`
- an access or executive-function barrier → `Access notes`

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it in code; the weeding-gate example set references it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* No code reads it. June, 2026-07-18: "Keep this — its pending further design." docs/route_structure_assessment_2026-07-12.md §5 names 'barriers never resurface' as the missing piece — the resurfacing, not the definition.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- as a PhD I'm overqualified and never know how to handle that in a cover letter
- don't know whether to pitch this as a paper or a tool
- no idea what a reasonable rate would be to ask for
- unclear who the audience even is

**Rules that govern a write:**

- Held so June doesn't re-derive it; queryable so the AI can find patterns across barriers over time (June's stated reason for making it a field).
- These must NOT become tasks with done-boxes — the system would quietly score her as 'behind' on things that have no answer yet, which the guards forbid.
- The AI proposes it from what June articulates as struggle; optional.

⚠️ **Observed use differs:** Nothing reads it yet, and that is a pending design rather than a dead field — June, 2026-07-18: "Keep this — its pending further design." docs/route_structure_assessment_2026-07-12.md §5 names 'barriers never resurface' as the missing piece: what is unbuilt is the resurfacing, not the definition. Keep writing it; the content is what the later design needs.

<sub>from AI_LAYER_SPEC.md §2 Goal table; docs/route_structure_assessment_2026-07-12.md §5</sub>

- [ ] this is right
- Change it to:

---

### Block chunk min

A durable per-project preference: how many minutes one work chunk on this project should be.

**Not this:** Ephemeral state such as 'did a chunk today' — that stays in the local block_duration_log.jsonl.

**What it does — Working now**

- *What writes it:* Nothing writes it — June's durable preference, set on the project. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* block_duration.py and daily_plan.py, to size one work chunk on this project. Read by DISPLAY NAME, because its Anytype key is auto-generated.

**Rules that govern a write:**

- Anytype-is-master: durable preference → Anytype; ephemeral/resetting state → local file. An earlier draft put this number in a local file; that was flagged as forking the source of truth.
- Its Anytype key is auto-generated (block_chunk_min, no gsdo_ prefix), so it is read BY DISPLAY NAME.

<sub>from docs/display_grain_design.md (revised 2026-07-14, post-swarm); scripts/block_duration.py</sub>

- [ ] this is right
- Change it to:

---

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**What it does — Working now**

- *What writes it:* Every write path: capture, the weeding gate (prompts/weeding_gate.md), the MCP server, the app, direct agent writes.
- *What reads it, and what changes:* The most widely read text field in the system — daily_plan.py, plan_generate.py, status_check.py, focus_period_generate.py all load it in full into the model's context, and the app renders it. ⚠ Do NOT write your own filing rationale here: an agent's reasoning about WHY it filed something belongs in the write log, not in a field June reads. That misroute was real and was closed in commit e39dd5b.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- confirmed 2026-07-02: the screen does not allow AI tools
- came out of the Tuesday conversation with M.
- there are two versions of this file and the newer one is in Drive, not the repo
- she has asked twice; the second ask was more urgent than the first

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

**What it does — Working now**

- *What writes it:* The capture path; the app's detail pane.
- *What reads it, and what changes:* daily_plan.py and plan_generate.py load it into the planning context.

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

**What it does — Nothing uses it yet, and no design was found**

- *What writes it:* Nothing writes it.
- *What reads it, and what changes:* Nothing reads it. Documented in the per-repo binding scripts/gsdt_bind.py generates; no ordering code consumes it and no plan for one was found.

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

**What it does — Working now**

- *What writes it:* The capture path, the MCP server, server.py, the app.
- *What reads it, and what changes:* daily_plan.py, plan_generate.py, status_check.py and the app's plan view.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- a short article for a general audience, drafted then workshopped
- the household admin that keeps the flat running
- rebuilding the tool's front end so it works on a phone
- physiotherapy and the appointments around it

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

**What it does — Working now**

- *What writes it:* The capture path (default Open for a new project), the weeding gate, server.py, and the app.
- *What reads it, and what changes:* The most consequential select on Project. daily_plan.py, plan_generate.py, grain.py, neglect.py, block_duration.py, status_check.py and focus_period_generate.py all gate on it, and the app shows it as a chip. Setting Backburner removes a project from the daily plan until a neglect threshold; Done removes it entirely. This value decides whether June sees the project at all.

**Rules that govern a write:**

- Steady → one normal daily move the plan commits to. Open → available, surfaced gently, not pushed (the default a new project is born with). Backburner → not surfaced unless a neglect threshold. Done → excluded, and never a birth value.
- An invalid or blank value means Open — the default lives in capture_fields, not in gsdo_objects (there is deliberately no born-Open chokepoint in the write layer).

<sub>from AI_LAYER_SPEC.md §2 Project table + the 2026-07-11 selection reconciliation note; scripts/capture_fields.py PROJECT_ENGAGEMENTS</sub>

- [ ] this is right
- Change it to:

---

### Engagement notes

The situated specifics the Engagement select cannot hold: the threshold that would change it, the cadence it implies, a date it turns on, or hyperfixation/intensity context.

**What it does — Working now**

- *What writes it:* The capture path and the weeding gate.
- *What reads it, and what changes:* daily_plan.py passes it to the planner as the authoritative statement of what the Engagement value MEANS for this project right now.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- Steady: about half an hour a day, mornings
- Backburner until after the surgery recovery
- opens up once the grant decision lands
- weighed against the article — whichever has the nearer date

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

**What it does — Working now**

- *What writes it:* The capture path, the MCP server, gsdo_objects (which drops a wrong-kind link rather than writing it).
- *What reads it, and what changes:* daily_plan.py:147 — the alignment chain the plan uses to say which goal a piece of work serves. (Read nowhere before the 2026-07-14 loader fix.)

**Rules that govern a write:**

- A Project may serve multiple Goals; storage is a graph, not a tree.

⚠️ **Observed use differs:** docs/structural_diagnosis_2026-07-11.md called goal_link 'the alignment chain' and said it was read NOWHERE in the plan path. ⚠ RE-VERIFIED 2026-07-18: STALE — daily_plan.py:147 reads it, fixed 2026-07-14 (the loader used to drop the relation).

<sub>from AI_LAYER_SPEC.md §2 Project table</sub>

- [ ] this is right
- Change it to:

---

### Intentionally none

PLUMBING, not a field June fills in. Which INHERITABLE fields this object has deliberately set to empty — spec §4's third state, "custom, and the custom value is none". Its options are the display names of the inheritable fields themselves (Access conditions / Block chunk min / Affective).

**Not this:** An access condition, a status, or anything June selects directly. She never sees or manages it — unticking every option in a field IS how it is set.

**If it's actually…**

- a real access barrier → `Access conditions`
- a barrier with no matching tag → `Access notes`

**What it does — Working now**

- *What writes it:* api_write.set_vals (marks when an inheritable field is written empty, unmarks when it is written a real value) and api_write.clear_field (drops it, so Inherit really does go back to inheriting). Written only when it CHANGES, so an ordinary edit logs no correction. Nothing else writes it — not capture, not the LLM.
- *What reads it, and what changes:* api_tree._vals ONLY, which folds it back in as a present-but-empty key so the spec §4 resolver stops walking at this object instead of inheriting. Deliberately invisible to everything that consumes access tags (daily_plan.py, plan_generate.py) — that invisibility is the whole reason it is a separate property.

**Rules that govern a write:**

- Spec §4 needs three states per inheritable field: unset (inherit from the nearest ancestor that sets it), set here, and set here to an explicit empty. Key-presence carries that — but only for TEXT. Verified live 2026-07-19: an empty write to a multi_select DELETES the property, and a number has no empty at all, so for `access` and `blockMin` "deliberately none" and "never touched" were the same bytes and the override silently reverted to inheriting on reload.
- It is a SEPARATE property rather than a "none of these" tag inside the field, because daily_plan.py reads access tags and PRINTS them and plan_generate.py FILTERS tasks by them — a marker in that list would render as a fake access condition and act as a phantom constraint on selection.
- The AI never proposes it and capture never writes it.

⚠️ **Observed use differs:** Added 2026-07-19 after June hit the failure it fixes: pressing Custom on a field with nothing to inherit wrote an empty value, which deleted the property, so the save failed its own read-back and she got an error for pressing a button. She confirmed overriding to empty is a real need — a task under dev work whose inherited conditions genuinely do not apply.

<sub>from review_reorganize_backend_spec.md §4 (tri-state); scripts/intentionally_none.py</sub>

- [ ] this is right
- Change it to:

---

### Parent project

The containing Project. Enables nesting and sub-routes — a work stream is a Project under a parent Project; leaf nodes are Tasks.

**What it does — Working now**

- *What writes it:* server.py (the move operation), api_write.move_object. Also api_write.convert_type (backend spec §5): a type conversion RELINKS the parent onto whichever of these properties the new type uses, and clears the one it converted away from, so the tree never reaches the object two ways.
- *What reads it, and what changes:* daily_plan.py:170-180 walks it upward to inherit Side, and the app's map renders the nesting. This is the edge that makes work streams work.

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

**What it does — Nothing uses it yet, and no design was found**

- *What writes it:* Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* Nothing in scripts/ reads it; the app's detail pane still displays it. Superseded by Engagement, which is what the plan actually gates on.

**Rules that govern a write:**

- LEGACY — the spec records that `Engagement` REPLACES this field. Prefer Engagement.

<sub>from AI_LAYER_SPEC.md §2 Project table ('Replaces the old Project status … legacy'); docs/review_reorganize_backend_spec.md §12</sub>

- [ ] this is right
- Change it to:

---

### Reaching for

The WHY — optional but load-bearing when present.

**What it does — Working now**

- *What writes it:* The weeding gate proposes it for sub-goals and Projects; top-level Goals are June's to author.
- *What reads it, and what changes:* daily_plan.py:417 and plan_generate.py print it on the goal's line, so it reaches the model as the reason the goal exists.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- income that covers rent without contract work
- being able to work without pain by the autumn
- a practice that keeps going when the job situation changes
- staying in touch with the people who matter

**Rules that govern a write:**

- Top-level Goals require HUMAN authorship — drawn from a conversation or document, never AI-invented. For sub-goals and Projects the AI proposes text June edits.
- Fill rate is itself a learning-loop signal: a low fill rate means the field is not earning its place yet.
- Deliberately THIN now, designed to point at PMA's rich version later.

<sub>from AI_LAYER_SPEC.md §2 Goal + Project tables; DESIGN_v1_emerging.md §7</sub>

- [ ] this is right
- Change it to:

---

### Relevant docs

Filepaths, directory paths, or document locations an agent should read before working on this item — a repo path, a folder, a named doc, an external system.

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it. field_semantics previously said the weeding gate populates it; no prompt in prompts/ mentions it, so that was not accurate. June can set it by hand in the review surface (review_surface.py:43). ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* Nothing reads it, and the plan path is the wrong place to look — its consumer is an AGENT about to work the item. June, 2026-07-18: "Need to be fixed." Concretely, fixed means three things: (1) the MCP server exposes it — cd_mcp_server.list_tasks returns only id/name/status and there is no get_task(id) tool at all, so a full-field read tool is the missing seam; (2) the drift skill gains a READ-side rule to match its write-routing table, telling an agent to open these paths before starting; (3) something populates it — capture should set it when an item names a file or an external system.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- ~/Documents/papers/anthro-article/
- the shared Drive folder for the grant, plus the PDF of the call
- docs/api_contract_v2.md
- the email thread with the clinic, in Mail

**Rules that govern a write:**

- Populated by the weeding gate when an item references a file or external system; the AI reads them before working on the item.

⚠️ **Observed use differs:** RE-VERIFIED 2026-07-18: not read by the plan path — but that is the WRONG TEST, same as AI autonomous. Its consumer is agent-facing: an agent working the task should open these paths first. June, 2026-07-18: "Need to be fixed." What fixed means mechanically is stated under what-it-does above (expose it through the MCP read surface, add a read-side rule to the drift skill, and populate it at capture). Correction: the usage rule above says the weeding gate populates it — no prompt in prompts/ mentions it, so nothing does. That rule is intent, not built behaviour.

<sub>from AI_LAYER_SPEC.md §2 Project + Task tables</sub>

- [ ] this is right
- Change it to:

---

### Side

An orthogonal life-domain marker on a project: Obligation / Wellbeing / Fun-hobby / Daily life (Daily life added 2026-07-13, marking the sustainable-daily-life subprojects — medical, household, self-care, social).

**Not this:** A priority or a ranking. It is applied orthogonally to engagement, never overwriting it.

**What it does — Working now**

- *What writes it:* The capture path, the weeding gate, server.py, focus_period_author.py, and the app's detail pane (on Project and sub-project only — not on work streams, goals or tasks). ⚠ A RENAME IS AGREED: June, 2026-07-18, "lets rename to work" — Obligation becomes Work per docs/review_reorganize_backend_spec.md §12. Another thread is applying it; until then the live option is still `Obligation`, and only live option names may be written.
- *What reads it, and what changes:* This is the field with the widest visible consequence, so what it does is worth knowing precisely. BACKEND — grain.py:21-40 is the whole rule, and it runs on every plan (daily_plan.py, plan_generate.py, focus_period_generate.py). `Fun / hobby` → the project is EXCLUDED from the plan; its tasks are pulled out (daily_plan.partition_by_side) and replaced by one open self-directed block, so the time is protected but June picks what goes in it. `Daily life` → rendered at TASK grain: the specific chore appears by name. `Obligation` / `Wellbeing` → rendered as a work block ("work on X"); no code distinguishes the two in selection. Side is also printed on the project's line in the planning prompt. Descendants inherit it from the nearest ancestor that sets it (daily_plan.py:170-180; app/src/model/fields.ts sideOf). FRONTEND — it renders as a labelled chip on the project row (one uniform colour: the chip says WHICH side by its word, never by hue), and it is the Map's filter axis (FilterMenu.tsx → MapScreen.tsx), so setting it decides which subtrees are reachable when June filters. A node with no Side anywhere in its chain fails every specific filter and disappears from a filtered map. The Routines tab deliberately ignores the Side filter.

**Rules that govern a write:**

- Feeds a display-grain rule: Fun-hobby → excluded from the plan; Daily life → render at TASK grain (the specific chore); everything else → smallest-subproject grain once workstreams are filtered out.
- Descendants inherit from the nearest ancestor that has it set.

⚠️ **Observed use differs:** The rename Obligation → Work (backend spec §12) is DECIDED — June, 2026-07-18: "lets rename to work" — and is another thread's to apply. Not live as of 2026-07-18, so `Obligation` is still the only writable name. Wellbeing and Obligation are distinguished in the docs but not in any selection code; the difference is currently semantic only.

<sub>from AI_LAYER_SPEC.md §2 selection-reconciliation note (2026-07-11 / 2026-07-13)</sub>

- [ ] this is right
- Change it to:

---

## Task

### AI autonomous

Can the AI do this with minimal oversight?

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* Nothing reads it, and again the plan path is the wrong test. June: it is "useful more in the agent-facing interface" — an agent deciding whether it can just do the task. Same missing seam as Relevant docs: not returned by any MCP tool, not mentioned in the drift skill.

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
- deliberately NO barriers, overriding what would be inherited → `Intentionally none`

**What it does — Working now**

- *What writes it:* The capture path (capture_fields.ALLOWED_ACCESS) and the app's detail pane. An unknown tag name is dropped, never created.
- *What reads it, and what changes:* daily_plan.py reads it ON A TASK, for low-capacity filtering and errand batching. On a PROJECT it is live in the schema but nothing reads it yet (docs/BUILD_DOC.md Track B §4), so a tag set there does not currently reach the plan. PLANNED ADDITION: docs/review_reorganize_backend_spec.md §6 adds `Requires-deep-thinking`, `Involves-bureaucracy` and `Induces-pain` (§6 gives behaviour only for Induces-pain: a capacity signal the scheduler and model weigh, deprioritised on low-capacity days and paired with rest, kept as a tag and never a number). Another thread is building these; until they exist, writing them does nothing because unknown tags are dropped.

**Rules that govern a write:**

- Two tags earn their place because they drive real behavior: Can-be-done-lying-down (low-capacity filtering) and Involves-leaving-house (errand-batching). Requires-talking-to-a-person is also live.
- Only live option names are ever written — an unknown tag is DROPPED, never created.
- The AI infers and proposes; June never sets it cold; ambiguous → leave empty.

⚠️ **Observed use differs:** Live tags are only the original three. The three additions in backend spec §6 (Requires-deep-thinking / Involves-bureaucracy / Induces-pain) are AGREED AND PLANNED — June, 2026-07-18: "We want to build the new tags" — and are being built by another thread. Until they are live, writing them does nothing: an unknown tag is dropped. §6 gives behaviour for only one of the three (Induces-pain, a capacity signal to weigh on low-capacity days and pair with rest); the other two are specified as names with no stated behaviour yet. ⚠ CORRECTION 2026-07-18, found by running describe_model.py against the live space: `Access conditions` IS on the Project type now — another thread added it read-back-confirmed the same day, and docs/BUILD_DOC.md Track B §4 already records that. This module was the stale one: its type list said Task/Recurring, so the field read as having no documented meaning wherever a Project was described. Project added. Note per Track B that nothing yet READS Project-level access conditions; the reader below is the Task-level one.

<sub>from AI_LAYER_SPEC.md §2 Task table `access` row; scripts/capture_fields.py ALLOWED_ACCESS</sub>

- [ ] this is right
- Change it to:

---

### Access notes

Open-text extension of the `Access conditions` tags: what the task needs, or what is in the way of STARTING it, for barriers that have no tag yet — unnamed executive-function and access barriers (initiation-heavy, context-switch-heavy, sensory, social, cognitive-load).

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it today; the live space is empty of it. The intended writer is the AI at capture/weeding time, proposing from what June says. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* No code reads it yet. It is designed as the place unnamed barriers accumulate so recurring ones can be promoted to real tags — AI_LAYER_SPEC.md §2 Task `access` row + the §6 promotion loop. June, 2026-07-18: surfacing the field and its purpose is the intended remedy for its emptiness.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- hard to start cold; needs someone to sit with me for the first ten minutes
- phone call — I put these off for weeks
- too many open tabs of decision before anything can be typed
- fine lying down, impossible at a desk

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

The emotional charge of THIS item, in June's words — affective conditions only. The KIND of thing that belongs here: stress, avoidance, dread, hyperfixation, flatness, relief, unexpected enthusiasm.

**Not this:** Status. Findings. Confirmations. Blockers. Progress notes. Anything about the state of the WORK rather than how June feels about it. Never a number or rating.

**If it's actually…**

- a blocker → `Blocked on`
- a finding, confirmation, or origin note → `Context`
- an access or executive-function barrier → `Access notes`

**What it does — Working now**

- *What writes it:* The capture path (capture_generate.py) and ANY agent writing directly through gsdo_objects / the MCP server. There is no validator on the content — the only mechanical check is guard #3, which refuses a bare number. Everything else about whether the text is affect is your judgment.
- *What reads it, and what changes:* daily_plan.py loads it and passes it into the planning prompt, so what you write here is read back to June as part of how her day is described. A status note written here becomes the plan's account of how she FEELS about the item.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- dreading it
- keeps sliding — I think I'm avoiding it
- actually excited about this one, first time in weeks
- not scared of it, just flat about it

**Rules that govern a write:**

- Never a scalar (guard #3). Open text, explicitly marked unstable, capable of holding multiple distinct signals at once — 'affective weight is a constellation, not a scale.'
- Only surfaced when relevant; NEVER asked for tiny tasks.
- Each item's affect matches the scope June's words gave it: a feeling about one item lands on that item; a feeling she states about the whole dump lands on every item.
- The AI may offer a rough intensity read purely for filtering, but that read is low-confidence, always correctable, and never the canonical value — the text is canonical.

⚠️ **Observed use differs:** The leak lives here. Of 14 populated Affective values in the live space, the agent-written ones are status/findings, not affect. Spec and observed use disagree; the spec is the rule and the data is what needs fixing. PARTLY ADDRESSED 2026-07-18, commit e39dd5b — but read the boundary carefully, because June's note and the commit are about adjacent things. e39dd5b removed `props["Context"] = item["reasoning"]` from capture_generate._creation_props, so the gate's own filing rationale no longer lands in `Context`; it is now stamped in the write log (corrections_log.log_authorship → scripts/data/corrections.jsonl) after read-back. That closes the CONTEXT misroute on the capture path. It does NOT touch Affective: nothing in that commit changes what goes into this field, and the 14 polluted Context values were deliberately left alone (clearing them is a data edit on real objects and stays June's call). So the status-notes-in-Affective leak is still current, and prose guidance — this module, the MCP routing brief, the drift skill — is the whole of what prevents it. Separately, docs/structural_diagnosis_2026-07-11.md said Affective drove no selection; RE-VERIFIED 2026-07-18, it IS read in the plan path now. That half is STALE.

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

**What it does — Working now**

- *What writes it:* The capture path and direct agent writes.
- *What reads it, and what changes:* daily_plan.py; prompts/daily_list.md and prompts/daily_memory_pass.md instruct the planner on it. When set it becomes the item's displayed line — the plan shows what is being waited for instead of asking her to act.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- waiting on the landlord's reply
- the portal is down
- needs Julia's spec before anything can be drafted
- insurance card hasn't arrived

**Rules that govern a write:**

- When set, this IS the displayed next item, and it is surfaced positively — the plan reports what is being waited on and treats 'nothing to do here right now' as the right answer, not as a gap. Relief, not anxiety.
- Free text, not a traversable link (noted as a gap, not a rule).

<sub>from AI_LAYER_SPEC.md §2 Task table, `blocked_on` row; docs/structural_diagnosis_2026-07-11.md (free text, not a link)</sub>

- [ ] this is right
- Change it to:

---

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**What it does — Working now**

- *What writes it:* Every write path: capture, the weeding gate (prompts/weeding_gate.md), the MCP server, the app, direct agent writes.
- *What reads it, and what changes:* The most widely read text field in the system — daily_plan.py, plan_generate.py, status_check.py, focus_period_generate.py all load it in full into the model's context, and the app renders it. ⚠ Do NOT write your own filing rationale here: an agent's reasoning about WHY it filed something belongs in the write log, not in a field June reads. That misroute was real and was closed in commit e39dd5b.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- confirmed 2026-07-02: the screen does not allow AI tools
- came out of the Tuesday conversation with M.
- there are two versions of this file and the newer one is in Drive, not the repo
- she has asked twice; the second ask was more urgent than the first

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

**What it does — Working now**

- *What writes it:* Everything: check-off in the app, the MCP server's complete_task, server.py, the capture path.
- *What reads it, and what changes:* Everything: daily_plan.py, plan_generate.py, grain.py, neglect.py, status_check.py, and roughly twenty app components. Checking it removes the item from the plan and feeds the completion record.

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

**What it does — Working now**

- *What writes it:* Not written by any Python path — set by June in the app or in Anytype. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* daily_plan.py and plan_generate.py: it drives urgency and ordering, and the within-thread pick uses the nearest deadline to choose what surfaces.

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

**What it does — Working now**

- *What writes it:* The capture path, and the app.
- *What reads it, and what changes:* scheduler.py places the day around it, grain.py sizes work blocks from it, daily_plan.py and plan_generate.py both read it. It is the single number that decides how much of June's day an item is allowed to claim — a wrong estimate here shows up as a day that does not fit.

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

**What it does — Designed, not built yet**

- *What writes it:* The capture path, always alongside Duration min.
- *What reads it, and what changes:* Nothing reads it yet. It exists so the duration-bias learning loop can separate June's own numbers from the model's guesses (scripts/capture_fields.py build_optional_props). Recording it now is what makes that loop possible later; the data cannot be reconstructed after the fact.

**Rules that govern a write:**

- Written whenever Duration min is written; never on its own.
- Exists so the future duration-bias learning loop can tell the two apart.

<sub>from scripts/capture_fields.py build_optional_props docstring</sub>

- [ ] this is right
- Change it to:

---

### Intentionally none

PLUMBING, not a field June fills in. Which INHERITABLE fields this object has deliberately set to empty — spec §4's third state, "custom, and the custom value is none". Its options are the display names of the inheritable fields themselves (Access conditions / Block chunk min / Affective).

**Not this:** An access condition, a status, or anything June selects directly. She never sees or manages it — unticking every option in a field IS how it is set.

**If it's actually…**

- a real access barrier → `Access conditions`
- a barrier with no matching tag → `Access notes`

**What it does — Working now**

- *What writes it:* api_write.set_vals (marks when an inheritable field is written empty, unmarks when it is written a real value) and api_write.clear_field (drops it, so Inherit really does go back to inheriting). Written only when it CHANGES, so an ordinary edit logs no correction. Nothing else writes it — not capture, not the LLM.
- *What reads it, and what changes:* api_tree._vals ONLY, which folds it back in as a present-but-empty key so the spec §4 resolver stops walking at this object instead of inheriting. Deliberately invisible to everything that consumes access tags (daily_plan.py, plan_generate.py) — that invisibility is the whole reason it is a separate property.

**Rules that govern a write:**

- Spec §4 needs three states per inheritable field: unset (inherit from the nearest ancestor that sets it), set here, and set here to an explicit empty. Key-presence carries that — but only for TEXT. Verified live 2026-07-19: an empty write to a multi_select DELETES the property, and a number has no empty at all, so for `access` and `blockMin` "deliberately none" and "never touched" were the same bytes and the override silently reverted to inheriting on reload.
- It is a SEPARATE property rather than a "none of these" tag inside the field, because daily_plan.py reads access tags and PRINTS them and plan_generate.py FILTERS tasks by them — a marker in that list would render as a fake access condition and act as a phantom constraint on selection.
- The AI never proposes it and capture never writes it.

⚠️ **Observed use differs:** Added 2026-07-19 after June hit the failure it fixes: pressing Custom on a field with nothing to inherit wrote an empty value, which deleted the property, so the save failed its own read-back and she got an error for pressing a button. She confirmed overriding to empty is a real need — a task under dev work whose inherited conditions genuinely do not apply.

<sub>from review_reorganize_backend_spec.md §4 (tri-state); scripts/intentionally_none.py</sub>

- [ ] this is right
- Change it to:

---

### Linked Projects

The Project(s) this task belongs to — the anti-drift chain.

**Not this:** A Goal. A Task links to Projects only; a wrong-kind link is dropped.

**What it does — Working now**

- *What writes it:* The capture path, the MCP server, gsdo_objects, api_write.move_object. Also api_write.convert_type (backend spec §5): a type conversion RELINKS the parent onto whichever of these properties the new type uses, and clears the one it converted away from, so the tree never reaches the object two ways.
- *What reads it, and what changes:* daily_plan.py, plan_generate.py, grain.py, neglect.py, focus_period_generate.py. It is how a task inherits its project's engagement, Side and grain — an unlinked task is a bare chore with no inheritance.

**Rules that govern a write:**

- Optional for bare chores. A Task may link to multiple Projects (many-to-many).

<sub>from AI_LAYER_SPEC.md §2 Task table; scripts/gsdo_objects.py _LINK_KIND</sub>

- [ ] this is right
- Change it to:

---

### Relevant docs

Filepaths, directory paths, or document locations an agent should read before working on this item — a repo path, a folder, a named doc, an external system.

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it. field_semantics previously said the weeding gate populates it; no prompt in prompts/ mentions it, so that was not accurate. June can set it by hand in the review surface (review_surface.py:43). ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* Nothing reads it, and the plan path is the wrong place to look — its consumer is an AGENT about to work the item. June, 2026-07-18: "Need to be fixed." Concretely, fixed means three things: (1) the MCP server exposes it — cd_mcp_server.list_tasks returns only id/name/status and there is no get_task(id) tool at all, so a full-field read tool is the missing seam; (2) the drift skill gains a READ-side rule to match its write-routing table, telling an agent to open these paths before starting; (3) something populates it — capture should set it when an item names a file or an external system.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- ~/Documents/papers/anthro-article/
- the shared Drive folder for the grant, plus the PDF of the call
- docs/api_contract_v2.md
- the email thread with the clinic, in Mail

**Rules that govern a write:**

- Populated by the weeding gate when an item references a file or external system; the AI reads them before working on the item.

⚠️ **Observed use differs:** RE-VERIFIED 2026-07-18: not read by the plan path — but that is the WRONG TEST, same as AI autonomous. Its consumer is agent-facing: an agent working the task should open these paths first. June, 2026-07-18: "Need to be fixed." What fixed means mechanically is stated under what-it-does above (expose it through the MCP read surface, add a read-side rule to the drift skill, and populate it at capture). Correction: the usage rule above says the weeding gate populates it — no prompt in prompts/ mentions it, so nothing does. That rule is intent, not built behaviour.

<sub>from AI_LAYER_SPEC.md §2 Project + Task tables</sub>

- [ ] this is right
- Change it to:

---

### Scheduled

The day the plan has actually PLACED the task — set by the scheduler or by June moving it. A placement record, not a deadline.

**Not this:** A deadline — that is `Due date`.

**If it's actually…**

- a deadline → `Due date`

**What it does — Working now**

- *What writes it:* plan generation (capture_generate.py, server.py) — it records a placement the system made, or June moving an item.
- *What reads it, and what changes:* daily_plan.py, plan_generate.py, grain.py, block_duration.py, status_check.py, and the app's plan view. A future-dated Scheduled keeps an item out of today.

**Rules that govern a write:**

- Keep separate from Due date; the plan reads Due date for urgency.

<sub>from docs/review_reorganize_backend_spec.md §8 (DECIDED)</sub>

- [ ] this is right
- Change it to:

---

### Task status

Ready / In Design / Parked / Needs Clarifying / Blocked / Done.

**What it does — Working now**

- *What writes it:* The capture path, the weeding gate, the MCP server, server.py, the app.
- *What reads it, and what changes:* daily_plan.py, grain.py, neglect.py. Parked takes a task out of the daily plan and the orient map; Blocked makes the plan display `Blocked on` instead of an action. Legacy `Active` is treated as Ready.

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

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* Nothing reads it, and again the plan path is the wrong test. June: it is "useful more in the agent-facing interface" — an agent deciding whether it can just do the task. Same missing seam as Relevant docs: not returned by any MCP tool, not mentioned in the drift skill.

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
- deliberately NO barriers, overriding what would be inherited → `Intentionally none`

**What it does — Working now**

- *What writes it:* The capture path (capture_fields.ALLOWED_ACCESS) and the app's detail pane. An unknown tag name is dropped, never created.
- *What reads it, and what changes:* daily_plan.py reads it ON A TASK, for low-capacity filtering and errand batching. On a PROJECT it is live in the schema but nothing reads it yet (docs/BUILD_DOC.md Track B §4), so a tag set there does not currently reach the plan. PLANNED ADDITION: docs/review_reorganize_backend_spec.md §6 adds `Requires-deep-thinking`, `Involves-bureaucracy` and `Induces-pain` (§6 gives behaviour only for Induces-pain: a capacity signal the scheduler and model weigh, deprioritised on low-capacity days and paired with rest, kept as a tag and never a number). Another thread is building these; until they exist, writing them does nothing because unknown tags are dropped.

**Rules that govern a write:**

- Two tags earn their place because they drive real behavior: Can-be-done-lying-down (low-capacity filtering) and Involves-leaving-house (errand-batching). Requires-talking-to-a-person is also live.
- Only live option names are ever written — an unknown tag is DROPPED, never created.
- The AI infers and proposes; June never sets it cold; ambiguous → leave empty.

⚠️ **Observed use differs:** Live tags are only the original three. The three additions in backend spec §6 (Requires-deep-thinking / Involves-bureaucracy / Induces-pain) are AGREED AND PLANNED — June, 2026-07-18: "We want to build the new tags" — and are being built by another thread. Until they are live, writing them does nothing: an unknown tag is dropped. §6 gives behaviour for only one of the three (Induces-pain, a capacity signal to weigh on low-capacity days and pair with rest); the other two are specified as names with no stated behaviour yet. ⚠ CORRECTION 2026-07-18, found by running describe_model.py against the live space: `Access conditions` IS on the Project type now — another thread added it read-back-confirmed the same day, and docs/BUILD_DOC.md Track B §4 already records that. This module was the stale one: its type list said Task/Recurring, so the field read as having no documented meaning wherever a Project was described. Project added. Note per Track B that nothing yet READS Project-level access conditions; the reader below is the Task-level one.

<sub>from AI_LAYER_SPEC.md §2 Task table `access` row; scripts/capture_fields.py ALLOWED_ACCESS</sub>

- [ ] this is right
- Change it to:

---

### Access notes

Open-text extension of the `Access conditions` tags: what the task needs, or what is in the way of STARTING it, for barriers that have no tag yet — unnamed executive-function and access barriers (initiation-heavy, context-switch-heavy, sensory, social, cognitive-load).

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it today; the live space is empty of it. The intended writer is the AI at capture/weeding time, proposing from what June says. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* No code reads it yet. It is designed as the place unnamed barriers accumulate so recurring ones can be promoted to real tags — AI_LAYER_SPEC.md §2 Task `access` row + the §6 promotion loop. June, 2026-07-18: surfacing the field and its purpose is the intended remedy for its emptiness.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- hard to start cold; needs someone to sit with me for the first ten minutes
- phone call — I put these off for weeks
- too many open tabs of decision before anything can be typed
- fine lying down, impossible at a desk

**Rules that govern a write:**

- The fixed category list was deliberately NOT pre-enumerated — June's correction: the four-category body list was overengineered, and the barriers that matter aren't only about the body. The set GROWS from her real annotations.
- Recurring patterns in this note feed the §6 promotion loop: when an unnamed barrier keeps recurring, the AI surfaces it as a candidate to name as its own tag.
- The AI infers and proposes; June never sets it cold; when genuinely ambiguous the AI leaves it EMPTY rather than guessing.

⚠️ **Observed use differs:** Unpopulated across the entire live space (2026-07-18). Per the spec this is where unnamed barriers accumulate to feed tag promotion, so nothing is currently prompting for it. Recorded as an observation, not asserted as a bug. docs/structural_diagnosis_2026-07-11.md also lists access_notes among fields nothing reads.

<sub>from AI_LAYER_SPEC.md §2 Task table, `access` row</sub>

- [ ] this is right
- Change it to:

---

### Active

The on/off switch for whether this recurring item is currently part of June's daily plan. Backend spec §3: "it is not 'done' (that's per-occurrence); it is an on/off 'in my daily plan' toggle." Default on. PROMOTED out of UNDEFINED 2026-07-18: this module previously said no doc defined it, which was wrong — §3 defines it and datetime_seam.py reads it.

**Not this:** A completion state (a recurring item is never 'done', only done for today), and not the legacy `Active` value of Task status, which is a different field.

**If it's actually…**

- whether today's occurrence is finished → `the per-day completion path, not this flag`

**What it does — Working now**

- *What writes it:* recurring_active.set_recurring_active is the single writer (server.py's complete/uncomplete/toggle endpoints and capture_generate.py call it). It reads back and logs.
- *What reads it, and what changes:* datetime_seam.py:112-116, and ONLY inside the `as_needed` branch. June's read of it — "probably a tick we use to determine whether or not it surfaces in the daily plan" — matches what the spec asks for: docs/review_reorganize_backend_spec.md §3 says "it is not 'done' (that's per-occurrence); it is an on/off 'in my daily plan' toggle" and "Add `active` … Default active. `daily_plan`/scheduler skip recurring anchors that are not active." ⚠ Built only halfway: for an as-needed item Active IS the surfaces-today answer, but day/week/month items ignore it entirely, so unticking a weekly recurring currently does nothing. The scheduler-level skip §3 describes is unbuilt.

**Rules that govern a write:**

- Write it through recurring_active.set_recurring_active, the single writer — never by hand. It reads back and logs.
- ⚠ It only takes effect on `as_needed` items. On day/week/month items nothing consults it, so unticking a weekly recurring does not currently remove it from the plan. The scheduler-level skip backend spec §3 asks for is unbuilt.

⚠️ **Observed use differs:** June, 2026-07-18, before this was traced: "probably a tick we use to determine whether or not it surfaces in the daily plan." That matches §3 exactly. The gap is in the build, not in her reading of it.

<sub>from docs/review_reorganize_backend_spec.md §3; scripts/datetime_seam.py:105-116; scripts/recurring_active.py</sub>

- [ ] this is right
- Change it to:

---

### Affective

The emotional charge of THIS item, in June's words — affective conditions only. The KIND of thing that belongs here: stress, avoidance, dread, hyperfixation, flatness, relief, unexpected enthusiasm.

**Not this:** Status. Findings. Confirmations. Blockers. Progress notes. Anything about the state of the WORK rather than how June feels about it. Never a number or rating.

**If it's actually…**

- a blocker → `Blocked on`
- a finding, confirmation, or origin note → `Context`
- an access or executive-function barrier → `Access notes`

**What it does — Working now**

- *What writes it:* The capture path (capture_generate.py) and ANY agent writing directly through gsdo_objects / the MCP server. There is no validator on the content — the only mechanical check is guard #3, which refuses a bare number. Everything else about whether the text is affect is your judgment.
- *What reads it, and what changes:* daily_plan.py loads it and passes it into the planning prompt, so what you write here is read back to June as part of how her day is described. A status note written here becomes the plan's account of how she FEELS about the item.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- dreading it
- keeps sliding — I think I'm avoiding it
- actually excited about this one, first time in weeks
- not scared of it, just flat about it

**Rules that govern a write:**

- Never a scalar (guard #3). Open text, explicitly marked unstable, capable of holding multiple distinct signals at once — 'affective weight is a constellation, not a scale.'
- Only surfaced when relevant; NEVER asked for tiny tasks.
- Each item's affect matches the scope June's words gave it: a feeling about one item lands on that item; a feeling she states about the whole dump lands on every item.
- The AI may offer a rough intensity read purely for filtering, but that read is low-confidence, always correctable, and never the canonical value — the text is canonical.

⚠️ **Observed use differs:** The leak lives here. Of 14 populated Affective values in the live space, the agent-written ones are status/findings, not affect. Spec and observed use disagree; the spec is the rule and the data is what needs fixing. PARTLY ADDRESSED 2026-07-18, commit e39dd5b — but read the boundary carefully, because June's note and the commit are about adjacent things. e39dd5b removed `props["Context"] = item["reasoning"]` from capture_generate._creation_props, so the gate's own filing rationale no longer lands in `Context`; it is now stamped in the write log (corrections_log.log_authorship → scripts/data/corrections.jsonl) after read-back. That closes the CONTEXT misroute on the capture path. It does NOT touch Affective: nothing in that commit changes what goes into this field, and the 14 polluted Context values were deliberately left alone (clearing them is a data edit on real objects and stays June's call). So the status-notes-in-Affective leak is still current, and prose guidance — this module, the MCP routing brief, the drift skill — is the whole of what prevents it. Separately, docs/structural_diagnosis_2026-07-11.md said Affective drove no selection; RE-VERIFIED 2026-07-18, it IS read in the plan path now. That half is STALE.

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

**What it does — Working now**

- *What writes it:* The capture path and direct agent writes.
- *What reads it, and what changes:* daily_plan.py; prompts/daily_list.md and prompts/daily_memory_pass.md instruct the planner on it. When set it becomes the item's displayed line — the plan shows what is being waited for instead of asking her to act.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- waiting on the landlord's reply
- the portal is down
- needs Julia's spec before anything can be drafted
- insurance card hasn't arrived

**Rules that govern a write:**

- When set, this IS the displayed next item, and it is surfaced positively — the plan reports what is being waited on and treats 'nothing to do here right now' as the right answer, not as a gap. Relief, not anxiety.
- Free text, not a traversable link (noted as a gap, not a rule).

<sub>from AI_LAYER_SPEC.md §2 Task table, `blocked_on` row; docs/structural_diagnosis_2026-07-11.md (free text, not a link)</sub>

- [ ] this is right
- Change it to:

---

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**What it does — Working now**

- *What writes it:* Every write path: capture, the weeding gate (prompts/weeding_gate.md), the MCP server, the app, direct agent writes.
- *What reads it, and what changes:* The most widely read text field in the system — daily_plan.py, plan_generate.py, status_check.py, focus_period_generate.py all load it in full into the model's context, and the app renders it. ⚠ Do NOT write your own filing rationale here: an agent's reasoning about WHY it filed something belongs in the write log, not in a field June reads. That misroute was real and was closed in commit e39dd5b.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- confirmed 2026-07-02: the screen does not allow AI tools
- came out of the Tuesday conversation with M.
- there are two versions of this file and the newer one is in Drive, not the repo
- she has asked twice; the second ask was more urgent than the first

**Rules that govern a write:**

- 'The fundamental rule: formal fields exist only for what the AI must query or filter on. Everything else lives in `context` (free text, always present, always read).'
- New patterns emerge in Context BEFORE we know they are patterns; they promote to formal fields when they have earned it (§6). So writing something here is the correct default, not a fallback.
- On Strategy: origin, lifespan notes, why it was adopted. Heavily used — ~10 of June's 12 real Strategy objects populate it.

<sub>from AI_LAYER_SPEC.md §2 ('The fundamental rule') + per-type tables; docs/BUILD_DOC.md §8 Strategy decision (live usage across her 12 Strategies)</sub>

- [ ] this is right
- Change it to:

---

### Day of month

The day-of-month anchor for a month-unit recurrence: the day number, 1-31, this item is due on. Defined 2026-07-18 from the code that reads it — no spec document defines this field.

**Not this:** A weekly anchor (that is `Day of week`) and a one-off date (that is `Due date` on a Task).

**If it's actually…**

- a weekly anchor → `Day of week`
- a one-off date → `Due date`

**What it does — Working now**

- *What writes it:* Nothing writes it; the app's recurrence card and the review surface edit it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* datetime_seam.py:131-140, the month branch: due when today's day number equals it, clamped to the month's last day so 31 fires on Feb 28/29. Two consequences worth knowing — a month-unit recurring with this UNSET is never due, silently; and Interval count is ignored for months, so every-N-months runs monthly. Semantics are from the code; no spec defines this field.

**Rules that govern a write:**

- Required for any Recurring whose `Interval unit` is `month`. ⚠ Leaving it unset makes a monthly item NEVER due, and nothing reports that — so an unset value is a silent disappearance, not a harmless default.
- A value larger than the current month allows is clamped to that month's last day, so 31 fires on Feb 28 or 29.
- ⚠ `Interval count` is ignored for month units, so 'every 3 months' currently runs every month (datetime_seam.py:22-24 — every-N-months needs a stored start anchor the system does not keep yet).

<sub>from scripts/datetime_seam.py:131-140 (the only reader); scripts/build_recurring.py:14 (schema)</sub>

- [ ] this is right
- Change it to:

---

### Day of week

Mon–Sun. The weekly anchor: set only for items pinned to specific day(s), e.g. weekly therapy on Tuesday.

**What it does — Working now**

- *What writes it:* Nothing writes it; the app's recurrence card edits it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* datetime_seam.py, for week-unit items. Empty means un-anchored.

**Rules that govern a write:**

- Empty for un-anchored daily routines.

<sub>from AI_LAYER_SPEC.md §2 Recurring table</sub>

- [ ] this is right
- Change it to:

---

### Duration min

Estimated minutes for the item. The AI proposes a default at cold-start from task type and context — never left blank.

**What it does — Working now**

- *What writes it:* The capture path, and the app.
- *What reads it, and what changes:* scheduler.py places the day around it, grain.py sizes work blocks from it, daily_plan.py and plan_generate.py both read it. It is the single number that decides how much of June's day an item is allowed to claim — a wrong estimate here shows up as a day that does not fit.

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

**What it does — Working now**

- *What writes it:* Nothing writes it; a checkbox June sets.
- *What reads it, and what changes:* plan_generate.py:621,643 — a missed Fixed-appointment recurring is SKIPPED by the persistence rule and waits for its next cadence instead of carrying forward.

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

**What it does — Nothing uses it yet, and no design was found**

- *What writes it:* Nothing writes it.
- *What reads it, and what changes:* Nothing reads it. Legacy from the v1 prototype, replaced by Interval unit + Interval count. It may still exist in the space; ignore it.

**Rules that govern a write:**

- Replaced by the interval model. Ignore it when building; it may still exist in the space as a legacy property.

<sub>from AI_LAYER_SPEC.md §2 Recurring table note</sub>

- [ ] this is right
- Change it to:

---

### Intentionally none

PLUMBING, not a field June fills in. Which INHERITABLE fields this object has deliberately set to empty — spec §4's third state, "custom, and the custom value is none". Its options are the display names of the inheritable fields themselves (Access conditions / Block chunk min / Affective).

**Not this:** An access condition, a status, or anything June selects directly. She never sees or manages it — unticking every option in a field IS how it is set.

**If it's actually…**

- a real access barrier → `Access conditions`
- a barrier with no matching tag → `Access notes`

**What it does — Working now**

- *What writes it:* api_write.set_vals (marks when an inheritable field is written empty, unmarks when it is written a real value) and api_write.clear_field (drops it, so Inherit really does go back to inheriting). Written only when it CHANGES, so an ordinary edit logs no correction. Nothing else writes it — not capture, not the LLM.
- *What reads it, and what changes:* api_tree._vals ONLY, which folds it back in as a present-but-empty key so the spec §4 resolver stops walking at this object instead of inheriting. Deliberately invisible to everything that consumes access tags (daily_plan.py, plan_generate.py) — that invisibility is the whole reason it is a separate property.

**Rules that govern a write:**

- Spec §4 needs three states per inheritable field: unset (inherit from the nearest ancestor that sets it), set here, and set here to an explicit empty. Key-presence carries that — but only for TEXT. Verified live 2026-07-19: an empty write to a multi_select DELETES the property, and a number has no empty at all, so for `access` and `blockMin` "deliberately none" and "never touched" were the same bytes and the override silently reverted to inheriting on reload.
- It is a SEPARATE property rather than a "none of these" tag inside the field, because daily_plan.py reads access tags and PRINTS them and plan_generate.py FILTERS tasks by them — a marker in that list would render as a fake access condition and act as a phantom constraint on selection.
- The AI never proposes it and capture never writes it.

⚠️ **Observed use differs:** Added 2026-07-19 after June hit the failure it fixes: pressing Custom on a field with nothing to inherit wrote an empty value, which deleted the property, so the save failed its own read-back and she got an error for pressing a button. She confirmed overriding to empty is a real need — a task under dev work whose inherited conditions genuinely do not apply.

<sub>from review_reorganize_backend_spec.md §4 (tri-state); scripts/intentionally_none.py</sub>

- [ ] this is right
- Change it to:

---

### Interval count

N in 'every N days/weeks/months'. Default 1. day/1 = daily; day/3 = every 3 days.

**What it does — Working now**

- *What writes it:* Nothing writes it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* datetime_seam.py, for day and week units. ⚠ It is IGNORED for `month`: datetime_seam.py:22-24 records that v1 fires monthly regardless of N, because every-N-months needs a stored start anchor the system does not keep. So 'every 3 months' currently runs every month.

<sub>from AI_LAYER_SPEC.md §2 Recurring table</sub>

- [ ] this is right
- Change it to:

---

### Interval unit

day / week / month / as_needed — the recurrence interval's unit.

**Not this:** A Practice-vs-Routine distinction. `Has target` / `Target` were RETIRED 2026-07-16/17; a recurring item is defined by its interval alone.

**What it does — Working now**

- *What writes it:* The capture path.
- *What reads it, and what changes:* datetime_seam.py:105-141 — it selects the whole due-today branch. It also decides whether `Active` means anything: on `as_needed` the Active checkbox IS the due-today answer; on day/week/month Active is never consulted.

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

**What it does — Working now**

- *What writes it:* The capture path, the MCP server, gsdo_objects, api_write.move_object. Also api_write.convert_type (backend spec §5): a type conversion RELINKS the parent onto whichever of these properties the new type uses, and clears the one it converted away from, so the tree never reaches the object two ways.
- *What reads it, and what changes:* daily_plan.py, for the recurring item's project association.

<sub>from AI_LAYER_SPEC.md §2 Recurring table; scripts/gsdo_objects.py _LINK_KIND</sub>

- [ ] this is right
- Change it to:

---

### Relevant docs

Filepaths, directory paths, or document locations an agent should read before working on this item — a repo path, a folder, a named doc, an external system.

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it. field_semantics previously said the weeding gate populates it; no prompt in prompts/ mentions it, so that was not accurate. June can set it by hand in the review surface (review_surface.py:43). ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* Nothing reads it, and the plan path is the wrong place to look — its consumer is an AGENT about to work the item. June, 2026-07-18: "Need to be fixed." Concretely, fixed means three things: (1) the MCP server exposes it — cd_mcp_server.list_tasks returns only id/name/status and there is no get_task(id) tool at all, so a full-field read tool is the missing seam; (2) the drift skill gains a READ-side rule to match its write-routing table, telling an agent to open these paths before starting; (3) something populates it — capture should set it when an item names a file or an external system.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- ~/Documents/papers/anthro-article/
- the shared Drive folder for the grant, plus the PDF of the call
- docs/api_contract_v2.md
- the email thread with the clinic, in Mail

**Rules that govern a write:**

- Populated by the weeding gate when an item references a file or external system; the AI reads them before working on the item.

⚠️ **Observed use differs:** RE-VERIFIED 2026-07-18: not read by the plan path — but that is the WRONG TEST, same as AI autonomous. Its consumer is agent-facing: an agent working the task should open these paths first. June, 2026-07-18: "Need to be fixed." What fixed means mechanically is stated under what-it-does above (expose it through the MCP read surface, add a read-side rule to the drift skill, and populate it at capture). Correction: the usage rule above says the weeding gate populates it — no prompt in prompts/ mentions it, so nothing does. That rule is intent, not built behaviour.

<sub>from AI_LAYER_SPEC.md §2 Project + Task tables</sub>

- [ ] this is right
- Change it to:

---

### Time of day

Clock time 'HH:MM'. When set, the deterministic scheduler treats this as a FIXED ANCHOR that the day's flexible tasks flow around.

**What it does — Working now**

- *What writes it:* Nothing writes it; the app's recurrence card edits it. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* datetime_seam.py and daily_plan.py — it makes the item a fixed anchor the day's flexible work is arranged around, rather than something the scheduler may move.

**Rules that govern a write:**

- A Recurring with Day of week + Time of day + Duration min set is a fixed appointment placed at its real clock time.

<sub>from AI_LAYER_SPEC.md §2 Recurring table + 'Fixed recurring appointments'</sub>

- [ ] this is right
- Change it to:

---

## Strategy

### Context

Everything else — findings, confirmations, origin, constraints, what June keeps forgetting about this item. The catch-all the AI reads in full.

**What it does — Working now**

- *What writes it:* Every write path: capture, the weeding gate (prompts/weeding_gate.md), the MCP server, the app, direct agent writes.
- *What reads it, and what changes:* The most widely read text field in the system — daily_plan.py, plan_generate.py, status_check.py, focus_period_generate.py all load it in full into the model's context, and the app renders it. ⚠ Do NOT write your own filing rationale here: an agent's reasoning about WHY it filed something belongs in the write log, not in a field June reads. That misroute was real and was closed in commit e39dd5b.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- confirmed 2026-07-02: the screen does not allow AI tools
- came out of the Tuesday conversation with M.
- there are two versions of this file and the newer one is in Drive, not the repo
- she has asked twice; the second ask was more urgent than the first

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

**What it does — Designed, not built yet**

- *What writes it:* Nothing writes it; unused across her 12 live Strategy objects.
- *What reads it, and what changes:* No code reads it. The app displays it (strategyFields.ts). It IS defined in the spec — AI_LAYER_SPEC.md §2 Strategy calls it "the anti-forgetting field: what this strategy needs that it isn't doing yet; annotations on whether it's still working. A learning loop targets this field so the strategy improves instead of silently failing — and so June is reminded the system is revisable, not stuck." AI_LAYER_SPEC.md:505 lists that loop as still open, to be designed once strategies have accumulated real annotations.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- this one only fires when I'm already calm — needs a version for bad days
- worked in June, stopped working once the schedule got fragmented
- too abstract to act on; needs a concrete first move attached
- still good, no change needed as of this month

**Rules that govern a write:**

- A learning loop targets this field so the strategy improves instead of silently failing — and so June is reminded the system is revisable, not stuck.

⚠️ **Observed use differs:** Designed, defined, and unused — not undefined. Unused across her 12 live Strategy objects (docs/BUILD_DOC.md §8). June, 2026-07-18: "useful to build on later, although im not sure what the original plan for it was." The plan IS written down, in AI_LAYER_SPEC.md §2 Strategy, and is quoted in full under what-it-does above so it does not have to be hunted for.

<sub>from AI_LAYER_SPEC.md §2 Strategy table</sub>

- [ ] this is right
- Change it to:

---

### Strategy status

Active / Retired. Queried so the AI applies only currently-active strategies.

**What it does — Working now**

- *What writes it:* capture_generate.py:392 sets it to Active when a strategy is adopted.
- *What reads it, and what changes:* daily_plan.py:252-253 filters the strategy set on it — only Active (or unset) strategies are loaded into the planning prompt. Setting Retired takes a strategy out of every plan from that point on.

**Rules that govern a write:**

- A strategy's lifespan is terminal — retiring one is EXPECTED, not failure.

<sub>from AI_LAYER_SPEC.md §2 Strategy table</sub>

- [ ] this is right
- Change it to:

---

### What for

When and where to apply the strategy — the point-of-performance trigger (Barkley: surface it at the moment the behavior has to happen, not in the abstract).

**What it does — Working now**

- *What writes it:* Nothing writes it — June writes it, in the app or in Anytype. ⚠ CORRECTED 2026-07-18 — that is no longer true: the Review & Reorganize write layer (api_write.py, behind PATCH /api/object/{id}) writes it from the surface's form, with read-back and a corrections_log record naming who authored the old value.
- *What reads it, and what changes:* daily_plan.py:258 loads it and it is printed under 'Active strategies' in the planning prompt, so it is read by the model on every plan.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- When planning a day that involves leaving the house.
- At the point of sitting down to write, before opening anything else.
- Whenever a task has been carried over three days running.
- When the plan has more than four items on it.

**Rules that govern a write:**

- Lets the AI know WHEN a strategy is relevant.

⚠️ **Observed use differs:** In June's 12 real Strategy objects this field carries BOTH the trigger AND the instruction — e.g. 'When planning days that involve leaving the house. Weigh the cumulative spoon-cost of errands, not just count.' Used on essentially all of them (docs/BUILD_DOC.md §8 Strategy decision). Broader than the spec's trigger-only definition; reported, not reconciled.

<sub>from AI_LAYER_SPEC.md §2 Strategy table</sub>

- [ ] this is right
- Change it to:

---

## Focus Period

### Availability end

The end of the narrower free window inside the period.

**Not this:** The period's own bounds — those are `Period start` / `Period end`.

**If it's actually…**

- the period's own bounds → `Period start / Period end`

**What it does — Working now**

- *What writes it:* focus_period_author.py.
- *What reads it, and what changes:* focus_period.in_availability_window; the test needs both ends.

**Rules that govern a write:**

- Set together with `Availability start`; the window test needs both.

⚠️ **Observed use differs:** Populated on 3 of 7 live periods, always paired with `Availability start`.

<sub>from docs/focus_configuration_addendum.md (Focus Period field table); docs/review_reorganize_backend_spec.md §17; scripts/focus_period.py</sub>

- [ ] this is right
- Change it to:

---

### Availability note

What the availability window MEANS for planning — how fragmented the time is, what kind of work fits it, whether it is wider or narrower than usual. The dates say when; this says what to do about it, and this is what the planner reads.

**Not this:** A number, a rating, or anything compressed. Never a restatement of the dates.

**What it does — Working now**

- *What writes it:* focus_period_author.py.
- *What reads it, and what changes:* daily_plan.py and focus_period_generate.py pass it to the planner. The dates say when the window is; this says what to do about it, and this is the half the planner actually acts on.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- caregiving; fragmented time; no deep-focus blocks
- mornings only, and the mornings are good ones
- more time than usual this week, not less — evenings are free
- in and out of appointments; assume interruptions

**Rules that govern a write:**

- June: 'this note IS the mechanism… nuance lives here, not in the enum — the anti-flattening path.' The meaning is never flattened into the dates.
- A period may describe as MANY availability shapes as it needs here; the single structured window exists only for Python's is-today-affected test.
- The framing is neutral OVERRIDES, not reductions — a sprint week is MORE availability, not less. Do not write it as though every period shrinks the day.

⚠️ **Observed use differs:** Populated on 4 of 7 live periods. All 4 describe REDUCED or fragmented availability ('Limited spoon', 'Fragmented or reduced availability due to moving assistance'). The 'a period can be MORE' half of the reframe has no live use — consistent with `Workday end` being unpopulated on all 7.

<sub>from docs/focus_configuration_addendum.md (Focus Period field table, June's note; 'Reframe: drop the negative reduced framing'); docs/review_reorganize_backend_spec.md §17</sub>

- [ ] this is right
- Change it to:

---

### Availability start

The start of a NARROWER free window inside the period — caregiving days, mornings only. Empty means the whole period is available.

**Not this:** The period's own bounds — those are `Period start` / `Period end`.

**If it's actually…**

- the period's own bounds → `Period start / Period end`

**What it does — Working now**

- *What writes it:* focus_period_author.py.
- *What reads it, and what changes:* focus_period.in_availability_window, deterministically. On `Auto`, being inside this window is what makes the plan render as a priority list rather than a clock schedule.

**Rules that govern a write:**

- Structured so Python can test 'is today in the window' deterministically, with no natural-language parsing (focus_period.in_availability_window).
- Feeds the output-shape choice: on `Auto`, being inside the window is what makes the plan render as a priority list instead of a clock schedule.
- The dates carry only WHEN. What the window MEANS goes in `Availability note`.

⚠️ **Observed use differs:** Populated on 3 of 7 live periods, always paired with `Availability end`.

<sub>from docs/focus_configuration_addendum.md (Focus Period field table + 'Reframe'); docs/review_reorganize_backend_spec.md §17; scripts/focus_period.py</sub>

- [ ] this is right
- Change it to:

---

### Days off

Dates in this period that are forced OFF, overriding the weekly default (Sat/Sun, from settings.json). A structured list of ISO dates.

**Not this:** Natural language ('the weekend', 'my birthday'). Python must parse it without interpreting text.

**If it's actually…**

- why the day is off, or what it means → `Intent / Availability note`

**What it does — Working now**

- *What writes it:* focus_period_author.py, as a parsed list of ISO dates.
- *What reads it, and what changes:* focus_period.is_day_off, second in precedence after Days on and ahead of the weekly default. A day marked off is not planned as a work day.

**Rules that govern a write:**

- Structured, not natural language — deterministically testable, honoring the regex-burn lesson (no NL scanning anywhere in the calendar path).
- Precedence in focus_period.is_day_off: an explicit `Days on` date wins first, then `Days off`, then the weekly default.
- The point is to break the planner's hidden assumption that EVERY day is a full work day — a wrong default for June.
- A malformed list must surface to June, never be silently dropped: a silently-ignored day off that plans a workday is quietly punitive.

⚠️ **Observed use differs:** UNPOPULATED on all 7 live periods (2026-07-18) — only `Days on` is used. Encoding note: the build plan's tests use a JSON array; focus_period_adapter._csv writes comma-separated and every live value is comma-separated. focus_period._parse_date_list accepts both, so nothing is broken, but the plan's stated shape is not the one in the data.

<sub>from docs/focus_configuration_addendum.md (Focus Period field table, `days_off` row + June's weekly-default recommendation); docs/superpowers/plans/2026-07-02-focus-configuration-layer.md Tasks 2.1/2.2 + step 2 of Task 3.3; scripts/build_focus_period.py</sub>

- [ ] this is right
- Change it to:

---

### Days on

Dates in this period that are forced to be WORK days, overriding a weekly default that would otherwise make them off (e.g. working a Saturday). A structured list of ISO dates.

**Not this:** Natural language. Same deterministic-parsing constraint as `Days off`.

**If it's actually…**

- why the day is on, or what it means → `Intent / Availability note`

**What it does — Working now**

- *What writes it:* focus_period_author.py.
- *What reads it, and what changes:* focus_period.is_day_off, HIGHEST precedence — it beats Days off and the weekly Sat/Sun default.

**Rules that govern a write:**

- Highest precedence in focus_period.is_day_off — a `Days on` date beats both `Days off` and the weekly default.
- Only meaningful for a day the weekly default would otherwise mark off; writing an already-working weekday here is harmless but says nothing.

⚠️ **Observed use differs:** Populated on 4 of 7 live periods, comma-separated. Only ONE of those 4 carries a real override (Sat 2026-07-18); the other 3 list days that are ALREADY work days under the Sat/Sun default — redundant, not wrong. Separately: docs/review_reorganize_backend_spec.md §17 still calls this field 'stubbed in the UI but not yet a committed field — leave OPEN'. That is stale: it is a committed field, parsed and populated. Reported, not reconciled.

<sub>from docs/focus_configuration_addendum.md (Focus Period field table, June's 'overridable both ways per day'); docs/superpowers/plans/2026-07-02-focus-configuration-layer.md Task 2.2; scripts/build_focus_period.py</sub>

- [ ] this is right
- Change it to:

---

### Foreground projects

The projects June has put IN FRONT for this stretch — overriding their enduring per-project `Engagement` while the period is active.

**Not this:** A permanent change to how she engages the project. When the period lapses the project's own Engagement returns.

**If it's actually…**

- a lasting change to how she engages a project → `Engagement`
- the specifics of what that engagement means → `Engagement notes`

**What it does — Working now**

- *What writes it:* focus_period_author.py, as real object ids — and only after June confirms the reflect-back.
- *What reads it, and what changes:* daily_plan.py:437 and plan_generate.py:409 drive real SELECTION from it, by id, not as a prose hint. While the period is active these projects override their own Engagement; when it lapses the project's Engagement returns.

**Rules that govern a write:**

- This is the short-term layer of a two-layer model: the Project holds the enduring default, the period overrides it while active, and when the two contradict THE PERIOD WINS (June's decision).
- Drives REAL selection by object id — not a prose hint handed to the LLM.
- A sprint is expressed here, as a foreground action for a period. It is deliberately NOT a stored Engagement value (`Sprint` was retired 2026-07-16) and never a Goal-level state.

⚠️ **Observed use differs:** Populated on all 7 live periods (1-4 projects each) — with `Intent`, the most used field on the type. NOTE: a field with this same display name also exists on the live Goal type, where no doc explains what it means; that one stays in UNDEFINED as 'Foreground projects (on Goal)'.

<sub>from docs/focus_configuration_addendum.md ('Two layers' + precedence + 'Foreground overrides'); docs/superpowers/plans/2026-07-02-focus-configuration-layer.md Task 3.2; AI_LAYER_SPEC.md §2 Project `engagement` retirement note</sub>

- [ ] this is right
- Change it to:

---

### Intent

What this stretch of time is about, in June's own words. The primary carrier of the period's meaning — read by the planning LLM as framing.

**Not this:** Anything the structured fields already hold as an executable instruction (which projects are in front, the day's end time, which days are off).

**If it's actually…**

- which projects are in front → `Foreground projects`
- when the day ends → `Workday end`
- which days are off or on → `Days off / Days on`

**What it does — Working now**

- *What writes it:* focus_period_author.py, in June's own words, NEVER reworded by the generator (backend spec §17).
- *What reads it, and what changes:* daily_plan.py, plan_generate.py, focus_period_generate.py — it goes into the planning prompt as framing, and it is the most heavily used field on the type. This is where a nuance goes when you are tempted to invent a field for it.

**Examples — Illustrations of the KIND of content only — NOT a template and NOT a vocabulary. Write what is actually true of this item, in June's words. Do not reuse, adapt, or echo the wording below.**

- A slow week. Recovery is the point; anything else is a bonus.
- Sprint on the application. Everything else waits until it is sent.
- Caregiving most days. Short windows only, and I don't know when they'll come.
- Back to normal after the move. Ease in rather than starting at full speed.

**Rules that govern a write:**

- NEVER reworded by the generator — it is her words (backend spec §17).
- This is where the nuance lives, on purpose. The system does not meet June's variability by predicting circumstances and adding a field for each; the fields are deliberately minimal and the intelligence is in the READING. If you find yourself wanting a new field to capture a feeling or a nuance, that is the signal it belongs here instead.
- She authors it by SAYING it — the AI structures it and reflects it back for her to confirm or edit. She never fills a form.

⚠️ **Observed use differs:** Populated on all 7 live periods and consistently rich — several sentences carrying capacity, framing and explicit planning instructions (e.g. 'Dev, creative, and hobby work is open time June chooses herself - do NOT schedule specific hobby tasks'). The most heavily used field on the type.

<sub>from docs/focus_configuration_addendum.md ('Where the nuance actually lives', 'How June inputs it'); docs/review_reorganize_backend_spec.md §17</sub>

- [ ] this is right
- Change it to:

---

### Output format

The shape the day's plan is rendered in: Auto / Clock schedule / Priority list. A per-period override of how the plan looks, not of what is in it.

**Not this:** A priority, a capacity level, or how hard June is working.

**If it's actually…**

- how much capacity this stretch has → `Availability note / Intent`

**What it does — Working now**

- *What writes it:* focus_period_author.py.
- *What reads it, and what changes:* focus_period.resolve_output_shape. It changes the SHAPE the day is rendered in, not what is in it: a clock schedule, or a short priority-ordered list to pull from when a window opens. On `Auto` the shape resolves from the availability window alone — structured inputs only, never a text scan.

**Rules that govern a write:**

- A clock-time schedule literally cannot express 'a couple of hours, whenever they come' — forcing it is an instance of June's own output-format-bias principle, where the wrong output shape distorts the result. Priority list is the answer to that: a priority-ordered short list to pull from when a window opens.
- The priority-list shape is ADHD-friendly by design — few items, plain language, no clock pressure, a clear 'when you get a window, do this next.'
- `Auto` resolves from STRUCTURED inputs only (focus_period.resolve_output_shape): priority iff today is inside the availability window. The capacity nuance is the model's to read from free text, never Python's to scan.

⚠️ **Observed use differs:** Populated on 6 of 7 live periods: Auto x4, Clock schedule x1, Priority list x1.

<sub>from docs/focus_configuration_addendum.md ('When the day has no fixed shape, the plan changes shape too'); docs/review_reorganize_backend_spec.md §17; scripts/focus_period.py resolve_output_shape</sub>

- [ ] this is right
- Change it to:

---

### Paused projects

Projects held OUT of plan generation entirely while this period is active — an explicit stop, not a de-prioritization.

**Not this:** Everything that is merely not foreground. Non-foreground is NOT paused: those projects stay present and are simply scheduled after the foreground ones.

**If it's actually…**

- a project that is just not in front right now → `leave it out of both lists`

**What it does — Working now**

- *What writes it:* focus_period_author.py — and rarely. The first authoring run over-paused every non-foreground project, which silently dropped their tasks from the plan; the prompt now requires an explicit stop from June.
- *What reads it, and what changes:* focus_period_generate.py and the plan path: a paused project is held out of generation entirely. Not-foreground is NOT paused.

**Rules that govern a write:**

- Pausing must be RARE — explicit-stop only. Default is an empty list. It requires June having said something like 'stop X this period'.
- The first LLM authoring run over-paused, pausing every non-foreground project, which DROPS their tasks from the plan. The authoring prompt was tuned to require an explicit stop; that correction is the reason this rule exists.
- Pickers filter to 'pausable' projects — only those that would normally populate the plan (not Backburner/Done engagement, not Parked/Inactive status).

⚠️ **Observed use differs:** UNPOPULATED on all 7 live periods (2026-07-18) — consistent with the pause-is-rare rule holding in practice after the prompt was tuned.

<sub>from docs/superpowers/plans/2026-07-02-focus-configuration-layer.md ('Learned from first real use', commit 2a85dbd); docs/review_reorganize_backend_spec.md §17</sub>

- [ ] this is right
- Change it to:

---

### Period end

The date this stretch lapses. Its purpose beyond bounding the range: a lapsed period is what triggers the prompt to re-author, so the configuration cannot go silently stale — the exact failure this type exists to fix.

**Not this:** A deadline for any piece of work.

**If it's actually…**

- a deadline → `Due date (Task) or Deadline (Project)`

**What it does — Working now**

- *What writes it:* focus_period_author.py.
- *What reads it, and what changes:* focus_period.py. When today is past it, no period is active and the plan appends a gentle prompt to write a new one rather than planning without a configuration. Lapsed periods are kept, never deleted.

**Rules that govern a write:**

- Lapsed periods are KEPT, never deleted — history is data for the learning loops and a record of how June's phases actually went.
- When no period is active the plan appends a gentle lapse-nudge rather than silently planning without a configuration.

⚠️ **Observed use differs:** Populated on all 7 live periods.

<sub>from docs/focus_configuration_addendum.md ('Gaps the plan must address' — staleness, history is a free win); docs/superpowers/plans/2026-07-02-focus-configuration-layer.md Task 3.3 / Decision 7</sub>

- [ ] this is right
- Change it to:

---

### Period start

The date this stretch of time begins. Together with `Period end` it defines when the period is ACTIVE — the plan loads the period whose range contains today.

**Not this:** A narrower free window inside the period — that is `Availability start`.

**If it's actually…**

- a narrower free window inside the period → `Availability start`

**What it does — Working now**

- *What writes it:* focus_period_author.py, from June speaking the period aloud. Python anchors the date; the model never resolves a weekday itself.
- *What reads it, and what changes:* focus_period.py — with Period end it decides WHICH period is active, and the active period is what the whole plan is generated under.

**Rules that govern a write:**

- Python resolves every calendar fact; the agent must never infer a date or weekday. Authoring passes today's date as a deterministic anchor so 'Saturday' resolves to a real date.

⚠️ **Observed use differs:** Populated on all 7 live periods. On 4 of the 7 it EQUALS `Period end` — a single day — although the design assumes a week-long stretch (one object is even named 'Week of Jul 14' with start == end == 2026-07-14). Design and use disagree about the grain; reported, not reconciled.

<sub>from docs/focus_configuration_addendum.md (Focus Period field table); docs/superpowers/plans/2026-07-02-focus-configuration-layer.md Task 1.1; AI_LAYER_SPEC.md §2 Focus Period table</sub>

- [ ] this is right
- Change it to:

---

### Workday end

The clock time 'HH:MM' the workday ends for this period. Empty means the system default (18:00).

**Not this:** A deadline, and not a statement about capacity.

**If it's actually…**

- what this stretch feels like or demands → `Intent / Availability note`

**What it does — Working now**

- *What writes it:* focus_period_author.py.
- *What reads it, and what changes:* plan_generate.py and focus_period.py override the hardcoded 18:00 with it. Unpopulated on all 7 live periods, so the widening case it was built for (working later during a sprint) has never actually run. A companion `Workday start` is specified in backend spec §17 and does not exist yet.

**Rules that govern a write:**

- Designed to be pushed WIDER for a sprint (working till 10, 11, midnight) or narrower for a gentle week — June asked for this explicitly. It is the field that carries the 'a period can be MORE, not less' half of the design.
- Wired into the scheduler's end time, overriding the hardcoded default.

⚠️ **Observed use differs:** UNPOPULATED on all 7 live periods (2026-07-18) — the widening case the field was built for has never been used. Separately, the companion `Workday start` (backend spec §17) is now BUILT in code — the day-bounds logic reads both ends — but its schema write is still pending June's approval; see that field's entry.

<sub>from docs/focus_configuration_addendum.md ('Workday bounds' under the overrides list); docs/superpowers/plans/2026-07-02-focus-configuration-layer.md Task 3.3</sub>

- [ ] this is right
- Change it to:

---

### Workday start

The clock time 'HH:MM' the workday starts for this period. Empty means the system default (10:00).

**Not this:** A wake-up time, and not a statement about capacity.

**If it's actually…**

- what this stretch feels like or demands → `Intent / Availability note`
- a narrower stretch of DAYS inside the period → `Availability start / end`

**What it does — Designed, not built yet**

- *What writes it:* focus_period_author.py, via focus_period_adapter's authoring payload.
- *What reads it, and what changes:* plan_generate.py's day-bounds, replacing the hardcoded 10:00 start. Wired end to end, but the property does not exist on the live Focus Period type yet — build_focus_period.py adds it and has NOT been run (human-gated). Until June approves that write, reads return None and the default applies.

**Rules that govern a write:**

- The companion to `Workday end`, added for backend spec §17 — the day-bounds logic was end-only, so a period could say 'work till 22:00 this sprint' but not 'don't start me before 11' on a slow-morning stretch.
- It moves the FLOOR only. A plan generated after this time still starts now — the field never schedules work into the past.
- Distinct from Availability start, which is a DATE bounding which days are free; this is a CLOCK time bounding the hours within a day.

⚠️ **Observed use differs:** NOT YET ON THE LIVE TYPE (2026-07-18). The builder was edited to add it but deliberately not run — schema writes to June's space are human-gated (docs/BUILD_DOC.md §2). Every reader/writer is wired and inert until then.

<sub>from docs/review_reorganize_backend_spec.md §17 (flagged NEW there); scripts/plan_generate.py day-bounds; scripts/build_focus_period.py</sub>

- [ ] this is right
- Change it to:

---


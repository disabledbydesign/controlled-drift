# Controlled Drift — AI Layer Spec *(GSDO = the mechanics layer; see Name below)*

**What this is.** The design spec for the thin AI layer being built over Anytype. Written for a cold instance with no prior session context — everything a build agent needs to understand the system's purpose, constraints, and data model without reading the full research corpus.

**Name (decided session 5):** **Controlled Drift** names the *whole system* — and especially the AI alignment layer that is the real contribution. It's the name for professional / CV / public contexts. The "controlled drift" is read in the **motorsport** sense: a high-skill maneuver where you intentionally break traction and still steer the corner — *skilled nonlinear movement, not suppression of it*. **GSDO (get-shit-done-o-tron)** names the **deterministic mechanics layer** — the Python core + Anytype store + scheduler that just reliably *gets shit done*, no judgment. The productivity-framed name lands honestly where it's literally true (the dumb reliable executor); the thesis-name covers the whole. *(Note: "GSDO" is used as established shorthand throughout this spec and the repo; read it as the working/mechanics-layer term. The system is Controlled Drift.)*

**Where to start if you're building:** read §0 (why), §2 (data model), §3 (the five guards), then §9 (build sequencing + what v1 actually is). The subsystem stubs (§8) are not yet build-ready — §9 says which one to design first.

**Session context (read for depth):** `Parameters_v2.md` (formal brief + 16 parameters), `DESIGN_v1_emerging.md` (synthesis decisions + June's `//` margin notes — keep them), `JULIA_FRAMEWORK.md` (Julia Cordero's ADHD system — the porting source, credited), `SUBSTRATE_eval.md` (Anytype validated 14/14 as store), `EVAL_adopt_adapt_build.md` (ADHD tool field scan), `REFRAME_DESIGN_INDEX.md` (reading guide to the Reframe codebase).

**Design discipline: stay minimal.** Patterns that emerge in use get promoted — not pre-built. The infinity drift loop (designing forever without building) is the failure mode to refuse.

---

## 0. Who this is for and why it matters

**June** is a disabled, autistic, ADHD scholar building a task system for her own executive function. She thinks associatively and nonlinearly — the important things for her are often in the *relationships between* ideas and projects, not the items themselves. This is a design input: the system's relational model is built around how she thinks, not despite it. She forgets readily and is easily overwhelmed by heavy structure or long lists. Her input is associational — she doesn't pre-organize her thoughts before entering them, and the system should never require her to. Full profile: `~/Documents/GitHub/profile/JUNE_BLOCH_AGENT_BRIEFING.md`.

**The core problem:** alignment lives in June's head, and her head can't hold it. She can't hold her goals, the strategies pursuing them, the current tasks, and the future steps all at once. So she forgets the plan, reinvents it, forgets it again. The anxiety she's escaping comes from not being able to trust the alignment — not because something is wrong with how she thinks, but because holding it all simultaneously is genuinely too much to carry solo. The system is the other half of the partnership.

**The core telos:** the system holds the goal → strategy → alignment *for her* — she can trust she's aligned without carrying it. This is distributed cognition (June + the AI layer + the stored context jointly hold what no single part holds alone). "It lives outside my head" is the architecture, not a metaphor.

**The master design principle (June's own research finding):** *the output format is what triggers the bias.* A binary to-do list (done/not-done, priority 1–5, % complete) forces a deficit frame ("did this meet the standard?") and closes off "what is this person reaching for?" Generative and relational description over scalar scoring is what fixes it. Every flattening risk in this design traces back to this. (June calls this "output-format bias" — it's a finding from her Autograder research, where a binary classifier mis-flagged minoritized students until the output format was changed from a score to open description.)

**Completion visibility is a first-class navigation need — distinct from deficit-framing.** Knowing what remains ("3 tasks done, 4 left: [list]") answers "how much is left and what is it?" — a real ADHD time-blindness need. This is different from a judgmental progress score. The guard is against deficit framing ("you're only 40% done"), not against visibility. GSDO surfaces completion state as: tasks done + tasks remaining with their names, at both project and daily-list level. A visual progress indicator (bar, count, or arc) is valid when it shows navigation information, not judgment. What to avoid: scores, "behind," percent-as-evaluation. What to include: "X done, Y to go: [what they are]."

**Accessibility first, with flexibility and adaptability rather than rigid systems:** The system needs to accommodate June's neurodivergence all the way down, at every level. This includes both the strengths and limitations of her disability, as understood from the inside (not through the medical model of disability or external diagnostic criteria). The system should be adapted to her specific needs. However, she cannot always articulate these in advance – the system needs to be flexible enough to learn and adapt to it – including the ways that her accessibility needs shift over time and strategies that used to work well suddenly stop working. AI provides semantic flexibility capacities; database and code hold deterministic state and processes. 

**System learning, as an extension of "system holds for June" and "accessibility first" principles:** Additionally, we can count on June to forget things – a system that improves itself or surfaces emergent issues that can be designed for or around will work better than one that counts on her to remember and synthesize failure modes, structural limitations, and new needs she didn't think to name. This is the "June can't hold alignment and detailed context in her head; this system holds it for her" principle applied recursively to the system's own architecture as an ongoing process. This has an additional design benefit: we can afford to not get specifics in the build precisely right the first time if learning loops are designed well, balancing low-friction (a massive growing list requiring manual review becomes its own EF barrier) with human-in-the-loop (where her validation is load-bearing). **(v1 caveat: those self-correcting learning loops are post-v1 — v1 only *logs* the data, §9. What makes "afford to get it wrong" safe in v1 isn't a loop watching; it's that the data model is cheaply revisable — fields promote from `context`, nothing is locked. The net arrives later; until then, June's validation is the correction mechanism.)**

---

## 1. Architecture

```
June (associational voice/text input — no pre-sorting required)
        ↓
  [AI interface layer]   ← the thing being built
   MCP  |  chat-stream
        ↓
  Anytype Local API      ← the store (validated)
  localhost:31009/v1
        ↓
  Anytype (visual dashboard, sync, mobile)
```

**Store:** Anytype — local-first, end-to-end encrypted, offline-capable. The only finalist that satisfies June's privacy need (tasks include legal, health, and job-search material) natively, without infrastructure to run. Validated 14/14 including custom types, objects-relations (Anytype's term for a field that links one stored object to another, like a foreign key), and batch writes. API auth: `Authorization: Bearer <key>` + `Anytype-Version: 2025-11-08`; key in project `.env` as `get_shit_done`; OpenAPI at `localhost:31009/docs/openapi.json`. Validation scripts (durable, in-repo): `scripts/anytype_test.py` (auth/explore helpers), `scripts/anytype_validate.py` (full data-model run — what passed 14/14).

**AI interface — two surfaces, prototype both:**

- **MCP path:** `anyproto/anytype-mcp` (official Anytype MCP server) + Claude Code (June's existing subscription). Terminal front door. Minimal to set up — install the MCP. Primary fallback and development surface.
- **Chat-stream bridge:** small background process subscribing to Anytype's `/v1/spaces/{space_id}/chats/{chat_id}/messages` stream. June types in an Anytype chat object; the AI reads her data and responds there. No app-switching. Prototype after MCP is confirmed. **What this needs:** the Anytype Local API (already running, no extra cost); a small Python/Node process; the `space_id` and a designated GSDO `chat_id` (both discoverable via the API at setup, then stored in config). **Streaming vs. polling:** prefer the `/messages/stream` endpoint (lower latency, native); fall back to polling `/messages` only if the stream proves unreliable in the Developer-Preview API. The process calls Claude's API using June's subscription — no separate inference service.

**Inference:**
- Claude (via June's subscription, through Claude Code) for most tasks — strongest reasoning, works with the MCP.
- Local model (Ollama + MLX — already installed) for the sensitive tier (legal/health). Tabled as a testable question once the layer runs.

**The AI layer is the scarce thing being built.** Brain-dump-to-task-breakdown is commodity (any LLM does it). What's un-adoptable is the alignment + capacity-selection layer: the `reaching_for` check, drift detection, capacity-aware list generation. That's what we build.

**On compute cost:** the AI computes fresh where judgment is needed; results are stored where a decision has been made. When June confirms today's sort axis, it's stored for the day. When she accepts a duration estimate, it's written to `duration_estimate`. The model doesn't re-derive settled decisions every call. Fresh computation is for judgment; storage is for settled outcomes.

**Two surfaces with two jobs (negotiation vs. artifact) — load-bearing.** Distinct from the two *delivery* surfaces above (MCP vs. chat-stream), there are two *interaction* surfaces with different jobs, and conflating them caused real friction in design (June read a chat output as if it were the artifact, found it overwhelming — because a negotiation transcript is the wrong shape for a thing you live in and check back on):

- **The conversation (chat)** is the *negotiation/draft surface*. "Here's the proposed plan" → June pushes back, moves things, confirms. Ephemeral, lean. It carries only what's needed to negotiate — not the full visual organization.
- **Anytype** is the *persistent visual artifact*. The confirmed plan is **written** here: the checkable list, the clock-time schedule, the visuals, the big-picture goal/strategy connections. This is what June checks back on and lives in.

The LLM still does the *thinking* (alignment, the woven frame, ordering, drift) — but its output becomes **display-ready data written to Anytype**, which renders it. Chat negotiates; Anytype holds and renders. (This is the backend/frontend separation principle from Reframe — minimize sources of truth — applied to GSDO.)

**Clock-time is deterministic (Python, not LLM).** LLMs cannot reliably know the current time or do duration arithmetic. So the daily schedule's clock times are computed by **deterministic Python** from the current system time + stored `duration_estimate`s. The LLM proposes *ordering and content* (judgment); Python places it in time (determinism) and writes it to Anytype. This is what makes "organize my day" actually work — June needs real clock times she can trust, not an LLM's guess at what time it is.

---

## 2. Data model

**The fundamental rule: formal fields exist only for what the AI must query or filter on. Everything else lives in `context` (free text, always present, always read).**

Only what June cannot re-hold gets persisted as a formal field. `context` absorbs the rest. New patterns emerge in `context` before we know they're patterns; they promote to formal fields when they've earned it (§6).

**On "optional" fields and the bare-task principle.** A field existing in the Anytype schema does NOT mean June fills a form. June never faces a blank field. The AI surfaces a field conversationally only when it's relevant ("this one feels heavy — want to note why?"), and most fields stay empty on most tasks. The schema is the AI's queryable substrate, not June's data-entry burden. "Wash the dishes" is name + done checkbox and nothing else, forever, unless June or the AI adds more. This resolves the apparent contradiction between "bare by default" and a rich field set: the fields are for the AI to read and filter; they are never a form to complete.

### Three-level hierarchy: Goal → Project → Task

- A **Goal** is orienting and cross-cutting — it may outlast any single project and be served by many. The "why" that persists. "Material survival." "Maintain my one-practice identity as a scholar-builder." Goals have no tasks directly attached.
- A **Project** is a discrete body of work with scope, tasks, and (usually) an end. "GSDO." "Output-bias paper." "Apply to tech companies." Projects link to the Goal(s) they serve.
- A **Task** is a single checkable action within a Project.

The route-prioritization problem (§8d) lives at the Goal level: when a Goal is served by multiple Projects, which gets this week's energy? Distinct from which Task to do today.

**Structure: a graph stored, viewed as both a tree AND a graph (ratified, not inherited).** A strict Goal→Project→Task *tree* is the deep convention of every productivity app — and June thinks associatively, not hierarchically. So we don't store a tree: storage is a **graph** (Anytype objects-relations are graph edges), where the cross-cutting June cares about is native — a Task links to multiple Projects, a Project serves multiple Goals, Projects nest. The "hierarchy" is a *view*, not the storage shape. And we get **both views for free** from Anytype: a **tree view** (a Set/Collection grouped Goal→Project, legible and navigable — the default) and Anytype's **built-in graph view** (shows the cross-cutting web directly). June has used neither this kind of system nor a graph view before, so we present both from day one and learn from real use which serves her cognition — rather than deciding in the abstract. Low-risk: because storage is already relational, switching emphasis between views costs no data migration. The tree is chosen as the default *because externalized structure should be more legible than June's internal one* — not because the convention went unexamined.

**Goal ordering (no stored priority scalar).** Goals are never ranked by a stored priority number — that would be the scalar flattening guard #3 refuses. When ordering matters (the deference protocol, §7), the AI *proposes* an ordering by reading `horizon` + `status` + `reaching_for` + current situational context, and June redirects. Ordering is a live read, not a stored field.

---

### Object types

#### Goal *(custom Anytype type)*

| Field | Type | Notes |
|---|---|---|
| `name` | text | The orienting intention. |
| `reaching_for` | text | **The why — optional but load-bearing when present.** Top-level goals require human authorship (drawn from a conversation or document, not AI-invented). For sub-goals the AI proposes text June edits. Fill rate is itself a learning-loop signal — low fill rate means the field isn't earning its place yet. See §2's note on what drift detection does with this text. |
| `horizon` | select | Long-term / Medium-term / Short-term. Distinguishes orienting vision from near-term milestone; feeds Goal ordering. |
| `status` | select | Active / Parked / Achieved |
| `barriers` | text | **What's blocking progress — the strategic/decisional "I don't know how to…" struggle** (distinct from a Task's concrete `blocked_on` and from `access`). Held so June doesn't re-derive it; **queryable so the AI can find patterns across barriers over time** (June's reason for making it a field). The AI proposes it from what June articulates as struggle; optional. The *help* with these barriers is the parked stuck-support work (§10) — this field is just the persistence. |
| `context` | text | Strategic nuance, constraints, what June keeps forgetting about this goal. AI reads all of it. |

#### Project *(custom Anytype type)*

A discrete body of work serving one or more Goals. Nestable via `parent_project` (a Job Search Project might contain academic-track, tech-track, immediate-income-track sub-Projects). Leaf nodes are Tasks; intermediate nodes are sub-Projects. Nesting produces "next tangible item" structure at any level. A Task can link to multiple Projects (many-to-many).

| Field | Type | Notes |
|---|---|---|
| `name` | text | |
| `goal_link` | objects-relation | The Goal(s) this serves. **The alignment chain.** |
| `description` | text | What this project is and its approach. The "what." |
| `reaching_for` | text | Optional. The project's own "why" within its goal context. AI proposes; June authors for major projects. |
| `status` | select | Active / Parked / Inactive |
| `deadline` | date | Optional. Only when real. |
| `parent_project` | objects-relation | Optional. Enables nesting / sub-routes. |
| `excitement_level` | number 1–5 | Optional. Always displayed and confirmed as "X out of 5," never a bare number. ADHD motivation is interest-driven — excitement is a valid signal (§7). AI can read it from context rather than asking; shifts over time. |
| `relevant_docs` | text | Filepaths, directory paths, or document locations relevant to this project. AI reads these before working on project tasks. Populated by the weeding gate when a project references files or external systems. |
| `affective` | **capacity signal** (see below) | The emotional charge of this project. **Not a scalar** — modeled as a capacity signal: open text, marked unstable, may hold multiple signals at once. See "Affective weight is a constellation" below. |
| `barriers` | text | Same as Goal's `barriers`: the strategic/decisional struggle blocking this project, held + queryable for pattern-finding. Optional; AI-proposed from articulated struggle. |
| `context` | text | Everything else. AI reads all of it. |

#### Task *(built-in Anytype type — gets the free Tasks tab)*

**Bare by default.** A chore is name + done checkbox. Structure accretes only as it earns its place (and per the form-free principle above, accreting structure never means June filling a form).

A step-trajectory from task breakdown (§8c) produces de facto sub-tasks without nesting the Task type: one-time sequences → a breakdown trajectory generated on demand (not stored as Task objects); recurring or long-horizon sequences → a nested sub-Project.

| Field | Type | Notes |
|---|---|---|
| `name` | text | |
| `done` | bool | Always present. |
| `status` | select | **Active / Needs Clarifying / Blocked / Done.** "Needs Clarifying" gates vague items out of the actionable list. Associational input lands here first. "Blocked" surfaces `blocked_on`. |
| `project` | objects-relation | Links to one or more Projects (the anti-drift chain). Optional for bare chores. |
| `blocked_on` | text | What's being waited for. When set, this IS the displayed next item, surfaced positively: "Waiting: Julia's spec. Job Search is healthy — nothing to do here right now is the right answer." Relief, not anxiety. |
| `deadline` | date | Optional. |
| `duration_estimate` | number (min) | AI proposes a default at cold-start from task type/context — never left blank. Learning loop refines it from actual-vs-estimated. |
| `affective` | **capacity signal** (see below) | The emotional charge of *this task*, if any. Not a scalar; only surfaced when relevant; never asked for tiny tasks. |
| `access` | multi-select + open text | **Access conditions: what the task needs, or what's in the way of starting it.** Open by design (June's correction: the fixed four-category body list was overengineered, and the barriers that matter aren't only about the body — there are executive-function barriers not yet named). Two tags earn their place now because they're queryable and load-bearing: **Can-be-done-lying-down** (low-capacity filtering) and **Involves-leaving-house** (errand-batching). Everything else goes in the **open-text note** — unnamed EF/access barriers (initiation-heavy, context-switch-heavy, sensory, social, cognitive-load, etc.). Recurring patterns in that note **feed the §6 promotion loop**: when an unnamed barrier keeps recurring, the AI surfaces it as a candidate to name as its own tag. So the category set *grows from June's real annotations* rather than being pre-enumerated — and this is where the dropped "cognitive load" capacity axis lives (it emerges if it earns it, instead of being guessed up front). The AI infers and proposes from the task; June never sets it cold; when genuinely ambiguous, the AI leaves it empty rather than guessing. |
| `ai_autonomous` | bool | Can the AI do this with minimal oversight? Lets the system offload work June doesn't need to touch. |
| `relevant_docs` | text | Filepaths, directory paths, or document locations the AI should read when working on this task. E.g. `/Users/june/Documents/papers/anthro-article/`. The gate populates this when a task references a file or folder; the AI reads it before working on the task. |
| `context` | text | Anything else. AI reads all of it. |

**Affective weight is a constellation, not a scale.** Affective weight ("job apps after the non-renewal are heavy") is too broad and too many different signals to be a single 1–5 number — and the load-bearing axes swing week to week, sometimes day to day. A scalar would repeat the exact flattening guards #3 and #5 forbid. So `affective` is modeled the same way as capacity (the FeelingSignal pattern, §4): **open text, explicitly marked unstable, capable of holding multiple distinct signals at once.** The AI may offer a rough "X out of 5" *intensity read* derived from the text purely for filtering ("show me only the light-feeling tasks today"), but that read is low-confidence, always correctable, and never the canonical value — the text is canonical. A dedicated learning loop tracks how a given Goal/Project/Task's affective weight shifts over time *and how fast* (instability is itself data: a steadily-heavy project differs from a wildly-swinging one).

**Rest is first-class and checkable.** Rest/wellbeing/enjoyment are Tasks, checkable like any other. Making rest non-checkable was the wrong instinct (it would read as "failed at resting"). Checkable rest creates just enough friction that *not*-resting becomes gently visible — June notices the pattern without being scored as failing. The signal points at under-rest, not at failure.

**Household tasks are real labor, woven in** by `access` (leaving-house tasks batch; lying-down tasks surface on low-capacity days alongside project work). Not a second-class list.

#### Recurring *(custom Anytype type — covers Practices and Routines)*

When recurring items mix into the Task list, the list looks enormous and nothing feels done. Julia Cordero found this was why her prior system failed (she was "literally thinking of practices and mindsets as tasks"). A separate type lets the AI surface them apart from actionable one-off Tasks.

| Field | Type | Notes |
|---|---|---|
| `name` | text | |
| `interval_unit` | select | `day` / `week` / `month` / `as_needed` — replaces the old `frequency` (Daily/Weekly/As-needed). The general interval model subsumes all prior cases. |
| `interval_count` | number | N in "every N days/weeks/months." Default 1. `day/1` = daily; `day/3` = every 3 days; `week/1 + day_of_week` = weekly on those days. |
| `has_target` | bool | True = Practice (track against a target). False = Routine (just check off). |
| `target` | text | Optional; only if `has_target`. "3x/week." |
| `day_of_week` | multi-select | Optional. Mon–Sun. Weekly anchor: set only for items pinned to specific day(s) — e.g. weekly therapy (Tuesday). Empty for un-anchored daily routines. |
| `time_of_day` | text | Optional. Clock time "HH:MM". When set, the deterministic scheduler treats this as a **fixed anchor** the day's flexible tasks flow around. |
| `duration_estimate` | number (min) | Optional. Reuses the Task duration property. Needed for a time-anchored item so the scheduler knows the block length. |
| `project` | objects-relation | Optional. Links to the goal/project it serves. |
| `context` | text | Free text. |

*Note: `frequency` (select: Daily/Weekly/As-needed) was the v1-prototype field; replaced by the interval model (`interval_unit` + `interval_count`) built in session 7. The old field may still exist in the Anytype space as a legacy property — ignore it when building. `build_recurring.py` creates the interval fields idempotently.*

**Fixed recurring appointments (e.g. weekly therapy).** A recurring item with `day_of_week` + `time_of_day` + `duration_estimate` set is a fixed appointment: the scheduler (§1, deterministic Python) places it at its real clock time and arranges flexible tasks around it. v1 holds appointments here, entered once. **Reading appointments from a calendar app is parked (§10):** the privacy-right path is Apple Calendar via local AppleScript (June's actual calendar; stays on-device — *not* Google Calendar), post-v1.

#### Strategy *(custom Anytype type — covers strategies, disciplines, mindsets)*

**Not feel-good validation; a calibration input that shapes how the system behaves.** A strategy/discipline/mindset is a conceptual frame June has adopted that should change how the AI surfaces work — e.g. "present the next tangible item per project, not the whole list" (a strategy June learned, which also happens to be baked into the architecture). These have a **terminal lifespan** — usually months, occasionally years — then they drift or expire. The failure this type fixes: June adopts a strategy that works, forgets it after it lapses, and reinvents it from scratch (the same "alignment lives outside her head" failure, applied to strategies — documented across Julia's framework, June's job-search plan, and the build sessions). The daily-list and weeding prompts **read active strategies and apply them**; that's the integration layer.

A strategy can graduate to architecture (like next-item-per-project did) or be mirrored here even when baked in, so June can see/revise it. Resolves the §10 parked question (these are calibration inputs, not retrieve-later reference) — see §10.

| Field | Type | Notes |
|---|---|---|
| `name` | text | The strategy/discipline/mindset, in June's words. |
| `status` | select | Active / Retired. Queried so the AI applies only currently-active strategies. Lifespan is terminal — retiring one is expected, not failure. |
| `what_for` | text | When/where to apply it — the point-of-performance trigger (Barkley: surface it at the moment the behavior has to happen, not in the abstract). Lets the AI know *when* a strategy is relevant. |
| `learning_notes` | text | **The anti-forgetting field.** What this strategy needs that it isn't doing yet; annotations on whether it's still working. A learning loop targets this field so the strategy improves instead of silently failing — and so June is reminded the system is revisable, not stuck. |
| `context` | text | Everything else — origin, lifespan notes, why it was adopted. AI reads all of it. |

**Two senses of "strategy" — don't conflate them (June, session 4 stress test).** The everyday word "strategy" covers two genuinely different things, and only one is this type:

1. **Strategy-as-AI-calibration — *this* type.** A discipline/mindset that changes *how the AI surfaces work*: "present the next tangible item per project," "work in timed blocks then stop." The AI *applies* these; but a strategy that works for June over several months may suddenly *stop* working. This is what `Strategy` objects hold.
2. **Strategy-as-life-plan — NOT this type.** A multi-route, conditional, evolving plan about *what to pursue and when* — e.g. June's job-search strategy (grants vs. academic vs. industry vs. consulting vs. own-business vs. stable-income, gated by savings runway, surgery recovery, a possible GA move, and their timing). This is **not** a `Strategy` object. It lives in the **Goal → Projects structure**: a Goal (`reaching_for` = "material survival"), its route-Projects (nested via `parent_project`, cross-cutting where one route serves several), and **route-prioritization (§8d)**, where the AI reads the Goal + route `context` + situational context and *proposes* which route gets this week's energy. The conditional logic ("don't take a job I don't want until money runs lower"; "move to GA only after recovery and if savings drop below X") is `context` the AI reasons over. "I keep forgetting and reinventing this whole plan" is the core telos (§0) at the strategy layer — the plan lives outside June's head.

Routing rule for the weeding gate: an adopted *behavioral discipline* → `Strategy`; a *multi-route plan about what to pursue* → a Goal with route-Projects, never a single `Strategy` object.

---

### What the AI computes fresh (not stored as fields)

- **Today's sort axis** — the axis that matters shifts daily (everything-takes-too-long → duration; can't-leave-house → access; heavy day → affective). The AI proposes it as a diagnosis of today's friction; June's confirmation is stored for the day.
- **Which tasks fit current state** — AI reads context + fields, proposes the match, never imposes.
- **Breakdown trajectory** — generated on demand (§8c), not stored frozen.
- **Drift detection** — computed against `reaching_for` + `goal_link` chains in real time (mechanism in §2 note below).
- **Errand-batching** — groups `access = Involves-leaving-house`, caps the batch to avoid over-cram.
- **Route-prioritization** — which Project serving a Goal gets this week's energy (§8d).

**What drift detection actually does with `reaching_for` (the mechanism).** `reaching_for` is free text, and drift detection is NOT string comparison. The AI uses the text as a *semantic anchor*: when a new task/step/project change comes in, it reads the change against the anchor and asks itself, in natural language, "does this still serve what June said this is for?" If the answer is "not obviously," it surfaces a permission-granting question to June (never blocks). This is a soft semantic judgment, the kind LLMs do well — not a metric, not a threshold on a number. The thin free-text field is sufficient for this; it does not need PMA's richer structure to work (the PMA seam, §10, only deepens it later).

---

## 3. The five guards (non-negotiable)

Satisfy/violate boundaries. Violating one means the tool reproduced what it was built to refuse. Each names what violates it, because a requirement you can't violate is decoration.

**1. Nothing punitive.** No streaks, no red "overdue," no rollover-shame. Undone tasks roll forward or compost — a missed task is soil, not failure; returning to something isn't starting over. *Violates:* any mechanic that scores June as behind or failing.

**2. Offer, don't impose (crip-time temporal sovereignty — crip time treats variable capacity as the baseline, not the exception; rest is not lost time; non-linear progress is valid).** The system *offers* a reading of capacity or pacing; June always holds final authority over her own time and state. Permission-granting register throughout ("you can… you don't have to…"), never imperative. Capacity inference has its own learning loop and is always correctable. *Violates:* imperative/nagging push-language; any uncorrectable automatic action; capacity inference treated as ground truth. Rest is sometimes important in ways that June may struggle to make time for, especially when hyperfixated, and needs scaffolding around - but that scaffolding needs to be through fluid and adaptable strategies, not rigid. 

**3. Capacity is multi-dimensional, never one scalar.** Energy ≠ embodiment ≠ location ≠ duration ≠ social ≠ sensory ≠ affective weight. Collapsing them to a single readiness/priority number is the output-format-bias flattening. *Violates:* any single number that stands in for June's overall readiness or a task's overall weight.

**4. The alignment check must not become surveillance.** Drift is *offered* ("this looks like it might be pulling away from what you said this is for — intentional?"), never scolded, never blocked. Drift may be the goal evolving — returning to the same territory with deeper understanding is valid progress. The system asks; it doesn't enforce. *Violates:* nagging, blocking, automatic re-routing, treating alignment as a performance metric.

**5. Don't flatten June's situated specifics.** A task/project/day is never collapsed to a tidy number. Generative/relational description over scalar scoring — the master principle. *Violates:* any output format that produces a single score for June's work, state, or day.

---

## 4. Reframe design inheritance

The Reframe codebase was built for June, by June, and encodes hard-won knowledge about how she thinks. Several of its systems are direct design precedents for GSDO. (No prior standalone Reframe analysis exists — only `REFRAME_DESIGN_INDEX.md`, a reading guide. This section is the first port-oriented analysis; GSDO may be its natural long-term home — see §10.)

> **Audit before porting.** A concept being sound does NOT mean the code works or was implemented well. Reframe is acknowledged (by June) to possibly be several programs fused together, and its systems vary in implementation quality. Before copying ANY Reframe code: read the actual implementation, test it, and decide copy-vs-adapt-vs-rewrite per component. Adopt the *design*; re-verify or rewrite the *implementation*.

**STEP → Weeding gate (§8a).** STEP: "infodump a mess of related ideas across topics; the engine organizes them into parallel trackable sequences without requiring you to organize first." Those sequences are GSDO's Projects + Tasks + Practices. The weeding gate IS GSDO's STEP. Note (June): Reframe's STEP was limited by having no deterministic store behind it — GSDO has Anytype, a deterministic store, so GSDO is a *better* home for this logic.

**PARK → mid-stream tangent capture + `blocked_on` (§8c).** PARK: "captures the note plus full context — what you were doing, the active sequence — so when you return, context is restored." When June goes sideways mid-breakdown, the system PARKs the tangent with full context. `blocked_on` is PARK at the task level. Note (June): PARK likely belongs *in GSDO* more than in Reframe — flagged in §10 as a copy-vs-migrate decision.

**WEAVE → alignment check + route-prioritization + wins mirror (§8b, §8d, §8g).** WEAVE "analyzes every parked tangent, every completed sequence, recent exchanges — and finds through-lines." A periodic WEAVE pass drives: neglect detection ("Job Search untouched 3 days"), route-prioritization, and the wins mirror (what through-lines completed this week). Note (June): there are actually *multiple* WEAVE functions in Reframe — identify which variant(s) GSDO needs when designing §8b/§8d, don't assume one.

**FeelingSignal → capacity inference, including affective weight (§8e).** Reframe's `FeelingSignal`: `feeling_name, intensity (0.0–1.0), source ("explicit" | "heuristic" | "llm_inferred" | "pattern_learned"), decay_turns, raw_text`. GSDO: today's capacity state is a **composite of signals with sources**, not one stored field. "Bed day" stated by June = explicit (high confidence, stored); overwhelm inferred from typo density = heuristic (low confidence, correctable). **Affective weight is one of these signals** — this is why §2 models `affective` as a capacity signal rather than a scalar. The `FeelingMechanism` dataclass maps too: `routing_bias (WEAVE|SEQUENCE)` = today's sort axis; `confirmation_required` = the offer-don't-impose guard made mechanical; `learning_modifier (pause|flag|slow|accelerate)` = the system-level learning loop, slowed on bad-capacity days.

**Both affect channels are first-class (non-negotiable).** June stating affect AND the AI inferring it from heuristics (typo density, word choice, what she's avoiding) are both valid inputs — neither is primary. Every AI-inferred signal is labeled by its source ("I'm reading this as a heavy day because of X — accurate?"), surfaced for confirmation before the system acts on it, and correctable at any point. An uncorrectable inference that silently shapes the list violates guard #2.

**Crip-time changes PRESENTATION, not depth** (from `task_intensity_resolver.py`, load-bearing comment): *"crip_time NEVER modifies intensity. What it changes is OUTPUT PRESENTATION, not analytical rigor. Reducing depth for disabled users IS the ableist move crip_time exists to refuse. Access means changing the interface, not the thinking."* GSDO adaptation: on a low-capacity day the AI still reads everything and runs the full alignment + drift checks — and then surfaces *less*, phrased simply. **How much less is learned, not fixed.** (An earlier draft said "surface one task"; that's too rigid — some low-capacity days hold more than one thing, and the right amount varies. A learning loop tunes how much to surface per capacity state; this loop is a good candidate for automation.)

**Crip-time signal decay:** at low capacity, feeling signals persist until capacity lifts — they don't expire after N turns. A "bed day" at 9am holds until June updates it or the AI sees clear signals of lift.

**Idle-aware background work:** Reframe's auxiliary LLM "works when you're not, defers when you are." GSDO can do the same — update duration estimates, check neglected Goals, pre-generate a parked project's next step while June is away. Cheap once the MCP path works.

---

## 5. Additional design principles (load-bearing, not guards)

**Visual-first; numbers always shown as "X out of N."** Any scale June sets or confirms is always presented as a position out of a range ("4 out of 5"), never a bare "4," and never invented cold — the AI proposes a position *with reasoning* ("this reads like 4 out of 5: heavy but not maxed, because it's the post-non-renewal apps") and June confirms or adjusts. A true visual slider is a v2 web-UI affordance; v1 uses this conversational scale-position confirmation (resolves the "no surface renders sliders" problem without a separate v1 build surface).

**Visual dashboards over folder/text systems — a first-class UX principle.** June (and Julia) navigate by *seeing*, not by hierarchical text/folders. Anytype's Sets and Collections provide the visual dashboard without us building it; the AI layer produces display-ready data, Anytype renders. This is a load-bearing access principle, not a nicety.

**Associational input is a primary mode.** June thinks associatively, not pre-organized; the system accepts an unstructured voice/text dump and organizes it (weeds Tasks vs. Practices vs. Routines, assigns Needs-Clarifying, proposes project links). Significance may lie in interdependent, mutually informing threads, not just discrete items.  Ideas or memories of what is important may come in iterative waves, not just the step she is currently on – these need to be persisted (as per the "June's head can't hold; system needs to hold for her" principle). The AI weaves and organizes; June doesn't pre-sort. (This is a capability of her cognition the system is built around, not a deficit to correct.)

**Reminding without nagging — and why it's not actually a dial to balance.** The obvious framing is a tension between two poles: remind enough (June forgets) vs. don't watch (the anxiety). But that treats *reminding* and *surveillance* as the same axis, where more reminding is necessarily more watching — and they aren't. The anxiety isn't caused by being reminded; it's caused by *not trusting the system holds her alignment* (§0). So the cure for nag-anxiety is not *less reminding* — it's *more trustworthy holding*. A reminder from a system June fully trusts to hold her alignment doesn't read as surveillance; it reads as **her own intention, time-shifted back to her.** That reframes the whole problem from a fragile dial (always re-tuning how much to remind) to a **voice/sourcing question: whose voice does the reminder speak in?** It should sound like June reminding herself, not the system catching her. This connects to legibility (the AI's *reads* are inspectable, not just its outputs — §5 "X out of N with reasoning") — a reminder feels self-authored when June can see the reasoning behind it. **Two tiers of learning loop** (defined once here): *records-level* loops tune the data (duration estimates, affective-weight drift, capacity-surface amount); a *system-level* loop tunes the AI's own behavior (register, check-in timing, whose-voice). Both first-class. Own design pass before the chat-stream bridge ships.

**"Feel-productive" days are legitimate.** Quick-wins-for-momentum is a real ADHD need; honor a quick-wins day without guilt (maybe weave in one goal-aligned win). Offer, don't impose.

**Modes are instances, not hardcoded features.** "Healing week," "bed day," "quick-wins day" are not built-in modes — they're instances the LLM handles from context. Pre-enumerating modes pulls flexibility back onto June and freezes the AI's judgment. Guard: if tempted to build for the state June is in right now, check whether the general machinery + LLM flexibility already covers it. It usually does. Carry the current state as a test case, not a feature.

**Cold-start is real.** The system must be useful before it has learned June's patterns. Duration estimates default to AI-proposed values from day one; capacity reads start from explicit, correctable defaults. Improves with data.

**Don't specialize for the current edge case.** Building around June's current state creates dead weight when the state changes. Test current states against the general design.

---

## 6. Extensibility pattern

The system will surface things we haven't thought of yet. Expected, not a failure.

1. **`context` is the flex space.** Anything without a formal field goes here; the AI reads it; patterns emerge before we name them.

2. **AI-prompted seeding.** For a non-trivial task/project the AI may ask one targeted question ("anything about embodiment or affective charge here?"). A prompt, not a form. Tiny tasks get nothing.

3. **AI-initiated promotion loop — June will NOT notice patterns manually** (that's the ADHD she's building this to address; a "human notices and promotes" design would silently fail). The system tracks what recurs in `context`, and *surfaces* a periodic, low-pressure check-in: "I keep seeing you note emotional charge in context — make it a real field? Here's what I've seen." It also **visualizes readiness-to-promote** (a small dashboard signal) so the candidate is visible and not forgotten. June responds when she has capacity; it never nags. *v1 scope:* track patterns, surface the check-in, visualize readiness; a human makes the actual schema change. Automated schema modification is a later subsystem.

**Meta-feedback loop (own design session, not v1).** "I actually need this other thing from the system" — friction discovered in use needs a capture-and-route path into system revision. A loop on top of the records-level loops.

---

## 7. Excitement, hyperfixation, and the deference problem

ADHD motivation is interest- and passion-driven, not importance-driven (the INCUP heuristic — Interest, Challenge, Urgency, Passion — validated in `EVAL_adopt_adapt_build.md`). Excitement is a valid signal. Hold two dynamics at once:

- **Work with excitement.** High `excitement_level` on a Project → surface its tasks. Hyperfocus is leverage.
- **Surface neglected priorities** via the Goal→Project chain: if Job Search (`reaching_for` = "material survival") is untouched 3 days while GSDO is the hyperfixation, the AI offers awareness — "Job Search has a deadline and you said it's about survival; weave one task in?" An offer, not a scold.
- **Continually deferred tasks** need specific strategies – for example, when household chores or life tasks continue to not get done day after day, or even week after week, June needs help finding ways to help overcome EF – but these strategies are not yet fully defined. 

**The deference problem (why the AI will follow June into a spiral).** Agents are trained to defer; left alone, an agent helps June rabbit-hole because it's just following her in-the-moment instructions. This system needs to counteract that training to provide June with the support she actually needs. Counter-protocol: when June asks for help on a Project and the alignment read shows a higher-ordered Goal (per §2 Goal ordering — proposed, not stored-scalar) is being neglected, the AI *acknowledges first, then surfaces, then defers*: "Happy to work on GSDO — I also notice Job Search hasn't had attention in 3 days and has a Thursday deadline. Handle that first, or keep going here?" One offer. Then it does what June says.

---

## 8. Subsystem stubs

Not yet build-ready. §9 gives the build order. Each is a future design session.

Items in 8 and 10 can be added *into* the system as todo's under the GSDO project once v1 is built and validated.

### 8a. Weeding / input gate
Associational input → AI weeds Tasks (one-off) from Practices/Routines (recurring), Mindsets/Strategies (not tasks), and Vague Things (→ `Needs Clarifying`, kept out of the actionable list until clarified). Julia's central move. *Implements STEP (§4).*

**Type routing — RESOLVED (session 4), and the weeding prompt MUST encode it.** Where each weeded item lands is no longer open: one-off action → **Task**; recurring practice/routine → **Recurring**; an adopted behavioral discipline/mindset → **Strategy** (§2 — but see the two-senses note: a multi-route *life-plan* is NOT a Strategy object, it's a Goal + route-Projects); anything non-task / non-recurring / non-strategy → built-in **Note**; too-vague-to-act → Task with `status = Needs Clarifying`. The current `weeding_gate.md` reads input as a web and groups it (validated) but does **not** yet propose this routing — that gap is being closed by adding routing as a *post-web proposal layer* (group/find-through-lines first, then propose a type per item for June to confirm), re-validated on sample output. **Still to design:** the Needs-Clarifying → Clarified flow.

### 8b. Alignment hierarchy and drift detection
Task → Project → Goal → `reaching_for`, read before list generation and on proposed changes. Mechanism in §2 (semantic anchor, soft judgment, permission-granting, never blocks). **Three scales, design each separately:** (1) Goal-level drift (periodic, weekly-review register); (2) task/step-level drift within a Project (the concrete scale with real teeth — PARK/STEP scaffolding is the precedent); (3) route-prioritization (→ §8d). **To design:** prompt + sensitivity per scale; the goal-evolution-vs-drift distinction; which WEAVE variant(s) this needs (§4).

### 8c. AI-assisted task breakdown
AI proposes a step-trajectory so June needn't enumerate. (1) Living/re-runnable ("re-lay from here"); (2) collapsible (next-step vs. whole-arc by capacity); (3) "waiting on" is a first-class step; (4) steps get capacity tags → schedulable across states; (5) duration loop attaches here. **June sees and edits the breakdown — it's a proposal, not read-only.** Mid-stream tangents PARK with context (§4). **Design guard:** flexible enough for the unexpected, structured enough to prevent rabbit-holes — the AI holds the arc and surfaces (scale-2 drift), never blocks. **To design:** breakdown prompt; capacity-tagging; collapse + edit/re-lay flows. Some of its small loops are automatable (with a trends dashboard).

### 8d. Route-prioritization *(high-priority — v1 or immediately after)*
A Goal served by multiple Projects: which avenue gets this week's energy? Depends on finances, recovery, apps-in-flight, energy — and June keeps forgetting/reinventing the decision. Arguably the most painful problem alongside the capacity picker; it's the goal-level "what do I do now," and what `reaching_for` on Goals exists to enable. **Approach:** AI reads the Goal's `reaching_for` + linked Projects' `context` + situational context, proposes a prioritization with reasoning, June redirects. Framed as a read, not a directive.

### 8e. Capacity picker — "what do I do right now?" *(design from what we have)*
Assemble a day/week from parameters + current state + alignment + errand-batching + rest, without a single priority scalar. Julia re-sorts by *why she's procrastinating today* (the chosen axis = a diagnosis of today's friction). Julia's full axis spec probably isn't coming — design from: duration, embodiment, affective (the constellation signal), excitement, ai_autonomous, + the FeelingSignal composite (§4). **Audit `feeling_signal_processor.py` and `task_intensity_resolver.py` before porting (§4 caveat).** Include the §7 deference protocol and the learned capacity-surface amount (§4).

### 8f. Spatial-time view *(confirmed cheap build; disc is v1, timeline is v2)*
Time as space: proportional duration blocks; a shrinking-disc countdown. June: "I need that desperately." `vis-timeline` for the timeline; ~30 lines of SVG for the disc. The expensive part is the AI planning logic we own regardless. **Caution:** must feel like a tool June holds, not a clock watching her (guard #2). **v1 scope:** the shrinking-disc countdown only (dopamine affordance — see §9). Full vis-timeline is v2. **To design:** surface (embedded in Anytype dashboard vs. standalone); chat-stream integration.

### 8g. Wins mirror
Celebrate presence, never penalize absence (Julia's end-of-day wins, in June's register — voice-check `~/.claude/skills/voice-check/profiles/` before drafting). June's note: "a 'yeah, you did it!' moment." A WEAVE variant finds the week's completed through-lines.

**Wins are not only completed Tasks — capacity-relative and qualitative wins count, and often matter most.** A win can be embodied and untethered to any task: "went on a long walk today; couldn't have a week ago." That's a real accomplishment *relative to June's current capacity trajectory* (healing, getting stronger) — and a wins mirror that only counts task-completions would silently reproduce the productivity frame it exists to refuse (guards #1, #5), and would miss exactly the wins that matter most on low-capacity days. So: June can log a freeform win anytime, and the AI can *recognize* a candidate win from conversation ("you mentioned the walk — want to mark that?") and log it with its context (why it mattered, what it's relative to). Capacity-relative significance ("couldn't do this a week ago") is read from context, never reduced to a field. Implementation: lightweight — a `Win` note object or freeform win-entries the mirror reads; decide at build. **To design:** trigger; how the AI spots candidate wins (especially capacity-relative ones) without being saccharine or surveilling; register.

**Unexpected wins are a first-class category — and the wins mirror is balanced surfacing, not just celebration (June, session 4).** Because June thinks nonlinearly, she accomplishes *unplanned* things constantly — often huge ones — and loses track of them (the design session itself was the proof case: major unexpected wins, lost track of by day's end). The reframe this resolves: nonlinear work is a source of anxiety ("I drifted, I didn't do the plan") *only because the wins it produces are invisible*. Make them visible and the same nonlinearity becomes "here's what you actually accomplished." The AI should recognize unexpected wins as they happen (from conversation, completions off-plan, things that weren't on any list) and surface them at the wins mirror.

**The wins mirror and neglect-resurfacing (§9 v1) are one mechanism pointed two directions: make the invisible visible — both the wins June isn't crediting AND the essentials she isn't touching.** Balance is the point: if unexpected wins are pouring in, show that (relief); if something essential has gone untouched too long, show that too (don't let it slide silently). Neither direction is a score or a scold — both are "here's what's actually happening that you can't hold in your head." This is why the wins mirror is *not* cheesy validation (June's initial fear): the anxiety relief comes from **seeing the truth of what's happening**, good and concerning, instead of carrying vague dread. Same telos as the whole system — it lives outside her head. June, session 4: *"if I'm drifting, at least I should be able to SEE it."* **To design (with the balanced-surfacing framing):** how unexpected wins get detected without surveilling; how the two directions are surfaced together without the concerning one reading as punitive (guards #1, #4).

---

## 9. Build sequencing & v1 scope

**The failure mode to avoid is NOT just infinity-drift — it's shipping a clean data model that sits unused because no *behavior* crosses the usefulness threshold.** The data model (§2) is the foundation, but a foundation isn't a usable system. v1 must include enough behavior to be worth opening.

**Dependency order:**
```
data model (§2)  ──>  weeding gate (8a)  ──>  alignment/drift (8b)  ──>  task breakdown (8c)
       │                     │                                              
       │                     └──> capacity picker (8e) ──> spatial-time (8f)
       └──> (route-prioritization 8d depends on 8b + multiple Projects existing)
                              wins mirror (8g) depends on completed-task data (light, late)
```

**v1 = the smallest thing that's actually useful:**
1. MCP path working (Claude Code ↔ Anytype).
2. Data model created in Anytype (Goal / Project / Task / Recurring / Strategy + fields).
3. **Weeding gate (8a)** — so associational input becomes structured items. This is the first behavior; without it June faces a blank store. (Prompt drafted: `prompts/weeding_gate.md`.)
4. **Daily plan generation (richer than "a first cut" — June confirmed this is the usefulness threshold, session 4).** Not a flat list. It must:
   - surface the **next tangible item per project/thread** (Param #13 — June holds one move per thread, never the pile), organized by today's sort axis;
   - carry a **woven conceptual frame** — a narrative sentence on the organizing strategy + how today's moves advance her goals + a progress reminder (read from active `Strategy` objects + the Goal→Project chain);
   - propose a **deterministic clock-time schedule** (Python computes times from current time + `duration_estimate`s — NOT the LLM; see §1) that June negotiates in chat, then it writes to Anytype;
   - include a **"still here, not today" list** that reassures: each parked item shows its designated rhythm/slot + the reason, and the system actually re-surfaces it (see neglect-resurfacing below). The relief depends on the re-surfacing being *real*, not just stated.
   (Prompt drafted: `prompts/daily_list.md` — needs revision to this richer spec.)
5. **Alignment/drift scale-2** (task/step level) — the scale with the most teeth, cheapest to make useful.
6. **Minimal neglect-resurfacing** — a deterministic query for active items not surfaced in N days, re-raised in the daily plan. This is what makes the "not today" reassurance honest (without it, "you won't forget" is a lie that breaks the trust-the-system telos). Cheap; a light WEAVE variant (§8b/§4).
7. **Log June's plan-corrections from day 1** — when she moves a proposed time/item, record it. Don't build the learning loop in v1, but capture the data so the rhythm-learning loop (§10) has something to train on later.

**Explicitly NOT v1:** full capacity picker (8e beyond what the daily plan needs), wins mirror (8g), automated promotion, the meta-feedback loop, the chat-stream bridge (MCP first), the *visual* spatial-time timeline/disc (§8f — clock-time-as-text IS v1, the visual is v2), the rhythm/strategy *learning loops* themselves (v1 only logs the data). Route-prioritization (8d) is high-value but depends on real Project data accumulating — design it as soon as there's data to test against.

**One dopamine affordance in v1.** The wins mirror (§8g) handles the completion acknowledgment — no separate mechanism. Add a small positive sound on task completion via `afplay` (macOS system sound, ~1 line in the completion script). Try it; keep it if it helps. The full spatial-time timeline view (§8f, vis-timeline) remains v2.

**Build incrementally:** build a piece, test it in real use, commit, then the next. Each step should leave June with something she can actually open and use.

---

## 10. Open / parked (don't let these get lost)

- **Where the session mechanics live (architectural).** STEP/PARK/WEAVE currently live in Reframe, which may be trying to be several programs at once. These may belong in GSDO (PARK especially), or in cyborg-memory (the future home of PMA + RMA), or as their own stack layer. Decide copy-vs-adapt-vs-migrate per function. This spec's §4 is effectively the first port analysis; its home may be GSDO. *Big decision — its own conversation.* **Scope for that assessment (June, session 4):** it must cover Reframe's full set of session processes — not just STEP/PARK/WEAVE but **Garden, ParkRanger, mycelial network, Compost, Seed, Tend** — and decide per-process whether GSDO adopts/adapts/leaves it. Several connect to the dormant-thread-surfacing entry below; that and the wins-mirror are the GSDO-side hooks they'd attach to. Audit-before-port applies (§4): concept-sound ≠ implemented-well.
- **Two-tier learning loop: signal detection + response calibration (June, 2026-06-16).** Two distinct loops needed. (1) *Signal precision:* affect detection is multi-signal (typo density is one heuristic; others will surface in use); the loop gets more precise over time about which signals correlate with which states. (2) *Response calibration:* what to DO about a detected state can't be predicted upfront and must be learned — counterintuitive responses are the norm (overwhelm for June → longer list of completable checkable items, not shorter, because visible progress reduces anxiety while a sparse list increases it). Both loops surface patterns to June for confirmation rather than auto-applying. Design pass once there's real use data.
- **Route-prioritization** — high-priority (§8d); design as soon as there's Project data.
- **Explicit "route parameters" on Projects? (June, session 5).** Routes-as-Projects carry the conditions that drive prioritization — a route's *launch trigger* ("this opens up if X happens," often not explicit), or the *pieces being weighed* against other routes. June's question: would an explicit `parameters`/`conditions` section (vs. burying it in `context`) make it **easier to use** — both for her to see and for the AI to read in §8d? Recommendation (not yet decided): keep it in `context` for v1 and let the shape **emerge, then promote to a formal field when it earns it (§6)** — because (a) §8d is what consumes it and isn't built yet, so we'd be guessing the field shape, and (b) there are no real cross-route examples yet. Same emerge-then-promote move as the `access` field. **Decide this when §8d is designed** — or sooner if June wants the optional field now (cheap to add). Note the usability axis June raised (her own legibility), which is a *distinct* reason from AI-queryability and the §2 "formal-only-if-queried" rule doesn't fully cover it.
- **Stuck-support / "think-with-me" mode (June, session 5 — important; likely its own design pass).** The weeding gate *names and sorts* a problem well — but naming it can leave June with *"I still don't know what to DO about any of it."* There's a capability missing here, distinct from organizing: when June articulates struggle ("I don't know how to solve this," "I don't know which to prioritize," "I don't know where to start"), the system should shift from organizing to **thinking *with* her** — helping work the problem, not just filing it. This is arguably the deepest expression of the core telos ("the system is the other half of the partnership," §0). What it does: (a) **brainstorm candidate strategies/disciplines** for a recurring barrier → which then populate the `Strategy` type (a generative front-end to it); (b) **help reason through a decision she can't make alone** (which route to prioritize; when to move to GA) — route-prioritization (§8d) is one instance of this, in a "think with me" register, not a "here's the answer" one; (c) **persist the barriers/problems themselves** (June's suggestion) so they're held, returnable-to, and feed the learning loops. The weeding gate is the natural *trigger* — when it detects struggle in a dump, it offers to shift into this mode (June's intuition: "at most this prompt would route into it in cases where I'm articulating struggle"). **The hardest part to design well:** the §7 deference problem is acute here — the AI must genuinely help-think, not dispense generic advice or follow June into a spiral. Design as its own pass, with real stuck-examples. May be partly absorbed by the learning loops + populated Strategy/mindset objects (June's read) rather than a standalone subsystem — decide at design. **Connects to:** persisted-barriers ↔ the `access_notes`/EF-barrier annotations; the "which to prioritize" question below; the populated `Strategy` type.

**Separate the cheap part from the hard part (June, session 5 — corrects an over-bundling).** *Persisting* a barrier is trivial. **Decided v1 (June, session 5): add the `barriers` text field on Goal + Project** — June wants it queryable so the AI can find *patterns* across barriers over time (a recurring block is itself a signal). The cross-barrier *pattern-finding* is a loop (deferred); the field is just the storage. What's hard and genuinely deferred is the **help** layer — (a) brainstorm and (b) think-through-the-decision. Don't let "persist the barriers" get dragged into the hard design pass; the storage is a field, the *help* is the work.
- **Audit-before-port** — for every Reframe component (§4 caveat): verify the implementation, don't assume the concept's soundness means the code is good.
- **Julia's first-party spec / full capacity axes** — asked for, probably won't arrive. Don't block; design §8e from what we have.
- **Global vs. per-project scope** (Param #14) — one system vs. dev-task sprawl; reconcile with job-search TRACKER, Canvas, Reframe's Garden/OpenSpec, per-repo notes. **→ Resolution direction is the repo-binding item below.**
- **Repo/folder ↔ Goal/Project binding (June, session 7 — requested).** The `drift` skill is global but *location-blind*: invoked from the job-search folder it works "from anywhere" yet doesn't know that folder **is** the Material survival cluster. The ask: bind a repo/folder to a specific Goal/Project so that *being there* auto-contextualizes capture/weed/plan to that slice of the graph — capture lands pre-aligned, the weeding alignment step starts from the right cluster, planning is scoped. (This is the **inverse** of `relevant_docs`: that points a Project/Task *outward* to files the AI reads; this points a *folder inward* to the part of the graph it belongs to.) **Proposed mechanism** (parallels the `.reframe-active` dotfile pattern June already uses): a small per-repo marker file named **`.gsdot`** (decided session 7 — June rejected `.drift`: the bare word reads as stressful stripped of the "controlled" reframe; `.gsdot` = get-shit-done-o-tron) (or a stanza in that repo's own `CLAUDE.md`) — naming the Anytype Goal/Project this location maps to. An instance starting in a bound repo reads the marker → loads that slice → operates pre-contextualized. Keeps the system **global** (Anytype is still the one store); location merely carries context. **First bindings:** the job-search folder → *Material survival* Goal; this repo → a "Build Controlled Drift" Project (mixed case — it both builds and operates the system). **⚠️ DESIGN-FIRST, NOT BUILT.** A throwaway spike exists (`scripts/gsdt_bind.py`, committed *labeled as a spike, not wired*) that surfaced — but does **not** answer — the core design question: **what should `/drift` (or a fresh instance) do when invoked in a directory with no marker?** June's framing (session 7): does it (a) **inherit a parent folder's** binding by walking up, (b) **offer to set one up** here, or (c) get **added to an ignore-list** so it's never asked again? These likely **compose** into a resolution order rather than compete — e.g. *marker here → marker in a parent (walk up; child overrides; ignore-marker blocks) → on ignore-list → else default to silent global-unbound, never auto-nagging* (most folders June works in are NOT task folders; offering on every new dir is exactly the management-burden the system exists to remove — so a smart "offer" is probably *pattern-triggered* and belongs to the proactive/learning layer, not presence-triggered). **This whole resolution behavior is the design pass owed** before any build. **Other open sub-questions:** id-vs-name binding (ids stable, names legible — likely store id, show name); one folder → many Projects; and **precedence in a *mixed* repo** (this repo: when "todos here" means *build-the-system* dev work vs. a life-task — the job-search folder sidesteps this by being pure-Controlled-Drift).
- **Weeding dedup gap (found live, session 7 — significant; June flagged).** The weeding alignment step loads existing **Goals + Projects** but **not existing Tasks/Recurring**, so a cold instance can propose creating something that already exists → **duplicates**. Found: a cold weed proposed a new Recurring `Work on SSRC grant (daily)` while an `SSRC grant application` **Task** already existed under Grants / fellowships. **Why this matters:** duplicates break the system's core promise (one trustworthy picture June doesn't have to police) — the same trust failure as the ding bug, one layer up. **The load-bearing fix:** the alignment step must load existing **items within the projects it's aligning to** (Tasks/Recurring under the relevant Goal/Project cluster), so same-subject items surface *under any name or type* and the instance proposes **link/merge**, not create. ⚠️ The dupe was **cross-type + different-name**, so a same-name+type write-time guard would **not** have caught it — that guard (ensure-style, mirroring `seed_jobsearch.ensure_object`, promoted into the weeding write path) is a worthwhile **secondary** backstop for exact dupes only. **Structural lesson (same as the read-back/ding guard, [[feedback-good-answer-not-saved-object]]):** don't rely on the instance *remembering* to check — surface what already exists *and* guard the write. Fold into the pending weeding-prompt revision pass.
- **Recurring frequency grain + timezone (June, session 7 — design inputs for the Step-2 datetime seam).** Current Recurring Frequency (Daily/Weekly) is **too coarse** — found live: "dishes every few days" had to round to Daily (daily-for-dishes itself is fine = loading the dishwasher; the *grain* is the problem). **Direction (June):** generalize to an **interval model — `{unit: day/week/month, count: N, anchor: day-of-week | day-of-month}`** — which subsumes Daily (`day/1`), Every-N-days (`day/N`), Weekly+day-of-week, and **Monthly-on-calendar-dates** (`month/1 + day-of-month`). Recommended over an enum of special cases (general pattern, per design discipline); **store general, present friendly** ("Every 3 days", "Monthly on the 15th") — fields are the AI's substrate, not June's form. Open edge: day-of-month in short months → default **clamp to last day** (or support a "last day" anchor). **Timezone (June: "all our clocks need to be synced to the right zone"):** system is `America/Los_Angeles` (PDT); the built scheduler is TZ-agnostic (fine) and `neglect.py` ignores the offset at day-grain (fine multi-day, slightly risky at midnight edges). Anytype stores dates **UTC** (`...Z`). The real TZ work is the **Step-2 datetime seam**: build "today at HH:MM" in **local** TZ, convert to UTC only at the Anytype boundary; one rule — wall-clock reasoning stays local throughout. Make local TZ **location-derived, not hardcoded Pacific** (the move-to-GA/Eastern gating condition in the Material survival Goal would silently break a hardcoded zone). Build the schema change **alongside Step 2** — the frequency model only gets consumed there.
- **Model privacy-tiering** — can a local model handle the sensitive tier's breakdown? Empirical test once the layer runs.
- **PMA seam** — `reaching_for` thin-now → point to PMA's richer version when PMA runs (`~/Documents/GitHub/propositional-memory-architecture/`; not yet running).
- **Author-informed critic profile** — no critic-swarm author profile exists for June yet; creating one would let future reviews check against her voice/priorities.
- **Three principles the gap-check (session 5) found *practiced but not named*** — fold into §4/§5 if they earn it; all low-risk, currently covered behaviorally: (a) *frame-before-content / never-naked* (a PMA principle) — nothing surfaces stripped of the context that makes it mean what it means (the woven frame, "X out of N with reasoning," `blocked_on`-surfaced-positively are all instances; the general rule just isn't stated); (b) *an honest empty/quiet day is valid output* — below a relevance floor, "nothing held meets the bar today" is a real answer the system shouldn't pad over (adjacent to "not-today is not failure," but stronger); (c) *body-doubling / co-regulation* — parallel presence lowers initiation friction; even a solo tool can borrow the form (an ambient "work mode," witnessed-not-judged framing). Field-validated (EVAL doc) but absent from the spec.
- **Test artifacts in Anytype** — demo Goal+Task deleted (session 3). Two test properties remain in the space (`gsdo_reaching_for` as objects-relation, `gsdo_location_mode` as single select) — neither matches the final model; ignore when building, delete when convenient.
- **Mindset/strategy/discipline routing — RESOLVED (session 4).** Earlier provisional: these land in Notes; open question was whether they're calibration inputs or retrieve-later reference. June supplied the real example that resolves it: a strategy/discipline/mindset is a **calibration input that shapes system behavior**, with a **terminal lifespan** (months/years), and "present the next tangible item per project" is one such strategy (learned, then baked into architecture). → They get their own queryable type (`Strategy`, §2), not Notes. The prompts read active strategies and apply them. **Still open (needs real use):** the *learning loop* on `Strategy.learning_notes` — how the system detects a strategy is lapsing or needs revision and surfaces that to June (the anti-forgetting mechanism), rather than letting it silently fail. Design once strategies have accumulated real annotations.
- **Dormant-thread surfacing / mycelial synthesis (future, NOT v1).** Beyond surfacing *recently-active* threads, the system could surface *dormant* threads strategically — old tasks/projects June forgot, links between distant ideas, synthesis proposals — adapting Reframe's Garden/composting + background link-finding. Real capability with precedent; explicitly more than v1 needs. Park until the core daily-list + thread-view behaviors are in real use. (June flagged the overengineering risk herself; noting, not building.)
- **Calendar integration (post-v1; June, session 4).** v1 holds fixed appointments in the `Recurring` type (entered once). *Reading* appointments from a calendar app is deferred, and the path is decided: **Apple Calendar via local AppleScript/EventKit** — June's actual calendar, read on-device, no cloud. Explicitly **not** Google Calendar (June doesn't use it; its only draw was an already-wired MCP, which reads an empty calendar) and **not** writing June's private task content out to any cloud calendar (that would undercut the privacy reason the store is Anytype, §1). One-time macOS automation-permission prompt is the cost. Two-way sync / phone-sync remains the harder, separately-scoped problem.
- **Temporal-lens narration (Park A; June, session 4 — confirmed for incorporation).** The same goal/project can be *narrated* through different time-logics — long-horizon/no-urgency (goals that shouldn't feel rushed), returning-not-restarting / spiral (a project re-entered after drift: "last cycle you worked out X; this isn't starting over"), and deliberate-linear (real deadlines only). It is a **framing layer over existing behaviors** (the daily plan's woven frame, the drift message, the wins mirror each choose register from a lens picked for that goal/project), not new data or a new subsystem — which is why it's v2: it needs those behaviors built first. This is the resolution to the goal-orientation-vs-goal-evolution tension (Param #6 vs #7): you don't pick one, you rotate the lens.
- **Timed work-blocks + soothing alerts (Park B; June, session 4 — wanted, design pass needed).** "Work on this for X, then wrap up/stop" as an enacted discipline; generalizable to any timer (laundry: washer→dryer). The discipline itself is a **`Strategy`** ("I work in 45-min blocks"); the timer *enacts* it. Two delivery tiers: (1) **computer-open** — a soothing, snoozable local alert (`afplay` + macOS notification while a GSDO process runs); v1 already has the toe-in via the §9 completion sound. (2) **fires-on-phone-even-when-computer-closed** — the hard part, and it *converges with calendar integration*: the native cross-device mechanism is **a (local) Apple Calendar event with an alarm**, which the phone's calendar fires regardless of the Mac. So B's hard half and Apple-Calendar integration are one thread. Alerts must stay soothing + snoozable (guard #2 — a tool June holds, not a clock watching her).
- **Type-of-work axis + minimal-path command (Park C; June, session 4 — YES, both).** (1) An **open** "kind of work" axis (writing / research / dev / admin / …) so a day can deliberately *mix* work types instead of being all drafting — open/emergent like `access`, **not** a hardcoded enum (same lesson). (2) A **"minimal path to completion"** command — surface the smallest set of steps that lets June call something done — available as a systemically-surfaced command so she doesn't forget it exists (June's framing: not letting "minimum" become the *only* frame, but having it on tap). Confirm at design which of the two the surfaced-command affordance attaches to.
- **Graceful degradation (the AI half can go down).** Anytype's API is Developer-Preview; subscriptions lapse; keys expire. For a tool holding survival-critical (legal/health/job) tasks for someone without an institutional backstop, June must keep a usable system when the AI layer is unavailable — at minimum, Anytype's own visual dashboard stays fully usable, so the human-readable layer must never depend on the AI to be legible. Design graceful degradation, don't treat it as an ops afterthought.

---

## 11. Decision provenance

Workshop Session 2, 2026-06-15/16. Co-designed dialogically with June. Load-bearing decisions:

- **Names (session 5):** **Controlled Drift** = the whole system (the public/CV name; "controlled drift" in the *motorsport* sense — skilled nonlinear movement, not suppression). **GSDO** = the deterministic mechanics layer (the reliable executor that just gets shit done) and the repo's established shorthand.
- **Goal ≠ Project** — Goals orient and cross-cut; Projects are discrete work. Route-prioritization is a Goal-level question.
- **Affective weight is a constellation capacity signal, NOT a 1–5 scalar** (June's correction): too broad, too multi-signal, too unstable for a number; modeled like FeelingSignal (open text, unstable-marked, multi-signal), with an optional low-confidence derived intensity for filtering only. Lives on Goal-context/Project/Task.
- **Scales always shown "X out of N," AI-proposed-with-reasoning, never cold** (June): resolves the slider-surface problem for v1; true visual slider is v2.
- **Crip-time changes presentation, not depth; the surfaced amount is learned, not fixed at one** (June's correction to an earlier "one task" draft).
- **The LLM is where flexibility lives** — persist only what June can't re-hold; settled computations get stored.
- **Modes are instances, not hardcoded features** — general machinery + LLM covers current states.
- **Always offer a real "no/reframe" option** — binary choices foreclose the reframe that's often right.
- **Rest is checkable with inverted friction** — not-resting becomes gently visible.
- **Fields are the AI's substrate, never June's form** — bare-by-default reconciled with a rich schema.
- **Audit Reframe code before porting** (June): concept-sound ≠ implemented-well.
- **v1 must cross the usefulness threshold** (swarm): ship behavior, not just a schema.
- **Structure ratified: graph stored, both tree + graph views** (June): not an inherited tree. Cross-cutting is native (many-to-many); Anytype provides both views for free; June compares them in real use since she's used neither before.
- **Reminding is a voice/sourcing problem, not a remind-vs-watch dial** (from critic D1, June affirmed): the cure for nag-anxiety is more trustworthy holding, so a reminder reads as June's own intention time-shifted back, not surveillance.
- **Qualitative/capacity-relative wins count** (June): a healing-relative win ("walked today, couldn't a week ago") is real; task-completion-only wins would reproduce the productivity frame.
- **Store = Anytype** (validated 14/14) — see `SUBSTRATE_eval.md`.

*Reviewed twice (2026-06-15/16): (1) a 4-persona critic-swarm (build-agent, architect, intelligibility, jargon) — blocking + convergent findings integrated; (2) an ADHD/accessibility + systems critic — its frame findings folded in (reminding-as-voice §5, structure-ratified §2, qualitative wins §8g) plus graceful-degradation (§10). **Folded 2026-06-16:** both affect channels first-class + inferences labeled by source (§4 FeelingSignal); dopamine affordance (SVG countdown disc) added to v1 scope (§9, §8f).*

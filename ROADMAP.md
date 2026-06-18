# Controlled Drift — Build Roadmap & "What Now"

*Written session 6 (2026-06-17), after the data model was built. Plain-language map of where the system is and what comes next. Authoritative for sequencing; `AI_LAYER_SPEC.md` is authoritative for design.*

## Is the system "running"? — Honest answer: not yet.

What you have after session 6 is the **skeleton + some organs, not a wired-up body**:

- ✅ **The data model** — the 5 object types (Goal / Project / Task / Recurring / Strategy) and their fields exist in your Anytype "Get Started" space. You *can* manually add a Goal or Task right now and it works as plain Anytype.
- ✅ **Deterministic scaffolding (libraries, not yet called by anything):** `scheduler.py` (places a day's items in clock time around fixed appointments), `neglect.py` (finds work not surfaced in N days), `plan_corrections_log.py` (records your plan edits for future learning).
- ✅ **Idempotent schema helpers** (`gsdo_anytype.py`) — the tooling that built and can rebuild the model.
- 🔶 **Two prompts drafted, not wired:** the weeding gate (needs re-validation), the daily plan (needs the pipeline + re-validation).
- ❌ **No pipelines yet.** Nothing connects "brain-dump → typed objects" or "objects → a daily plan." **The AI layer — the actual value — is the next build.** Until then, it's Anytype with a good schema.

So: the **usefulness threshold** (spec §9 — don't ship a schema that sits unused) is crossed when Step 1 below ships.

## The build sequence ahead

### Step 0 — Schema polish (now, small)
Rename: drop the "GSDO" display-name prefix; Task uses built-in **Due date** + **Linked Projects**; keep a distinct **Task status** (carries the `Needs Clarifying` weeding state). Clean up test-artifact properties. *One-time tidy so the model reads clean before real data lands.*

### Step 1 — Weeding pipeline  ← first real AI layer; **this is where real data enters**
1. **Re-validate the weeding prompt** on a *real brain-dump* from you (the method that works: AI runs the draft on your actual input → you react to the output → iterate → lock). This is the answer to "when do we do prompt re-validation" — **now-ish, as the first move of building this pipeline**, because the method is react-to-real-output, not review-in-the-abstract.
2. Wire the locked prompt to actually **create typed objects in Anytype** (Task/Recurring/Strategy/Note/Needs-Clarifying) via the helpers.
3. Result: you brain-dump → the system sorts it into the right types and flags what needs clarifying. **That's the first thing worth using.**

### Step 2 — Daily-plan pipeline
1. Re-validate the `daily_list` prompt on real objects (same react-to-output method).
2. Wire it: pull active items → LLM proposes order/selection (capacity-aware) → `scheduler.py` places them in clock time (incl. the **datetime seam**: a Recurring appointment's day/time rule → a concrete "today at HH:MM" anchor) → `neglect.py` resurfaces neglected work honestly.
3. Result: you get a capacity-first daily plan; edits get logged for the future rhythm-learning loop.

### Step 3+ — Later increments (not soon)
Drift detection (§8b); the learning loops (rhythm, strategy lifespan, access-barrier promotion, the surface-log companion to `last_surfaced`); wins mirror; Apple-Calendar integration; the no-app-switching chat-stream surface; pagination on `query_neglected`; **repo/folder ↔ Goal/Project binding** (being in a given folder auto-contextualizes the system to that slice of the graph — first binding: job-search folder → Material survival; mechanism + open questions in `AI_LAYER_SPEC.md §10`).

## How you invoke it (so you never have to remember functions)

The system is **not this repo** — it's your Anytype data + behaviors any Claude instance can perform. Anytype runs globally on your Mac, so the system is reachable from anywhere. Invocation has three modes; you remember none of the functions:

1. **From any project — the `drift` skill.** In any Claude session, anywhere, invoke `/drift` (or just mention a todo / dump / "what should I do"). The skill (`~/.claude/skills/drift/SKILL.md`, mirrored in-repo at `skills/drift/SKILL.md`) turns that instance into the system: it infers whether you're capturing, weeding, planning, or stuck — you never name the function. Verified working from outside the repo.
2. **In this repo — being here is itself the signal.** A project `CLAUDE.md` makes any instance here operate as the system. Good for sitting down to weed/plan. *(Planned extension: bind **other** folders too — e.g. the job-search folder → the Material survival cluster — so being in that folder auto-scopes the system to that part of the graph. Step 3+; design in `AI_LAYER_SPEC.md §10`.)*
3. **Endgame (not built): it comes to you.** A scheduled morning plan, a nudge when Job Search goes quiet — so you initiate nothing. This is the real destination (post-v1 automation).

**Confirmation:** every time something lands in the system, the instance says what landed *and* plays an audible **ding** (`scripts/notify.py`, sound "Tink" — not "Glass", which is reserved). So you never have to open Anytype to check it saved.

**Still open (a real design conversation, not solved yet):** a dedicated always-on capture *surface* (menu-bar/hotkey) vs. the skill, and the proactive layer. Mode 1 removes the "only one repo" problem today; the richer surface is its own piece.

## "What do I (June) do now?"
- **Nothing is required of you to keep it alive** — there's no running process to babysit. It only does something when we build + run a pipeline.
- **Optional, low-effort:** add a real Goal or two in Anytype to feel whether the types fit. (Pure sanity check; not load-bearing.)
- **The real next thing that needs *you*:** a brain-dump to re-validate the weeding prompt (Step 1.1). 60-second voice memo or a typed dump — your actual current swirl of tasks/ideas. That unblocks the first useful pipeline.

## When do we feed it real information?
Through **Step 1** — the weeding pipeline is the front door. Feeding raw info before that just means manual Anytype entry with no AI value-add. The brain-dump in Step 1.1 *is* the first real feeding.

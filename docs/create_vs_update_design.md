# Create-vs-update capture — design seed

**Status:** design session owed — NOT a built plan, not yet fully designed. This is the design *home* for the thread; a build plan comes later, out of a design session with June. Conceptually downstream of **new-object-defaults** (the *create* side must be settled before the *update* side is built). Cross-refs: `docs/handoff_2026-07-14_open-redefinition-and-new-object-rework.md`, the `capture-writes` plan's out-of-scope note, and the Anytype task "Create-vs-update capture design conversation."

## The core gap

The system can *create* an object, but **nothing recognizes "new information about a thing that already exists."** When June re-mentions something she already captured, the new detail either duplicates the object or is dropped — it doesn't *update* the existing one. Create-vs-update is the **update** side of "keep an object's fields populated," the twin of new-object-defaults' **create** side.

## Recorded requirement — affect-over-time upkeep (June)

June can add/change affect (and other situated information) about a thing **over time**, and agents should **notice-and-ask when things seem to have shifted** ("this seems stale — still true?"). Recorded in the `capture-writes` plan's out-of-scope note; it lands with this thread, not with capture.

## The generalization (June, 2026-07-14) — field-population is ONE problem, two sides, two directions

The swarm's overclaim flag on new-object-defaults surfaced that field-population is a **general** problem ("fields aren't getting populated in many different cases"), not an Engagement-on-Project one. New-object-defaults (create side) and this thread (update side) are the same problem at two moments, and both are instances of **one loop**: *assistant proposes a field value → June confirms or edits it → logged + revisited.* Flagged **foundational** in the selection handoff — the engagement upkeep, affect-over-time updates, and "still true?" nudges all assume this loop; none of it is built.

The generalization goes **two ways:**

### Direction A — the edit / upkeep loop (DECIDED to extend here)
One mechanism: **propose → confirm or tap-to-change → log → revisit.** The `tap-to-change-engagement` chip seeded in the new-object-defaults plan is the primitive; **June wants that tap-to-change structure extended into create-vs-update — generalized from "engagement" to *any* field.** It is what makes editing fields easy for her, and it is the edit primitive the whole upkeep loop rests on. This is decided; the design work is *how* it renders for update (where proposals surface, how "notice-and-ask" is triggered, the revisit interval).

### Direction B — inference-completeness (OPEN — assess first)
The weeding LLM should fill every field it can **infer from June's words** — not leave a field blank when what she said carries the value.

- **Guardrail already in the system** (`capture-writes` Global Constraints): *only from her words, never invent a situated value; absent stays absent.* So B is **not** "make the LLM guess more." It is the narrow question: **which fields are inferable-from-her-words but the weeding contract doesn't currently ask for?** — keeping June's situated/inferable line intact (infer what she said; don't guess what only she can know).
- **Starting evidence:** `capture-writes` found only ~3 of a Task's 14 / a Project's 16 fields are ever written.

**June's sequence for B (her register — assess before deciding, don't force it):**
1. **Assess whether it's actually an issue** — observe which inferable-from-her-words fields come back empty on real captures (a field-by-field audit vs. the live weeding contract).
2. **Then decide scope** — does B fold into new-object-defaults / create-vs-update, or does it need its own design session?

**Ready next step for B.1 (offered, not yet run):** audit each Task/Project field — *inferable from typical capture language? does the contract already ask for it?* — which answers "is it an issue" before any build.

## Relationship to new-object-defaults (create side)

| | Create side | Update side |
|---|---|---|
| **Build** | new-object-defaults (on hold, needs rework) | create-vs-update (this doc — design owed) |
| **Job** | object born with fields populated | object's fields kept current as things change |
| **Both are** | the same propose → confirm/tap-to-change → log loop | " |

The edit primitive (Direction A) and the born-value default should share one mechanism so create-vs-update inherits it rather than reinventing it.

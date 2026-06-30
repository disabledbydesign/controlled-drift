# Where is Drift's surface? — a stab (for June to react to)

**What this is.** A stab at the open question *"what belongs in Drift, and what doesn't?"* — written by a Claude instance from the GRA session where the question surfaced (it surfaced because *I* kept over-routing little GRA implementation items into Drift, and June caught it). It is a **proposal to react to, not a settled answer.** June runs Drift; the boundary is hers to draw. Written 2026-06-21, late; read it when fresh.

**June's question, in her words.** *"It's the same flat-document problem. Will Drift give us a better way of keeping track of everything, even the little minutiae? But I don't need that surfaced for me most of the time."* — i.e. a tension between **anti-loss** (capture everything so nothing falls through the cracks) and **anti-overwhelm** (don't bury me in minutiae).

---

## 1. You've already resolved the anti-loss/anti-overwhelm tension *inside* Drift

The tension dissolves once you see that **capture and surface are different operations** — and Drift's design already separates them. From `AI_LAYER_SPEC.md`:

- **Sweep ≠ Orient** (§"the sweep does not find todos already in Anytype"): *capture* (find what's uncaptured) and *surface* (show what's there) are explicitly distinct and "must not be conflated."
- **`engagement` drives real-estate** (§2): Sprint/Hyperfixation get priority; **Backburner is invisible unless a neglect threshold trips.** That *is* "captured but not surfaced-by-default, surfaces on a trigger."
- **Never a flat list; always grouped by stream** (§"core ADHD accessibility parameter"): the accessibility mechanism is *grouping*, not *omission* — 50 todos in 4 named streams is navigable; the same 50 flat is not.
- **Julia's weed** (`Conversation with Julia.md`): weed the practices/routines/strategies *out of the action view* so you can SEE the actions — they're still captured, just not in the do-this-today surface.

So the answer to *"will Drift track even the minutiae without overwhelming me?"* is **yes, that's already the design**: capture liberally, surface selectively (by stream, by engagement, by capacity, by weeding non-actions out of the action view). You don't have to choose.

## 2. The question you actually hit is at the *edge* of Drift's domain

Tonight's friction wasn't "should this surface or stay quiet" — it was **"is this a Drift item at all?"** I routed a *GRA-internal* thing (a ten-line export helper that isn't built yet) into Drift. That's not a capture-vs-surface call; it's a **domain** call — and that's the genuinely-undrawn line.

**Proposed principle:** *Drift's domain is **your executive layer** — your goals, the work-threads you carry, what to do across your projects and life.* Project-internal implementation state — a not-built helper, a code `FIXME`, a "described-but-not-built" gap — **lives inline in the project**, where whoever is working in that file finds it in context. It is not yours to carry, so it doesn't belong on your surface. // the question is - does storing that within Controlled Drift INSTEAD of only inline give us something in terms of overall organization - consolidation outside of flat docs. Then, in terms of what needs to be surfaced, I absolutely don't need that level of detail until we're diving in - and even then, it may be agent facing more than june facing. 

**The test (one question):** *Does this need to resurface for **you** to stay aligned or decide what to work on — independent of already being in the relevant file?*
- **Yes → Drift.** (e.g. the *no-silent-suffering* design thread; a research workstream like Q2; "apply to SSRC.")
- **Only meaningful once you're in the file → inline.** (e.g. the export helper; a code TODO; an "aspiration, not yet built" marker.) // my fear - and my fear may not be warrented - is that we lose track of these loose ends, and repos grow to the point where we can't easily surface them, and they fall between the cracks. Compared to even a layer where I can just say, "hey can you knock out whatever tasks you can do mechanically without having to consult me deeply?"

## 3. The anti-loss worry, answered: nothing is lost either way

The pull to route everything to Drift comes from a real fear (the flat-doc loss). But **Drift is not the only durable home.** Project-internal minutiae captured *inline* (an aspiration-marker in the skill, a `TODO` in the code) are *also* durable — and better placed, because they're in context for the person who needs them. So nothing falls through the cracks; the only question is **which durable home**, and that's decided by **whose attention needs it** — yours (Drift) or the in-file worker's (inline).

## 4. The discipline that keeps Drift from *becoming* the flat-doc wall

This is the sharp edge: **if everything from every project pours into Drift, Drift becomes the unreadable wall you built it to escape** — the same flat-doc failure, one level up. The §1 mechanisms protect the *surface*, but pouring in project-internal minutiae still bloats the captured set and the upkeep. So "capture liberally" means **liberally within your executive domain** — not "capture literally everything from every codebase." The domain test (§2) is what protects Drift from eating itself. // Option 3 - and im just spitballing here - unless we have a systme that can handle the *storage* without *surfacing* that level of detail to me as the default, unless i want to dive in. Which means the question is - what will improve overall organization *for agents*, who become the primary readers for these kinds of items?

## 5. What's genuinely still open — and why that's fine (and very Drift-like)

The **fuzzy middle** is real: deferred *design/research threads* (substance lives in the project's docs; a resurfacing-pointer lives in Drift). How *granular* those pointers should be — one card per thread? per sub-question? — can't be fully pre-specified. **And it shouldn't be**, because that's exactly Drift's own philosophy: *learn the pattern from corrections over time, don't pre-spec it* (the two-tier learning loop; the "qualitative patterns resist EMA" note). // agreed, but this sounds like a workstream, not a task. So that may *already* give us the storage vs surfaced distinctionl. 

**Recommendation:** adopt §2's principle + test as the **starting line**, and **learn the real boundary through use** — log the corrections (when something was over-captured → clutter; when something was under-captured → it got lost), and let those teach the line, the same way the daily-plan corrections teach the picker. The boundary is a learning-loop target, not a one-time definition. // agreed, but the open question is at what layer (workstream/subproject vs. task)

---

**TL;DR:** capture-vs-surface is already solved inside Drift (capture liberally, surface selectively — §1). The open question is the *domain edge* (§2): Drift holds **your executive layer**; project-internal implementation lives **inline**. Test: *would you need this to stay aligned, outside the file?* Nothing's lost either way (§3); the discipline is don't-pour-minutiae-in (§4); and the exact line gets **learned through use**, not pre-specified (§5). // circling back - so let's think about it as two sides - June's executive layer, and agents executive layer. Does that change the picture, or does it not? I'm not specificying what I want in these comments - I'm opening questions to work through, worth assessing fully without pre-specificying the answer. 

*— a stab, react freely. The over-routing that surfaced this is itself case-zero of the corrections log §5 proposes.*

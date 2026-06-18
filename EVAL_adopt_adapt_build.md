# Adopt / Adapt / Build — field scan + evaluation

**What this is.** The first design-phase task from `Parameters_v2.md` §C.1: evaluate how existing tools design for ADHD/neurodivergent people, so gsdo can *adapt* what works instead of reinventing — or decide it must build, and know why. Produced 2026-06-14 by an open qualitative survey (two parallel research passes: tools-as-designed, and the articulated design philosophy), then read against gsdo's own framing.

**Method note (important — this replaced a wrong first pass).** The first attempt scored each tool pass/fail against gsdo's guards (a satisfy/violate rubric). June correctly rejected that: it answered a compliance question nobody asked and imported a positivist register the project resists. The real question is open — *how do others design for ADHD, what ideas and frameworks can we learn from or adapt.* This doc is a tour of the design space, not a scorecard. See [[project-gsdo]].

---

## A. The design philosophy the field already has (frameworks to adapt, not reinvent)

Named frameworks, in plain language, strongest-evidenced first. Evidence grading is honest — see §F.

- **Executive function as the thing to externalize (Barkley).** ADHD is a disorder of *self-regulation / doing what you know*, not of knowing. The therapeutic move: when the internal version (working memory, time-sense, motivation) is unreliable, push it *out* into the environment — and locate it at the **"point of performance,"** the moment and place the behavior actually has to happen, not in a planning session beforehand. *Implication:* gsdo is a working-memory/time prosthesis, not a discipline aid. A task captured but only surfaced when you open the app has failed the point-of-performance test. **(Strongest evidence in the field.)**

- **The Wall of Awful (Mahan) — initiation is gated by emotion, not logic.** Every past failure/shame around a task lays an emotional "brick"; the accumulated wall, not the task's difficulty, is what blocks starting. ADHD people accumulate more walls. *Implication:* "just break it into steps" misses the barrier. Design for the dreaded task specifically; and anything that produces shame on contact (red overdue badge, broken streak, guilt-tinted empty state) is *literally building the wall taller*. (Community/coaching knowledge — but it converges with the HCI "emotional scaffolding" finding from an independent direction, which is a strong signal.)

- **Interest-based nervous system / INCUP (Dodson).** ADHD motivation runs on **Interest, Novelty, Challenge, Urgency, Passion** rather than importance/obligation. This is *why* GTD and priority-ranking underperform — they're built on the importance engine the ADHD brain doesn't run on. *Implication:* don't lean on priority as the motivator; it's the weakest lever. But INCUP is also the door gamification walks through — see the contested-gamification note in §F. (Clinical-practitioner framework.)

- **Shame-free / gentle productivity + the critique of streaks.** Streaks create all-or-nothing traps; breaking one tends to make ADHD users *abandon the app entirely* rather than restart. The prescription: self-compassion, curiosity, playfulness; "welcome users back gently" instead of emphasizing loss. *Implication:* no punishment for absence anywhere; the lapsed/empty/re-entry state is a **primary screen**, where shame is either built or refused. (Maps directly onto gsdo's "nothing punitive" guard — the field confirms it.)

- **Crip time + spoon theory + disability-justice design.** Crip time (Kafer, Samuels): bend the clock to the body, not the body to the clock — ableist temporal expectations are baked into "productivity." Spoon theory (Miserandino): finite, depletable, variable daily capacity. Crip technoscience (Hamraie & Fritsch): disabled people as *designers*, interdependence and access over efficiency. *Implication + the deep caution:* there's a live tension between the **prosthesis lineage** (externalize, structure, support output) and the **crip-time lineage** (resist the output imperative itself). A tool can hold both only if you design that tension in deliberately — the productivity-app genre silently encodes the neurotypical clock as the measure. This is where the *frame*, not the feature set, is the thing to examine. (Real scholarship; tool-level application still mostly conceptual — nobody has a validated crip-designed todo app.)

- **Body doubling / co-regulation.** Parallel *presence* of another person (not collaboration) lowers initiation friction via external regulation — "step into momentum that already exists." Framed as gentle witnessing, explicitly not judgment. *Implication:* initiation support can be presence-based, not just logistical; even a solo tool can borrow the *form* (ambient "work mode," witnessed-not-judged framing).

- **Time-blindness aids — make time spatial.** Time-blindness is a measurable trait (meta-analysis of 55 studies). The consensus mechanism: convert a temporal judgment into a spatial one (visual timer's shrinking disc) so you *see* duration rather than read a number. *Caution:* imposed timers caused stress; kids hid them. Externalized time must feel like a tool the user holds, not a clock watching them.

---

## B. The tools, as designed (where the ideas live)

Grouped by their core design bet. Adaptability facts (open/local/API) in §D.

- **Brain-dump → steps (decomposition as the core act).** **Goblin Tools** — the reference object; Magic ToDo + Compiler turn a dump into steps, and the **"spiciness" slider** is the field's most-copied idea (you tell it how overwhelming the task feels; it matches the grain — it makes *felt difficulty an input*). **Tiimo** — visual ADHD/autism planner; AI co-planner breaks projects into steps *and* lays them on a proportional visual timeline (breakdown + auto-schedule, rare combo). **Saner.ai** — "second brain" assistant; low-friction (voice) capture, proactive check-ins. (Goblin's "Taskmaster" is one of its own sub-tools — that resolves the name; the *other* "Taskmaster" is `claude-task-master`, an open-source code-task decomposition engine — see §D.)

- **Daily ritual as a bounded ceremony.** **Sunsama** — guided morning plan + evening shutdown; **workload/capacity protection** warns when you've planned more than your set daily hours (structural counter to the ADHD 14-hour-plan). **Akiflow** — keyboard-first Command Bar capture; Time Slots batch small tasks. **Structured** — pre-structured visual timeline + capture inbox; auto-reschedules missed tasks (removes the shame of re-confronting a failed task).

- **Customization / strategy library.** **Amazing Marvin** — ships a library of toggleable "Strategies" (build your own system); "Start small" collapses the view to the next three actions; a **Procrastination Wizard** treats stuckness as a diagnosable barrier. Optional *opt-in* gamification.

- **Single-tasking / time-awareness.** **Llama Life** — one task + running clock + **projected "you'll finish at…" time for the whole list** (makes over-commitment visible before you start).

- **Routine sequencing.** **Focus Bear** (AuDHD-built; guided routines + blocking; deliberately firmer/coach register), **Routinery** (habit-sequence-as-timer; pause/skip mid-routine).

- **Presence / motivation.** **Sukha** (body-doubling co-working), **Numo** ("cringe-free" gamified + body-doubling), **Finch** (self-care pet — **"the pet waits for you," no broken streaks**; the cleanest design answer to streak-shame in the field).

---

## C. Genuinely novel ideas worth stealing

- **Spiciness as user-overwhelm-as-input** (Goblin) — make *felt difficulty* a first-class control; most tools infer grain, Goblin asks. Cheap, high payoff.
- **Emotional/sentiment tagging per task** (Leantime's emoji, Lunatask's mood/energy) — treat *how you feel about a task* as the top predictor of whether you'll start it. The most under-explored good idea in the field, and it sits in open-source code.
- **Projected finish-time / capacity warnings** (Llama Life, Sunsama) — over-commitment made visible structurally, before the day, not moralized after.
- **Reward decoupled from streaks** (Finch) — measure accumulation, never penalize gaps.
- **CBT-model procrastination help** (Super Productivity, Marvin) — stuckness as a barrier with a matched move, not a willpower failure.

---

## D. Adopt / adapt / build landscape — three axes, kept separate

The eval's central correction to its own earlier framing: **open-source, local-vs-hosted, and adopt-mode are three independent axes** and were being collapsed. They decide different things:

| Axis | What it actually governs |
|---|---|
| **Open-source vs. closed** | Whether you can fork/modify the code |
| **Local vs. hosted** | Where the *data* lives — the privacy question for legal/health/job material |
| **Adopt-as-is / substrate / port-ideas** | The build question itself |

A tool can be closed-but-local (private, not forkable), or open-but-you'd-still-rebuild-around-it. "Not open source" does **not** imply "can't use it"; what matters for gsdo's sensitive data is *local*, which is a separate axis from *open*.

**What the field offers on each:**
- **Goblin Tools** (the brain-dump engine June wanted): closed, hosted, **no API / no self-host**. → *learn-from, not reusable.*
- **Super Productivity**: **open-source AND local-first** (no accounts/telemetry; optional sync via *your own* Dropbox/WebDAV), ADHD-oriented, CBT procrastination helper. → the one tool architecturally aligned with gsdo; viable **substrate or reference implementation**.
- **`claude-task-master`**: open-source, runs locally, NL-spec → stepped tasks. → a reusable decomposition *engine*, but built for **code tasks**, not life tasks.
- **Leantime**: open-source, self-hostable (Docker); the emoji-sentiment-per-task idea lives here. Heavier (full PM platform) than a personal organizer needs.
- **Lunatask**: privacy-first, E2E-encrypted, energy/mood tracking — but **storage model unconfirmed** (encrypted-cloud ≠ local-only); verify before trusting for sensitive data.
- Most polished AI-breakdown tools (Tiimo, Saner) are hosted/closed → learn-from.

---

## E. The gaps = gsdo's opportunity space (and the honest "good reason to build")

The field's thin spots map almost exactly onto gsdo's distinctive intentions:

1. **Local-first AND smart is the biggest hole.** Good AI breakdown is all hosted/closed; local-first tools aren't AI-driven. With local LLMs now viable, an on-device-breakdown + local-data tool is an open niche — and it's exactly gsdo's hard constraint.
2. **Capacity-aware *selection*, not just tagging.** Some tools let you tag energy; almost nothing closes the loop (log today's capacity → propose the matching subset). This *is* gsdo's "what do I do right now" picker — and it barely exists anywhere.
3. **Breakdown quality for abstract/knowledge work is unverified everywhere** — every published example is dishes/laundry; "write the lit review section" (an ADHD scholar's actual workload) is untested across the board.
4. **Honest handling of the failed day** is mostly left to the user; only Finch addresses it affectively.

**So: the genuine "good reason to build" is the core telos.** No existing tool does *alignment-held-outside-June's-head* (`reaching_for` + goal-alignment + the relational-project layer + the PMA seam) or capacity-driven *selection*. An adopted tool gets a good brain-dump→breakdown + gentle register + maybe energy tagging — i.e. **a better todo app, but not gsdo.** The build question is whether the distinctive layer is worth the cost, or whether a good-enough adopted tool now + a thin personal layer later is the crip-time-honest move (consistent with the thin-now-rich-later ethic already chosen for the PMA seam — see [[project-gsdo]]).

**The co-design reframe (field's near-consensus).** A CHI 2022 review found only ~12% of ADHD-tech studies involved ADHD people as designers; the field's conclusion is that the missing ingredient isn't a better framework, it's ADHD people designing *with*, not being designed *for*. gsdo *is* an ADHD scholar designing with an AI partner — the exact intervention the research says is absent. Worth stating plainly, and honestly (it's a methodological alignment, not a validation of the tool).

---

## F. Honesty audit of the evidence

- **Strong (real research):** Barkley's executive-function/self-regulation model; time-blindness as measurable; the CHI 2022 review's characterization of the literature (deficit framing, ~12% participation).
- **Moderate (some clinical, much practitioner):** self-compassion helping ADHD; visual-timer effectiveness.
- **Community/practitioner (resonant, widely cross-corroborated, not empirically tested):** Wall of Awful, INCUP, body-doubling *mechanism*, streak-causes-abandonment. Wide adoption = lived-experience resonance (legitimately valuable for a co-designed tool), but not validation.
- **Theory awaiting application:** crip time / spoon theory applied to todo tools specifically — strong scholarship, tool-level application still conceptual. Don't claim the field has crip-designed productivity tools; it has the theory and the call to build them.
- **Genuinely contested — gamification.** INCUP says novelty/challenge motivate; the streak critique says loss-framed mechanics harm. One industry source claims gamified apps retain ~48% better. Resolution the sources point to: the contested variable is *valence* — **celebrate presence, never penalize absence** — not games-vs-no-games.
- **Thinnest spot overall:** very little validated, *deployed-system* evidence for what specific todo designs actually help ADHD users over time. The prescriptive consensus is real at the level of *principle*, weak at the level of *proven implementation* — which is itself the opening.

---

## G. Open forks this eval hands to the next conversation (June's reframe, 2026-06-14)

June loosened an assumption this eval was smuggling: **building is not the default.** The decision tree is:

1. **Do we build our own at all** — or adopt an existing tool, *even a closed-source one*? (Disentangle: the privacy question is *local vs hosted*, not *open vs closed* — a closed-but-local tool could be acceptable; a hosted one holding legal/health data probably is not. There may be a split: hosted breakdown for non-sensitive dumps, local for sensitive material.)
2. **If we build:** do we **port selected ideas** (build around them) or **use an existing system as substrate** (Super Productivity is the realistic open/local candidate)?

The honest input to that conversation: an adopted tool gives a better todo app; only a build gives the alignment-outside-her-head telos and capacity-driven selection. The question is whether those are worth the cost now, given capacity/timing — or whether adopt-now + build-the-distinctive-layer-later is the move.

---

## Sources (selected)

Barkley EF/self-regulation factsheet (russellbarkley.org); CHI 2022 "ADHD and Technology Research — Investigated by Neurodivergent Readers" (dl.acm.org/doi/10.1145/3491102.3517592); "Toward Neurodivergent-Aware Productivity" (arXiv 2507.06864); Mahan, Wall of Awful (adhdessentials.com); Dodson, INCUP (neurodivergentinsights.com); Samuels, "Six Ways of Looking at Crip Time"; Goblin Tools (goblin.tools/About); Tiimo (tiimoapp.com); Amazing Marvin (amazingmarvin.com); Sunsama (sunsama.com); Llama Life (llamalife.co); Finch (resetadhd.com); Super Productivity (super-productivity.com); Leantime (leantime.io); Lunatask (lunatask.app); claude-task-master (github.com/eyaltoledano/claude-task-master). Full URL list in the two research-pass outputs (session 2026-06-14).

# Open thread — spoon accounting (a parameters doc, not a scalar field)

*Status: **open design thread, not built.** Surfaced session 24 (2026-07-02) while capturing the strategy "Batch errands by spoon-cost, not count." Parked deliberately — it wants its own design session. This doc preserves the specifics so we don't reinvent them.*

---

## The problem

The strategy **"Batch errands by spoon-cost, not count"** (and, more broadly, planning around variable capacity) needs the system to know **how heavy each errand/task is for June specifically** — not how heavy it is on average.

June's limit, in her words: a model can do "a decent job, but will top out where I have specific needs that may vary from the average." Guessing hits the average and misses exactly where June diverges.

## Why the low-cost stopgap doesn't actually solve it

The for-now option is: the LLM writes spoon annotations into the open-text `access` note per item. **June's catch:** this doesn't solve the core problem, because in the low-friction flow *the LLM enters items for June* — so the LLM is still **guessing** her specifics. Annotation-by-LLM = the average again, just written down.

Keep annotation as the **low-cost placeholder** for now, but with eyes open: it does not capture June's specific spoon-knowledge.

## The real approach (June's synthesis)

A **spoon-parameters doc** that encodes June's specific spoon-factors **once**, read by the weeding/adding mechanism, which the LLM then **applies** to compute/annotate spoon-weight per item.

- Her knowledge is captured **once** (in the parameters doc), not guessed per-item.
- The LLM is **applying June's rules**, not inferring averages.
- **Low-friction:** June doesn't annotate each item; she helps build the parameters doc once, and the LLM applies it consistently.

This is a **parameters/config doc the LLM reads** — *not* a new scalar field on tasks/projects (which would repeat the scalar-flattening the spec's guard #3 forbids, and June's own worry: "I'm not sure how to even measure spoons in a way I will be able to intuit").

## June's specific spoon-factors (from the grocery-store example — preserve these)

Spoon-weight is **multi-factor**, and the factors are **independent axes** (this is the key insight — don't collapse them into one number):

- **Leaving the house** — costs EF (executive function) to initiate.
- **Visually dense environments** (searching through dense shelves) — higher spoons.
- **Fluorescent lights** — higher spoons (sensory load).
- **Driving distance** — a *separate* factor, and in the grocery case **low** (the store is close). So "close but exhausting" is a real, non-contradictory combination the current system can't express.

Worked example (June's): the grocery store is **high-spoon** (leaving house + dense visual search + fluorescent light) **but low travel** (close). Pharmacy pickup is **lightweight**. A walk is **leisure** — but still involves leaving the house, so it still carries a house-leaving cost the batching must weigh.

## The recovery axis (genuinely new — don't lose it)

Spoon-weight is **cost AND restoration**. Some activities *restore* spoons rather than draining them — walks, and the **7 types of rest** (see the "Honor the 7 types of rest" Strategy + the addendum's wellbeing side). So the axis is not cost-only.

- A scale like **High / Medium / Recovery** could work (recovery = restores spoons), but it **lacks granularity** and its shape should **emerge from real data**, not be imposed up front.
- May **interact with other categories** — e.g. focused-concentration tasks are their own kind of load.

## Guardrails for the eventual design session

- **Not a scalar field.** A parameters doc / rule-set the LLM reads, not a 1–5 number on each task (guard #3, no scalar-flattening).
- **Build it *from* accumulated real data.** Which parameters actually drive June's spoons should be learned from her real annotations/corrections (the §6 promotion / emergent method), not guessed. Don't pre-enumerate the axis.
- **Independent axes, not one number.** Preserve that "close but exhausting" and "far but easy" are both expressible.
- **Overengineering risk is real** (June flagged it). The parameters-doc approach is the minimal thing that actually solves the problem; the full parameterized spoon-map is a later step, grounded in data.

## Related

- Strategy: **"Batch errands by spoon-cost, not count"** (Anytype, Active).
- Strategy: **"Honor the 7 types of rest"** (the recovery side).
- `AI_LAYER_SPEC.md` §2 — the `access` field (open-text note + the two earned tags; the §6 promotion loop).
- `docs/focus_configuration_addendum.md` — capacity composes with the focus configuration; the anti-field principle ("if we're adding a field to capture a feeling, that's the signal we're doing it wrong").

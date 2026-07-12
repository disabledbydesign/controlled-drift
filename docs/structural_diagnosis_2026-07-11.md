# Structural Diagnosis — why the daily plan feels arbitrary & overwhelming (2026-07-11)

**Status:** diagnosis, June-confirmed in direction; grounded in a 3-agent structural audit of the live code + data model against the founding design (`DESIGN_v1_emerging.md`, `SYNTHESIS_design_time.md`, `AI_LAYER_SPEC.md`, `JULIA_FRAMEWORK.md`). Read-only audit — nothing was changed.

**Why this doc exists:** June stopped using the system — "when I open it, it's too overwhelming, so I just ignore it." She named the problem as structural, not a bandaid: "the data structure, the way we're implementing the data structure, gaps between structures we haven't wired so they aren't talking to one another." This is the answer to that, so the root is held outside her head and the agents fixing individual pieces can see what they're actually downstream of. **Fix directions are deliberately NOT in here yet — June chooses the direction; this is the diagnosis only.**

---

## The one cause (through-line all three audits converged on)

The daily plan is decided by a single deterministic function — `select_and_order_tasks` (`plan_generate.py:318-341`) — the choke point that picks and orders June's whole day. It reads only **three** signals:

1. Focus-Period **foreground / paused** projects (`plan_generate.py:332,339`) — a real authored signal ✅
2. a **date-seeded MD5 hash** of the project name (`plan_generate.py:337`) — an arbitrary daily shuffle
3. **Side** (Obligation/Wellbeing) via `partition_by_side` (`daily_plan.py:681-699`)

It then schedules *every* remaining task first-fit until `end_time` and force-appends the overflow into "still here" (`plan_generate.py:377,396,594`). The LLM is explicitly **forbidden to reorder or drop** (`daily_list.md:61`, `plan_generate.py:266`) — it only frames/narrates. **So wherever the selector is arbitrary, that arbitrariness reaches June unfiltered.**

Everything else the design built to shape her day is either not built as a real structure, or built and never read by the selector.

## Maps to June's exact words

| June's words | Structural cause | Anchor |
|---|---|---|
| "arbitrary 30 minutes" | `duration_min` is never authored on any capture path; flat `DEFAULT_DURATION_MIN = 30` fires for ~every task | `scheduler.py:6,8-9`; weeding path writes no duration |
| "chosen seemingly at random" | order = date-hash after foreground; `deadline` & `blocked_on` loaded then ignored | `plan_generate.py:337`; `daily_plan.py:91,129` |
| "guessing which workstream" | no structure picks a next move per project; all tasks surface in Anytype storage order (stable-sort accident) | `plan_generate.py:337-339` |
| "long list, mostly dev" | no per-project cap, no importance weighting; project with more tasks = more blocks; dev has the most | `plan_generate.py` build_context (no cap); `_ensure_all_tasks_accounted:594` |
| "verbose and unclear" | mandatory per-item `why` + woven frame + per-block framing = ~`3 + blocks + 2N` sentences justifying an arbitrary order | `plan_generate.py:277,279-284,292,298`; `daily_list.md:24,72` |

## The design's three non-negotiables — all collapsed

The design named three structures as load-bearing. Each is the exact thing that was never built as a real structure:

1. **Step trajectory / "just the next step"** (the core anti-overwhelm mechanism, `DESIGN_v1_emerging.md:85-99`) → **COLLAPSED to a text convention.** No Step object anywhere; the "arc / next step" is parsed by `str.split("—")` over the Project `Context` free-text and silently vanishes if the text isn't em-dash-formatted (`orient_map.py:140-167`). This is the "next-step surface that kept breaking" — it's not a structure, it's fragile string-matching.
2. **Multi-dimensional capacity, never a scalar** (guard #3, `AI_LAYER_SPEC.md:221`) → **COLLAPSED to a binary.** Only capacity fields on a Task are `Duration min`, `Affective` (text), and a 3-tag `Access conditions` multi-select fusing embodiment+location+social. No energy field, no sensory field. At use, the whole state is reduced to `'low'`/`'normal'` (`daily_plan.py:189-201`), and **capacity never enters task selection at all** (`select_and_order_tasks` isn't even passed it).
3. **First-class relations** (June's Param #2, how she thinks) → **PARTIALLY MISSING.** Project→Goal, Project→Project hierarchy/`Depends on`, Task→Project exist. The **mutually-informing** project↔project relation (the one she named as core) has no structure; there's no "takes-up" relation; `blocked_on` is free text, not a traversable link.

## The telos spine is built but unwired

`Goal → reaching_for → Project → Task` exists in the schema and is rendered in the **map**, but is **not connected to the day.** `goal_link` (labelled "the alignment chain" in the spec) is read *nowhere* in the plan path. The promised **drift-check against `reaching_for`** was never written (`grep drift` → nothing). Two read bugs make it worse: Goal `reaching_for` is read under key `gsdo_reaching_for_(text)` (an Anytype collision-rename → likely reads empty), and `load_active_items` reads a **phantom "Goal engagement" field that `build_goal.py` never creates** (`daily_plan.py:65`), so every goal silently defaults to "Steady."

## Strategies can't hold June's real plan (her suspicion, confirmed)

The `Strategy` type holds a single behavioral discipline (`What for`, `Applies when` ∈ {Always, Low energy} only — `build_strategy.py:8-16`). It structurally cannot hold a conditional, multi-step, evolving material-survival plan. The spec intended that plan to live in Goal/Project `Context` + **route-prioritization (§8d) — which was never built** (`AI_LAYER_SPEC.md:417`). So June's survival strategy lives nowhere durable; the plan re-derives it from scattered free text every run. This is the exact failure the whole system exists to fix ("I keep forgetting and reinventing this whole plan").

## Built-but-dead fields (nothing reads them)

`excitement_level`, Goal+Project `barriers`, `ai_autonomous`, Project+Task `relevant_docs`, `access_notes`, Project `deadline` (loaded, never displayed/ordered), Task `due_date` (not even loaded in the plan path). `affective` is loaded into LLM context but drives no selection/filter.

## The answer to "it's not integrating"

It isn't integrating because **the one place that decides the day is wired to almost none of the structures.** The rich layers (goals, reaching_for, capacity axes, arc/dependencies) feed the orientation map; the day is decided by foreground + hash + side, then dressed in explanatory prose by an LLM barred from changing it. The generator's ambition (produce a grounded, capacity-fit, next-step-per-thread plan) exceeds what the data model can hold, so it fills every gap by guessing. **One cause, many symptoms — not many separate bugs.**

## Cross-cutting flag

By default the entire Wellbeing side is now excluded from the plan (`HOBBY_BLOCK_DEFAULT = False`, `daily_plan.py:666,681-699`) — plan is obligation-only unless toggled. Noted for whoever owns that thread.

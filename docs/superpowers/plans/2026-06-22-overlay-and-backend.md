# Controlled Drift — the ambient overlay + its backend

*Plan written + approved 2026-06-22 (session 16). Build sequenced one slice at a time.*

## Context — why this, why now

The whole telos of Controlled Drift is *alignment lives outside June's head*. But right now June is **building it, not using it** — and the reason is structural, not motivational: the system is **passive-invocation**. Under hyperfocus she never thinks to invoke it. The overlay is meant to fix that ("it comes to you" — ROADMAP §3, the stated endgame).

An earlier mockup (`docs/overlay_daily.html`, this session) was designed *in the abstract* — it invented a stream-card layout and a capacity-dots widget that **do not match what the backend actually produces**. The real daily plan (`prompts/daily_list.md`) is a **time-block plan** (Morning/Midday/Afternoon/Evening, each with narrative framing and `HH:MM | Project · task` items + a one-line *why here*), followed by a *still here, not today* section. The real map (`scripts/orient_map.py`) is **deterministic monospace** that must render verbatim in a `<pre>`. This plan re-grounds the overlay in the actual data + the accessibility design DNA (`SYNTHESIS_design_time.md`), and builds the thin backend that feeds it — **with the learning logs wired from the first interaction**, because every button press and freetext request is correction data the system was built to collect.

**Honest framing:** the overlay is the *destination*; the **morning push is the keystone**. A web page June has to open is still an invocation — it doesn't solve the EF barrier by itself. So the build is sequenced so the push (Slice 2) isn't deferred behind endless UI polish.

## Generation backend — pluggable (decided with June)

`daily_plan.py` only **prepares context and prints it**; generation is handed to an LLM. Both the morning push and the overlay's refresh/negotiate buttons need to call an LLM headless. **Same generator serves both.**

- **Default now: headless `claude -p`** (`/Users/june/.local/bin/claude`, v2.1.186). Draws on June's existing Claude subscription usage; no separate money unless an API key is deliberately configured. Best prose quality, zero setup.
- **Swappable: a free local offline model** (MLX already on the machine). The generator wraps the LLM call behind one seam (`generate(prompt) -> text`) so a local model replaces `claude -p` with no rework.
- **Billing context (checked 2026-06-22):** Anthropic announced (May 13) moving Claude Code onto a *separate paid credit pool at API rates* effective June 15; **paused** June 15, revised version signaled. So `claude -p` works today but a change is in flight → **local seam is interface-from-day-one (Slice 1); a working local backend is brought up early (by Slice 2), not deferred.** A future pricing change becomes a one-line backend swap.

## Architecture

```
overlay (HTML/JS)  ──HTTP──>  server.py  ──>  plan_generate.py ──> generate() [claude -p | local]
   |                              |                  |
   GET /api/plan   <─ cache ──────┤                  ├─> daily_plan.py (context, scheduler, meals)
   GET /api/map    <─ orient_map ─┤                  ├─> plan_store.py  (cache R/W)
   GET /api/actions<─ actions.json┤                  ├─> log_surfaced_batch()   [learning]
   POST /api/refresh ─────────────┤                  └─> log_correction()       [learning]
   POST /api/negotiate ───────────┘
```

Cache + config live in `~/.controlled-drift/` (user-local, outside the repo).

**Surface evolution — URL first, ambient shell after.** The URL is just *how the overlay is served*; the rose+gold tabbed design is unchanged. Slices 1–2 serve the exact design at `localhost:5050`; once verified, wrap the same HTML in a chromeless always-on surface (PWA / menu-bar / native shell — own piece, later). Requires the laptop **on + awake** (runs lid-closed / asleep-then-wakes via launchd; not while shut down). No browser/login-session needed for the morning push — it runs headless and writes the cache.

## Slice 0 — document + capture (this slice)
- Persist this plan into the repo (here).
- Log the meta-insight as memory: *June hyperfocuses on the tractable, satisfying sub-problem (e.g. overlay colors) while the actual goal stays distant — ADHD, not a failing; naming it is useful data, not a correction.* Connects to the undesigned **strategies** + **"I'm stuck"** streams as first case data.

## Slice 1 — the working surface (smallest end-to-end usable)
Goal: open `localhost:5050` → see today's *real* plan in the correct format → press a button / type a request → it regenerates → **the correction is logged**. No launchd yet.

1. **`scripts/plan_store.py`** — R/W `~/.controlled-drift/current_plan.json` (`{woven_frame, blocks[], still_here[], generated_at, source}`) + `~/.controlled-drift/actions.json` (variable button schema, seeded from a default).
2. **`scripts/plan_generate.py`** — the generation module, reused everywhere. Reuses from `daily_plan.py`: `load_active_items`, `format_context`, `build_schedule`, `format_schedule_blocks`, `default_meal_anchors`. Flow: build context (no blocking `input()` — capacity optional/ambient, passed in) → `generate()` with `daily_list.md` + context → parse → structured JSON → write cache → `log_surfaced_batch(...)`. `negotiate(message, kind)` variant: include current plan + message, regenerate, `log_correction(kind, before, after)`; if Lunch moved, `update_meal_learned_time(...)`.
3. **`prompts/daily_list.md`** — extend to additionally emit a fenced ```json block (structured `blocks`/`items`/`why`) alongside the prose woven frame. Prose stays for the `/drift` chat flow; overlay reads JSON. **Re-validate on a real plan.**
4. **`scripts/server.py`** — stdlib `http.server` (no flask). Routes: `GET /`, `GET /api/plan`, `GET /api/map` (`orient_map.render_map("Build Controlled Drift")` verbatim), `GET /api/actions`, `POST /api/refresh`, `POST /api/negotiate`.
5. **`docs/overlay_daily.html`** — already re-grounded (time-block Today + `<pre>` Map). Load buttons from `GET /api/actions` (not hardcoded); keep live-fetch JS. Register: permission-granting, never imperative; keep meal/rest blocks.

**Done = June opens `localhost:5050`, sees a real plan, negotiates it, and `plan_corrections.jsonl` + `surface_log.jsonl` grow.**

## Slice 2 — the keystone: it comes to her
6. **`scripts/morning_push.py`** — `plan_generate` (fresh) → write cache → fire a real macOS notification (`osascript -e 'display notification …'`) in permission-granting register ("a possible shape for today is ready"). Optional `notify.ding()`.
7. **launchd plist** (`~/Library/LaunchAgents/com.june.controlled-drift.morning.plist`) — runs `morning_push.py` at a set morning hour. Solve + verify headless-`claude`-under-launchd auth/PATH here. Bring up the local backend here too.

## Slice 3 — variable button schema + the hard, undesigned pieces
8. **Variable action schema (both-and).** `actions.json` defines buttons (id, label, payload); overlay renders from it (no code edits to change buttons). Every action invocation logged (preset, or freetext + raw text). Post-v1 pass clusters freetext → proposes new presets June approves; unused presets surface for pruning. Serves Param #11/#12 — a learning loop on the *interface*.
9. **"I'm stuck" → one tiny step (genuinely designed, not faked).** Stuck-support is undesigned; only case data is this session. Button is the entry point; the *response* needs real design (ONE 5-min step, holds everything else, asks June to decide nothing). Own focused piece.

## Learning-logs accounting (verified against existing code)
- `surface_log.log_surfaced_batch(...)` on **every** generation → neglect/rhythm history.
- `plan_corrections_log.log_correction(kind, before, after)` on **every** negotiate: preset → `kind="preset:<id>"`; freetext → `kind="freetext"` + raw message (the variable-schema signal).
- Duration learning (Param #5): negotiate diffs item times old→new, logs per-item move deltas (data now; estimator post-v1).
- Meal timing: Lunch moved → `update_meal_learned_time(...)`.
- The functions already exist; the job is **routing every overlay interaction through them** so the live-negotiation data stops leaking.

## Recommendations folded in (from `SYNTHESIS_design_time.md`)
- **Capacity is ambient/after, not a gate** — invert the blocking `input("Capacity signal…")`; generate first, "Low energy today" adjusts after.
- **Permission-granting register everywhere** — offer a reading, never command.
- **Keep rest/wellbeing + meal blocks** (Param #16).
- **"Right now" collapse** (candidate, Slice 3) — one tap → just the current block's single next thing + its why, for overwhelm days.

## Verification
- **Slice 1:** start `server.py`; load `localhost:5050`; Today shows the real plan, Map shows `orient_map` verbatim. Press each preset + a freetext request; plan regenerates AND `tail` of `scripts/data/plan_corrections.jsonl` + `surface_log.jsonl` shows new records with correct `kind`. Tests self-clean; never write artifacts into June's real Anytype space.
- **Slice 2:** `morning_push.py` manually → notification + cache update; then load plist, confirm headless fire (auth/PATH).
- **Slice 3:** add a preset to `actions.json` → appears in overlay with no code change; freetext invocations show in the action log.

## Discipline
Idempotent; no silent failures (raise, don't `assert`); read-back where it touches Anytype; tests never leave artifacts in June's space. Build **one slice at a time**, verify, then the next.

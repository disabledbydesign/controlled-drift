# Controlled Drift — project instructions

This repo **is Controlled Drift**, June's neurodivergent task system (built *for and by* her). "GSDO" / "get-shit-done-o-tron" is the repo's established shorthand and names the deterministic mechanics layer. Telos: **alignment lives outside June's head** — the system holds her goals/tasks/threads *and its own functions*, so she never has to.

## Two modes of working in here

**1. OPERATING the system (June using it — capture / weed / plan her todos).**
The operating logic lives in the global **`drift` skill** (`~/.claude/skills/drift/SKILL.md`) — invoke it / follow it. In short: June never names a function; you infer from what she's doing (mentions a task → capture; dumps a tangle → weed via `prompts/weeding_gate.md`; asks what to do → plan; voices being stuck → think *with* her). Her data is in Anytype (`localhost:31009`; open the app if refused). Create objects via `scripts/gsdo_objects.py`, then **re-fetch the object to prove it persisted, and only then confirm in words AND ding** (`scripts/notify.py` `ding()`) so she never has to wonder if it saved. ⚠️ A good answer is not a saved object: never reason about an item in prose and stop, and never ding on the strength of a good answer alone — the ding is a promise the write actually happened. **Being in this repo is itself a signal** she's here to process todos — but the skill works from any repo too.

**2. BUILDING the system (developing it further).**
**Orient from the live system first, so you don't re-derive it from source:** `python3 scripts/describe_model.py` (the live data model — the five types and their real fields) and `python3 scripts/whats_open.py` (what's already open — the live work-stream map). Then read `ROADMAP.md` (what's built / what's next), `AI_LAYER_SPEC.md` (the design — §2 data model, §3 guards, §9 sequencing), and the auto-memory (project state). Plans live in `docs/superpowers/plans/`. Build discipline: idempotent Anytype writes, no silent failures (raise, don't `assert`), no scalar-flattening of affect fields (guard #3), verify against the live space (read-back), tests self-clean (never leave artifacts in June's real space). **Every landed build gets a non-Claude cross-family review before its thread closes** (`~/.claude/skills/requesting-code-review/github_models_review.py` — a different training family catches blind spots a same-family reviewer shares); triage the findings, apply what's real. Note: that API caps requests at ~8k tokens — chunk large diffs per file (send a file and its tests in the same chunk, or the reviewer false-flags "no tests").

## Key facts
- **Schema:** 5 types — Goal / Project / Task (built-in, extended) / Recurring / Strategy — live in the "Get Started" Anytype space. Property/type display names are clean (no "GSDO" prefix); keys stay `gsdo_*`. `python3 scripts/build_model.py` rebuilds + verifies (idempotent).
- **Confirmation discipline (operating):** every time something lands in the system, *read it back to confirm it persisted*, then say what landed + `notify.ding()`. Not "Glass" — that sound is reserved. (Read-back before ding: a good answer is not a saved object.)
- **Anytype is global, not repo-bound** — that's why the system can be reached from anywhere via the `drift` skill.

When in doubt about June's working style, the global `~/.claude/CLAUDE.md` governs (neurodivergent-aware: STEP/PARK/WEAVE, bring options she directs, anti-sycophancy).

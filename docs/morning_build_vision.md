# Morning build vision — the overlay as a from-bed control surface

*Captured session 16 (2026-06-23, ~2 AM) from June's ideation flow. These are a build-WITH-June
set — designed one piece at a time (STEP), kept simple (her anti-fragility constraint: "without
drowning in maintenance costs"). Not built solo overnight on purpose.*

## The telos of this batch
Get the plan to June **in bed, as she wakes, before hyperfixation starts** — and let her
**adjust it from there**: add what's missing, replan the day, before she's even up. That's the
real lever against "work on hyperfixations all day." The morning push already delivers the plan;
these make it *interactive from the phone*.

## 1. Phone — read it in bed
- **Push (read-only):** `ntfy.sh` — free, open-source, no Apple dev account (fits the
  billing-proof values). Install the ntfy app, subscribe to one private topic; `morning_push.py`
  POSTs the plan to it → lands on the lock screen. First version: woven frame + first moves.
- **Interactive from phone (the bigger want):** reach the overlay's *server* from the phone over
  local wifi. Today `server.py` binds `127.0.0.1` (Mac-only). To allow the phone: bind `0.0.0.0`
  and open `http://<Mac-LAN-IP>:5050` on the phone (same wifi). **Security note to decide:** that
  exposes the surface to the home network — fine for a personal device on a trusted network, but
  it's June's call. Keep it simple (no auth/tunnel) unless she wants it.

## 2. The overlay as a capture surface (add, not just plan)
Right now the overlay *plans*. June wants it to *capture* too — add the missing thing and replan,
from bed. Build incrementally, one type at a time:
- **Add a Task** (first — highest value for "replan from bed").
- **Add a Strategy / discipline** (the GSDO `Strategy` type — adopted mindsets).
- **Add Recurring, Goal, Project** (the rest of the 5 types).
- This reuses the existing `drift` skill's **capture** function + `gsdo_objects.create()` — the
  write layer already exists; the overlay just needs to expose it (a small POST endpoint per type,
  or one "capture" endpoint that infers the type, mirroring how `/drift` already infers).
- **Park / weed access** — direct from the overlay. June marked this **a future build** (after the
  add-types surface lands).
- **Mark tasks complete from the overlay** (June added, session 16). She closes a *June-facing*
  task from the surface (taps done) → the overlay PATCHes its status in Anytype. This is the UI
  expression of the recovered **two-layer "who closes Done"** design ([[store-vs-surface-and-agent-protocol]]):
  June-facing tasks → June closes (here); agent-facing tasks → the agent that finishes closes.
  Pairs naturally with capture (add + complete = full task lifecycle from bed).

**Status (2026-06-24, session 17):** the always-on server (`com.june.controlled-drift.server.plist`,
`CD_BIND=0.0.0.0`) + ntfy phone push are LIVE. Phone reaches the *interactive* overlay over wifi
(read + replan, verified in Safari); ntfy delivers the read-only morning ping.
- **Notification → overlay tap-link BUILT:** `morning_push.py` adds an ntfy `Click` header pointing
  at the overlay (LAN IP auto-detected each run via `_overlay_url()`, override at
  `~/.controlled-drift/overlay_url`). Tap the push → opens the live overlay. *Pending June's phone tap.*
- **Mark-complete BUILT (code-complete, unit + live-read verified; pending June's live tap):** wrinkle
  below solved. New `scripts/task_actions.py` `complete_task(id)` (read-back confirmed), `POST
  /api/complete`, `plan_store.mark_item_done`, quiet ✓ affordance in the overlay.
- Remaining for the from-bed loop: add-types capture (next build).

**✅ Design wrinkle SOLVED (was: "solve FIRST in the mark-complete build"):** plan items carried task
*text* but not the Anytype id. Solved with a **short-token handshake** (cleaner than the two options
originally listed — raw-id-echo mangles 50-char ids; name-match breaks because the prompt rewords
tasks): each active task gets a `T1`/`T2` token in the prompt, the planner copies just the token,
`plan_generate._resolve_ids` maps it back to the real id (name-match fallback; no match → no id, never
the wrong one). Completion writes **`gsdo_task_status="Done"`** — the canonical status property the
whole system uses (NOT the vestigial built-in `done` checkbox; verified live).
**⚠️ Bug found + fixed en route:** `daily_plan.load_active_items` read the *built-in* `status`
(always empty) instead of `gsdo_task_status`, so Done tasks (e.g. "build the arc") were silently
leaking into the plan. Fixed to read the canonical property — the morning plan will be shorter/cleaner.
Adding-types is still the next build (`POST /api/capture {text, type?}`, reuse `gsdo_objects.create()`
+ drift capture inference). **Recommend: fresh session, planning mode first.**

## 3. One open-chat affordance — stuck-support AND help
June folded these together: "I'm stuck" (can't start) and "help, how do I even do this" (mid-task)
are **both open-chat interfaces**, so build one. A chat affordance in the overlay that opens a
conversation with the system — for starting, for unblocking, for thinking-with. (This is also the
real home of the genuinely-undesigned stuck-support *response* — design it here, from case data:
the stuck-support stream's agent reference in Anytype now holds case #1 + #2.)

## 4. Make the system self-describing to its AI operators (the gap June named)
The system has agent-facing protocol built in — e.g. the **`ai_autonomous`** field (can the AI do
this with minimal oversight?), the **store-vs-surface** distinction (agent-facing storage vs
June-facing surface), affect/feeling-signal constellations — but **none of it is formalized into a
surface a Claude instance can discover.** A cold instance has to grep `AI_LAYER_SPEC.md` to learn
its own operating protocol. **Build a Claude-facing index** — "how this system works for *you*
(the agent): the fields, what's agent-facing vs surfaced, what you may act on autonomously, the
capture/weed/plan protocols" — so the system holds its functions for its operators, not only for
June. (This is the telos applied one level up: alignment + protocol live outside the instance's
head too.)

## Sequencing decision: UI polish vs. "converting out of HTML" (June's question, 2026-06-23)

"Convert out of HTML" bundles two separate things — **(1) stop being a browser tab** (become
chromeless/ambient) and **(2) stop using HTML/CSS as the UI tech** (native rewrite). **June wants
(1), not (2).** The realistic "not a web app" path is **wrapping this same HTML in a chromeless
shell** — a **PWA** ("Add to Home Screen" on the phone / "Add to Dock" on Mac) or a tiny webview
app. The HTML/CSS stays, so **UI polish transfers — it is NOT wasted.** Only a full native rewrite
would discard it, and that's **not recommended**: far more work + maintenance, and it forfeits the
single codebase that already runs on both Mac AND phone (the anti-fragility win).

**Therefore the order is:** (1) functional builds first (mark-done, adding) — frame-independent, and
don't polish a half-functional UI; (2) **get the PWA shell in BEFORE polishing** (June's call,
2026-06-23, and correct); (3) THEN polish, in the standalone frame.

**Why shell-before-polish (not a wash):** the chromeless PWA changes the rendering *frame*, not just
the chrome — **safe-area insets** (content runs under the notch + home-indicator; needs
`viewport-fit=cover` + `env(safe-area-inset-*)`), **full height** (no Safari toolbar), and status-bar
handling. Polishing in a browser tab and then converting means redoing spacing against the real
insets — the wasted-energy path. So establish the real frame first, then tune to it.

**The shell is cheap (~15 min, not an infra project):** phone PWA = a few `<meta>` tags
(`apple-mobile-web-app-capable`, `viewport-fit=cover`, `theme-color`) + a tiny `manifest.webmanifest`
+ "Add to Home Screen" in Safari. Bonus: it gives June the *real* chromeless launch experience to
react to early (the react-to-the-real-thing discipline). No native rewrite — same HTML.

## Discipline for all of the above
Simple over clever; reuse the existing write layer (`gsdo_objects`, the `drift` skill); each piece
independently usable; nothing fragile. Build one, verify, then the next.

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

**Status (2026-06-23):** the always-on server (`com.june.controlled-drift.server.plist`,
`CD_BIND=0.0.0.0`) + ntfy phone push are LIVE. Phone reaches the *interactive* overlay over wifi
(read + replan, verified in Safari); ntfy delivers the read-only morning ping. Remaining for the
from-bed loop: add-types capture + mark-complete (this section).

**⚠️ Design wrinkle to solve FIRST in the mark-complete build:** the plan JSON items carry task
*text* but NOT the Anytype object ID, so the overlay can't yet PATCH a task to Done. Thread the
task `id` through to each plan item — options: (a) include the active task list *with ids* in the
generation prompt and ask the LLM to echo each item's `id`; or (b) deterministically match plan
items back to Anytype tasks by name after generation (fuzzy, fragile); (a) is cleaner. Then
`POST /api/complete {id}` → `gsdo_objects.update(id, properties={"Task status":"Done","done":True})`
→ re-render. Adding reuses `gsdo_objects.create()` + the drift capture inference; `POST /api/capture
{text, type?}`. **Recommend: fresh session, planning mode first — these have real design depth.**

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

## Discipline for all of the above
Simple over clever; reuse the existing write layer (`gsdo_objects`, the `drift` skill); each piece
independently usable; nothing fragile. Build one, verify, then the next.

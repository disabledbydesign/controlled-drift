#!/usr/bin/env python3
"""The local surface server — what the overlay talks to.

A tiny stdlib HTTP server (no dependencies) that joins the overlay HTML to the Python
backend. It does two cheap reads instantly (the cached plan, the live map) so the surface
appears the moment June opens it, and two slower writes (refresh, negotiate) that call the
LLM and re-cache — each routed through the learning logs so live negotiation data is kept.

Routes:
  GET  /                serve the overlay (docs/overlay_daily.html)
  GET  /api/plan        the cached daily plan (JSON) — instant, no LLM
  GET  /api/map         orient_map.render_map(...) verbatim (text) — deterministic, no LLM
  GET  /api/actions     the variable button schema (JSON)
  GET  /api/status      generation state {idle|running|error} + plan timestamp (for polling)
  POST /api/refresh     start a fresh generation (async, 202); poll /api/status  [logs surfaced]
  POST /api/negotiate   {preset_id}|{message} -> start a renegotiation (async, 202); poll status
  POST /api/complete    {id} -> mark a task done in Anytype (read-back) + flip the cache
  POST /api/task/reschedule {id, when} -> anchor a when-token to a date (read-back) {ok, when_label}
  POST /api/uncomplete  {id} -> undo: status back to Ready (read-back) + un-flip the cache
  GET  /api/session     ?stream=capture|negotiate -> recent session log entries (the receipt)
  POST /api/capture     {text} -> weed input into typed/linked Anytype objects (async, 202)
  POST /api/capture/undo {id}  -> archive a just-captured object + log the undo (sync)

Run:  python3 scripts/server.py   (then open http://localhost:5050)
"""
import sys, os, json, threading
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(__file__))
import plan_store
import project_summary
import plan_generate
import task_actions
import capture_generate
import session_store
import orient_map
import period_view
import focus_period
import focus_period_generate
import focus_period_adapter
import focus_period_author
import focus_store
import daily_plan
import signal_log
import chunk_log
import block_duration
import gsdo_anytype as g
import cd_paths

# The LLM backends the overlay can switch between live (mirrors plan_generate's accepted set).
# June changes this from the gear panel without restarting; the choice persists in settings.json.
VALID_BACKENDS = ("mistral", "openrouter", "claude", "local")


def _load_settings():
    """Read persisted overlay settings, or an empty dict if none/corrupt (benign first-run)."""
    try:
        with open(cd_paths.config_file("settings.json")) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_settings(data):
    """Atomic write — a half-written settings file must never be read (matches session_store)."""
    os.makedirs(cd_paths.config_dir(), exist_ok=True)
    path = cd_paths.config_file("settings.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# session_store logs capture failures loudly (never silent) via log_failure, but nothing ever
# READ them back — failures() had zero callers, so the health signal died on disk (the exact
# can't-attribute-the-degradation failure the session log exists to defeat). This gives it its
# first reader, on a surface June actually opens (the gear). Deterministic + June-facing: plain
# words, no metaphors, no jargon, and it names that the trouble wasn't hers.
_HEALTH_WINDOW_HOURS = 24 * 7   # a week — enough to catch "capture's been erroring lately"


def _health_summary():
    """A quiet health line for the Settings tab, or {} when the last week was clean.

    Counts real failed actions only; the 'prompt_large' entry is a size warning, not a failed
    capture, so it never inflates the count into a scare. Best-effort — a health read must never
    take the settings view down (the log is diagnostics, not load-bearing state)."""
    try:
        recent = [f for f in session_store.failures(hours=_HEALTH_WINDOW_HOURS)
                  if f.get("kind") != "prompt_large"]
    except Exception:
        return {}
    if not recent:
        return {}
    n = len(recent)
    thing = "time" if n == 1 else "times"
    line = (f"Heads up: capturing a task hit an error {n} {thing} in the last week — "
            "nothing you did, and the system caught each one. If capture has felt off "
            "lately, that's why.")
    return {"line": line, "count": n}

# A generation (the LLM call) takes ~60-110s — far longer than a phone browser will hold a
# connection open, so it must NOT block the HTTP request (that's the "build my plan from bed"
# timeout: the phone gives up, the server finishes into a dead socket). Instead we kick the
# generation off in the background and the overlay polls GET /api/status. One at a time —
# the lock means a second tap while one is running is a no-op, not a double generation.
_gen_lock = threading.Lock()


def _start_generation(fn):
    """Run a generation `fn()` in a background thread, tracking status for the poller.
    Returns True if started, False if one is already in flight (don't stack generations)."""
    if not _gen_lock.acquire(blocking=False):
        return False
    plan_store.set_gen_status("running")

    def worker():
        try:
            fn()
            plan_store.set_gen_status("idle")
        except Exception as e:
            # Surface the failure to the poller honestly — never a silent dead end.
            plan_store.set_gen_status("error", error=str(e))
        finally:
            _gen_lock.release()

    threading.Thread(target=worker, daemon=True).start()
    return True


def _start_focus_generation(fn):
    """Like _start_generation but tracks the FOCUS authoring status (separate surface, so an
    authoring run never reads as a plan generation to the Today poller). Shares the one _gen_lock
    so plan-gen and focus-gen stay mutually exclusive — one LLM job at a time."""
    if not _gen_lock.acquire(blocking=False):
        return False
    focus_store.set_status("running")

    def worker():
        try:
            fn()
            focus_store.set_status("idle")
        except Exception as e:
            focus_store.set_status("error", error=str(e))
        finally:
            _gen_lock.release()

    threading.Thread(target=worker, daemon=True).start()
    return True

# Bind address. Default is loopback (Mac-only). Set CD_BIND=0.0.0.0 to also accept
# connections from June's phone on the same wifi (so she can use the overlay from bed).
# Security note: 0.0.0.0 exposes the surface to everyone on the local network (no auth) —
# fine on a trusted home network, her call. Loopback stays the safe default.
HOST = os.environ.get("CD_BIND", "127.0.0.1")
PORT = int(os.environ.get("CD_PORT", "5050"))   # override for a sandboxed/second instance
OVERLAY_HTML = os.path.join(os.path.dirname(__file__), "..", "docs", "overlay_daily.html")
PROJECT_NAME = "Build Controlled Drift"  # the map's root project


class Handler(BaseHTTPRequestHandler):
    # --- small response helpers ---------------------------------------------

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    # --- GET ----------------------------------------------------------------

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            try:
                with open(OVERLAY_HTML, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self._send(404, {"error": "overlay HTML not found"})
            return

        if self.path == "/manifest.webmanifest":
            try:
                p = os.path.join(os.path.dirname(OVERLAY_HTML), "manifest.webmanifest")
                with open(p, "rb") as f:
                    self._send(200, f.read(), ctype="application/manifest+json")
            except FileNotFoundError:
                self._send(404, {"error": "manifest not found"})
            return

        if self.path == "/api/plan":
            plan = plan_store.load_plan()
            # None is honest — first run / failed generation. The overlay shows an empty
            # state, never a fabricated plan.
            self._send(200, plan if plan is not None else {"empty": True})
            return

        if self.path == "/api/map":
            try:
                text = orient_map.render_map(PROJECT_NAME)
            except Exception as e:
                self._send(500, f"(map render failed: {e})", ctype="text/plain; charset=utf-8")
                return
            self._send(200, text, ctype="text/plain; charset=utf-8")
            return

        if self.path == "/api/actions":
            self._send(200, plan_store.load_actions())
            return

        if self.path == "/api/status":
            # The overlay polls this after kicking off a generation: are we still running,
            # did it land (idle + a newer plan timestamp), or did it fail?
            st = plan_store.get_gen_status()
            plan = plan_store.load_plan()
            st["plan_generated_at"] = plan.get("generated_at") if plan else None
            self._send(200, st)
            return

        if self.path == "/api/period":
            # Read-only "see my week": the active Focus Period, rendered as a plain JSON payload
            # the Today tab folds in. Synchronous + deterministic (no LLM, no _gen_lock) — same
            # tier as /api/map. {"active": false} is the honest empty state when none is set.
            try:
                self._send(200, period_view.render_period())
            except Exception as e:
                self._send(500, {"error": f"period render failed: {e}"})
            return

        if self.path == "/api/projects":
            # The "in front" selector reads this: every non-Done project with its category (Side —
            # a DATA-DRIVEN stub until June's multi-tier categories land) + engagement + parent, so
            # the picker can group + show hierarchy without hardcoding the category values.
            try:
                _g, projects, *_ = daily_plan.load_active_items(g.get_space_id())
                self._send(200, {"projects": [
                    {"id": p["id"], "name": p["name"], "side": p.get("side"),
                     "engagement": p.get("engagement"), "parent_id": p.get("parent_project_id")}
                    for p in projects]})
            except Exception as e:
                self._send(500, {"error": f"projects load failed: {e}"})
            return

        if self.path == "/api/project-summaries":
            # Per-project 'what it is / next step' for the expandable work-stream rows — parsed
            # deterministically from each project's Context (NO LLM), same tier as /api/map +
            # /api/projects. Only projects whose Context actually parses appear here; the overlay
            # falls back to the task list for the rest (honest empty, never fabricated text —
            # divergence ledger H2). Named 'summaries', not 'focus': that word is the Focus
            # Period's, and June flagged the collision.
            try:
                _g, projects, *_ = daily_plan.load_active_items(g.get_space_id())
                self._send(200, {"summaries": project_summary.summary_map(projects)})
            except Exception as e:
                self._send(500, {"error": f"project summaries load failed: {e}"})
            return

        if self.path == "/api/focus/status":
            # The authoring poller: is the structure step still running, did it land, did it fail?
            st = focus_store.get_status()
            st["result_ready"] = focus_store.load_result() is not None
            self._send(200, st)
            return

        if self.path == "/api/focus/result":
            # The structured fields + deterministic reflect-back payload, for the confirm surface.
            r = focus_store.load_result()
            self._send(200, r if r is not None else {"empty": True})
            return

        if self.path == "/api/focus/edit-fields":
            # Seed an EDIT (Task 4): the active period's current state as editable fields, so June
            # starts from what's there (route A: direct per-field fixes, no LLM). No period -> honest.
            try:
                _goals, _projects, *_rest, period_ctx = daily_plan.load_active_items(g.get_space_id())
                period = period_ctx.get("period")
                if not period:
                    self._send(200, {"active": False})
                    return
                fields = focus_period_adapter.period_to_fields(period)
                self._send(200, {"active": True, "id": period.get("id"), "fields": fields,
                                 "reflect": focus_period_adapter.reflect_back(fields)})
            except Exception as e:
                self._send(500, {"error": f"edit-fields failed: {e}"})
            return

        if self.path == "/api/settings":
            # The settings view reads this: which backend is live, and for each option the real
            # routing mechanism + concrete model (computed by plan_generate, so the UI shows the
            # truth — not a hand-written description that drifts from what the backend does).
            current = os.environ.get("CD_BACKEND", "mistral")
            options = [{"id": b, **plan_generate.backend_descriptor(b)} for b in VALID_BACKENDS]
            self._send(200, {"backend": current, "options": options,
                             "include_hobby_block": _load_settings().get("include_hobby_block", False),
                             "health": _health_summary()})
            return

        if urlparse(self.path).path == "/api/session":
            # The Add tab's receipt: EVERY capture (or negotiate) turn this session, so June can
            # SEE what she's done without holding it — and undo from there. Uses receipt_entries
            # (no token trim) — recent_entries() would silently drop older turns once a session's
            # JSON gets big, which is exactly the "did my tasks get undone?" confusion from
            # 2026-07-01. recent_entries() stays reserved for what gets fed to the LLM as history.
            stream = (parse_qs(urlparse(self.path).query).get("stream", ["capture"])[0])
            if stream not in session_store.STREAMS:
                self._send(400, {"error": f"unknown stream {stream!r}"})
                return
            self._send(200, {"stream": stream, "entries": session_store.receipt_entries(stream)})
            return

        self._send(404, {"error": f"no route {self.path}"})

    # --- POST ---------------------------------------------------------------

    def do_POST(self):
        if self.path == "/api/refresh":
            # Async: kick off the generation, return immediately; the overlay polls /api/status.
            # Optional `capacity` in the request body (e.g. from the freetext toggle or a
            # generate-dispatched preset) is passed through to plan generation.
            body = self._read_json_body()
            capacity = (body.get("capacity") or "").strip() or None
            started = _start_generation(
                lambda: plan_generate.generate_plan(capacity=capacity, source="refresh"))
            self._send(202, {"state": "running", "started": started})
            return

        if self.path == "/api/negotiate":
            body = self._read_json_body()
            preset_id = body.get("preset_id")
            if preset_id:
                preset = plan_store.find_preset(preset_id)
                if not preset:
                    self._send(400, {"error": f"unknown preset {preset_id!r}"})
                    return
                operation = preset.get("operation", "reorder")
                payload = preset.get("payload")
                if not payload and operation != "generate":
                    # e.g. "add" — a UI-only action; nothing to generate (synchronous).
                    self._send(200, plan_store.load_plan() or {"empty": True})
                    return
                if operation == "generate":
                    # Preset signals a fresh generation (e.g. low-energy) — select from the
                    # full task list with the capacity flag, not just reorder the existing plan.
                    # payload is also passed as `extra`: until 2026-07-02 only capacity_flag (a
                    # short flag string) reached the model — the preset's actual instructional
                    # text ("shorter sessions, lower-stakes tasks first...") was silently dropped.
                    cap = preset.get("capacity_flag") or None
                    started = _start_generation(
                        lambda: plan_generate.generate_plan(
                            capacity=cap, source=f"preset:{preset_id}", extra=payload))
                    session_store.append_entry("negotiate", {
                        "intent": "generate",
                        "raw_input": f"[preset:{preset_id}]",
                        "request_type": "generate",
                        "result_summary": f"fresh generation triggered (capacity={cap})",
                    })
                else:
                    started = _start_generation(
                        lambda: plan_generate.reorder(payload, kind=f"preset:{preset_id}"))
                    session_store.append_entry("negotiate", {
                        "intent": "reorder",
                        "raw_input": f"[preset:{preset_id}]",
                        "request_type": "reorder",
                        "result_summary": f"reorder triggered",
                    })
                self._send(202, {"state": "running", "started": started})
                return
            message = (body.get("message") or "").strip()
            if message:
                operation = (body.get("operation") or "reorder").strip()
                if operation == "generate":
                    # THE BUG (found 2026-07-02): this used to call generate_plan(source=...)
                    # with no way for `message` to reach the model at all — June's freetext was
                    # logged to session history but never made it into the generation prompt, so
                    # naming a task explicitly here had zero effect on what the plan produced.
                    started = _start_generation(
                        lambda: plan_generate.generate_plan(source="freetext-generate", extra=message))
                    session_store.append_entry("negotiate", {
                        "intent": "generate",
                        "raw_input": message,
                        "request_type": "generate",
                        "result_summary": "freetext-triggered fresh generation",
                    })
                else:
                    started = _start_generation(
                        lambda: plan_generate.reorder(message, kind="freetext"))
                    session_store.append_entry("negotiate", {
                        "intent": "reorder",
                        "raw_input": message,
                        "request_type": "reorder",
                        "result_summary": "freetext reorder",
                    })
                self._send(202, {"state": "running", "started": started})
                return
            self._send(400, {"error": "negotiate needs preset_id or message"})
            return

        if self.path == "/api/complete":
            body = self._read_json_body()
            task_id = (body.get("id") or "").strip()
            if not task_id:
                self._send(400, {"error": "complete needs a task id"})
                return
            # A recurring chore/appointment: "done for today" — flip the cache only, NO Anytype
            # write (Recurring objects have no Task status, and they recur; done-forever is wrong).
            # It comes back next cycle when the plan regenerates. This is what lets June finally
            # check off the dishes (2026-07-13).
            if plan_store.is_recurring_item(task_id):
                plan = plan_store.mark_item_done(task_id)
                self._send(200, {"completed": {"id": task_id, "done": True, "recurring": True},
                                 "plan": plan or {"empty": True}})
                return
            # A block check: "I worked on it today" — log locally + flip the cache, NEVER an
            # Anytype done-write (a block must not finish the project; it returns tomorrow). The
            # overlay sends the block's project_id in `id`. (display_grain_design.md decision 3.)
            if plan_store.is_block_item(task_id):
                chunk_log.log_chunk(task_id)
                plan = plan_store.mark_block_chunked(task_id, True)
                self._send(200, {"completed": {"id": task_id, "did_chunk_today": True, "block": True},
                                 "plan": plan or {"empty": True}})
                return
            # A real task: mark done in Anytype (with read-back), then flip the cache so the surface
            # shows it checked without a regeneration. A failed close surfaces honestly.
            try:
                confirmed = task_actions.complete_task(task_id)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            plan = plan_store.mark_item_done(task_id)
            self._send(200, {"completed": confirmed, "plan": plan or {"empty": True}})
            return

        if self.path == "/api/task/reschedule":
            body = self._read_json_body()
            task_id = (body.get("id") or "").strip()
            # The chip sends a resolver TOKEN (today/tomorrow/someday/a weekday/ISO), never a
            # rendered date label — Python re-anchors it to a real date server-side.
            when = (body.get("when") or "").strip()
            if not task_id or not when:
                self._send(400, {"error": "reschedule needs id and when"})
                return
            # Writes a Scheduled date or parks someday (never clears), with read-back. A failed
            # reschedule surfaces honestly.
            try:
                out = task_actions.reschedule_task(task_id, when)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            self._send(200, {"ok": True, "when_label": out.get("when_label")})
            return

        if self.path == "/api/task/not-today":
            # "Not today": take an item off TODAY'S list only. Cache-only by design — no Anytype
            # write, no status change, no reschedule (June, 2026-07-14: "removed from today's daily
            # list; the next day handles generation the same way, the item keeps the status it had").
            # `kind`: "task" (id = task id) or "block" (id = project id → drop all its rows).
            # The deferral is written to TWO logs, each with its own job:
            #   • session_store "deferral" stream — the 8h recency window build_context reads, so a
            #     SAME-DAY regenerate honors the deferral and then lets it expire (the stickiness).
            #   • signal_log (source plan_deferral) — the permanent qualitative learning record.
            # Neither touches the task. Removal is the primary effect; a log write that fails is
            # surfaced (warning + stderr), never silently swallowed and never undoes the removal.
            body = self._read_json_body()
            obj_id = (body.get("id") or "").strip()
            kind = (body.get("kind") or "task").strip()
            name = (body.get("name") or "").strip()
            if not obj_id:
                self._send(400, {"error": "not-today needs an id"})
                return
            try:
                if kind == "block":
                    plan, removed = plan_store.remove_block(obj_id)
                else:
                    plan, removed = plan_store.remove_item(obj_id)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            if plan is None:
                self._send(404, {"error": "no cached plan to remove from"})
                return
            if not removed:
                self._send(404, {"error": "that item isn't on today's list"})
                return
            resp = {"ok": True, "plan": plan}
            log_name = (name or removed[0].get("task") or removed[0].get("project")
                        or removed[0].get("name") or obj_id)
            warnings = []
            try:
                session_store.append_entry("deferral", {"kind": kind, "id": obj_id,
                                                        "name": log_name, "request_type": "not_today"})
            except Exception as e:
                print(f"[not-today] deferral-window log failed for {obj_id!r}: {e}", file=sys.stderr)
                warnings.append("removed for now, but it may come back if the plan regenerates today")
            try:
                signal_log.log_signal(log_name, source="plan_deferral", reference=obj_id)
            except Exception as e:
                print(f"[not-today] signal_log failed for {obj_id!r}: {e}", file=sys.stderr)
                warnings.append("removed, but the learning note didn't save")
            if warnings:
                resp["warning"] = "; ".join(warnings)
            self._send(200, resp)
            return

        if self.path == "/api/task/move":
            # Tap-to-place, deterministic: relocate one task LATER in the CACHED plan at the
            # tapped position, clock times re-flowed automatically from existing durations. No
            # LLM, no reorder call, no Anytype write (contrast /api/negotiate, which regenerates).
            # The move lives ONLY in the cache; the next generation rebuilds from Anytype and
            # it's gone. The overlay copy says so — no false promise of persistence.
            # Shapes: target_block present (int; optional int position, default append) -> clock
            #         move; position only -> fragmented-day (priority-shape) reorder.
            body = self._read_json_body()
            task_id = (body.get("id") or "").strip()
            target = body.get("target_block")
            position = body.get("position")

            def _bad_int(v):
                # bool is an int subclass in Python — a JSON `true` must not pass as an index.
                return v is not None and (not isinstance(v, int) or isinstance(v, bool))

            if not task_id or _bad_int(target) or _bad_int(position):
                self._send(400, {"error": "move needs a task id and integer target_block/position"})
                return
            if target is None and position is None:
                self._send(400, {"error": "move needs a destination (target_block and/or position)"})
                return
            try:
                if target is not None:
                    plan = plan_store.move_item_later(task_id, target, position=position)
                else:
                    plan = plan_store.move_priority_item_later(task_id, position)
            except ValueError as e:      # not later / out of range
                self._send(400, {"error": str(e)})
                return
            except LookupError as e:     # no cache / wrong shape / id not found
                self._send(404, {"error": str(e)})
                return
            self._send(200, {"ok": True, "plan": plan})
            return

        if self.path == "/api/uncomplete":
            body = self._read_json_body()
            task_id = (body.get("id") or "").strip()
            if not task_id:
                self._send(400, {"error": "uncomplete needs a task id"})
                return
            # A recurring chore: undo is a local cache un-flip only (nothing was written to Anytype).
            if plan_store.is_recurring_item(task_id):
                plan = plan_store.mark_item_undone(task_id)
                self._send(200, {"uncompleted": {"id": task_id, "done": False, "recurring": True},
                                 "plan": plan or {"empty": True}})
                return
            # A block un-check (mis-tap): un-log today's chunk + un-flip the cache. Cache-only.
            if plan_store.is_block_item(task_id):
                chunk_log.unlog_chunk(task_id)
                plan = plan_store.mark_block_chunked(task_id, False)
                self._send(200, {"uncompleted": {"id": task_id, "did_chunk_today": False, "block": True},
                                 "plan": plan or {"empty": True}})
                return
            # A real task: status back to Ready in Anytype (read-back), then un-check the cache.
            try:
                confirmed = task_actions.uncomplete_task(task_id)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            plan = plan_store.mark_item_undone(task_id)
            self._send(200, {"uncompleted": confirmed, "plan": plan or {"empty": True}})
            return

        if self.path == "/api/duration":
            # June set an item's duration from the overlay — one interface, dispatched by what the
            # row IS (display_grain_design.md + the duration-generalization, 2026-07-14):
            #   - a BLOCK  -> the durable Project field (block chunk length) via block_duration,
            #                 plus a timestamped event; a preference, NOT a completion.
            #   - a real TASK/RECURRING -> its own 'Duration min' field via task_actions (read-back).
            # A generated row with no backing object (a rest suggestion / the walk) never reaches
            # here: the overlay shows no duration chip on it, because there's nowhere to persist to.
            body = self._read_json_body()
            item_id = (body.get("id") or "").strip()
            minutes = body.get("minutes")
            if isinstance(minutes, bool):     # JSON true is an int subclass — reject it
                minutes = None
            try:
                minutes = int(minutes)
            except (TypeError, ValueError):
                minutes = None
            if not item_id or minutes is None or minutes <= 0:
                self._send(400, {"error": "duration needs id and positive integer minutes"})
                return
            try:
                if plan_store.is_block_item(item_id):
                    block_duration.set_chunk_min(item_id, minutes)
                    plan = plan_store.set_block_chunk(item_id, minutes)
                else:
                    task_actions.set_task_duration(item_id, minutes)
                    plan = plan_store.set_item_duration(item_id, minutes)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            self._send(200, {"ok": True, "id": item_id, "duration_min": minutes,
                             "plan": plan or {"empty": True}})
            return

        if self.path == "/api/settings":
            # Update overlay settings live — persisted so a restart keeps the choice. MERGE into
            # the existing file (never clobber other keys: the backend choice and the hobby toggle
            # are independent). The generation worker reads CD_BACKEND / settings.json fresh each run.
            body = self._read_json_body()
            settings = _load_settings()
            if "backend" in body:
                backend = (body.get("backend") or "").strip()
                if backend not in VALID_BACKENDS:
                    self._send(400, {"error": f"unknown backend {backend!r}"})
                    return
                os.environ["CD_BACKEND"] = backend
                settings["backend"] = backend
            if "include_hobby_block" in body:
                settings["include_hobby_block"] = bool(body.get("include_hobby_block"))
            _save_settings(settings)
            self._send(200, {"backend": os.environ.get("CD_BACKEND", "mistral"),
                             "include_hobby_block": settings.get("include_hobby_block", False)})
            return

        if self.path == "/api/logday":
            # Log (Task 5/6C, extended): June's own faithful record — how the day went AND/OR an
            # issue she hits in real time to come back to later. She picks which via `tags` (multi-
            # select: "day", "issue", or both) — a light label, NOT a classifier. Stored verbatim +
            # uncategorized via signal_log (source="log_day"); the tags ride in reference so a later
            # "review my issues" pass can find them, and Phase 7 still extracts from the raw text.
            # Sync, no LLM. We never narrate a classification back — only a plain acknowledgment.
            body = self._read_json_body()
            text = (body.get("text") or "").strip()
            if not text:
                self._send(400, {"error": "log needs text"})
                return
            # keep only known tags; tolerate a malformed (non-list) value; default to the day if
            # none came through (never lose the entry over a tag)
            raw_tags = body.get("tags")
            tags = ([t for t in raw_tags if t in ("day", "issue")]
                    if isinstance(raw_tags, list) else []) or ["day"]
            try:
                signal_log.log_signal(text, source="log_day",
                                      reference={"kind": "log_day", "tags": tags})
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            self._send(200, {"ok": True, "tags": tags})
            return

        if self.path == "/api/capture":
            body = self._read_json_body()
            text = (body.get("text") or "").strip()
            if not text:
                self._send(400, {"error": "capture needs text"})
                return
            # Async like /api/negotiate: a weed is an LLM call (~30s), too long to hold the
            # phone's connection. Kick it off; the Add tab polls /api/status, then reads
            # /api/session for the result. One generation at a time (the shared lock).
            started = _start_generation(lambda: capture_generate.capture(text))
            self._send(202, {"state": "running", "started": started})
            return

        if self.path == "/api/capture/undo":
            body = self._read_json_body()
            object_id = (body.get("id") or "").strip()
            if not object_id:
                self._send(400, {"error": "undo needs an object id"})
                return
            # Sync — undo is cheap (no LLM): archive the just-captured object, log the undo so
            # the next turn's LLM sees it. A failed undo surfaces honestly.
            try:
                archived = task_actions.archive_object(object_id)
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            session_store.mark_undo("capture", object_id, detail=f"removed {object_id}")
            self._send(200, {"undone": archived})
            return

        if self.path == "/api/focus/author":
            body = self._read_json_body()
            text = (body.get("text") or "").strip()
            if not text:
                self._send(400, {"error": "authoring needs text"})
                return
            # Async: the structure step is an LLM call (~30s). Kick it off; the overlay polls
            # /api/focus/status, then reads /api/focus/result. Shares the one lock — if a plan
            # generation (or another authoring) is already running, `started` is False and the UI
            # shows "one thing at a time," never a silent hang.
            def _job(t=text):
                fields = focus_period_generate.generate_focus_period(t)
                reflect = focus_period_adapter.reflect_back(fields)
                focus_store.save_result({"raw_text": t, "fields": fields, "reflect": reflect})
            started = _start_focus_generation(_job)
            self._send(202, {"state": "running", "started": started})
            return

        if self.path == "/api/focus/reflect":
            # Re-render the deterministic reflect-back after a client-side per-field fix. Cheap,
            # synchronous, NO LLM — keeps the reflect template single-source (Python) instead of
            # duplicating date/label formatting in the client.
            body = self._read_json_body()
            self._send(200, focus_period_adapter.reflect_back(
                body.get("fields") or {}, original=body.get("original")))
            return

        if self.path == "/api/focus/commit":
            # Confirm -> write. The client sends the (possibly per-field-edited) structured fields.
            body = self._read_json_body()
            fields = body.get("fields") or {}
            raw_text = (body.get("raw_text") or "").strip()
            # Guard the silent failure: a period with no start/end never activates and nothing
            # tells her. Block the write and surface exactly what's missing (Needs-Clarifying).
            blocking = focus_period_adapter.missing_required(fields)
            if blocking:
                self._send(200, {"blocked": blocking})
                return
            # Sync write (like /api/capture/undo) — avoids colliding with the single _gen_lock.
            try:
                objects = g.fetch_all_objects(g.get_space_id())
                name, props = focus_period_adapter.to_write_properties(fields, objects=objects)
                oid = focus_period_author.author_focus_period(
                    raw_text, name, props, source="config_authoring")
            except ValueError as e:   # an unknown project name — never silently dropped
                self._send(400, {"error": str(e)})
                return
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            # Read-back to PROVE it persisted before confirming success (confirmation discipline:
            # a good answer is not a saved object).
            try:
                data = g.fetch_all_objects(g.get_space_id())
                obj = next((o for o in data if o.get("id") == oid), None)
                parsed = focus_period.parse_focus_period(obj) if obj else None
                if not parsed or not (parsed["start"] and parsed["end"]):
                    self._send(500, {"error": "period did not persist correctly on read-back"})
                    return
            except Exception as e:
                self._send(500, {"error": f"read-back failed: {e}"})
                return
            focus_store.clear()
            self._send(200, {"ok": True, "id": oid, "name": name})
            return

        if self.path == "/api/focus/edit":
            # Route B (Task 4): a broad SPOKEN revision. Async — load the active period, let the LLM
            # apply the change against it (keeping untouched fields), and reflect back a DIFF (changed
            # vs stayed) so a clobbered field is visible before anything writes.
            body = self._read_json_body()
            text = (body.get("text") or "").strip()
            if not text:
                self._send(400, {"error": "editing needs text"})
                return
            def _job(t=text):
                _goals, projects, *_rest, period_ctx = daily_plan.load_active_items(g.get_space_id())
                period = period_ctx.get("period")
                if not period:
                    raise RuntimeError("no active period to edit")
                current = focus_period_adapter.period_to_fields(period)
                names = [p["name"] for p in projects]
                new_fields = focus_period_generate.generate_focus_period(t, names=names, current=current)
                reflect = focus_period_adapter.reflect_back(new_fields, original=current)
                focus_store.save_result({"raw_text": t, "fields": new_fields, "original": current,
                                         "id": period.get("id"), "reflect": reflect})
            started = _start_focus_generation(_job)
            self._send(202, {"state": "running", "started": started})
            return

        if self.path == "/api/focus/update":
            # Confirm an edit -> UPDATE IN PLACE (Task 4). Same guards as commit, but updates the
            # existing object (v1 choice) instead of creating a new one.
            body = self._read_json_body()
            fields = body.get("fields") or {}
            raw_text = (body.get("raw_text") or "").strip()
            oid = (body.get("id") or "").strip()
            if not oid:
                self._send(400, {"error": "update needs the period id"})
                return
            blocking = focus_period_adapter.missing_required(fields)
            if blocking:
                self._send(200, {"blocked": blocking})
                return
            try:
                objects = g.fetch_all_objects(g.get_space_id())
                name, props = focus_period_adapter.to_write_properties(fields, objects=objects)
                focus_period_author.update_focus_period(oid, raw_text, name, props,
                                                        source="config_correction")
            except ValueError as e:
                self._send(400, {"error": str(e)})
                return
            except Exception as e:
                self._send(500, {"error": str(e)})
                return
            try:
                data = g.fetch_all_objects(g.get_space_id())
                obj = next((o for o in data if o.get("id") == oid), None)
                parsed = focus_period.parse_focus_period(obj) if obj else None
                if not parsed or not (parsed["start"] and parsed["end"]):
                    self._send(500, {"error": "edit did not persist correctly on read-back"})
                    return
            except Exception as e:
                self._send(500, {"error": f"read-back failed: {e}"})
                return
            focus_store.clear()
            self._send(200, {"ok": True, "id": oid, "name": name})
            return

        self._send(404, {"error": f"no route {self.path}"})

    # quieter logging — one line per request, no client noise
    def log_message(self, fmt, *args):
        sys.stderr.write(f"[cd-server] {self.address_string()} {fmt % args}\n")


def main():
    plan_store.load_actions()  # seed the button schema on first run
    # Reconcile a stuck "running" status left by a crash/kill mid-generation: nothing else ever
    # resets it, so the overlay's poller would wait on it forever after a restart. A "running"
    # status at process startup is always stale (nothing was running before this process existed).
    if plan_store.get_gen_status().get("state") == "running":
        plan_store.set_gen_status("idle")
    # Restore the persisted backend choice (the gear panel writes it). Env var set by an outer
    # launcher still wins for this process only if no setting was saved.
    s = _load_settings()
    if s.get("backend") in VALID_BACKENDS:
        os.environ["CD_BACKEND"] = s["backend"]
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Controlled Drift overlay → http://{HOST}:{PORT}")
    print("  GET /api/plan · /api/map · /api/period · /api/actions · /api/status · /api/session · /api/settings")
    print("  GET /api/focus/status · /api/focus/result   POST /api/focus/author (async) · /api/focus/commit")
    print("  POST /api/refresh · /api/negotiate · /api/capture (async)")
    print("  POST /api/complete · /api/uncomplete · /api/capture/undo · /api/settings")
    print("  Ctrl-C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        srv.server_close()


if __name__ == "__main__":
    main()

# Spec deltas — 2026-07-16 (from the Reorganize-mobile UI session)

> **Vendored 2026-07-17** from the Claude Design project *"HTML overlay mobile adaptation"*
> (`spec-deltas-2026-07-16.md`). Companion: `docs/review_reorganize_backend_spec.md`.

Three changes decided while building the reorganize/detail overlay. Merged into `AI_LAYER_SPEC.md` on 2026-07-17. The first two touch backend, the third is UI-only.

---

## 1 — Retire Practice/Routine on Recurring items *(backend change)*

> ✅ **REAFFIRMED 2026-07-17.** Briefly reinstated when reframed in plain language, then cut again on reflection: the distinction gives the user nothing actionable (interval already encodes frequency; nothing reads `target`). Removed from the UI.
>
> ✅ **APPLIED 2026-07-17.** See "Status" below — this section is now history, not a TODO list.

**Decision:** the Practice-vs-Routine distinction is dropped. A recurring item is defined by its interval alone. No stored flag, no target field.

**Spec — §169–170 Recurring table:** both rows struck through and marked RETIRED (not deleted — the record is preserved), with a Practice/Routine retirement note added under the table. Done 2026-07-17.

**Safe to cut — verified against `feat/overlay-actionable` @76102384.** `has_target` / `Target` were referenced only in scaffolding + display paths, never in scheduling. **No consumer:** `datetime_seam.py` schedules purely on `interval_unit` / `interval_count` / `day_of_week` / `time_of_day` / `duration`; `daily_plan` / `plan_generate` never read `has_target`/`target`.

### Status (verified 2026-07-17)

The original TODO list in this section was **already stale when checked** — most of it had been applied by an earlier pass, and two items described code that never existed:

- [x] `build_recurring.py` — no longer creates `Has target` / `Target`; lines ~40–48 actively **unlink** both from the Recurring type (schema-level unlink, stored values untouched).
- [x] `orient_map.py` — **no such reference exists.** The only `target` hit is `x.get("target")`, an unrelated Anytype link-id fallback. The original TODO was wrong about this file.
- [x] `verify_model.py` — the Recurring expected list **never contained** these keys. Nothing to drop.
- [x] Live space confirms it: `describe_model.py` reports Recurring with 17 fields, neither present.
- [x] Legacy values left on existing Anytype objects, deliberately. Harmless; no reader looks at them.

---

## 2 — Calendar-sourced recurring items are read-only reflections *(reaffirms §454)*

**Decision:** a recurring item synced from a calendar carries `source = calendar`. Its calendar-owned fields are a **one-way, read-only reflection**; app-native fields stay editable. **No two-way write-back.** This does not introduce a new privacy stance — it **reaffirms the §454 decision** (Apple Calendar via local AppleScript/EventKit, on-device, read-only; not Google, and nothing written out).

**Spec — §179 / §454:** the read path is already decided (Apple EventKit, parked post-v1). The field contract for when that path lands:

> **Calendar-sourced recurring items (UI contract, 2026-07-16).** A synced item carries `source = "calendar"`. Its **calendar-owned fields — title, `day_of_week`, `time_of_day`, `interval_unit`/`interval_count` — are read-only in every GSDO surface**, edited only in Apple Calendar (one-way in, per §454). **App-native relations — `engagement`, `access_conditions`, `duration_estimate`, `context`, notes — stay fully editable in GSDO and never sync out.** Nothing propagates back to the calendar. Surfaces render the synced time as a locked "from Calendar" value with an "edit in Calendar" hint.

**Why one-way (not write-back):** write-back would mean EventKit write scopes and bidirectional conflict resolution, and it duplicates an editing surface June already has in Calendar. Calendar stays source of truth for calendar-owned fields. Consistent with §454; needs no re-litigation.

**Backend TODO (when the §454 read path is built — PARKED post-v1):**
- [ ] Add `source` to the Recurring type (`select`: `manual` (default) | `calendar`).
- [ ] EventKit sync sets `source = calendar` and populates title / `day_of_week` / `time_of_day` / interval from the event.
- [ ] Any write path (overlay, MCP `cd_mcp_server`, memory pass) rejects edits to calendar-owned fields when `source = calendar`; allows app-native fields.
- [ ] No scheduler change — `datetime_seam.py` already treats set `day_of_week` + `time_of_day` as a fixed anchor (spec §172, §179).

---

## 3 — Field options are schema-driven, not hardcoded *(UI note)*

The reorganize overlay derives every field's options (statuses, engagement levels, access conditions, frequencies, day-of-week, strategy triggers) from a single schema object rather than hardcoded lists, with a `loadSchema()` seam for a live pull. Consistent with §446 ("fields are the AI's substrate").

> ⚠ **Implication surfaced 2026-07-17:** this requires a `GET /api/schema` endpoint that **does not exist yet**. The whole form/picker/chip/dropdown layer is generated from it — load-bearing, not optional. See `docs/review_reorganize_backend_spec.md` §16 and `docs/api_contract_v2.md`.

---

## Related cut, not in the original delta doc

**Excitement — CUT 2026-07-17.** `excitement_level` (Project, number 1–5) removed from the data structure; never wired into selection. `AI_LAYER_SPEC.md` §7's *rationale* is retained and still live — the signal it described is carried by Project `engagement` + `affective`. Applied to `build_project.py`, `verify_model.py`, `review_surface.py`, `surface_template.html`. See `docs/review_reorganize_backend_spec.md` §10.

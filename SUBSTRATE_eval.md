# Substrate evaluation — choosing the store

**What this is.** The substrate fork from `Parameters_v2.md` §C / `JULIA_FRAMEWORK.md` §F: which existing tool holds the commodity list/dashboard (the *store*), under the resolved architecture "build only the thin AI layer, adopt a store." Two research passes, 2026-06-15. See [[project-gsdo]], [[EVAL_adopt_adapt_build]].

## The reframe that simplifies the choice (spatial time)

June prioritized "visual." That surfaced that **"visual" is two needs** with opposite implications:
- **Visual dashboards / grouping** (Notion-style views) → comes from the *store*. A store-selection criterion.
- **Spatial *time*** (proportional timeline; shrinking-disc countdown — June: "I need that desperately") → **does NOT come from any adoptable store, and is cheap to build ourselves.**

Why: the tools with the best ADHD spatial-time displays — **Tiimo, Structured** — are **closed, no public API** (calendar sync is inbound-only at best). They *cannot* be the store an AI layer reads/writes. The tools with real APIs (Amazing Marvin) have the *weakest* spatial-time rendering. So spatial-display and open-store don't coexist in one product. **And building spatial time is cheap:** `vis-timeline` (mature, actively maintained) for the proportional day-timeline; the shrinking disc is a small library (`react-countdown-circle-timer`, popular but stale) or ~30 lines of SVG (`stroke-dasharray` arc). The expensive/uncertain work is the AI planning logic (duration estimation, adaptive rescheduling) — which we own regardless of store.

**Consequence:** the store is chosen on **dashboards + AI read/write + privacy + cold-start friction**, NOT on spatial time. Spatial time is a confirmed-cheap build item in the layer.

## Store candidates

**Dropped:**
- **Capacities** — networked-notes/PKM, not a multi-view database; API early beta, gap-ridden. Fails the visual-database filter.
- **Tana** — outliner with supertags; good API (Input API + local API + MCP) but views-as-outline not views-first, and **cloud-only** (no local tier).
- **AppFlowy** — open-source, self-hostable, Notion-shaped, REST API + MCP. But good programmatic access effectively requires running **AppFlowy Cloud (8 services)** — sysadmin overhead that contradicts June's "don't want to maintain it." Privacy via self-hosting, but the burden moves to infra.

**Finalists:**

**Notion** — *the safe, polished default.*
- Visual: strongest in the set. Databases render as Table/Board/Gallery/Calendar/List/Timeline; multiple linked DBs as views on one dashboard page (the tasks+goals+practices+routines pattern). Best dashboards available.
- AI read/write: most mature. Stable REST API (full CRUD; "data sources" model as of 2025-09-03) + official hosted MCP. **Note:** the hosted MCP is for interactive clients and reportedly lacks bearer-token/unattended auth — a *headless* AI layer drives the **REST API directly** (integration tokens), not the MCP.
- Privacy: **hosted cloud only.** No local/self-host/E2E. → the sensitive (legal/health) tier *cannot* live in Notion; it fragments the "one place" telos.
- Cold-start: documented ADHD overwhelm risk (blank-canvas "total system" is what users bounce off). Mitigable with a deliberately minimal template + collapsible toggles, but real.
- Spatial time: absent (Timeline/Gantt is the closest; not a proportional spatial-time canvas).

**Anytype** — *the values-aligned, highest-fit, highest-uncertainty option.*
- Visual: real and better than expected. Typed Objects; **Sets** (query-driven) + **Collections** render as Grid/List/Gallery/Kanban/Calendar; Calendar/Kanban/Gallery widgets + graph view on the dashboard space. Clears the hard filter; less turnkey than Notion's free-form linked-DB embedding.
- AI read/write: **yes, two clean local paths** — a bundled **Local API** on localhost (create/edit/query/search, read+write confirmed; bearer key in-app) and an **official MCP server** (`anyproto/anytype-mcp`). *Caveat:* the Local API is a **Developer Preview** (~v0.46.x) — endpoint completeness, write reliability under constant agent writes, and performance are **unverified**. This is the single biggest unknown.
- Privacy: **genuinely local-first**, E2E-encrypted, offline-capable, P2P sync. The only finalist that satisfies the sensitive-tier privacy *want* natively, with no infra to run. Consistent with Reframe/PMA.
- Cold-start: moderate — typed objects give *scaffolding* (arguably gentler for ADHD than Notion's blank field), but the object/set/collection model is its own learning curve and the ADHD-template ecosystem is thin.
- Spatial time: absent (Calendar view only).

## DECISION: Anytype — validated 2026-06-15 ✅

Hands-on validation run against the live Local API (`http://localhost:31009/v1`, key in project `.env` as `get_shit_done`; test scripts `/tmp/anytype_test.py`, `/tmp/anytype_validate.py`). **14/14 checks passed**, including all four make-or-break:
- Create custom properties (number/checkbox/**objects-relation**/select) ✅
- Create a custom **Goal** type ✅
- Create a **Task linked to a Goal** via the `reaching_for` objects-relation — **link persists on read-back** ✅ (the alignment hierarchy depends on this)
- Update (mark done, change field) persists ✅
- **Batch 20 creates, ~12ms each, zero errors** ✅ (the Developer-Preview API held up under rapid writes)

API shape learned: REST at `/v1/spaces/{sid}/{objects|properties|types}`; auth `Authorization: Bearer <key>` + `Anytype-Version: 2025-11-08`; OpenAPI served at `localhost:31009/docs/openapi.json`. Object create body: `{type_key, name, body(markdown), properties:[{key, <typed-value>}]}`; relations use `{key, objects:[id,...]}`. **Store decided → Anytype.** Privacy = local-first/E2E already satisfied; model-tiering (local vs hosted inference for sensitive items) tabled as a separate, testable question (Ollama + MLX already installed on June's machine).

### Original recommendation (now resolved)
**Don't commit blind. Validate Anytype hands-on first.** It's the best fit for June on every axis *except* maturity — and maturity is testable. Concretely: June installs Anytype; an agent drives the Local API to confirm it can reliably read/write the data model the AI layer needs (tasks/goals/practices with relations, repeated writes). **If it holds up → Anytype** (private, unified, one place, ADHD-friendly scaffolding). **If too rough → Notion** as the safe fallback, accepting that the sensitive tier lives separately and a minimal starting template is mandatory.

**Architecture note retained:** because spatial-time and likely other custom views get built in the layer anyway, the store earns its place by providing the *ready-made visual dashboard + cross-device sync + mobile* — not by being the only UI. Keep the store's role to: data model + dashboard + sync. Build: the AI logic + the spatial-time view (cheap).

## Honest uncertainties
- Anytype Local API real-world reliability/coverage (Developer Preview) — the thing the validation pass must resolve.
- Whether Tiimo/Structured timeline blocks are *strictly* proportional (size = duration) — unverified, but moot since both are foreclosed as stores; matters only as design reference.
- Google Calendar is the one tool that's both proportional-time *and* a writable store (mature API, already wired into this environment) — but it's generic, not ADHD-tuned. Possible *secondary* surface for time-blocking, not the primary store.

## Sources
Notion API/MCP (github.com/makenotion/notion-mcp-server; stackone.com/blog/notion-mcp-deep-dive); Anytype Local API (doc.anytype.io/.../local-api) + MCP (github.com/anyproto/anytype-mcp); AppFlowy-Cloud (github.com/AppFlowy-IO/AppFlowy-Cloud); Capacities API (docs.capacities.io/developer/api); Tana Input API (tana.inc/docs/input-api); vis-timeline (github.com/visjs/vis-timeline); react-countdown-circle-timer (github.com/vydimitrov/react-countdown-circle-timer); Amazing Marvin API + MCP (github.com/amazingmarvin/MarvinAPI, github.com/bgheneti/Amazing-Marvin-MCP); Google Calendar API (developers.google.com/workspace/calendar). Full URLs in the two research-pass outputs (session 2026-06-15).

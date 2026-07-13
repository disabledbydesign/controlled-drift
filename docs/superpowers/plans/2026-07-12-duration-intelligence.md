# Duration Intelligence Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking. For code review, route through a **non-Claude** reviewer (`~/.claude/skills/requesting-code-review/github_models_review.py`) to avoid the same-family blind spot — this is Claude-generated code touching June's live task data.

**Goal:** Point LLM intelligence at task durations so the daily plan stops treating almost every task as a flat 30-minute block. Two moves: (1) at capture time, when June does *not* state a duration, the system *estimates* one from her stated priors + the task's project context, and **labels it as an estimate** (distinct from a duration June stated); (2) a reviewable backfill fills estimated, labeled durations onto the ~135 existing tasks that currently carry none. The scheduler already reads `Duration min` and falls back to 30 only when it is absent — so making that field present-and-honest is the whole fix; no scheduler-logic change is required.

**Architecture:** The estimate is produced by the LLM (Claude Code inline, or the `mistral` backend for the overlay/backfill), written through the *single* validation seam both existing write paths already share — `scripts/capture_fields.py:build_optional_props`. That seam gains provenance: it records the number in the existing `Duration min` property **and** a new companion `Duration source` property whose value is `stated` or `estimated`. Fidelity is structural, not a rule the model has to remember: the contract emits June's stated duration and the LLM's estimate as **two separate fields**, and the seam always prefers the stated one. The backfill is a standalone CLI script mirroring the memory-pass `--dry-run` / `--preview` / `--run` discipline exactly.

**Tech Stack:** Python 3 stdlib only (matches all of `scripts/`), pytest, the existing `gsdo_anytype` / `gsdo_objects` / `capture_fields` / `plan_generate` / `generation_log` modules, and Anytype at `localhost:31009`.

---

## ⚠️ OPEN QUESTIONS — surface to June before/around execution, do not silently resolve

These three are load-bearing and were left open on purpose. Each has a **recommended default** the plan is written against, so the plan is buildable today; each is a one-line flip if June/the reviewer decides otherwise.

**OQ1 — Where the estimate label lives.**
- *Recommended default (this plan builds it):* a new companion property **`Duration source`** on the Task type — an Anytype `select` with options `stated` / `estimated`. The number stays in the existing `Duration min` field (so `scheduler.get_duration` needs zero change), and `Duration source` records whether that number came from June's words or the model. A select (not a checkbox) because it reads plainly in June's Anytype UI ("estimated", not a bare checkbox) and leaves room for a future `corrected` value once the duration-bias loop lands.
- *Alternative:* a second **number** field `Duration est min` kept physically separate from June's `Duration min`, with `scheduler.get_duration` reading stated-first then estimate. Rejected as the default because it forces changes into three readers (`scheduler.py`, `daily_plan.py`, `datetime_seam.py`) for no gain — the companion-label approach keeps a single number field the scheduler already consumes. *If June prefers maximal physical separation, this is the flip.*
- *Non-negotiable either way:* a June-stated `90` and an LLM-estimated `90` must stay distinguishable at read time, or the learning loop cannot know what it is allowed to correct. Both options satisfy this.

**OQ2 — Backfill: per-task confirm vs. batch skim.**
- *Recommended default (this plan builds it):* **batch skim.** `duration_backfill.py --preview` prints every proposed estimate (task → minutes → one-line reasoning), grouped by project, for June to skim; `--run` applies them all. **Not** a 135-item per-task confirmation gate — that is exactly the spoon cost the system exists to remove, and it is disproportionate here because estimates are *labeled*, *never override anything June stated*, and are *self-correcting* once the duration-bias loop reads actuals. A wrong estimate is low-stakes and reversible; June can spot-fix an egregious one in the app.
- *Alternative:* per-task confirm (or a "confirm only the ones over N hours" middle path). *If June wants a tighter gate for the first-ever backfill specifically, the `--preview` output already gives her the review surface; tightening to per-task is a follow-up, not a rebuild.*

**OQ3 — "Multiple blocks in one day" / dedicated focus blocks — split-across-blocks scope.**
- *Decision (this plan): DEFERRED, and named.* June's "job applications need longer, or multiple blocks in one day" and "dedicated focus time blocks so I can get in the swing of it" describe a **scheduler placement** feature: taking one honest long duration (e.g. 150 min) and splitting it into N protected blocks with breaks between, possibly reserving focus time. That is genuinely separate work with its own design questions (break length between splits; whether the same task should appear twice on one plan; whether a block may span days; how it interacts with the already-built focus-configuration layer's Focus Period objects). It touches `scripts/scheduler.py` (placement) and `scripts/daily_plan.py` (break logic, lines ~525–538) and the focus-period layer (`scripts/focus_period.py`, `scripts/period_view.py`).
- *Why deferring is honest, not a dodge:* this plan produces the **precondition** for it — accurate large durations. Today the scheduler *can't* meaningfully split anything because every task claims 30 minutes. Once durations are honest, the split feature has something real to act on. Building split logic on top of fake 30-minute durations would be building on sand.
- *Where it lives:* a follow-up plan, `docs/superpowers/plans/YYYY-MM-DD-focus-blocks-and-splitting.md`, scoped to `scheduler.py` + the focus-period layer. Flag it to June as the natural next step once she's seen honest durations land.

---

## Reconciliation with `2026-07-02-learning-loops-v1.md` (do not re-implement across the two)

This plan and the learning-loops-v1 plan both touch task duration. They must not collide. Explicitly:

- **learning-loops-v1 Task 1 ("propose a duration estimate at capture time") — this plan ABSORBS and SUPERSEDES it.** That task was drafted 2026-07-02, before the `capture_fields.py` seam and the current weeding contract landed (2026-07-12). Two things changed since:
  1. The *stated-duration* write it described is **already live** — the current `_WEED_JSON_INSTRUCTION` reads `duration_min` from June's words and `capture_fields.build_optional_props` writes `Duration min`. That half is done.
  2. Its actual intent — *estimate when June is silent* — was **never built**, and the current contract explicitly forbids it ("null if she gave no signal — **NEVER guess**"). This plan builds that estimate step and deliberately flips that stance from "never guess" to "estimate, and label it as an estimate."
  → **Do not also execute learning-loops-v1 Task 1.** It is now historical; this plan is its live successor. (Leave the learning-loops-v1 doc as-is; this note is the pointer.)

- **learning-loops-v1 Task 4 (the duration-bias EMA loop, built-but-unwired) — this plan DEPENDS ON / ENABLES it; it does NOT re-implement or wire it.** The `Duration source` label added here is precisely the signal that lets a bias loop know which durations are *estimates it may correct* (`estimated`) versus *truths it must never touch* (`stated` / absent-and-pre-labeling). This plan does **not** build `duration_loop.py`, does **not** compute a bias multiplier, and does **not** wire any multiplier into the write path. Its two still-open dependencies remain open there and are out of scope here: the Phase 9 raw-text→`{estimated,actual}` extraction, and the unresolved project-vs-task-type keying question. Reference, don't rebuild.

---

## Global Constraints

- **Fidelity first (June's decision, 2026-07-12):** June's stated duration is truth and is **never** overridden by an estimate. An estimate fills silence only. This is enforced structurally (stated and estimated arrive as separate fields; the seam prefers stated), not by a rule the model must remember.
- **Every written estimate is labeled** `Duration source = "estimated"`; every written stated duration is labeled `Duration source = "stated"`. Absent `Duration source` on a task that has a `Duration min` means pre-labeling June-stated data (the only durations that existed before this plan) — treat as truth.
- **Backfill never silently rewrites June's space.** It mirrors the memory-pass flag discipline: `--dry-run` (no LLM, no writes) / `--preview` (LLM, shows what `--run` would do, writes nothing, safe to repeat) / `--run` (writes, with read-back). It only ever *fills* an absent duration — it never overwrites an existing `Duration min`, so re-running is idempotent by construction.
- **No silent failures:** raise, don't `assert`, on anything that isn't test-only sandboxing. A generation/parse failure is logged (`generation_log`) and surfaced, never swallowed. A single item's failure never aborts the batch (same discipline as `capture_generate` / `memory_pass`).
- **No scalar-flattening of affect (guard #3):** unchanged — `capture_fields` already enforces it; this plan does not touch it.
- **Property dict keys passed to `gsdo_objects.create`/`update` are display names** (`"Duration min"`, `"Duration source"`), not property keys (`gsdo_duration_min`) — matches every existing call site.
- **Verify against the live space (read-back):** every real write is followed by re-fetching the object and confirming the value persisted, before reporting success.
- **Tests self-clean:** never leave artifacts in June's real Anytype space or real data files. Redirect via `monkeypatch.setenv("CD_DATA_DIR", ...)` / `CD_CONFIG_DIR`, stub `plan_generate.generate` and `gsdo_objects.create`/`update`, exactly as the existing suite does. The one deliberate live write (final task) is deleted afterward.
- **Run the full suite** (`python3 -m pytest tests/ -q`) after every task — don't hardcode a baseline count (parallel work lands on this branch); compare before/after with `--collect-only`.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `scripts/build_task.py` | Idempotent Task-type schema builder | **Modify** — add the `Duration source` select property + link it to Task |
| `scripts/capture_fields.py` | The single shared validation seam for optional captured fields | **Modify** — make it provenance-aware: accept stated + estimated durations, prefer stated, write `Duration min` + `Duration source`; hold the shared estimation-priors text |
| `scripts/capture_generate.py` | Headless weed/capture engine (overlay Add tab) | **Modify** — contract now emits a separate `duration_estimate_min` with June's priors; thread it through to the seam |
| `scripts/memory_pass.py` | Memory→Anytype daily pass (shares the seam) | **Modify** — pass the new `duration_estimate_min` field through to the seam so the two write paths can't diverge |
| `scripts/duration_backfill.py` | **New** — reviewable backfill of estimated durations onto existing task-less-duration tasks | **Create** |
| `tests/test_capture_fields.py` | Seam unit tests | **Modify** — provenance assertions; update existing duration assertions |
| `tests/test_capture_generate.py` | Capture engine tests | **Modify** — estimate-written-and-labeled test |
| `tests/test_duration_backfill.py` | **New** — backfill tests | **Create** |

`scripts/scheduler.py`, `scripts/daily_plan.py`, `scripts/datetime_seam.py`, `scripts/plan_generate.py`, `scripts/daily_plan.py` selection logic — **untouched.** The scheduler already reads `Duration min`; making it present is the fix. (The final task *reads through* the scheduler to verify, but changes no scheduler code.)

---

### Task 1: Add the `Duration source` label property to the Task type

**What this gives you:** a place to record *whether* a task's duration came from June or from the model — so a stated 90 and an estimated 90 never look the same to the reader (the scheduler ignores this field; the future duration-bias loop reads it).

**Files:**
- Modify: `scripts/build_task.py`
- Test: `tests/test_build_task_duration_source.py` (new, tiny — verifies the builder call shape without hitting the live API)

**Interfaces:**
- Produces: a live Anytype `select` property named `"Duration source"` with options `["stated", "estimated"]`, linked to the built-in `task` type. Property key is Anytype-generated (do **not** assume `gsdo_duration_source`; downstream reads it by display name, matching the repo convention for the Engagement/Side fields — see `daily_plan.py:64`, `daily_plan.py:139`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_build_task_duration_source.py`:

```python
"""build_task must add a 'Duration source' select (stated/estimated) and link it to Task."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_task


def test_build_task_creates_and_links_duration_source(monkeypatch):
    ensured = []   # (name, fmt, options)
    linked = {}    # type_id -> list of props linked

    def fake_ensure_property(name, fmt, options=None):
        ensured.append((name, fmt, options))
        return f"prop-{name}"
    def fake_find_type(key):
        return {"id": "task-type-id", "key": "task"}
    def fake_link(type_id, props):
        linked[type_id] = props

    monkeypatch.setattr(build_task.g, "ensure_property", fake_ensure_property)
    monkeypatch.setattr(build_task.g, "find_type", fake_find_type)
    monkeypatch.setattr(build_task.g, "link_properties_to_type", fake_link)

    build_task.build_task()

    assert ("Duration source", "select", ["stated", "estimated"]) in ensured
    assert "prop-Duration source" in linked["task-type-id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build_task_duration_source.py -v`
Expected: FAIL — `AssertionError` (the property isn't ensured/linked yet).

- [ ] **Step 3: Add the property in `build_task.py`**

In `scripts/build_task.py`, inside `build_task()`, after the `p_scheduled` line (currently `p_scheduled  = g.ensure_property("Scheduled", "date")`), add:

```python
    # Provenance for Duration min: did June state this duration ("stated") or did the model
    # estimate it to fill a silence ("estimated")? The scheduler ignores this field — it only
    # reads Duration min — but the duration-bias learning loop reads it to know which durations
    # it may correct (estimated) vs. must never touch (stated). A select, not a checkbox, so it
    # reads plainly in June's UI and leaves room for a future "corrected" value.
    p_dur_source = g.ensure_property("Duration source", "select", ["stated", "estimated"])
```

Then in the `g.link_properties_to_type(task_type["id"], [ ... ])` call, add `p_dur_source` to the property list (e.g. right after `p_duration`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_build_task_duration_source.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS (one more than before).

- [ ] **Step 6: Apply the schema change to the live space, then verify**

The property must actually exist in June's space before any write can set it. Run the idempotent rebuild:

```bash
python3 scripts/build_model.py
```

Confirm no error, then verify the property and its options exist live:

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import gsdo_anytype as g
p = g.find_property('Duration source')
print('found:', p is not None, '| key:', p and p.get('key'), '| format:', p and p.get('format'))
"
```

Expected: `found: True`, a real generated key, format `select`. (If `build_model.py` doesn't already call `build_task()`, run `python3 -c "import sys; sys.path.insert(0,'scripts'); import build_task; build_task.build_task()"` instead — check `build_model.py` first.)

- [ ] **Step 7: Commit**

```bash
git add scripts/build_task.py tests/test_build_task_duration_source.py
git commit -m "feat(schema): add Duration source label (stated/estimated) to the Task type"
```

---

### Task 2: Make the shared seam provenance-aware (`capture_fields.build_optional_props`)

**What this gives you:** the one place both write paths (overlay capture *and* memory pass) go through now knows the difference between a duration June stated and one the model estimated — and writes the label automatically, so neither caller can forget it or diverge.

**Files:**
- Modify: `scripts/capture_fields.py`
- Test: `tests/test_capture_fields.py`

**Interfaces:**
- Produces:
  - `capture_fields.DURATION_PRIORS: str` — June's stated calibration priors, the single source of the estimation guidance text reused by both prompt sites (capture contract + backfill). Keeping it here (network-free, alongside the duration seam) means the two prompts can't drift apart.
  - `build_optional_props(*, duration_min=None, duration_estimate_min=None, affect=None, blocked_on=None, access_conditions=None) -> dict` — now also returns `"Duration source"` whenever it returns `"Duration min"`. Precedence: a valid `duration_min` (stated) wins and yields `Duration source="stated"`; else a valid `duration_estimate_min` yields `Duration source="estimated"`; else neither key is written. Both callers pass display-name dicts straight into `gsdo_objects.create`/`update`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_capture_fields.py`:

```python
def test_stated_duration_labels_source_stated():
    assert cf.build_optional_props(duration_min=90) == {
        "Duration min": 90, "Duration source": "stated"}


def test_estimated_duration_labels_source_estimated():
    assert cf.build_optional_props(duration_estimate_min=120) == {
        "Duration min": 120, "Duration source": "estimated"}


def test_stated_wins_over_estimate_fidelity_first():
    # June said 90; the model also guessed 120. Her number is truth; the estimate is discarded.
    assert cf.build_optional_props(duration_min=90, duration_estimate_min=120) == {
        "Duration min": 90, "Duration source": "stated"}


def test_no_duration_writes_neither_key():
    out = cf.build_optional_props(duration_min=None, duration_estimate_min=None)
    assert "Duration min" not in out and "Duration source" not in out


def test_invalid_estimate_writes_nothing():
    assert cf.build_optional_props(duration_estimate_min="soon") == {}
    assert cf.build_optional_props(duration_estimate_min=0) == {}
    assert cf.build_optional_props(duration_estimate_min=-5) == {}


def test_duration_priors_text_present():
    # The shared priors carry June's calibration so both prompt sites stay in sync.
    assert "1" in cf.DURATION_PRIORS and "hour" in cf.DURATION_PRIORS.lower()
```

Then **update the existing duration assertions** in this file — they now also carry the source label. Change:

```python
def test_duration_valid_int():
    assert cf.build_optional_props(duration_min=45) == {"Duration min": 45}


def test_duration_coerces_numeric_string():
    assert cf.build_optional_props(duration_min="30") == {"Duration min": 30}
```

to:

```python
def test_duration_valid_int():
    assert cf.build_optional_props(duration_min=45) == {
        "Duration min": 45, "Duration source": "stated"}


def test_duration_coerces_numeric_string():
    assert cf.build_optional_props(duration_min="30") == {
        "Duration min": 30, "Duration source": "stated"}
```

(`test_duration_absent_or_bad_writes_nothing` stays correct as-is — an absent/invalid stated duration with no estimate still writes nothing.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_capture_fields.py -v`
Expected: the new tests FAIL (`Duration source` not produced; `DURATION_PRIORS` missing) and the two edited existing tests FAIL (no source label yet).

- [ ] **Step 3: Implement provenance in `capture_fields.py`**

Add the priors constant near the top of `scripts/capture_fields.py` (after the module docstring, before `ALLOWED_ACCESS`):

```python
# June's stated duration calibration (2026-07-12), reused verbatim by every prompt site that
# asks the model to estimate — the single source so the capture contract and the backfill
# prompt can't drift apart. Her words: most tasks run 1-2 hours, not 30 minutes; focused-
# attention work (job applications) runs longer or needs multiple blocks in one day.
DURATION_PRIORS = (
    "June's real tasks almost never take 30 minutes. Her stated norm: most tasks run 1-2 hours. "
    "Studying, writing, learning, and focused project work: estimate 60-120 minutes or more. "
    "Focused-attention work like job applications: 120+ minutes, and may need multiple blocks in "
    "one day — estimate the full realistic time, do not shrink it to fit a single block. "
    "Genuinely quick actions (a short phone call, a single email, a small errand): 5-30 minutes. "
    "Use the task's linked project as context: a task under a heavy scholarly or application "
    "project skews longer than one under an errands project. Estimate the honest time the task "
    "actually takes for June, not a tidy default."
)
```

Replace `build_optional_props` (and add a small helper) so provenance is handled in one place:

```python
def _resolve_duration(stated, estimate):
    """Fidelity-first: a valid stated duration wins and is labeled 'stated'; otherwise a valid
    estimate fills the silence and is labeled 'estimated'; otherwise nothing. Returns
    (minutes|None, source|None)."""
    dur = _duration_prop(stated)
    if dur is not None:
        return dur, "stated"
    est = _duration_prop(estimate)
    if est is not None:
        return est, "estimated"
    return None, None


def build_optional_props(*, duration_min=None, duration_estimate_min=None, affect=None,
                         blocked_on=None, access_conditions=None):
    """Return {display_name: value} for ONLY the optional fields that validate.

    Duration carries provenance: June's stated duration (duration_min) is truth and always wins;
    an LLM estimate (duration_estimate_min) fills silence only. Whichever is written, a companion
    'Duration source' label ('stated'|'estimated') is written alongside it so the reader — and the
    future duration-bias loop — can tell them apart. A June-stated 90 and an estimated 90 must
    never be indistinguishable.
    """
    props = {}
    dur, source = _resolve_duration(duration_min, duration_estimate_min)
    if dur is not None:
        props["Duration min"] = dur
        props["Duration source"] = source
    aff = _text_prop(affect)
    if aff is not None:
        props["Affective"] = aff
    blk = _text_prop(blocked_on)
    if blk is not None:
        props["Blocked on"] = blk
    acc = _access_prop(access_conditions)
    if acc is not None:
        props["Access conditions"] = acc
    return props
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_capture_fields.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS. (Watch for any *other* test that asserted a bare `{"Duration min": N}` output from a caller — if `test_capture_generate.py` / `test_memory_pass.py` had one, it is updated in Tasks 3–4; if the full suite flags one here, note it and fix it in the owning task.)

- [ ] **Step 6: Commit**

```bash
git add scripts/capture_fields.py tests/test_capture_fields.py
git commit -m "feat(capture): provenance-aware durations — label stated vs estimated in the shared seam"
```

---

### Task 3: Estimate a duration at capture time when June is silent

**What this gives you:** when June adds a task without saying how long it takes, the overlay's capture engine now asks the model for an honest estimate (using her priors + the task's project) and writes it labeled `estimated` — instead of leaving it blank so the scheduler falls back to a flat 30 minutes.

**Depends on:** Task 2 (`build_optional_props` must accept `duration_estimate_min` and `capture_fields.DURATION_PRIORS` must exist).

**Files:**
- Modify: `scripts/capture_generate.py` (the `_WEED_JSON_INSTRUCTION` schema block + trailing guidance; `parse_weed` defaults; `_creation_props`)
- Test: `tests/test_capture_generate.py`

**Interfaces:**
- Consumes: `capture_fields.DURATION_PRIORS`, `capture_fields.build_optional_props(..., duration_estimate_min=...)` (Task 2).
- Produces: a weed-turn item dict may now carry `"duration_estimate_min": <int>|null` **separately from** `"duration_min"` (stated). `_creation_props` passes both to the seam; the seam prefers stated.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_capture_generate.py`, after `test_capture_creates_links_and_skips`:

```python
def test_capture_writes_estimated_duration_labeled(tmp_path, monkeypatch):
    # June stated no duration; the model estimated one. It lands labeled 'estimated'.
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Study Python", "link": "P1", "status": "Ready",
             "duration_min": None, "duration_estimate_min": 90,
             "action": "create", "reasoning": "learning block"},
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("study python")
    props = {name: p for (_t, name, p) in calls}["Study Python"]
    assert props["Duration min"] == 90
    assert props["Duration source"] == "estimated"


def test_capture_stated_duration_beats_estimate(tmp_path, monkeypatch):
    # June said 20; model also guessed 90. Her number wins and is labeled 'stated'.
    canned = json.dumps({"opening": "x", "capacity_read": None, "groups": [
        {"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Quick email to editor", "link": "P1", "status": "Ready",
             "duration_min": 20, "duration_estimate_min": 90,
             "action": "create", "reasoning": "she said 20"},
        ]},
    ]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("quick 20 min email to editor")
    props = {name: p for (_t, name, p) in calls}["Quick email to editor"]
    assert props["Duration min"] == 20
    assert props["Duration source"] == "stated"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_capture_generate.py::test_capture_writes_estimated_duration_labeled tests/test_capture_generate.py::test_capture_stated_duration_beats_estimate -v`
Expected: FAIL — `KeyError: 'Duration min'` on the estimate test (the estimate isn't read/written yet).

- [ ] **Step 3: Add `duration_estimate_min` to the JSON contract**

In `scripts/capture_generate.py`, in `_WEED_JSON_INSTRUCTION`, replace the existing `duration_min` line in the item schema:

```python
          "duration_min": <how many MINUTES this will take, as a number, ONLY if June said or clearly implied it ("a quick 15 min", "an hour"). null if she gave no signal — NEVER guess; a wrong guess is worse than leaving it unset.>,
```

with **both** fields (stated stays fidelity-only; estimate is new and always attempted for a Task):

```python
          "duration_min": <MINUTES, as a number, ONLY if June STATED or clearly implied it ("a quick 15 min", "an hour"). null if she gave no duration signal. This is her word — never put a guess here.>,
          "duration_estimate_min": <YOUR best-guess MINUTES for how long this Task actually takes, for EVERY Task, using the DURATION PRIORS below plus the task's linked project as context. This is a separate field from duration_min on purpose: duration_min is what June said; this is what you estimate. Give a real number, not null, unless the task is genuinely too vague to size (Needs Clarifying) — a rough honest estimate beats the flat 30-minute fallback every unsized Task currently gets. null for non-Task types.>,
```

Then, in the trailing guidance block of `_WEED_JSON_INSTRUCTION`, replace the closing paragraph that begins ``` `capacity_read` may be null...``` with a version that injects June's priors. **Import the shared priors** — at the top of `_WEED_JSON_INSTRUCTION`'s construction this is a plain string, so build it with the constant. Concretely, change the module so the instruction embeds `capture_fields.DURATION_PRIORS`:

Replace the final triple-quoted tail of `_WEED_JSON_INSTRUCTION` (the paragraph starting ``` `capacity_read` may be null if no signal is present.```) with:

```python
`capacity_read` may be null if no signal is present. `status` applies to Tasks (default "Ready";
"Needs Clarifying" if too vague to act on). `duration_min` is June's STATED time (null unless she
said one); `duration_estimate_min` is YOUR estimate for a Task and should be filled for every
sizable Task. Keep every `reasoning` present — the system must be able to show June why each thing
landed where it did.

## DURATION PRIORS — use these to estimate `duration_estimate_min`

""" + capture_fields.DURATION_PRIORS + """
"""
```

(Structure `_WEED_JSON_INSTRUCTION` as string concatenation so `capture_fields.DURATION_PRIORS` is spliced in — `capture_fields` is already imported at the top of `capture_generate.py`. If `_WEED_JSON_INSTRUCTION` is currently one triple-quoted literal, split it into `"""...front..."""` + `capture_fields.DURATION_PRIORS` + `"""...back..."""` accordingly.)

- [ ] **Step 4: Default the new field in `parse_weed`**

In `parse_weed`, in the per-item `setdefault` loop, add the new field alongside the existing ones:

```python
            item.setdefault("duration_min", None)
            item.setdefault("duration_estimate_min", None)
            item.setdefault("affect", "")
            item.setdefault("blocked_on", "")
            item.setdefault("access_conditions", [])
```

- [ ] **Step 5: Pass the estimate through `_creation_props`**

In `_creation_props`, in the `props.update(capture_fields.build_optional_props(...))` call, add the estimate argument:

```python
    props.update(capture_fields.build_optional_props(
        duration_min=item.get("duration_min"),
        duration_estimate_min=item.get("duration_estimate_min"),
        affect=item.get("affect"),
        blocked_on=item.get("blocked_on"),
        access_conditions=item.get("access_conditions"),
    ))
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_capture_generate.py -v`
Expected: all PASS, including the two new tests. (If any *pre-existing* capture test asserted a bare `{"Duration min": N}` without `Duration source`, update it to include `"Duration source": "stated"` — that is a correct consequence of Task 2, not a regression.)

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 8: Verify live — real backend produces sensible estimates, then clean up**

Mocked tests prove the wiring; they don't prove the real model estimates sensibly. Run for real (creates a real object in June's live space):

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import capture_generate as cg
print(cg.capture('study python for a while'))
"
```

Then read the created Task's `Duration min` and `Duration source` directly:

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import gsdo_anytype as g
sid = g.get_space_id()
for o in g.fetch_all_objects(sid):
    if o.get('type', {}).get('key') == 'task' and o.get('name') == 'Study python for a while' or (o.get('name','').lower().startswith('study python')):
        pbn = {p.get('name'): p for p in o.get('properties', [])}
        dur = (pbn.get('Duration min') or {}).get('number')
        src = ((pbn.get('Duration source') or {}).get('select') or {}).get('name')
        print(o['id'], '| Duration min:', dur, '| source:', src)
"
```

Expected: a duration clearly larger than 30 (June's "1-2 hours" prior for a study block, so ~60-120), labeled `estimated` — **not** blank, **not** the flat 30. **Then delete the test object** (Anytype app, or `gsdo_anytype`'s delete path) — dev runs never leave artifacts in her real space.

- [ ] **Step 9: Commit**

```bash
git add scripts/capture_generate.py tests/test_capture_generate.py
git commit -m "feat(capture): estimate a labeled duration when June states none, using her priors"
```

---

### Task 4: Keep the memory-pass write path in step with the seam

**What this gives you:** the *other* write path that shares `capture_fields` (the memory→Anytype pass) can't silently diverge — it passes the same new field through, so a Task created from a memory entry gets the same duration treatment.

**Why it's small:** `memory_pass.apply_candidate` already calls `build_optional_props(duration_min=candidate.get("duration_min"), ...)`. With Task 2's signature change it keeps working untouched (new kwarg defaults to `None`), but to actually *use* the new capability it must forward `duration_estimate_min`. This task is that one-line forward plus its regression test. (Teaching the memory-pass *prompt* to estimate is explicitly **not** in scope — memory entries rarely describe task durations, and the shared seam is the divergence risk this task closes; the prompt change, if ever wanted, is a follow-up.)

**Files:**
- Modify: `scripts/memory_pass.py` (`apply_candidate`)
- Test: `tests/test_memory_pass.py`

**Interfaces:**
- Consumes: `capture_fields.build_optional_props(..., duration_estimate_min=...)` (Task 2).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_memory_pass.py` (match the file's existing stubbing pattern — inspect how it currently stubs `gsdo_objects.create` and `_get_object`; mirror that. Skeleton):

```python
def test_apply_candidate_forwards_estimated_duration(monkeypatch):
    created = {}

    def fake_create(type_name, name, body=None, properties=None):
        created["props"] = properties or {}
        return "oid-1"
    monkeypatch.setattr(mp.gsdo_objects, "create", fake_create)
    monkeypatch.setattr(mp.gsdo_objects, "find_existing", lambda *a, **k: None)
    monkeypatch.setattr(mp.g, "find_type", lambda name: {"key": "task", "name": "Task"})
    monkeypatch.setattr(mp, "_get_object", lambda oid: {"name": "Draft the SSRC narrative"})
    monkeypatch.setattr(mp, "_resolve_link", lambda t, l: (None, None))

    mp.apply_candidate({
        "proposed_name": "Draft the SSRC narrative", "proposed_type": "Task",
        "belongs_in_anytype": True, "duration_estimate_min": 120,
    })
    assert created["props"]["Duration min"] == 120
    assert created["props"]["Duration source"] == "estimated"
```

(Adjust the monkeypatch targets to whatever names `tests/test_memory_pass.py` already uses — read the file first; the point is: a candidate carrying `duration_estimate_min` results in a labeled estimated duration in the created props.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_memory_pass.py::test_apply_candidate_forwards_estimated_duration -v`
Expected: FAIL — `KeyError: 'Duration min'` (the estimate isn't forwarded yet).

- [ ] **Step 3: Forward the field in `apply_candidate`**

In `scripts/memory_pass.py`, in `apply_candidate`, in the `props.update(capture_fields.build_optional_props(...))` call, add the estimate argument:

```python
    props.update(capture_fields.build_optional_props(
        duration_min=candidate.get("duration_min"),
        duration_estimate_min=candidate.get("duration_estimate_min"),
        affect=candidate.get("affect"),
        blocked_on=candidate.get("blocked_on"),
        access_conditions=candidate.get("access_conditions"),
    ))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_memory_pass.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/memory_pass.py tests/test_memory_pass.py
git commit -m "feat(memory-pass): forward estimated duration through the shared seam (no divergence)"
```

---

### Task 5: `duration_backfill.py` — reviewable backfill of the ~135 duration-less tasks

**What this gives you:** a script that finds every existing task with no duration, asks the model to estimate each (using June's priors + the task's project), shows you the whole list to skim, and — only on `--run` — writes those labeled `estimated` durations back with read-back. It never touches a task that already has a duration, so it's safe to run repeatedly and never overwrites anything June stated.

**Depends on:** Tasks 1 + 2 (the `Duration source` property must exist; the seam must label estimates).

**Files:**
- Create: `scripts/duration_backfill.py`
- Test: `tests/test_duration_backfill.py`

**Interfaces:**
- Produces:
  - `load_sizeless_tasks(sid=None) -> list[{"id","name","status","duration_min","project_names":[...] ,"context"}]` — every Task whose `Duration min` is absent. (Skips tasks that already have any `Duration min`, stated or estimated → idempotent by construction.)
  - `build_prompt(tasks) -> str` — embeds `capture_fields.DURATION_PRIORS` + a per-task line with name/status/project, asks for a JSON array of `{"id","estimated_min","reasoning"}`.
  - `parse_estimates(model_text) -> list[dict]` — extracts the fenced ```json``` array (same shape discipline as `memory_pass._parse_candidates`; raises if absent/unparseable).
  - `preview(sid=None, backend=None) -> {"tasks":[...], "estimates":[...], "by_id":{...}}` — LLM step, no writes.
  - `format_preview(preview) -> str` — grouped by project, `task → ~N min — reasoning`.
  - `apply(preview) -> {"updated":int,"failed":int,"skipped_no_estimate":int}` — for each estimate, `gsdo_objects.update(id, properties=capture_fields.build_optional_props(duration_estimate_min=est))`, then read back and confirm `Duration source == "estimated"`. Skips any task that gained a `Duration min` since the preview (re-fetch guards against a race / a stale preview).
- Consumes: `capture_fields.DURATION_PRIORS` / `build_optional_props`; `plan_generate.generate`; `gsdo_anytype` / `gsdo_objects`; `generation_log`.
- CLI: `--dry-run` (default; no LLM, no writes — lists sizeless tasks + counts), `--preview` (LLM, shows what `--run` would do, writes nothing, repeatable), `--run` (writes with read-back), `--backend` (override `CD_BACKEND`). Mirrors `memory_pass.py` / `status_check.py` flag discipline exactly. `--run` and `--preview` are mutually exclusive.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_duration_backfill.py`:

```python
"""Tests for duration_backfill — estimate + label durations onto existing duration-less tasks.
The LLM seam and Anytype are always mocked; nothing here calls a model or touches the live space."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import duration_backfill as db


def _task(oid, name, dur=None, status="Ready"):
    props = [{"key": "gsdo_task_status", "select": {"name": status}}]
    if dur is not None:
        props.append({"key": "gsdo_duration_min", "number": dur})
    return {"id": oid, "type": {"key": "task"}, "name": name, "properties": props}


def test_load_sizeless_tasks_excludes_tasks_with_a_duration(monkeypatch):
    monkeypatch.setattr(db.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(db.g, "fetch_all_objects", lambda sid: [
        _task("t1", "Study Python"),                 # no duration -> included
        _task("t2", "Call pharmacy", dur=15),        # already sized -> excluded
        {"id": "g1", "type": {"key": "gsdo_goal"}, "name": "A goal", "properties": []},
    ])
    tasks = db.load_sizeless_tasks(sid="sid")
    assert [t["id"] for t in tasks] == ["t1"]


def test_parse_estimates_reads_json_array():
    text = "```json\n" + json.dumps([{"id": "t1", "estimated_min": 90, "reasoning": "study block"}]) + "\n```"
    ests = db.parse_estimates(text)
    assert ests[0]["id"] == "t1" and ests[0]["estimated_min"] == 90


def test_parse_estimates_raises_without_block():
    import pytest
    with pytest.raises(RuntimeError):
        db.parse_estimates("no json here")


def test_apply_writes_labeled_estimate_and_reads_back(monkeypatch):
    monkeypatch.setattr(db.g, "get_space_id", lambda: "sid")
    updated = {}

    def fake_update(oid, name=None, properties=None):
        updated[oid] = properties or {}
        return oid
    monkeypatch.setattr(db.gsdo_objects, "update", fake_update)
    # read-back returns the value we just wrote, labeled estimated
    monkeypatch.setattr(db, "_get_task", lambda oid: {
        "id": oid, "properties": [
            {"key": "gsdo_duration_min", "number": 90},
            {"key": db._DURATION_SOURCE_KEY, "select": {"name": "estimated"}}]})

    preview = {"tasks": [_task("t1", "Study Python")],
               "estimates": [{"id": "t1", "estimated_min": 90, "reasoning": "x"}],
               "by_id": {"t1": _task("t1", "Study Python")}}
    result = db.apply(preview)
    assert result["updated"] == 1
    assert updated["t1"]["Duration min"] == 90
    assert updated["t1"]["Duration source"] == "estimated"


def test_apply_skips_task_that_gained_a_duration_since_preview(monkeypatch):
    monkeypatch.setattr(db.g, "get_space_id", lambda: "sid")
    monkeypatch.setattr(db.gsdo_objects, "update",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not write")))
    # by the time apply runs, t1 already has a stated duration -> never overwrite
    monkeypatch.setattr(db, "_get_task", lambda oid: _task("t1", "Study Python", dur=20))
    preview = {"tasks": [_task("t1", "Study Python")],
               "estimates": [{"id": "t1", "estimated_min": 90, "reasoning": "x"}],
               "by_id": {"t1": _task("t1", "Study Python")}}
    result = db.apply(preview)
    assert result["updated"] == 0 and result["skipped_no_estimate"] >= 0
```

> **Reader:** `_get_task` and `_DURATION_SOURCE_KEY` are helpers you define in Step 3. `_DURATION_SOURCE_KEY` is resolved *once at runtime* from the live property (Anytype-generated key), never hardcoded — the test monkeypatches around it, so its literal value doesn't matter to the test.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_duration_backfill.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'duration_backfill'`.

- [ ] **Step 3: Write `scripts/duration_backfill.py`**

```python
#!/usr/bin/env python3
"""Backfill estimated, LABELED durations onto existing tasks that carry none.

Why: scheduler.py falls back to a flat DEFAULT_DURATION_MIN=30 for any task with no Duration min,
and today almost every task hits that fallback — so the daily plan treats a 2-hour study block and
a 5-minute call identically. This fills the silence: for each task with no duration, the model
estimates one (using June's stated priors + the task's project), and it's written labeled
'estimated' (Duration source) — never confused with a duration June herself stated, and never
overwriting one. Fidelity-first: a task that already has ANY Duration min is skipped entirely.

Flag discipline mirrors memory_pass.py / status_check.py exactly:
  python3 scripts/duration_backfill.py            dry-run: list sizeless tasks + counts, no LLM
  python3 scripts/duration_backfill.py --preview  LLM estimates, shows what --run would do, no writes
  python3 scripts/duration_backfill.py --run       the real backfill (writes, with read-back)

Idempotent by construction: only sizeless tasks are selected, so once --run gives a task a
duration it drops out of the next run's candidate set. Re-running --preview is side-effect-free.

Reuses, never reinvents: capture_fields (the shared duration seam + June's priors),
plan_generate.generate (the LLM seam), gsdo_objects.update (deterministic write, read-back
proven), generation_log (durable generation record).
"""
import sys, os, re, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsdo_anytype as g
import gsdo_objects
import plan_generate
import generation_log
import capture_fields
from anytype_test import call


def _pv(obj, key, field):
    for p in obj.get("properties", []):
        if p.get("key") == key:
            return p.get(field)
    return None


def _project_id_to_name(objs):
    return {o["id"]: o.get("name") for o in objs
            if o.get("type", {}).get("key") == "gsdo_project"}


def load_sizeless_tasks(sid=None):
    """Every Task with NO Duration min (stated or estimated). Skips already-sized tasks so the
    backfill only ever fills silence and re-runs are idempotent. Carries project names + Context
    so the estimator has the same context the capture path gets."""
    sid = sid or g.get_space_id()
    objs = g.fetch_all_objects(sid)
    p_id2name = _project_id_to_name(objs)
    out = []
    for o in objs:
        if o.get("type", {}).get("key") != "task":
            continue
        if _pv(o, "gsdo_duration_min", "number") is not None:
            continue  # already sized — never touch
        status = (_pv(o, "gsdo_task_status", "select") or {}).get("name")
        linked = _pv(o, "linked_projects", "objects") or []
        names = []
        for x in linked:
            pid = x.get("id") if isinstance(x, dict) else x
            nm = p_id2name.get(pid)
            if nm:
                names.append(nm)
        out.append({"id": o["id"], "name": o.get("name"), "status": status,
                    "duration_min": None, "project_names": names,
                    "context": _pv(o, "gsdo_context", "text")})
    return out


def build_prompt(tasks):
    lines = [
        "You are estimating how long each of June's existing tasks actually takes, in MINUTES.",
        "These tasks were captured with no duration, so her daily plan currently treats every one",
        "as a flat 30 minutes — wildly wrong. Give each an honest estimate.",
        "",
        "## DURATION PRIORS",
        "",
        capture_fields.DURATION_PRIORS,
        "",
        "## TASKS TO ESTIMATE",
        "",
    ]
    for t in tasks:
        proj = ", ".join(t["project_names"]) if t["project_names"] else "(no project)"
        ctx = f" | context: {t['context']}" if t.get("context") else ""
        lines.append(f"- id={t['id']} | name: {t['name']} | project: {proj} | status: {t['status']}{ctx}")
    lines += [
        "",
        "## OUTPUT — one fenced ```json block, nothing else",
        "A JSON array, one object per task you can size:",
        '```json',
        '[{"id": "<the id copied exactly>", "estimated_min": <minutes, integer>, '
        '"reasoning": "<one short phrase: why this long>"}]',
        '```',
        "Copy each id EXACTLY. Omit a task only if it is genuinely too vague to size.",
    ]
    return "\n".join(lines)


def parse_estimates(model_text):
    """Extract the estimates array from the model's fenced ```json block. Raises if absent or
    unparseable — a run that produced nothing usable is a failure surfaced, never silent."""
    blocks = re.findall(r"```json\s*(.*?)\s*```", model_text, re.DOTALL)
    if not blocks:
        raise RuntimeError("model output had no ```json block — cannot backfill durations")
    try:
        parsed = json.loads(blocks[-1].strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"model's JSON block did not parse: {e}")
    if not isinstance(parsed, list):
        raise RuntimeError(f"model's JSON block was not a list (got {type(parsed).__name__})")
    return [c for c in parsed if isinstance(c, dict) and c.get("id")]


def preview(sid=None, backend=None):
    """Estimate every sizeless task WITHOUT writing anything. Repeatable, side-effect-free."""
    sid = sid or g.get_space_id()
    tasks = load_sizeless_tasks(sid=sid)
    if not tasks:
        return {"tasks": [], "estimates": [], "by_id": {}}
    prompt = build_prompt(tasks)
    backend_name = backend or os.environ.get("CD_BACKEND", "mistral")
    model = plan_generate._active_model(backend_name)
    backend_label = f"{backend_name}/{model}" if model else backend_name
    t0 = time.monotonic()
    try:
        model_text = plan_generate.generate(prompt, backend=backend)
        estimates = parse_estimates(model_text)
    except Exception as e:
        generation_log.log_generation(
            backend=backend_label, duration_s=time.monotonic() - t0,
            success=False, source="duration_backfill",
            error_type=type(e).__name__, error_msg=str(e))
        raise
    generation_log.log_generation(
        backend=backend_label, duration_s=time.monotonic() - t0,
        success=True, source="duration_backfill",
        structural={"n_tasks": len(tasks), "n_estimates": len(estimates)})
    return {"tasks": tasks, "estimates": estimates,
            "by_id": {t["id"]: t for t in tasks}}


def format_preview(prev):
    tasks, estimates, by_id = prev["tasks"], prev["estimates"], prev["by_id"]
    est_by_id = {e["id"]: e for e in estimates}
    if not tasks:
        return "No duration-less tasks found — nothing to backfill."
    # group by first project name
    groups = {}
    for t in tasks:
        proj = t["project_names"][0] if t["project_names"] else "(no project)"
        groups.setdefault(proj, []).append(t)
    lines = [f"{len(tasks)} duration-less task(s); {len(estimates)} estimated, "
             f"{len(tasks) - len(est_by_id)} left unsized.", ""]
    for proj in sorted(groups):
        lines.append(f"### {proj}")
        for t in groups[proj]:
            e = est_by_id.get(t["id"])
            if e:
                lines.append(f"  - {t['name']}  ~{e.get('estimated_min')} min  — {e.get('reasoning','')}")
            else:
                lines.append(f"  - {t['name']}  (no estimate — too vague to size)")
        lines.append("")
    return "\n".join(lines)


# --- writing (--run only) ----------------------------------------------------

def _duration_source_key():
    """Resolve the Anytype-generated key for 'Duration source' once, by display name (never
    hardcoded — same convention as Engagement/Side)."""
    p = g.find_property("Duration source")
    if p is None:
        raise RuntimeError("'Duration source' property not found — run build_task/build_model first")
    return p.get("key")


_DURATION_SOURCE_KEY = None  # lazily resolved in apply(); module-level so tests can monkeypatch


def _get_task(oid):
    sid = g.get_space_id()
    st, b = call("GET", f"/spaces/{sid}/objects/{oid}")
    if st != 200 or not isinstance(b, dict) or "object" not in b:
        raise RuntimeError(f"read-back failed for {oid!r}: {st} {b}")
    return b["object"]


def apply(prev):
    """Write each estimate as a labeled 'estimated' Duration min, read-back proven. Re-fetches
    each task first and skips any that gained a duration since the preview (fidelity: never
    overwrite a value that appeared in the meantime). One task's failure never aborts the rest."""
    global _DURATION_SOURCE_KEY
    if _DURATION_SOURCE_KEY is None:
        _DURATION_SOURCE_KEY = _duration_source_key()
    est_by_id = {e["id"]: e for e in prev["estimates"]}
    result = {"updated": 0, "failed": 0, "skipped_no_estimate": 0}
    for tid, t in prev["by_id"].items():
        e = est_by_id.get(tid)
        if not e:
            result["skipped_no_estimate"] += 1
            continue
        try:
            live = _get_task(tid)
            if _pv(live, "gsdo_duration_min", "number") is not None:
                # gained a duration since preview — never overwrite
                result["skipped_no_estimate"] += 1
                continue
            props = capture_fields.build_optional_props(duration_estimate_min=e.get("estimated_min"))
            if "Duration min" not in props:
                result["skipped_no_estimate"] += 1
                continue
            gsdo_objects.update(tid, properties=props)
            back = _get_task(tid)
            got = _pv(back, "gsdo_duration_min", "number")
            src = (_pv(back, _DURATION_SOURCE_KEY, "select") or {}).get("name")
            if got != props["Duration min"] or src != "estimated":
                raise RuntimeError(f"read-back mismatch for {tid!r}: dur={got} src={src}")
            result["updated"] += 1
        except Exception as ex:
            result["failed"] += 1
            generation_log.log_generation(
                backend="duration_backfill", duration_s=0.0, success=False,
                source="duration_backfill", error_type=type(ex).__name__, error_msg=str(ex))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Backfill estimated durations onto duration-less tasks")
    ap.add_argument("--preview", action="store_true",
                     help="LLM estimates + show what --run would do; writes NOTHING (repeatable)")
    ap.add_argument("--run", action="store_true",
                     help="actually write the estimated durations (with read-back)")
    ap.add_argument("--backend", default=None, help="override CD_BACKEND for this run")
    args = ap.parse_args()
    if args.run and args.preview:
        print("--run and --preview are mutually exclusive", file=sys.stderr); sys.exit(1)

    if args.preview:
        print(format_preview(preview(backend=args.backend)))
    elif args.run:
        prev = preview(backend=args.backend)
        print(format_preview(prev))
        print("\n--- applying ---")
        print(json.dumps(apply(prev), indent=2))
    else:
        tasks = load_sizeless_tasks()
        print(f"duration-less tasks: {len(tasks)}")
        for t in tasks:
            proj = ", ".join(t["project_names"]) or "(no project)"
            print(f"  - {t['name']}  [{t['status']}]  project: {proj}")
        print("\nRun --preview to see estimates, --run to write them.")
```

> **Reader — one seam detail:** `plan_generate.generate(prompt, backend=backend)` — confirm `generate` accepts a `backend=` kwarg (it does in `memory_pass.generate_candidates`). If the installed signature differs, match `memory_pass.py`'s call exactly.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_duration_backfill.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS.

- [ ] **Step 6: Verify live — dry-run + preview against the real space (read-only, no writes)**

```bash
python3 scripts/duration_backfill.py            # dry-run: counts + list, no LLM, no writes
python3 scripts/duration_backfill.py --preview  # real LLM estimates; writes NOTHING
```

Confirm: the dry-run count is in the expected range (~130+ duration-less tasks); the `--preview` output reads as a coherent grouped list where study/writing/application tasks skew toward 60-120+ min and quick actions stay small — i.e. the priors are actually shaping estimates, not a flat number. **Both are read-only; nothing to revert.** (Do **not** run `--run` here — that is June's call, gated on her skim of this preview per OQ2.)

- [ ] **Step 7: Commit**

```bash
git add scripts/duration_backfill.py tests/test_duration_backfill.py
git commit -m "feat(duration): reviewable backfill of estimated labeled durations (dry-run/preview/run)"
```

---

### Task 6: Integration, end-to-end verification, and cross-family review

**This is the required final task.** The pieces above pass their own unit tests; this task proves the feature is *wired into the running system and observed working end-to-end*, then runs the non-Claude review.

**Where it wires in (the real call sites — nothing new to connect, name them explicitly):**
- **Capture path:** `scripts/server.py`'s async capture worker → `capture_generate.capture()` → `_creation_props` → `capture_fields.build_optional_props` → `gsdo_objects.create`. The estimate now flows through the existing overlay Add-tab path; no new wiring, the seam is the connection.
- **Read path (proof the estimate is *used*):** `scripts/daily_plan.py:129` reads `gsdo_duration_min` into each task's `duration_min`; `scripts/scheduler.py:_dur` uses it and only falls back to 30 when absent. An estimated duration is a present `Duration min`, so the scheduler consumes it with no change. This is the whole point — verify it actually happens.
- **Backfill path:** `scripts/duration_backfill.py` (standalone CLI; its home is June's manual `--run` after skimming `--preview`).

- [ ] **Step 1: End-to-end live check — capture without a stated duration, all the way to the scheduler**

Drive the real flow (this creates one real object; it is deleted in Step 2):

```bash
python3 -c "
import sys, datetime as dt; sys.path.insert(0, 'scripts')
import capture_generate as cg, gsdo_anytype as g, scheduler

# 1) Capture a task with NO stated duration -> an estimate should land, labeled.
res = cg.capture('spend some time applying for jobs')   # job-application: should skew LONG
print('capture result summary:', res['result_summary'])

# 2) Find it and read Duration min + Duration source back from the live space.
sid = g.get_space_id()
def pv(o, key, field):
    for p in o.get('properties', []):
        if p.get('key') == key: return p.get(field)
    return None
match = None
for o in g.fetch_all_objects(sid):
    if o.get('type', {}).get('key') == 'task' and 'applying for jobs' in (o.get('name','').lower()):
        match = o
print('OBJECT ID:', match and match['id'])
dur = pv(match, 'gsdo_duration_min', 'number')
src_p = pv(match, g.find_property('Duration source')['key'], 'select') or {}
print('Duration min:', dur, '| Duration source:', src_p.get('name'))

# 3) Prove the scheduler USES it (not the flat 30 fallback).
placed = scheduler.schedule(
    [{'name': match['name'], 'duration_min': dur, 'fixed_time': None}],
    start=dt.datetime(2026,7,12,9,0))
mins = int((placed[0]['end_time'] - placed[0]['start_time']).total_seconds() // 60)
print('scheduler block length (min):', mins)
assert src_p.get('name') == 'estimated', 'estimate not labeled'
assert dur and dur > 30, 'job-application estimate did not exceed the flat 30'
assert mins == dur, 'scheduler did not use the estimated duration'
print('PASS: estimated + labeled + scheduler used it')
"
```

Expected observations: a `Duration min` well above 30 (June's prior: focused-attention job work runs long), `Duration source = estimated`, and a scheduler block whose length equals that estimate — not 30. If the block length is 30, the scheduler is still hitting the fallback and the wiring is broken — investigate before proceeding.

- [ ] **Step 2: Delete the test object**

Delete the object created in Step 1 (print its `OBJECT ID` above; remove via the Anytype app or `gsdo_anytype`'s delete path). Confirm it's gone with a re-fetch. **No dev artifact may remain in June's real space.**

- [ ] **Step 3: Full suite, final**

Run: `python3 -m pytest tests/ -q`
Expected: all PASS. Re-run `python3 -m pytest tests/ --collect-only -q | tail -1` first to get the real current baseline; confirm the final count is baseline + the tests this plan added (Task 1: 1, Task 2: 6, Task 3: 2, Task 4: 1, Task 5: 5 = 15 new), not fewer.

- [ ] **Step 4: Cross-family code review — chunked per file, ~8k-token cap, file + its tests together**

Per repo CLAUDE.md, this is Claude-generated code touching June's live data, so it gets a genuine cross-*family* review (not a same-family Claude reviewer). Use the GitHub Models reviewer:

```bash
python3 ~/.claude/skills/requesting-code-review/github_models_review.py <files...>
```

Send these chunks (each stays under ~8k tokens; each pairs the changed source with its tests):
1. `scripts/capture_fields.py` + `tests/test_capture_fields.py` (the seam — the highest-value review: fidelity precedence + guard #3 live here)
2. `scripts/capture_generate.py` + `tests/test_capture_generate.py` (contract change: stated-vs-estimate separation)
3. `scripts/duration_backfill.py` + `tests/test_duration_backfill.py` (the new write tool: idempotency + read-back + never-overwrite)
4. `scripts/build_task.py` + `scripts/memory_pass.py` (schema add + seam forward — both small; group them)

For each returned finding: evaluate against intent before acting (a deviation may be an insight). Fix real issues; note any deliberate divergences. Specifically ask the reviewer to check: (a) can an estimate ever overwrite a stated duration? (it must not); (b) is a stated `N` always distinguishable from an estimated `N` at read time?; (c) is the backfill truly idempotent and re-run-safe?

- [ ] **Step 5: Final commit (review fixes, if any)**

```bash
git add -A
git commit -m "chore(duration): apply cross-family review fixes for duration intelligence"
```

---

## Self-Review (run before handoff)

**1. Spec coverage:**
- LLM pointed at duration estimates → Task 3 (capture) + Task 5 (backfill). ✓
- Estimates labeled/distinguishable from stated → Task 1 (`Duration source` property) + Task 2 (seam labels). ✓
- Fidelity-first (stated never overridden) → Task 2 precedence + Task 5 never-overwrite re-fetch. ✓
- June's priors + project context in the prompt → `capture_fields.DURATION_PRIORS` (Task 2), used by Tasks 3 + 5. ✓
- Backfill propose-then-apply with reviewable preview, mirroring memory-pass flags → Task 5 (`--dry-run`/`--preview`/`--run`). ✓
- Don't touch selection logic; scheduler `get_duration` is the seam → nothing changes scheduler code; the estimate simply makes `Duration min` present. ✓
- Reuse learning-loops-v1 duration work, don't re-implement → Reconciliation section (absorbs Task 1, depends-on/enables Task 4). ✓
- Split-across-blocks scope call → OQ3 (deferred, named home). ✓
- Tests self-clean, stdlib only, per-task commits → Global Constraints + each task. ✓
- Final task: live end-to-end + cross-family review chunked per file → Task 6. ✓

**2. Placeholder scan:** no TBD/TODO/"handle edge cases" — each code step shows the code; each test shows the assertions. ✓

**3. Type consistency:** `build_optional_props(duration_min=, duration_estimate_min=, ...)` signature is identical across Tasks 2, 3, 4, 5. `Duration source` display name consistent throughout; its live key is read by display-name lookup (never hardcoded), matching the Engagement/Side convention. `_pv(obj, key, field)` used consistently in `duration_backfill.py` and the Task 6 check. ✓

## Execution Handoff

Plan complete, saved to `docs/superpowers/plans/2026-07-12-duration-intelligence.md`. Execution is subagent-driven-development (fresh subagent per task, per-task review, final whole-branch review), per this project's established default. **Before executing, get June's read on the three open questions at the top** — the plan is built against the recommended defaults, so a "yes, defaults are fine" unblocks it entirely; a flip on OQ1 changes Tasks 1–2 only, a flip on OQ2 changes Task 5's CLI gate only, and OQ3 is already deferred.

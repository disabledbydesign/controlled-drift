# Capture-side engagement proposal + Sprint/Hyperfixation cleanup — Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per
> task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps
> use checkbox (`- [ ]`) syntax. **Subagents WRITE files but CANNOT run Bash — the main agent runs every
> test / read-back / migration / `verify` gate.** Bash-only steps are marked **(main agent, Bash)**.
> Line anchors are from live HEAD `b6330e9` (2026-07-16); re-derive each at its live line before editing.

**Goal:** When June captures a new Project, the weeding LLM reads her words and proposes its
`Engagement` — **Steady / Open / Backburner**, default **Open** — instead of the blind hardcoded
`Steady` every new Project gets today; it also fills `Engagement notes` from the situated specifics she
speaks (deadline, cadence, intensity). And separately: remove the retired **Sprint** and
**Hyperfixation** values from the engagement data structure, migrating any live project off them first.

**Architecture:** Two independent work streams on non-overlapping files. **Stream A (the proposal)**
extends the existing shared, network-free field builder (`capture_fields.py`) with a Project-engagement
validator — the *single* place the default-Open and the coarse-three validation live, so both write
paths (capture, memory-pass) inherit it and can't diverge; the weeding + memory-pass contracts gain a
per-Project `engagement`/`engagement_notes`; `gsdt_bind` asks dialogically. **There is deliberately NO
born-Open chokepoint** in `gsdo_objects` — the post-seam loader already treats a blank engagement as
"Open" (`daily_plan.py:390`, `eng = p.get("engagement") or "Open"`), so the default belongs in the
proposal layer, not a low-level writer (June, 2026-07-16). **Stream B (the cleanup)** is a delegated
sweep: retire `Sprint`/`Hyperfixation` from `build_project.py`'s select and from every "active cohort"
definition that hardcodes them (`neglect.py`, `daily_plan.py`, `orient_map.py`), migrate any live
project still tagged with them (June confirms per project), then delete the two tags.

**Tech Stack:** Python 3 stdlib only (`python3`, never `python`); existing modules `capture_fields`,
`capture_generate`, `memory_pass`, `gsdt_bind`, `gsdo_objects`, `gsdo_anytype`, `build_project`,
`neglect`, `daily_plan`, `orient_map`; the prompts `weeding_gate.md` / `daily_memory_pass.md`; pytest
with the repo `conftest.py` sandbox redirect. No new dependencies.

## Global Constraints

- **`python3`, not `python`.** Suite: `python3 -m pytest -q` from repo root.
- **The reconciled engagement set is coarse.** The proposal writes **only** `Steady / Open / Backburner`
  (`docs/spec_reconciliation_selection_2026-07-11.md`). `Sprint` and `Hyperfixation` are **retired** from
  `engagement` (Sprint → a Focus Period foreground action; Hyperfixation → routed through the qualitative
  `engagement_notes` / `affective` free-text). `Done` is never a birth value. Neutral / no-signal → `Open`.
- **`gsdo_objects.create`/`update` take DISPLAY names** (`"Engagement"`, `"Engagement notes"`), resolving
  select values by option name. Never pass a property key or tag id.
- **Read select fields by DISPLAY name, not key** (`daily_plan.py:97-98` reads `"Engagement"` by name
  because the Anytype key is generated/unpredictable). Any read-back here follows that convention.
- **Idempotent writes; no silent failures — raise, don't `assert`; verify against the live space with
  read-back** after every write.
- **Anytype schema deletions are ASYNCHRONOUS (probe-confirmed 2026-07-16).** `DELETE` on a select-option
  tag (and on a property) returns `200` *before* the change propagates (~0.5–1s later). A delete read-back
  must **poll until the item actually disappears** (bounded, e.g. 10×0.5s) — never check once (false
  failure) and never trust the `200` alone (silent failure). Note `gsdo_anytype.find_property` also caches,
  so verify a deletion via a FRESH `GET /spaces/{sid}/properties` list, not `find_property`. Object
  *property* updates (`gsdo_objects.update`) remain synchronously read-back-verifiable as today — this
  async caveat is specific to schema tag/property deletion.
- **Tests self-clean — NEVER leave artifacts in June's real space.** Unit tests mock the LLM and Anytype;
  `tests/conftest.py` redirects data/config to a sandbox and *fails the suite* on any write to the real
  data dir. The end-to-end task (Task C) creates real objects and **deletes them in the same run**.
- **Additive / behavior-preserving except where named.** Every existing capture with no engagement signal
  must behave as before *except* that a new Project's born value is now the proposal (default `Open`)
  instead of the constant `Steady`. That is the one intended change on the create side.
- **One decision, one place.** `capture_fields.build_project_engagement_props` is the single validator +
  default; no other creation path re-implements the coarse-set check or the default.

## File Structure

**Stream A (the proposal) — owns these; Stream B never touches them:**
- `scripts/capture_fields.py` — NEW shared `build_project_engagement_props()` (validator + default-Open +
  notes). One source of truth for both write paths (Task A1).
- `scripts/capture_generate.py` — weeding JSON contract gains per-item `engagement`/`engagement_notes`;
  `parse_weed` defaults them; `_creation_props` Project branch writes via the shared builder, retiring the
  hardcoded `Steady` (Tasks A2, A3).
- `prompts/weeding_gate.md` — a real Project definition + an engagement-noticing line; and retire the
  stale prompt references to the removed values (the `Hyperfixation` check at `:7`, the `Sprint` in the
  Goal-engagement line at `:34`) so the gate speaks only the coarse set (Tasks A2, A3).
- `scripts/memory_pass.py` — `apply_candidate` writes a Project candidate's engagement via the same shared
  builder (Task A3).
- `prompts/daily_memory_pass.md` — an optional `engagement`/`engagement_notes` on a Project candidate
  (from the entry's own words) (Task A3).
- `scripts/gsdt_bind.py` — `init_binding` asks for engagement instead of hardcoding `Steady` (Task A4).
- Tests: `tests/test_engagement_proposal.py` (NEW), additions to `tests/test_capture_generate.py`,
  `tests/test_capture_fields.py`, `tests/test_memory_pass_fields.py`.

**Stream B (the cleanup) — owns these; Stream A never touches them:**
- `scripts/build_project.py` — remove `Sprint`/`Hyperfixation` from the `Engagement` select option list
  (`:25-26`) (Task B1).
- `scripts/neglect.py` — `_ACTIVE_ENGAGEMENT` (`:71`) and its comments (`:60-64, :196, :280`) (Task B1).
- `scripts/daily_plan.py` — the inline `active_engagement` set (`:527`) and its comment (`:520`) (Task B1).
- `scripts/orient_map.py` — the engagement→status mapping / docstring (`:29-32` + the real code it
  describes) (Task B1).
- `scripts/migrate_engagement_cleanup.py` — NEW. Surfaces live `Sprint`/`Hyperfixation` projects, proposes
  a per-project migration for June, writes + read-back on confirm, then deletes the two tags (Task B1).
- Tests: `tests/test_engagement_cleanup.py` (NEW), additions to `tests/test_neglect_active.py`.

---

## STREAM A — Capture-side engagement proposal

### Task A1: The shared engagement builder (validator + default-Open + notes)

**Files:**
- Modify: `scripts/capture_fields.py` — add `PROJECT_ENGAGEMENTS`, `_engagement_value`,
  `build_project_engagement_props` (after `build_optional_props`, `:86-110`).
- Test: `tests/test_capture_fields.py` (append; NEW file if absent).

**Interfaces:**
- Produces: `build_project_engagement_props(engagement=None, engagement_notes=None) -> dict` — always
  returns `{"Engagement": <Steady|Open|Backburner>}` (invalid/blank/retired/None → `"Open"`), plus
  `{"Engagement notes": <text>}` only when the notes validate as non-empty free text.

- [ ] **Step 1: Write the failing tests.**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import capture_fields as cf


def test_engagement_valid_value_kept():
    assert cf.build_project_engagement_props(engagement="Steady")["Engagement"] == "Steady"
    assert cf.build_project_engagement_props(engagement="Backburner")["Engagement"] == "Backburner"


def test_engagement_case_insensitive():
    assert cf.build_project_engagement_props(engagement="open")["Engagement"] == "Open"


def test_engagement_absent_or_invalid_defaults_open():
    assert cf.build_project_engagement_props(engagement=None)["Engagement"] == "Open"
    assert cf.build_project_engagement_props(engagement="")["Engagement"] == "Open"
    # retired values are NOT valid engagement anymore -> fall back to Open, never written through
    assert cf.build_project_engagement_props(engagement="Sprint")["Engagement"] == "Open"
    assert cf.build_project_engagement_props(engagement="Hyperfixation")["Engagement"] == "Open"


def test_engagement_notes_written_only_when_present():
    out = cf.build_project_engagement_props(engagement="Steady", engagement_notes="deadline Friday")
    assert out["Engagement notes"] == "deadline Friday"
    assert "Engagement notes" not in cf.build_project_engagement_props(engagement="Steady", engagement_notes="")
    # guard #3: a bare number is not valid free text
    assert "Engagement notes" not in cf.build_project_engagement_props(engagement="Steady", engagement_notes=3)
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_capture_fields.py -k engagement -v`
Expected: FAIL (`AttributeError: module 'capture_fields' has no attribute 'build_project_engagement_props'`).

- [ ] **Step 3: Implement** in `scripts/capture_fields.py`, after `build_optional_props` (`:110`):

```python
# The coarse, reconciled Project-engagement set (docs/spec_reconciliation_selection_2026-07-11.md):
# Steady = a normal daily move the system commits to the day; Open = available, shown gently, not
# pushed (the neutral default); Backburner = set aside, not in the plan unless a neglected obligation.
# Sprint/Hyperfixation are RETIRED from engagement (Sprint -> Focus Period foreground; Hyperfixation ->
# the qualitative Engagement-notes/Affective free text). Done is never a birth value.
PROJECT_ENGAGEMENTS = {"Steady", "Open", "Backburner"}
DEFAULT_ENGAGEMENT = "Open"


def _engagement_value(raw):
    """The proposed Project engagement, validated against the coarse set. Anything else — blank,
    None, a retired value (Sprint/Hyperfixation), a typo — becomes Open. This is the ONE place the
    default-Open lives (there is deliberately no born-Open chokepoint in gsdo_objects: the post-seam
    loader already reads a blank engagement as Open, so the default belongs here in the proposal)."""
    if isinstance(raw, str):
        v = raw.strip().capitalize()   # "backburner" -> "Backburner"; all three are single words
        if v in PROJECT_ENGAGEMENTS:
            return v
    return DEFAULT_ENGAGEMENT


def build_project_engagement_props(engagement=None, engagement_notes=None):
    """Project-only. The Engagement select (always written; default Open) plus the optional free-text
    Engagement notes (absent/invalid stays absent — the situated specifics the select can't hold:
    'deadline July 1', '~30 min daily', 'hyperfixating but stuck'). Both write paths call this so
    capture and the memory pass can never diverge on the default or the coarse-set validation."""
    props = {"Engagement": _engagement_value(engagement)}
    notes = _text_prop(engagement_notes)   # reuses the guard-#3 free-text validator above
    if notes is not None:
        props["Engagement notes"] = notes
    return props
```

- [ ] **Step 4: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_capture_fields.py -k engagement -v`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/capture_fields.py tests/test_capture_fields.py
git commit -m "feat(capture): shared Project-engagement builder (coarse set, default Open, notes)"
```

---

### Task A2: Weeding contract proposes per-Project engagement (+ a real Project definition)

**Files:**
- Modify: `scripts/capture_generate.py` — the `_WEED_JSON_INSTRUCTION` per-item object (`:169-183`), the
  schema note (`:190-194`), the Per-item prose bullet (`:145-153`), the `parse_weed` per-item default loop
  (`:265-271`).
- Modify: `prompts/weeding_gate.md` — add a Project definition to the type list (`:34-40`, which has no
  Project bullet); add an engagement-noticing line; retire the stale `Hyperfixation` check (`:7`) and the
  `Sprint` in the Goal-engagement line (`:34`).
- Test: `tests/test_capture_generate.py` (parse-only; no network).

**Interfaces:**
- Produces: each parsed item dict may carry `"engagement"` (str) and `"engagement_notes"` (str),
  meaningful only when `type == "Project"`. `engagement` defaults to `"Open"`; `engagement_notes` to `""`.

- [ ] **Step 1: Write the failing parse tests** (append to `tests/test_capture_generate.py`).

```python
def test_parse_weed_reads_project_engagement_and_notes():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Project","name":"Leatherworking","link":null,"status":null,"action":"create",
       "reasoning":"r","engagement":"Steady","engagement_notes":"~30 min daily"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["engagement"] == "Steady" and item["engagement_notes"] == "~30 min daily"


def test_parse_weed_engagement_defaults_open_notes_blank():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Project","name":"X","link":null,"status":null,"action":"create","reasoning":"r"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["engagement"] == "Open" and item["engagement_notes"] == ""
```

- [ ] **Step 2: Run to verify they fail (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py -k engagement -v`
Expected: FAIL (KeyError / default absent).

- [ ] **Step 3: Add the fields to the JSON contract.** In `_WEED_JSON_INSTRUCTION`, inside the per-item
object (after the `"access_conditions"` line, `:182`), add:

```
          "engagement": "<ONLY for type==Project: how June is engaging with this thread, read from HER words. 'I'm starting/focusing on X', a deadline, 'this is my main thing right now' -> \"Steady\" (a normal daily move). 'set X aside', 'not now', 'someday/maybe' -> \"Backburner\". A thing she names but isn't necessarily starting -> \"Open\". Default \"Open\" when she gives no engagement signal — NEVER guess Steady, and NEVER use Sprint/Hyperfixation (retired). Omit for non-Project types.>",
          "engagement_notes": "<ONLY for type==Project: the situated specifics of her engagement, in HER words, that the coarse label can't hold — a deadline ('due July 1'), a cadence ('~30 min daily'), an intensity/affective note ('hyperfixating but stuck', 'this one's urgent'). Empty string if she gave none. Never invent.>"
```

- [ ] **Step 4: Add the schema note.** After the `duration_min`/`duration_estimate_min` note (`:190-194`),
add a line:

```
`engagement` / `engagement_notes` apply ONLY to Projects — the coarse engagement set is Steady / Open /
Backburner (default Open when unsignalled); Sprint and Hyperfixation are retired, so never propose them —
intensity or hyperfixation-context belongs in `engagement_notes`, not the select.
```

- [ ] **Step 5: Add the Per-item prose bullet.** After the Per-item fields bullet (`:145-153`), add:

```
- **Project engagement (type==Project only).** When an item becomes a Project, read June's words for
  how she's engaging with it and set `engagement`: a clear "I'm starting / focusing on / this is due" ->
  "Steady"; "set aside / not now / someday" -> "Backburner"; a thing she names but isn't necessarily
  starting -> "Open". Default "Open" when there's no signal — a new project should be available and
  findable, never pushed at her uninvited, never a guess of Steady, and never Sprint/Hyperfixation
  (retired). Put any deadline / cadence / intensity she voiced into `engagement_notes`. Non-Project
  items carry neither.
```

- [ ] **Step 6: Default the fields in `parse_weed`.** In the per-item `setdefault` loop (`:265-271`), add:

```python
            item.setdefault("engagement", "Open")
            item.setdefault("engagement_notes", "")
```

- [ ] **Step 7: Add the Project definition + retire stale references in `prompts/weeding_gate.md`.**
In the type list (`:34-40`), add a Project bullet (there is none today):

```
- **Project** — a "work on this over time" thread that holds tasks: an ongoing effort with an arc, not a
  single do-it-once action. Mint a Project when the item is a body of work June returns to ("learn
  leatherworking", "the job search"), not a discrete task. When you mint one, propose its `engagement`
  (Steady / Open / Backburner — "Open" by default, "Steady" only when her words say she's actively
  starting/feeding it, "Backburner" when she's setting it aside) and any `engagement_notes` her words
  carry. See the JSON contract.
```

Then retire the two stale references to removed values:
- `:7` — remove the sentence **"Check for any project with Engagement = Hyperfixation … don't propagate it
  as a barrier on every other project."** (Hyperfixation is no longer an engagement value; its context now
  lives in `engagement_notes`/`affective`.)
- `:34` — in the Goal bullet, change **`an `engagement` (Steady / Sprint / Backburner)`** to
  **`an `engagement` (Steady / Open / Backburner)`** (goals never carry Sprint — `build_goal.py:18`).

- [ ] **Step 8: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py -k engagement -v`
Expected: PASS.

- [ ] **Step 9: Commit (main agent, Bash).**
```bash
git add scripts/capture_generate.py prompts/weeding_gate.md tests/test_capture_generate.py
git commit -m "feat(capture): weeding gate proposes per-project engagement + notes (Open default); Project definition; retire Sprint/Hyperfixation prompt refs"
```

---

### Task A3: Capture + memory-pass write the proposed engagement (retire hardcoded Steady)

**Files:**
- Modify: `scripts/capture_generate.py` — `_creation_props` Project branch (`:299-300`).
- Modify: `scripts/memory_pass.py` — `apply_candidate` props block (`:426-434`).
- Modify: `prompts/daily_memory_pass.md` — an optional `engagement`/`engagement_notes` on a Project candidate.
- Test: `tests/test_capture_generate.py`, `tests/test_memory_pass_fields.py`.

**Interfaces:**
- Consumes: parsed item `engagement`/`engagement_notes` (Task A2); the shared builder (Task A1).
- Produces: a captured Project's props carry `Engagement = <proposed or Open>` and, when present,
  `Engagement notes` — **never** the old constant `"Steady"`. Memory-pass Projects inherit the same.

- [ ] **Step 1: Write the failing capture test** (uses the file's `_stub` pattern):

```python
def test_capture_project_writes_proposed_engagement(monkeypatch, tmp_path):
    canned = json.dumps({"opening":"o","capacity_read":None,"groups":[{"label":"g","through_line":"t","items":[
        {"type":"Project","name":"Leatherworking","link":None,"status":None,"action":"create",
         "reasoning":"r","engagement":"Steady","engagement_notes":"~30 min daily"},
        {"type":"Project","name":"Maybe-someday garden","link":None,"status":None,"action":"create",
         "reasoning":"r"},   # no signal -> parse_weed defaulted engagement to "Open"
    ]}]})
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("start leatherworking, ~30 min a day; maybe a garden someday")
    props = {name: p for (typ, name, p) in calls}
    assert props["Leatherworking"]["Engagement"] == "Steady"
    assert props["Leatherworking"]["Engagement notes"] == "~30 min daily"
    assert props["Maybe-someday garden"]["Engagement"] == "Open"   # NOT the old hardcoded Steady
    assert "Engagement notes" not in props["Maybe-someday garden"]
```

*Implementer: match `_stub`'s real return shape (the existing capture tests show it); `parse_weed` runs
inside `capture`, so the second item arrives with `engagement=="Open"`, `engagement_notes==""`.*

- [ ] **Step 2: Run to verify it fails (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py -k proposed_engagement -v`
Expected: FAIL (still writes `"Steady"`).

- [ ] **Step 3: Implement.** Replace the hardcoded Project branch in `_creation_props` (`:299-300`):

```python
    elif type_name == "Project":
        # Born with the weeding LLM's proposed engagement (Open by default; Steady only when June's
        # words said she's starting it; Backburner when she's setting it aside) + any situated notes.
        # Replaces the old blind hardcoded Steady. The shared builder is the single validator/default,
        # so this path and the memory pass cannot diverge. (June, 2026-07-16.)
        props.update(capture_fields.build_project_engagement_props(
            engagement=item.get("engagement"),
            engagement_notes=item.get("engagement_notes"),
        ))
```

In `memory_pass.apply_candidate`, after the link block (`:433-434`) and before the
`build_optional_props` call (`:439`), add:

```python
    if type_name == "Project":
        props.update(capture_fields.build_project_engagement_props(
            engagement=candidate.get("engagement"),
            engagement_notes=candidate.get("engagement_notes"),
        ))
```

In `prompts/daily_memory_pass.md`, add to the candidate JSON contract (Projects only):
`"engagement": "for a Project candidate only, from the entry's OWN words: 'start/focus on'/a deadline -> \"Steady\"; 'set aside/someday' -> \"Backburner\"; else null (born Open). Never Sprint/Hyperfixation."` and
`"engagement_notes": "for a Project only: a deadline/cadence/intensity in the entry's words, else null."`

- [ ] **Step 4: Write the failing memory-pass test** (`tests/test_memory_pass_fields.py`, mirroring its
existing pattern for the optional fields):

```python
def test_memory_pass_project_writes_engagement(monkeypatch):
    # a Project candidate with an explicit Backburner signal + notes
    props = _apply_candidate_props(monkeypatch, {
        "proposed_type": "Project", "proposed_name": "Old side thing",
        "engagement": "Backburner", "engagement_notes": "revisit after the move",
    })
    assert props["Engagement"] == "Backburner"
    assert props["Engagement notes"] == "revisit after the move"


def test_memory_pass_project_defaults_open(monkeypatch):
    props = _apply_candidate_props(monkeypatch, {
        "proposed_type": "Project", "proposed_name": "Named but unsignalled",
    })
    assert props["Engagement"] == "Open"   # NOT hardcoded Steady, NOT blank
```

*Implementer: reuse or add `_apply_candidate_props` — the file's existing helper that captures the props
passed to `gsdo_objects.create`; stub the network + read-back the same way the duration/affect tests do.*

- [ ] **Step 5: Run tests + the capture/memory suites (main agent, Bash).**
`python3 -m pytest tests/test_capture_generate.py tests/test_memory_pass_fields.py -k "engagement or proposed" -v`
then `python3 -m pytest tests/test_capture_generate.py tests/test_memory_pass_fields.py -q`
Expected: PASS, no regressions.

- [ ] **Step 6: Commit (main agent, Bash).**
```bash
git add scripts/capture_generate.py scripts/memory_pass.py prompts/daily_memory_pass.md tests/test_capture_generate.py tests/test_memory_pass_fields.py
git commit -m "feat(capture): write proposed engagement + notes on new Projects, retire hardcoded Steady (both write paths)"
```

---

### Task A4: `gsdt_bind` asks for engagement (retire hardcoded Steady)

**Files:**
- Modify: `scripts/gsdt_bind.py` — `init_binding` (`:204`), `props = {"Engagement": "Steady"}`.
- Test: `tests/test_engagement_proposal.py` (NEW — the pure prompt/validate helper; the interactive
  prompt itself is exercised live in Task C).

**Interfaces:**
- Produces: `gsdt_bind._prompt_engagement(name, _input=input) -> str|None` — returns a validated coarse
  value the user typed, `None` on empty (→ the shared builder's Open default applies when props omit it).

- [ ] **Step 1: Write the failing test.**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gsdt_bind as gb


def test_prompt_engagement_accepts_valid():
    assert gb._prompt_engagement("Proj", _input=lambda _: "Backburner") == "Backburner"
    assert gb._prompt_engagement("Proj", _input=lambda _: "steady") == "Steady"


def test_prompt_engagement_empty_returns_none():
    assert gb._prompt_engagement("Proj", _input=lambda _: "") is None


def test_prompt_engagement_invalid_returns_none():
    # an unrecognized answer is not forced into a guess — None lets the Open default apply
    assert gb._prompt_engagement("Proj", _input=lambda _: "Sprint") is None
```

- [ ] **Step 2: Run to verify it fails (main agent, Bash).**
`python3 -m pytest tests/test_engagement_proposal.py -k prompt_engagement -v`
Expected: FAIL (`_prompt_engagement` undefined).

- [ ] **Step 3: Implement.** Add the helper (module level) and rewire `init_binding` (`:204`):

```python
def _prompt_engagement(name, _input=input):
    """Ask, in the terminal, how June is engaging with this project. Empty accepts the Open default
    (returns None -> the caller omits Engagement -> the shared builder writes Open). An unrecognized
    answer also returns None rather than guessing."""
    import capture_fields
    ans = _input(f"  Engagement for {name!r}? [Open]/Steady/Backburner: ").strip()
    if not ans:
        return None
    v = ans.capitalize()
    return v if v in capture_fields.PROJECT_ENGAGEMENTS else None
```

Replace `props = {"Engagement": "Steady"}` (`:204`) with:

```python
        props = {}
        eng = _prompt_engagement(project_name)
        if eng:
            props["Engagement"] = eng
        # (unset -> the create path's shared builder default writes Open, not Steady)
```

*Note: `init_binding`'s create path passes `properties=props` to `o.create("Project", …)`. Since bind
does NOT route through `_creation_props`, an omitted Engagement here must still land as Open — confirm
that `gsdo_objects.create`/the create path applies the shared default, OR set `props["Engagement"]` to
`capture_fields._engagement_value(eng)` explicitly so a bare bind still writes Open. Prefer the explicit
form to avoid relying on a chokepoint we deliberately did NOT build:*

```python
        import capture_fields
        props = {"Engagement": capture_fields._engagement_value(_prompt_engagement(project_name))}
```

- [ ] **Step 4: Run tests to verify they pass (main agent, Bash).**
`python3 -m pytest tests/test_engagement_proposal.py -q`
Expected: PASS.

- [ ] **Step 5: Commit (main agent, Bash).**
```bash
git add scripts/gsdt_bind.py tests/test_engagement_proposal.py
git commit -m "feat(bind): dialogic engagement prompt, retire hardcoded Steady (defaults Open)"
```

---

## STREAM B — Retire Sprint / Hyperfixation from the data structure

### Task B1: Cleanup sweep + live migration  **(DISPATCHED SUBAGENT — main agent runs all Bash/migration)**

> **June's structure (2026-07-16):** this is a *separate subagent the main agent sends off.* The subagent
> WRITES the code + the migration script; the **main agent** runs the tests, the dry-run, the
> June-confirmed live migration, the tag deletion, and the read-backs (subagents can't run Bash).

**Files:**
- Modify: `scripts/build_project.py:25-26` — drop `"Sprint"`, `"Hyperfixation"` from the `Engagement`
  option list (leaving `Steady, Open, Needs Clarifying, Backburner, Done`).
- Modify: `scripts/neglect.py:71` — `_ACTIVE_ENGAGEMENT = {"Steady"}`; update comments `:60-64, :196, :280`.
- Modify: `scripts/daily_plan.py:527` — `active_engagement = {"Steady"}`; update comment `:520`.
- Modify: `scripts/orient_map.py` — the engagement→status logic + docstring (`:29-32`): `Steady / unset →
  ● ACTIVE` (find the real mapping code, not only the docstring).
- Create: `scripts/migrate_engagement_cleanup.py` — surfaces live Sprint/Hyperfixation projects, proposes
  a migration, applies on `--apply` with read-back, then deletes the two tags.
- Test: `tests/test_engagement_cleanup.py` (NEW), `tests/test_neglect_active.py` (append).

**Interfaces:**
- Produces:
  - `propose_migration(projects) -> list[dict]` — pure: for each Project whose `engagement` is
    `"Sprint"` or `"Hyperfixation"`, propose `"Steady"` (they were being actively pursued; the closest
    surviving value). Returns `[{"id","name","current","proposed"}]`. June may override any per project.
  - `apply_migration(proposals) -> list[dict]` — idempotent `gsdo_objects.update` + by-name read-back per
    item; raises on mismatch; skips a project already off the retired values (re-run safe).
  - `delete_retired_tags()` — after migration proves zero live projects carry them, deletes the `Sprint`
    and `Hyperfixation` tags from the `Engagement` property (`DELETE /spaces/{sid}/properties/{pid}/tags/{tagId}`;
    `ensure_property` only ADDS options, so removal is a direct tag delete). **Deletion is async
    (probe-confirmed): after each `DELETE`, poll `GET .../tags` up to ~5s until the tag name is gone, and
    raise if it never disappears — do NOT trust the `200` alone, and do NOT read-back once.** No-op if a
    tag is already absent (re-run safe).

- [ ] **Step 1 (subagent): write the code-sweep changes.** In each file, remove `Sprint`/`Hyperfixation`
  from the engagement option list / active-cohort set and correct the neighboring comments to name only
  the surviving values. **Grep first** so nothing is missed:
  `grep -rn "Sprint\|Hyperfixation" scripts/` — every hit that treats them as an *engagement value* is in
  scope (the `build_project.py` select, `neglect.py` `_ACTIVE_ENGAGEMENT` + comments, `daily_plan.py`
  `active_engagement` + comment, `orient_map.py` mapping + docstring). Leave untouched any hit that is
  unrelated (e.g. an `_APPLIES_TO_LEVEL` comment that merely mentions the word as a future example — flag
  it in the task report rather than editing speculatively).

- [ ] **Step 2 (subagent): write the failing cohort test** (`tests/test_neglect_active.py`, append):

```python
def test_active_cohort_is_steady_only():
    import neglect
    assert neglect._ACTIVE_ENGAGEMENT == {"Steady"}   # Sprint/Hyperfixation retired
```

and the migration proposal test (`tests/test_engagement_cleanup.py`):

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import migrate_engagement_cleanup as mg


def test_proposes_steady_for_retired_values():
    projs = [
        {"id": "a", "name": "Cuffs", "engagement": "Sprint"},
        {"id": "b", "name": "Reading", "engagement": "Hyperfixation"},
        {"id": "c", "name": "Fine", "engagement": "Steady"},
    ]
    out = {p["name"]: p["proposed"] for p in mg.propose_migration(projs)}
    assert out == {"Cuffs": "Steady", "Reading": "Steady"}   # 'Fine' already off the retired values
```

- [ ] **Step 3 (main agent, Bash): run to verify they fail.**
`python3 -m pytest tests/test_neglect_active.py tests/test_engagement_cleanup.py -k "cohort or retired" -v`
Expected: FAIL (`_ACTIVE_ENGAGEMENT` still has 3; module missing).

- [ ] **Step 4 (subagent): implement** `propose_migration` (pure), `apply_migration` (update + by-name
  read-back, skip-if-already-migrated), `delete_retired_tags` (find the `Engagement` property id + the two
  tag ids via `GET /spaces/{sid}/properties/{pid}/tags`, `DELETE` each; tolerate already-absent), and a
  `__main__` that fetches live projects (`gsdo_anytype.fetch_all_objects`), prints the proposed migration
  as a table, and only migrates + deletes tags under an explicit `--apply` flag (bare run = dry-run).
  **Guard order in `--apply`: migrate ALL live retired-value projects first, re-fetch to confirm zero
  remain, and ONLY THEN delete the tags** — deleting a tag still referenced by an object would strand it.

- [ ] **Step 5 (main agent, Bash): run tests to verify pass.**
`python3 -m pytest tests/test_neglect_active.py tests/test_engagement_cleanup.py -q`
Expected: PASS.

- [ ] **Step 6 (main agent, Bash): DRY-RUN for June.** `python3 scripts/migrate_engagement_cleanup.py`
  (no `--apply`) → present the live mapping to June (there may be one Sprint project on record; possibly
  none). **Do not `--apply` until she confirms the per-project targets — her real data.** The live apply
  happens in Task C after her confirmation.

- [ ] **Step 7 (main agent, Bash): commit the code + script** (the live apply is Task C):
```bash
git add scripts/build_project.py scripts/neglect.py scripts/daily_plan.py scripts/orient_map.py scripts/migrate_engagement_cleanup.py tests/test_neglect_active.py tests/test_engagement_cleanup.py
git commit -m "feat(cleanup): retire Sprint/Hyperfixation from engagement (code + migration, dry-run by default)"
```

---

## Task C: Integration & end-to-end verify (REQUIRED — do not skip)

A plan is done only when the feature is wired into the running system and observed working on **real
data** — not merely green tests. Reason from how the system functions at runtime (capture → weed →
create → read-back; loader → neglect cohort), not from doc-text.

**Wiring this connects to:**
- `POST /api/capture` → `capture_generate.capture()` → `_creation_props` (Project branch now calls
  `capture_fields.build_project_engagement_props`) → `gsdo_objects.create` → a Project born with the
  proposed `Engagement` (+ notes), never blank, never a blind Steady.
- `memory_pass.apply_candidate` (Project branch) → the same shared builder.
- The daily-plan loader (`daily_plan.load_active_items`) already reads Engagement by name and treats blank
  as Open — so a proposed Open/Steady/Backburner flows straight into the plan's active set.
- Post-cleanup, `neglect._ACTIVE_ENGAGEMENT` / `daily_plan.active_engagement` = `{"Steady"}`; the
  `Engagement` select no longer offers Sprint/Hyperfixation.

- [ ] **Step 1 (main agent, Bash): restart the server** (memory flags a possibly-stale server) and load
  `docs/overlay_daily.html`.

- [ ] **Step 2 (main agent): drive a real capture** through the Add tab via the `verify` skill with a dump
  containing three clearly-different projects, all prefixed `CD-TEST`:
  *"CD-TEST I'm starting a leatherworking project, want to do ~30 min a day; CD-TEST maybe sell the old
  phone case someday; CD-TEST I want a herb garden."* (Steady+notes / Backburner / Open-neutral.)

- [ ] **Step 3 (main agent, Bash): read the created objects back** and confirm:
  - `CD-TEST … leatherworking` → `Engagement = Steady`, `Engagement notes ≈ "~30 min a day"`;
  - `CD-TEST … phone case someday` → `Engagement = Backburner`;
  - `CD-TEST … herb garden` → `Engagement = Open` (neutral default, NOT Steady, NOT blank).

- [ ] **Step 4 (main agent, Bash): the neutral/other-path default** — create a Project via the bare
  create path with no engagement
  (`python3 -c "import sys; sys.path.insert(0,'scripts'); import gsdo_objects as go; print(go.create('Project','CD-TEST bare project'))"`),
  read it back, confirm `Engagement == "Open"` (the proposal-layer default holds even without a chokepoint,
  because bind/creation set it explicitly; a raw MCP create with no props writes blank, which the loader
  reads as Open — confirm the read-back is either "Open" or blank-reads-as-Open, and note which).

- [ ] **Step 5 (main agent, Bash): the cleanup live apply** — with June's confirmation of the Task B1
  dry-run mapping, run `python3 scripts/migrate_engagement_cleanup.py --apply`; re-fetch and confirm no
  live project carries Sprint/Hyperfixation and both tags are gone from the `Engagement` property. (If June
  has not confirmed, STOP and hold — do not write her space.)

- [ ] **Step 6 (main agent, Bash): live-verify the neglect behavior didn't break** — the cohort shift
  ({Steady,Sprint,Hyperfixation} → {Steady}) is a real runtime change. Run the neglect/active-untouched
  path on real data (read-only) and confirm it returns a sane cohort (Steady projects only), no crash, no
  empty-where-it-shouldn't-be. Regenerate June's real daily plan once and confirm it still composes (the
  loader + "not getting to" section run clean with the new set).

- [ ] **Step 7 (main agent, Bash): delete ALL `CD-TEST` objects** from her real space; re-fetch to confirm
  they're gone. Nothing this plan created may remain.

- [ ] **Step 8 (main agent, Bash): full suite, clean tree.**
`python3 -m pytest -q`
Expected: all green; the conftest real-data tripwire did not fire.

- [ ] **Step 9: Commit, then cross-family review (main agent, Bash).** Request the non-Claude review
  (`~/.claude/skills/requesting-code-review/github_models_review.py`, chunked per file with its tests,
  ~8k-token cap) before the thread closes; triage findings, apply the real ones.
```bash
git add -A
git commit -m "test(engagement): end-to-end verify proposed engagement + notes + Sprint/Hyperfixation cleanup on real data"
```

---

## Self-Review (author checklist)

- **Spec coverage:** (1) capture proposes any coarse value from her words — A2 (contract) + A3 (write) +
  A1 (validator/default) ✓; (2) no born-Open chokepoint, default lives in the proposal layer — A1
  docstring + explicit note in A4 ✓; (3) fields populated when info exists — `engagement_notes` in A1/A2/A3
  ✓; (4) bind dialogic — A4 ✓; (5) Sprint/Hyperfixation removed from the data structure as a dispatched
  subagent — B1 (code sweep + live migration + tag delete), main-agent-runs-Bash division named ✓;
  (6) live-verify on real data incl. the neglect-cohort behavior change — C6 ✓. Deferred/not-in-scope
  (stated): the generalized tap-to-change UI + change-log (→ Claude design session); the broader
  field-population audit (Direction B assessment); the Sprint-*mode* design (Focus Period foreground).
- **Placeholder scan:** every code step carries real code. The two spots that depend on a live shape
  (`_stub` return in A3; the `orient_map` mapping vs. its docstring in B1) say "match/grep the real shape
  and extend additively" with the exact target behavior — honest instruction, not hand-wave.
- **Type consistency:** `engagement`/`engagement_notes` item keys flow contract (A2) → parse default (A2)
  → `_creation_props` / `apply_candidate` write (A3) via the one builder `build_project_engagement_props`
  (A1). `PROJECT_ENGAGEMENTS` used identically in A1, A4. `Engagement` always the display name; read-back
  always by name. `propose_migration`/`apply_migration`/`delete_retired_tags` names consistent across B1
  steps and Task C.
- **DRY / one-guard:** `build_project_engagement_props` is the single validator+default; no creation path
  re-implements it (A3 both paths call it; A4 uses `_engagement_value`). The migration script is the only
  writer of the tag deletion.
- **File ownership:** Stream A files (`capture_fields`, `capture_generate`, `memory_pass`, `gsdt_bind`,
  the two prompts) and Stream B files (`build_project`, `neglect`, `daily_plan`, `orient_map`, the
  migration script) do not overlap — the two streams can build in either order or in parallel; only Task C
  needs both landed.

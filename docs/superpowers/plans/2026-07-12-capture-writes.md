# Capture-Writes Fix Implementation Plan

> **For agentic workers:** implement this plan task-by-task via our build-loop — fresh subagent per task, per-task review, final whole-branch review (the `subagent-driven-development` pattern). Steps use checkbox (`- [ ]`) syntax for tracking. **Subagents here can WRITE files but CANNOT run Bash — the main agent runs every test / read-back / `verify` gate.** Bash-only steps are marked **(main agent, Bash)**.

**Goal:** Make the capture layer write the Task/Project fields the planner already reads and is starved for — a per-item duration, a per-item affect note, "waiting-on" blocks, and access conditions — so the day stops being scheduled from a flat 30-minute default and a thrown-away feeling.

**Architecture:** One new pure helper (`scripts/capture_fields.py`) becomes the single source of truth for turning a captured item's optional signals into validated Anytype property values (guard against scalar-flattening affect, against inventing a duration, against writing an unknown access tag). Both write paths — the overlay/chat capture (`capture_generate._creation_props`) and the memory pass (`memory_pass.apply_candidate`) — call that one helper, so they cannot diverge. The weeding-gate JSON contract and the memory-pass contract each gain the same optional **per-item** fields — duration, affect, blocked-on, access — read from June's words only (absent stays absent; a blank affect field is fine when there's no info).

**Tech Stack:** Python 3 stdlib only; existing modules `capture_generate`, `memory_pass`, `gsdo_objects`, `gsdo_anytype`, `plan_generate`, `session_store`; pytest with the repo's `conftest.py` sandbox redirect. No new dependencies.

---

## SEQUENCING CONSTRAINT — read before writing any code

**This plan is written now but BUILDS ONLY AFTER the capture-when thread lands** (`docs/superpowers/plans/2026-07-11-capture-when-regenerate-flow.md`). That thread is mid-build on the **same file** (`scripts/capture_generate.py`) and the **same JSON contract** (the `_WEED_JSON_INSTRUCTION` block + `parse_weed`). Building this in parallel would collide on every one of those edits.

**At build time, before Task 2, re-read these and re-derive every line anchor in this plan** — capture-when will have shifted them:

- `prompts/weeding_gate.md` — the human/gate logic (capture-when may add "when" noticing here).
- `scripts/capture_generate.py`:
  - `_WEED_JSON_INSTRUCTION` (currently `:116-176`) — capture-when adds a per-item `"when"` field to this contract. **Add this plan's fields alongside `when`; never remove or reshape `when`.**
  - `parse_weed` (currently `:225-239`) — capture-when adds an `item["when"]` default here. **Add this plan's item defaults next to it, same pattern.**
  - `_creation_props` (currently `:252-273`) — capture-when adds `Scheduled`/`Parked` writes and may change the signature to receive a resolved `when`/`today`. **This plan's field-writes must slot in additively; do not fight its signature — read the real one and extend it.**
  - `capture()` (currently `:316-401`) — capture-when adds a `today=None` param and a `has_today` return key. **Leave both intact.**

If capture-when has NOT landed yet at build time, stop and say so — do not build against a contract that is still moving.

---

## DECISIONS FROM JUNE (2026-07-12) — these govern the tasks below

1. **Affect follows the scope June gave it — a FIDELITY rule, stored per item.** June's principle (2026-07-12, her correction of an earlier over-narrow reading): *"the model should honor my text input. If I say one affect applies to everything, that's the truth, so all the agent has to do is to make sure it captures the information I provide, when provided."* So: the weeding-gate contract gains an optional **per-item `affect`** field (verbatim free text, guard #3 — never a scalar, never a paraphrase), and the object-level `Affective` is written only from it. The storage is per-item; **the scope comes from her words:**
   - Feeling attached to one item ("dreading the dentist") → only that item's `affect` carries it.
   - Feeling stated about the whole dump ("I'm dreading all of this") → **every** item's `affect` carries it — that is her information faithfully captured, not spread.
   - No feeling given → blank (blank is fine).
   **The prohibited move is the agent INVENTING scope** — inferring a dump-wide feeling from a single-item remark, or narrowing a dump-wide statement to one item. Capture what she provides, at the scope she provides it, when provided. The turn-level `capacity_read` keeps its existing flow (session log + generation log, as today) — objects get affect only through the per-item `affect` field under this rule. (Per-item storage matches the planner, which reads `Affective` per Task — `daily_plan.py:130,300`.)

2. **Access conditions: the three built tags are the honest boundary for THIS plan.** The live options are exactly `Can-be-done-lying-down`, `Involves-leaving-house`, `Requires-talking-to-a-person` (`build_task.py:22-24`). The contract asks the LLM to pick zero or more of *those exact* values when June's words indicate them — never free text, never an invented tag. **But June reframed the underlying question generatively:** the real design question is *"what would be helpful for an agent to know when making a plan for different kinds of days (not just accessibility)?"* — that design thread is hers to retrieve from another session, and the field set may grow later. **The `capture_fields` helper is deliberately the single extension point for that growth:** a future field (or new access options) means one change to `ALLOWED_ACCESS` / `build_optional_props` and both write paths inherit it — no rework of either path. Free-text access annotation belongs in `Access notes`, which is dead on both ends (no reader) and out of scope here.

---

## EXPLICITLY OUT OF SCOPE (state and hold)

- **The `Engagement="Steady"` default on captured Projects** (`capture_generate.py:260`) — owned by the selection/engagement thread per `docs/orchestrator_flags_2026-07-11.md`. Do not touch it.
- **The create-vs-update gap** (nothing recognizes "new information about a thing that already exists") — a design conversation with June, not a patch. One requirement of hers is already on record for that future design: she wants to be able to **add/change affect info over time**, and wants agents to **remember to ask her when things seem to have changed** — the affective-upkeep loop. It lands with create-vs-update, not this plan.
- **`scripts/daily_plan.py` and `scripts/plan_generate.py`** including the Deadline-drop fix — owned by the selection thread. This plan only *feeds* their existing readers; it changes no reader.
- **Anything in the capture-when plan's task list** (the `Scheduled` field, `when_resolve`, the reschedule endpoint, the verify box).
- **`Access notes`, `AI autonomous`, Task `Due date`, `Relevant docs`, Project `Description`/`Reaching for`** — the audit's "dead on both ends" bucket (no reader wired). Deciding build-reader-or-drop is a separate call; do not write to them.

---

## Global Constraints

- **Python 3 stdlib only** (matches `scripts/`). No new deps.
- **`gsdo_objects.create`/`update` take DISPLAY names** ("Duration min", "Affective", "Blocked on", "Access conditions"), and resolve select/multi-select **by option name**. Never pass a property key or a tag id.
- **Guard #3 — never scalar-flatten an affect field.** `Affective` is free text. Write the LLM's words verbatim. Never a 1–5 number, never a paraphrase.
- **Never invent a value.** Absent stays absent. A wrong duration guess is worse than the flat default (audit is explicit). A named-but-absent field writes nothing — the reader's own no-value path applies.
- **Idempotent writes; no silent failures — raise, don't `assert`; verify against the live space with read-back** after every write (the existing `_get_object` read-back stays).
- **Tests self-clean — NEVER leave artifacts in June's real Anytype space.** Unit tests mock the LLM and Anytype (the repo `conftest.py` already redirects data/config to a sandbox and *fails the suite* on any write to the real data dir). The end-to-end task (Task 5) creates real objects and **deletes them in the same run**.
- **Additive only.** Delete no existing behavior. Every field is optional; a capture that mentions none of them behaves exactly as it does today.
- **One contract, two paths — never diverge.** Any field added to the capture contract is added to the memory-pass contract and both write through the shared `capture_fields` helper (Task 1).

---

## File Structure

- `scripts/capture_fields.py` — **NEW.** Pure, network-free single source of truth: validate + shape the optional-field property values (duration, affect, blocked-on, access-conditions) into a props dict. Consumed by both write paths.
- `tests/test_capture_fields.py` — **NEW.** Unit tests for the helper (no network).
- `scripts/capture_generate.py` — the weeding-gate JSON contract (`_WEED_JSON_INSTRUCTION`) gains the four per-item fields (duration, affect, blocked-on, access); `parse_weed` defaults them; `_creation_props` writes them via `capture_fields`. `capture()` itself is untouched — `capacity_read` keeps flowing to the session/generation logs as today, nowhere else.
- `prompts/weeding_gate.md` — one noticing line so the gate reads duration / per-item feeling / waiting-on / access from June's words when present (never invented).
- `scripts/memory_pass.py` — `apply_candidate` writes the same fields via `capture_fields`.
- `prompts/daily_memory_pass.md` — its JSON contract gains the same optional fields (verbatim-from-body only, null when absent).
- `tests/test_capture_generate.py` — add cases asserting the new props are written from a canned weed.
- `tests/test_memory_pass_fields.py` — **NEW.** cases asserting `apply_candidate` writes the new props (mock Anytype).

---

### Task 1: `scripts/capture_fields.py` — the shared optional-field prop builder

**Files:**
- Create: `scripts/capture_fields.py`
- Test: `tests/test_capture_fields.py`

**Interfaces:**
- Produces:
  - `ALLOWED_ACCESS: tuple[str, ...]` — the three live access-condition option names (must match `build_task.py:22-24`). Per DECISION 2, this tuple + `build_optional_props` are the single extension point when the field set grows later.
  - `build_optional_props(*, duration_min=None, affect=None, blocked_on=None, access_conditions=None) -> dict` — return a props dict containing ONLY the keys whose values validate. Keys, when present: `"Duration min"` (int > 0), `"Affective"` (non-empty str — the item's own affect note, per DECISION 1), `"Blocked on"` (non-empty str), `"Access conditions"` (non-empty list of members of `ALLOWED_ACCESS`).

- [ ] **Step 1: Write the failing tests.**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import capture_fields as cf


def test_duration_valid_int():
    assert cf.build_optional_props(duration_min=45) == {"Duration min": 45}


def test_duration_coerces_numeric_string():
    assert cf.build_optional_props(duration_min="30") == {"Duration min": 30}


def test_duration_absent_or_bad_writes_nothing():
    assert cf.build_optional_props(duration_min=None) == {}
    assert cf.build_optional_props(duration_min="") == {}
    assert cf.build_optional_props(duration_min=0) == {}
    assert cf.build_optional_props(duration_min=-10) == {}
    assert cf.build_optional_props(duration_min="soon") == {}


def test_affect_verbatim_string():
    assert cf.build_optional_props(affect="this one is heavy") == {"Affective": "this one is heavy"}


def test_affect_blank_or_none_writes_nothing():
    assert cf.build_optional_props(affect="") == {}
    assert cf.build_optional_props(affect="   ") == {}
    assert cf.build_optional_props(affect=None) == {}


def test_affect_never_flattened_to_number():
    # guard #3: a bare scalar is not a valid affect note — do not store "3"
    assert cf.build_optional_props(affect=3) == {}


def test_blocked_on():
    assert cf.build_optional_props(blocked_on="waiting on Donna's edits") == {"Blocked on": "waiting on Donna's edits"}
    assert cf.build_optional_props(blocked_on="") == {}


def test_access_conditions_filters_to_known_options():
    got = cf.build_optional_props(access_conditions=["Involves-leaving-house", "made-up-tag"])
    assert got == {"Access conditions": ["Involves-leaving-house"]}


def test_access_conditions_empty_after_filter_writes_nothing():
    assert cf.build_optional_props(access_conditions=["nope"]) == {}
    assert cf.build_optional_props(access_conditions=[]) == {}
    assert cf.build_optional_props(access_conditions=None) == {}


def test_all_fields_together():
    got = cf.build_optional_props(duration_min=20, affect="dread", blocked_on="the API key",
                                  access_conditions=["Requires-talking-to-a-person"])
    assert got == {"Duration min": 20, "Affective": "dread", "Blocked on": "the API key",
                   "Access conditions": ["Requires-talking-to-a-person"]}
```

- [ ] **Step 2: Run to verify they fail.**
Run (**main agent, Bash**): `python3 -m pytest tests/test_capture_fields.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `scripts/capture_fields.py`.**

```python
"""Shared, network-free builder for a captured item's OPTIONAL Anytype field values.

Single source of truth for BOTH write paths (capture_generate._creation_props and
memory_pass.apply_candidate) so the two can never diverge on how a duration / affect /
blocked-on / access-condition is validated and shaped. All validation is here; the callers
just pass raw values in and splice the returned dict into their props.

Rules (from the 2026-07-12 capture audit + June's decisions + repo guards):
  - Never invent: an absent/blank/invalid value writes NOTHING (the reader's own no-value
    path then applies — e.g. the scheduler's default duration).
  - Affect fidelity (June, 2026-07-12): each item's affect matches the scope June's words
    gave it — a feeling about one item lands on that item; a feeling she states about the
    whole dump lands on every item (her information, honored); nothing given → blank (fine).
    The scope decision lives in the LLM contract, upstream; this helper just stores what
    arrives per item, verbatim.
  - Guard #3: Affective is free text, never a scalar. A bare number is NOT a valid affect
    note and is dropped, never stored as "3".
  - Access conditions is a fixed multi-select; only the live option names are ever written
    (an unknown tag is dropped, never created). ALLOWED_ACCESS + build_optional_props are
    the single extension point when the "what should a plan-making agent know about a day"
    field set grows (June's open design thread) — both write paths inherit any change here.
"""

# MUST stay in sync with scripts/build_task.py:22-24 (the live multi-select options).
ALLOWED_ACCESS = (
    "Can-be-done-lying-down",
    "Involves-leaving-house",
    "Requires-talking-to-a-person",
)


def _duration_prop(raw):
    if raw is None or isinstance(raw, bool):
        return None
    try:
        val = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def _text_prop(raw):
    # Guard #3 lives here too: a non-string (e.g. a bare number) is not a valid free-text note.
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    return raw or None


def _access_prop(raw):
    if not isinstance(raw, (list, tuple)):
        return None
    kept = [v for v in raw if v in ALLOWED_ACCESS]
    return kept or None


def build_optional_props(*, duration_min=None, affect=None, blocked_on=None,
                         access_conditions=None):
    """Return {display_name: value} for ONLY the optional fields that validate."""
    props = {}
    dur = _duration_prop(duration_min)
    if dur is not None:
        props["Duration min"] = dur
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

- [ ] **Step 4: Run tests to verify they pass.**
Run (**main agent, Bash**): `python3 -m pytest tests/test_capture_fields.py -v`
Expected: PASS (all cases).

- [ ] **Step 5: Commit** (**main agent, Bash**)
```bash
git add scripts/capture_fields.py tests/test_capture_fields.py
git commit -m "feat(capture): shared validated builder for optional Task/Project fields"
```

---

### Task 2: Weeding-gate contract reads per-item duration / affect / blocked-on / access

**Files:**
- Modify: `scripts/capture_generate.py` — the `_WEED_JSON_INSTRUCTION` per-item shape (re-derive line anchor; ~`:149-171`) and the item defaults in `parse_weed` (~`:225-239`).
- Modify: `prompts/weeding_gate.md` — one noticing line in the "Notice the whole before naming anything" list (~`:15-19`).
- Test: `tests/test_capture_generate.py` (parse-only cases; no network).

**Interfaces:**
- Produces: each parsed item dict may now carry `"duration_min"` (int or null), `"affect"` (str or ""), `"blocked_on"` (str or ""), `"access_conditions"` (list or []). Purely additive to the existing `type/name/link/status/action/dedup_note/reasoning` (and capture-when's `when`). The existing turn-level `capacity_read` stays in the contract untouched — it feeds the session log, not objects.

- [ ] **Step 1: Write the failing parse tests** (append to `tests/test_capture_generate.py`).

```python
def test_parse_weed_reads_optional_fields():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Task","name":"Call surgeon","link":null,"status":"Ready","action":"create",
       "reasoning":"r","duration_min":15,"affect":"been dreading this call",
       "blocked_on":"the referral","access_conditions":["Involves-leaving-house"]}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["duration_min"] == 15
    assert item["affect"] == "been dreading this call"
    assert item["blocked_on"] == "the referral"
    assert item["access_conditions"] == ["Involves-leaving-house"]


def test_parse_weed_optional_fields_default_safely_when_absent():
    raw = '''```json
    {"opening":"o","capacity_read":null,"groups":[{"label":"g","through_line":"t","items":[
      {"type":"Task","name":"X","link":null,"status":"Ready","action":"create","reasoning":"r"}
    ]}]}
    ```'''
    item = cg.parse_weed(raw)["groups"][0]["items"][0]
    assert item["duration_min"] is None
    assert item["affect"] == ""
    assert item["blocked_on"] == ""
    assert item["access_conditions"] == []
```

- [ ] **Step 2: Run to verify they fail.**
Run (**main agent, Bash**): `python3 -m pytest tests/test_capture_generate.py -k optional_fields -v`
Expected: FAIL (KeyError / defaults absent).

- [ ] **Step 3: Add the four fields to the JSON contract.** In `_WEED_JSON_INSTRUCTION`, inside the per-item object (alongside `type/name/link/status/action/dedup_note/reasoning` and capture-when's `when`), add:

```
          "duration_min": <how many MINUTES this will take, as a number, ONLY if June said or clearly implied it ("a quick 15 min", "an hour"). null if she gave no signal — NEVER guess; a wrong guess is worse than leaving it unset.>,
          "affect": "<how June feels about THIS item, in her words ('dreading it', 'excited about this one'). Match the SCOPE she gave the feeling: said about one item → only that item; said about the whole dump ('I'm dreading all of this') → put it on every item, because that's her information. Do NOT invent scope — never widen a single-item remark to the dump or narrow a dump-wide statement to one item. Empty string if she gave this item no signal (blank is fine). Never a number or rating.>",
          "blocked_on": "<what this is waiting on, in June's words, if she said it's blocked/waiting ('waiting on Donna', 'once the key arrives'). Empty string if nothing.>",
          "access_conditions": [<zero or more of EXACTLY these, only when her words indicate them: "Can-be-done-lying-down", "Involves-leaving-house", "Requires-talking-to-a-person". Empty list if none. Do NOT invent other values.>]
```

Add one bullet to the surrounding prose in that instruction block, directly after the existing **Capacity/affect** bullet (which stays as-is — `capacity_read` remains the turn-level session signal):

```
- **Per-item fields.** If June names how long something takes, how she feels about something,
  what it's waiting on, or an access condition (has to leave the house, can be done lying
  down, needs a phone call), record it on the item(s) in `duration_min` / `affect` / `blocked_on` /
  `access_conditions`. Only from her words — absent stays absent, and blank affect is fine.
  For `affect`, honor the scope she gave the feeling: about one item → that item only; about
  everything ("all of this feels heavy") → on every item, because that's the information she
  provided. Never invent scope in either direction. `affect` goes on the object; `capacity_read`
  stays the whole turn's session signal — set both when both are true, but don't auto-copy one
  into the other. These feed the planner directly; a guessed duration mis-shapes her day.
```

- [ ] **Step 4: Default the fields in `parse_weed`.** After the existing `parsed.setdefault(...)` calls, normalize every item so downstream code never KeyErrors (mirror how capture-when defaults `when`):

```python
    for grp in parsed.get("groups", []):
        for item in grp.get("items", []):
            item.setdefault("duration_min", None)
            item.setdefault("affect", "")
            item.setdefault("blocked_on", "")
            item.setdefault("access_conditions", [])
```
*Note to implementer: if capture-when already added a normalization loop here for `when`, add these `setdefault`s to that same loop rather than writing a second loop.*

- [ ] **Step 5: Add the noticing line to `prompts/weeding_gate.md`.** In the "Notice the whole before naming anything" bullet list, add:

```
- Is there a duration, a feeling, a blocker, or an access condition in her words? ("a quick
  15 min," "dreading that one," "all of this feels heavy," "waiting on the referral," "I'd have
  to leave the house") — hold it at the scope she gave it: a feeling about one item stays on
  that item; a feeling about the whole dump belongs on every item. Never invent one, and never
  invent its scope.
```

- [ ] **Step 6: Run tests to verify they pass.**
Run (**main agent, Bash**): `python3 -m pytest tests/test_capture_generate.py -k optional_fields -v`
Expected: PASS.

- [ ] **Step 7: Commit** (**main agent, Bash**)
```bash
git add scripts/capture_generate.py prompts/weeding_gate.md tests/test_capture_generate.py
git commit -m "feat(capture): weeding gate reads per-item duration, affect, blocked-on, access"
```

---

### Task 3: Capture writes the per-item optional fields (duration, affect, blocked-on, access)

**Files:**
- Modify: `scripts/capture_generate.py` — `_creation_props` only (re-derive anchor; ~`:252-273`). **`_create_one` and `capture()` are NOT modified** — per DECISION 1 the affect-scope judgment happens in the LLM contract, so a dump-wide feeling arrives already written on each item; everything this task writes is on the item dict, nothing to thread through.
- Test: `tests/test_capture_generate.py` (add cases; the LLM + Anytype are already mocked by the file's `_stub` helper).

**Interfaces:**
- Consumes: `capture_fields.build_optional_props` (Task 1); parsed item fields incl. per-item `affect` (Task 2).
- Produces: each created object's props dict now includes any validating `Duration min` / `Affective` / `Blocked on` / `Access conditions`, all read from that item alone. `capacity_read` keeps flowing to the session/generation logs exactly as today and is never written to an object. No return-shape change.

- [ ] **Step 1: Write the failing tests.** Use the file's existing `_stub` mocking pattern; assert on the props captured by the mocked `gsdo_objects.create`.

```python
def test_capture_affect_scope_single_item(monkeypatch, tmp_path):
    # FIDELITY case (a): June attached the feeling to ONE item — only that item carries it.
    # (The other item's blank affect is correct: she gave it no signal.)
    canned = json.dumps({
        "opening": "o",
        "capacity_read": {"text": "generally frazzled", "source": "inferred", "reasoning": "x"},
        "groups": [{"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Book dentist", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r", "duration_min": 10,
             "affect": "dreading the call", "blocked_on": "the insurance card",
             "access_conditions": ["Requires-talking-to-a-person"]},
            {"type": "Task", "name": "Sketch the zine cover", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r"},
        ]}],
    })
    calls = _stub(monkeypatch, tmp_path, canned=canned)  # -> list of (type, name, props)
    cg.capture("book the dentist (~10 min, dreading it, need the insurance card first); sketch the zine cover")
    props = {name: p for (typ, name, p) in calls}
    dentist = props["Book dentist"]
    assert dentist["Duration min"] == 10
    assert dentist["Affective"] == "dreading the call"        # the ITEM's affect, verbatim
    assert dentist["Blocked on"] == "the insurance card"
    assert dentist["Access conditions"] == ["Requires-talking-to-a-person"]
    zine = props["Sketch the zine cover"]
    for k in ("Duration min", "Affective", "Blocked on", "Access conditions"):
        assert k not in zine    # she gave this item no signal → nothing written
    # capacity_read is never auto-copied onto objects (objects get affect only via `affect`):
    assert dentist.get("Affective") != "generally frazzled"


def test_capture_affect_scope_whole_dump(monkeypatch, tmp_path):
    # FIDELITY case (b): June stated one feeling about EVERYTHING ("I'm dreading all of this")
    # — the contract has the LLM put it on every item, and every object carries it. That is
    # her information faithfully captured, not spread.
    canned = json.dumps({
        "opening": "o",
        "capacity_read": {"text": "dreading all of this", "source": "stated", "reasoning": "x"},
        "groups": [{"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "File the extension", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r", "affect": "dreading all of this"},
            {"type": "Task", "name": "Call the landlord", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r", "affect": "dreading all of this"},
        ]}],
    })
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("I'm dreading all of this: file the extension, call the landlord")
    props = {name: p for (typ, name, p) in calls}
    assert props["File the extension"]["Affective"] == "dreading all of this"
    assert props["Call the landlord"]["Affective"] == "dreading all of this"


def test_capture_no_signals_writes_no_optional_props(monkeypatch, tmp_path):
    canned = json.dumps({
        "opening": "o", "capacity_read": None,
        "groups": [{"label": "g", "through_line": "t", "items": [
            {"type": "Task", "name": "Email editor", "link": None, "status": "Ready",
             "action": "create", "reasoning": "r"},
        ]}],
    })
    calls = _stub(monkeypatch, tmp_path, canned=canned)
    cg.capture("email the editor")
    props = {name: p for (typ, name, p) in calls}["Email editor"]
    for k in ("Duration min", "Affective", "Blocked on", "Access conditions"):
        assert k not in props   # absent stays absent — flat-default behavior preserved
```
*Implementer: match `_stub`'s real return shape — it currently returns the list of create calls; confirm whether each element is `(type, name, props)` or a dict, and adjust the assertions' unpacking to the real shape without changing what they assert.*

- [ ] **Step 2: Run to verify they fail.**
Run (**main agent, Bash**): `python3 -m pytest tests/test_capture_generate.py -k "affect_scope or no_signals" -v`
Expected: FAIL.

- [ ] **Step 3: Implement.**
  - At the top of `capture_generate.py`, add `import capture_fields`.
  - In `_creation_props(type_name, item, link_id)` — signature unchanged (if capture-when changed it, keep its version; this edit is body-only) — after the existing type/link/Context logic, splice in the optional fields, all read from the item itself:
    ```python
    props.update(capture_fields.build_optional_props(
        duration_min=item.get("duration_min"),
        affect=item.get("affect"),
        blocked_on=item.get("blocked_on"),
        access_conditions=item.get("access_conditions"),
    ))
    ```
    *Note: `build_optional_props` never emits a key for a blank/invalid value, so the "no signals" case adds nothing — the existing bare-by-default behavior is preserved.*
  - **Do NOT touch `_create_one` or `capture()`.** Per DECISION 1 the turn-level `capacity_read` is never written to objects — its existing flow into the session/generation logs stays byte-for-byte as it is.

- [ ] **Step 4: Run tests to verify they pass, then the full capture suite.**
Run (**main agent, Bash**): `python3 -m pytest tests/test_capture_generate.py -v`
Expected: PASS, no regressions in the existing capture tests.

- [ ] **Step 5: Commit** (**main agent, Bash**)
```bash
git add scripts/capture_generate.py tests/test_capture_generate.py
git commit -m "feat(capture): write per-item duration, affect, blocked-on, access on capture"
```

---

### Task 4: Memory pass writes the same fields through the same helper

**Files:**
- Modify: `scripts/memory_pass.py` — `apply_candidate` (`:385-440`, specifically the props-building block `:425-433`).
- Modify: `prompts/daily_memory_pass.md` — the JSON contract object (`:64-78`).
- Test: `tests/test_memory_pass_fields.py` (**NEW**; mock Anytype, no network).

**Interfaces:**
- Consumes: `capture_fields.build_optional_props` (Task 1); new candidate keys `duration_min`, `affect`, `blocked_on`, `access_conditions`.
- Produces: `apply_candidate` writes any validating optional props on the created object, via the same helper as the capture path (paths cannot diverge). Note this path already conforms to DECISION 1 by construction: each candidate is one entry, so its `affect` is quoted from that entry's own words at the scope the entry states.

- [ ] **Step 1: Add the fields to the memory-pass contract.** In `prompts/daily_memory_pass.md`, inside the JSON object (after `reasoning`), add — worded for the memory pass's verbatim-from-body guard (guard #1: no re-summarizing):

```
    "duration_min": "how many MINUTES, as a number, ONLY if the entry's text states/implies it; null otherwise — never guess",
    "affect": "a short verbatim quote of any feeling/capacity signal in the entry's own words, or null",
    "blocked_on": "verbatim what it's waiting on, if the entry says so, or null",
    "access_conditions": "zero or more of EXACTLY: \"Can-be-done-lying-down\", \"Involves-leaving-house\", \"Requires-talking-to-a-person\" — only if the text indicates one; else empty list"
```

Add a sentence to guard #1 or the surrounding prose: *"These optional fields, like `context_verbatim`, are read from the entry's own words only — if the text doesn't state a duration / feeling / blocker / access condition, leave it null (or empty). Never infer one to fill the field."*

- [ ] **Step 2: Write the failing test** (`tests/test_memory_pass_fields.py`).

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import memory_pass as mp


def test_apply_candidate_writes_optional_fields(monkeypatch):
    seen = {}
    monkeypatch.setattr(mp.gsdo_objects, "create",
                        lambda typ, name, properties: seen.update(properties) or "oid-1")
    monkeypatch.setattr(mp.gsdo_objects, "find_existing", lambda key, name: None)
    monkeypatch.setattr(mp, "_get_object", lambda oid: {"name": "Renew passport"})
    monkeypatch.setattr(mp.g, "find_type", lambda name: {"key": "task", "id": "t"})
    out = mp.apply_candidate({
        "proposed_name": "Renew passport", "proposed_type": "Task", "link_to": None,
        "context_verbatim": "from memory", "duration_min": 40,
        "affect": "been dreading this", "blocked_on": "need the photos",
        "access_conditions": ["Involves-leaving-house"],
    })
    assert out["outcome"] == "created"
    assert seen["Duration min"] == 40
    assert seen["Affective"] == "been dreading this"
    assert seen["Blocked on"] == "need the photos"
    assert seen["Access conditions"] == ["Involves-leaving-house"]


def test_apply_candidate_no_optional_fields_writes_none(monkeypatch):
    seen = {}
    monkeypatch.setattr(mp.gsdo_objects, "create",
                        lambda typ, name, properties: seen.update(properties) or "oid-2")
    monkeypatch.setattr(mp.gsdo_objects, "find_existing", lambda key, name: None)
    monkeypatch.setattr(mp, "_get_object", lambda oid: {"name": "Note a thing"})
    monkeypatch.setattr(mp.g, "find_type", lambda name: {"key": "task", "id": "t"})
    mp.apply_candidate({"proposed_name": "Note a thing", "proposed_type": "Task", "link_to": None})
    for k in ("Duration min", "Affective", "Blocked on", "Access conditions"):
        assert k not in seen
```
*Implementer: confirm the real attribute names on the `memory_pass` module for `gsdo_objects`, `g`, and `_get_object` and match them; the assertions on written props are the contract.*

- [ ] **Step 3: Run to verify it fails.**
Run (**main agent, Bash**): `python3 -m pytest tests/test_memory_pass_fields.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement.**
  - Add `import capture_fields` at the top of `memory_pass.py`.
  - In `apply_candidate`, in the props-building block (currently `:425-433`, after the `Context`/status/link props are set and **before** `gsdo_objects.create` is called), splice:
    ```python
    props.update(capture_fields.build_optional_props(
        duration_min=candidate.get("duration_min"),
        affect=candidate.get("affect"),
        blocked_on=candidate.get("blocked_on"),
        access_conditions=candidate.get("access_conditions"),
    ))
    ```
    Do not change the `needs_clarifying` override, the dedup/read-back, or the return shape.

- [ ] **Step 5: Run tests to verify they pass, then the full memory-pass suite.**
Run (**main agent, Bash**): `python3 -m pytest tests/test_memory_pass_fields.py tests/ -k "memory_pass" -v`
Expected: PASS, no regressions.

- [ ] **Step 6: Commit** (**main agent, Bash**)
```bash
git add scripts/memory_pass.py prompts/daily_memory_pass.md tests/test_memory_pass_fields.py
git commit -m "feat(memory-pass): write duration, affect, blocked-on, access via shared builder"
```

---

### Task 5: Integration & end-to-end verify (REQUIRED — do not skip)

A plan is done only when the feature is wired into the running system and observed working end-to-end. The unit tests above prove the helper and the two write paths in isolation; this task proves a **real capture through the overlay lands the fields in Anytype** and that the **planner reads them.**

**Wiring this feature connects to:**
- `POST /api/capture` → `capture_generate.capture()` → `_create_one` → `_creation_props` → `capture_fields.build_optional_props` → `gsdo_objects.create` (the object now carries Duration min / Affective / Blocked on / Access conditions).
- `daily_plan.py` already reads every one of these back (`:129` duration, `:130,300` affective, `:132,341-342` blocked_on, `:116` access_conditions) into the planner context — the consumers this plan feeds. **This plan changes no reader**; it verifies the existing readers now receive data.
- `memory_pass.apply_candidate` writes the same fields on the extraction path.

- [ ] **Step 1 (main agent, Bash): restart the server** (memory flags a possibly-stale server): stop any running `scripts/server.py`, then `python3 scripts/server.py` and load the overlay (`docs/overlay_daily.html`).

- [ ] **Step 2 (main agent): drive a real capture** through the Add tab via the `verify` skill, with a two-item dump where June's words attach the feeling to ONE item only (fidelity case (a) — the scope she gave is the scope that lands; case (b), a dump-wide feeling on every item, is covered at the unit level in Task 3 so this live pass stays small), e.g.:
  *"CD-TEST book the dentist — a quick 10 minutes but I have to call them, and I'm dreading it; also waiting on my insurance card before I can. And CD-TEST water the ficus."*
  (Prefix both item names `CD-TEST` so the cleanup in Step 4 is unambiguous.)

- [ ] **Step 3 (main agent, Bash): read the created objects back from the live space** (`gsdo_anytype.fetch_all_objects` / `_get_object`) and confirm:
  - On `CD-TEST book the dentist`: `Duration min` == 10; `Affective` holds the dread wording (verbatim, free text — NOT a number); `Blocked on` mentions the insurance card; `Access conditions` includes `Requires-talking-to-a-person`.
  - On `CD-TEST water the ficus`: `Affective` is EMPTY — June gave that item no feeling, so it carries none (the scope of "I'm dreading it" was the dentist call; widening it would be the agent inventing scope — DECISION 1), and no `Duration min` / `Blocked on` / `Access conditions` were invented.
  Then run `python3 scripts/daily_plan.py` (or its context-builder) and confirm the dentist task's line now shows the duration and the "blocked on" / affective annotations — i.e. the planner is fed, not starved.

- [ ] **Step 4 (main agent, Bash): delete BOTH test objects** from June's real space (`API-delete-object` / the delete path used by other cleanups) and re-fetch to confirm they're gone. **Nothing this task created may remain in her space.**

- [ ] **Step 5 (main agent, Bash): full suite, clean tree.**
Run: `python3 -m pytest tests/ -q`
Expected: all green. Confirm the conftest real-data tripwire did not fire (no test wrote to the real space).

- [ ] **Step 6: Commit** (**main agent, Bash**)
```bash
git add -A
git commit -m "test(capture): end-to-end verify optional fields land in Anytype and feed the planner"
```

---

## Self-Review (author checklist — done)

- **Spec coverage:** (1) ask+write `Duration min` — contract Task 2, write Task 3, helper Task 1 ✓; (2) affect persisted under June's **fidelity rule** — per-item `affect` in the contract with scope-from-her-words in both directions (Task 2), written to `Affective` (Task 3) with unit tests for both single-item and dump-wide scope, guard #3 verbatim / no scalar-flatten (`_text_prop`, Task 1), blank-when-absent, no invented scope, `capacity_read` untouched in its session-log flow ✓; (3) prompt-notice `Blocked on` + `Access conditions`, readers already wired — Task 2 contract + Task 3 write, access held to the live 3 options with the growth path named (DECISION 2) ✓; (4) same contract changes in `memory_pass` — Task 4 ✓. Out-of-scope items enumerated and held, incl. the affective-upkeep loop parked with create-vs-update ✓. Sequencing constraint (build after capture-when; re-read the moving contract) at top ✓. Final integration-and-verify task naming the real call site + live read-back + scope-fidelity check (case (a) live, case (b) at unit level) + self-clean ✓.
- **Placeholder scan:** none — every code step carries real code; the spots that depend on capture-when's in-flight edits say explicitly "re-derive the real anchor and extend additively," which is the honest instruction, not a hand-wave.
- **Type consistency:** `build_optional_props(*, duration_min, affect, blocked_on, access_conditions) -> dict` is used identically in Tasks 1/3/4; `_creation_props` keeps its existing signature (body-only edit, no threading); contract keys `duration_min` / `affect` / `blocked_on` / `access_conditions` match between the prompt (Task 2), the parse defaults (Task 2), and the reads (Task 3); memory-pass candidate keys match between its prompt (Task 4) and its write (Task 4).
- **DRY / one-contract guard:** all validation lives once in `capture_fields`; both write paths call it — the divergence the flags doc warned about is structurally prevented, not just remembered — and it is the named single extension point for June's "what should an agent know about a kind of day" design thread.

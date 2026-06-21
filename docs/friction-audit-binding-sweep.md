# Friction audit — binding + sweep in a new repo (2026-06-20)

First time running bind-and-sweep in a repo other than controlled-drift itself (grounded-recollection). Full session log available in the Claude Code transcript. This doc catalogs every friction point, failed command, and output failure, with fix proposals. Source of truth for what to build next to make this system usable across repos.

---

## A. Code bugs (silent failures)

### A1. `load_context()` can't read multi-goal bindings — goal context silently lost

**What happened:** The GRA project belongs to both Builder practice and Scholarly practice. The instance wrote `.gsdot` with `"goals": [...]` (plural key). `load_context()` in `gsdt_bind.py` reads `bt.get("goal")` (singular key). Result: `load_context()` returns `Goal: None` for GRA — every future instance that opens this repo gets no goal context.

**Confirmed:** `python3 -c "from gsdt_bind import load_context; ctx = load_context('...grounded-recollection'); print(ctx['goal'])"` → `None`.

**Fix:** `load_context()` should handle both `goal` (singular, existing format) and `goals` (plural, multi-goal format). `init_binding()` should accept `goal_ids: list` and write plural format when given multiple. Schema change is backwards-compatible — single goal stays as `goal`, plural writes `goals`.

---

### A2. `init_binding()` only accepts one goal_id

**What happened:** Because `init_binding(folder, project_name, goal_id=None, ...)` takes a single goal, the instance couldn't use it for GRA's two-goal binding. It wrote inline Python instead — bypassing all the safety checks in `init_binding()`.

**Fix:** `init_binding()` should accept `goal_ids: list = None` as well as `goal_id` (single, kept for backwards compatibility). When `goal_ids` has more than one entry, write `goals` array to `.gsdot`; `load_context()` handles it (see A1).

---

### A3. `_write_claude_md()` was never called — Controlled Drift binding section missing from GRA CLAUDE.md

**What happened:** Because the instance wrote inline Python instead of calling `init_binding()`, `_write_claude_md()` was skipped. GRA's CLAUDE.md has no `## Controlled Drift binding` section. Future instances opening GRA have no agent-readable record of the binding, project context, or arc position rationale.

**Confirmed:** `grep "Controlled Drift binding" .../grounded-recollection/CLAUDE.md` → no match.

**Fix (immediate):** Call `_write_claude_md()` for GRA now to repair the missing section.

**Fix (structural):** SKILL.md must say explicitly: **always call `init_binding()` for binding creation — never write inline Python.** The current instruction ("Call `init_binding()`") wasn't strong enough to prevent the workaround when the function didn't fit (single goal_id limitation triggered the bypass). Fixing A2 removes the motivation to bypass it.

---

### A4. `sweep.py signals` only accepts one filepath — multiple paths cause exit code 2

**What happened:** The instance tried:
```
python3 scripts/sweep.py signals gra/store.py gra/trace.py gra/config.py ...
```
Got `exit code 2`. Then tried again with a different set of files — same error. Then resorted to a bash for-loop calling `sweep.py signals` per file.

**The CLI accepts exactly one filepath:** `p_sig.add_argument("filepath")` — no `nargs="*"`.

**Fix (trivial):** Change `add_argument("filepath")` to `add_argument("filepath", nargs="+")` and update the CLI to loop over all paths. Or just document clearly that it's one-at-a-time (the for-loop pattern the instance eventually used works fine).

---

### A5. `sweep.py signals` returns `[]` for planning docs (by design, but confusing)

**What happened:** The for-loop on code files returned `[]` for all of them (gra/*.py files had no `# TODO`, `# FIXME`, `# HACK`, or `NotImplementedError`). The instance ran it, got empty arrays, continued — but this looks like a failure.

**This is correct behavior** — `signals` only finds explicit code-level markers, not semantic todos. Planning docs and design files are supposed to be read by Haiku subagents, not scanned for markers.

**Fix:** Clarify in SKILL.md: `sweep.py signals` is for code files with explicit marker comments only. If no markers exist, `[]` is normal — it means the file has no stubs. Planning/docs sweep is a Haiku reading task, not a signals scan.

---

## B. Skill instruction gaps

### B1. Sweep subagents not given the existing stream list (no gap-analysis constraint)

**What happened:** The first planning subagent returned a large proposal with substantial overlap with what was already captured. It had no information about what streams already existed in Anytype, so it surfaced everything.

**The fix that worked (discovered mid-session):** Give each subagent the existing stream list explicitly and tell them: "return ONLY what's NOT covered by these." This gap-analysis frame dramatically reduced noise. Combined with territory splitting (two agents reading different file sets), the second round was much more targeted.

**Fix:** SKILL.md Mode 2 Step 2 subagent dispatch should include a template for gap-analysis framing:
- Always load bound project's existing sub-projects BEFORE dispatching subagents
- Include the stream list in each subagent prompt with explicit instruction: "only flag what's NOT already covered by this list"
- Split territory: Agent A → planning files, Agent B → code signals, Agent C → docs. Never one agent for everything.

---

### B2. No instruction to read `work_stream_register.md` as the FIRST step of naming

**What happened:** The register spec exists. SKILL.md mentions reading it ("read it first") inside the synthesis step description. The instance ignored it — proposing names in whatever register came naturally — then had to iterate 5+ times through correction cycles.

**Fix:** Make reading `work_stream_register.md` a named, numbered step that happens BEFORE any name proposal, not an instruction buried inside a synthesis description. Something like:

```
Step 0 — Before proposing any names: read REPO/docs/work_stream_register.md now.
Do not propose stream names until you've read it.
```

---

### B3. Binding creation flow doesn't say "never bypass init_binding()"

**What happened:** The binding creation flow in SKILL.md says "Call `init_binding()`" but doesn't say what happens if you don't. When `init_binding()` didn't support the multi-goal case, the instance reasoned its way around it rather than raising the limitation.

**Fix:** SKILL.md binding creation flow should say: "If `init_binding()` doesn't support your case, surface the gap — do not work around it by writing inline Python. The safety checks in `init_binding()` (read-back, CLAUDE.md write, ding) exist for a reason; bypassing them silently breaks the system."

---

## C. Output register failures

### C1. Labels without descriptions (internal shorthand as stream names)

**What happened:** First sweep proposal used project-internal terms as stream names:
- "VALUES.json authoring" — opaque without context
- "B-PRIME" — completely opaque
- "Flow-D" — June didn't recognize this term at all
- "Caller layer build" — unclear what it means

These are names that make sense *inside the project's design history* but are unreadable as a map someone hasn't been living in.

**Fix:** Work stream register spec already covers this ("The name must carry meaning on its own... could you hand this name to someone unfamiliar with the project?"). The issue is it wasn't read. See B2.

---

### C2. Overcorrection to vague generics after label feedback

**What happened:** After being told the labels were unreadable, the instance swung to vague descriptions:
- "How the system decides what to surface when someone asks"
- "The piece that surfaces GRA memories into live sessions"

These describe what something does at such a high level they're not scannable.

**Pattern:** This is a binary oscillation — too compressed → too vague → correct. The right answer (name the body of work in plain words, 4–8 words) was in the register spec. The oscillation would have been short-circuited by reading the spec first.

---

### C3. Project-internal jargon ("Flow-D") in user-facing summaries

**What happened:** "Flow-D" appeared in the sweep proposal without definition. June said it was "completely opaque." It's a term from GRA's own design history (the counter-training priming move for Flow-D bias) that the instance had read in docs and carried forward as a label.

**Fix:** When summarizing findings from a project's own docs to the project's owner, define internal terms on first use or rephrase in plain language. Do not assume the human carries the same compressed label the AI just read.

---

## D. Sweep reading failures

### D1. Missed VALUES.json actual completion state

**What happened:** The sweep proposed "VALUES.json authoring" as a significant open stream. June said it's mostly done and the remaining items depend on other streams. The sweep had read VALUES.json but didn't assess completion state accurately.

**Root cause:** The subagents weren't asked to check completion state — they were asked to find open work. A file being "mostly done" registers as "has open work" unless the agent is explicitly asked: "what's actually finished vs. still open?"

**Fix:** Sweep synthesis should include a completion-check pass: for any file-level work item, quickly check the actual file state before proposing it as open.

---

### D2. Missed the richer capture path vs. Plan 2 distinction

**What happened:** The sweep proposed one "Capture path build" stream (Plan 2 — the basic encoding step). June noted the richer version (the qualitative methods formation layer, designed via workshop, not yet specced) was a distinct stream that was missed entirely.

**Root cause:** The instance read the files that described the Plan 2 scope and didn't read far enough to find the design-conversation status of the formation layer.

**Fix:** Sweep subagents need to be instructed to surface design-conversation items and open design questions, not just implementation todos. "What is still being designed?" is a different question from "what still needs to be built?"

---

### D3. Instance asked June to re-explain information that was in the repo

**What happened (multiple instances):**
- "Which streams does VALUES.json depend on?" — answerable from the repo
- "Is Stream 3 and Stream 5 actually the same?" — answerable from the design docs

June explicitly said: "I do not want to have to re-explain things over and over again — that should have turned up in the sweep."

**Fix:** Before asking June a question about project state, check the repo first. If the question is genuinely unanswerable from the docs, say what you read and why it's still unclear — don't start with the question.

---

## E. UX / interaction failures

### E1. Multiple confirmation-proposal-correction cycles exhausted spoons

The binding + sweep flow required approximately:
- 5 rounds on naming register (labels → vague → better → still not right → final)
- 3 rounds on VALUES.json scope
- 2 rounds on the formation/surfacing distinction

Each round costs spoons. The register spec exists to make this a one-round process. The issue is instruction-following discipline, not the spec itself.

---

### E2. Self-explanation of better swarm approach came only on explicit request

**What happened:** The second subagent swarm worked much better. June asked why. The instance explained: gap-analysis framing + territory splitting.

**What should have happened:** Proactively surface what worked differently at the point of synthesis — "I structured this differently from the first round: I gave each agent the existing stream list and split them by file type. That's why the output is cleaner." June shouldn't have had to ask.

---

## Fix priority

**Immediate (repair GRA binding now):**
1. Call `_write_claude_md()` for GRA to add the missing Controlled Drift binding section (A3)
2. Update `.gsdot` or `load_context()` so the two goals are readable (A1)

**High (structural bugs):**
3. `init_binding()` multi-goal support — `goal_ids: list` (A2)
4. `load_context()` reads both `goal` and `goals` (A1)

**Medium (skill instruction quality):**
5. Add gap-analysis subagent template to Mode 2 sweep (B1)
6. Make reading `work_stream_register.md` a named Step 0 (B2)
7. Add "never bypass init_binding()" language to binding creation (B3)
8. Clarify `sweep.py signals` scope (A5)

**Low (polish):**
9. `sweep.py signals` accept multiple filepaths (A4)
10. Sweep synthesis: completion-check pass before proposing open items (D1)
11. Sweep subagents: include "what's still being designed?" as an explicit question (D2)

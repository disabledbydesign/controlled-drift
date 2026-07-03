# Daily Memory Pass — memory-to-Anytype extraction

**Where this sits (read first).** Claude Code keeps its own persistent memory as plain markdown
files (YAML frontmatter + body) under `~/.claude/projects/<project>/memory/`. Some of what lands
there is genuinely Claude's own operating knowledge (how to behave, what June prefers) — that
belongs in memory and should stay there. But some of it is really June's — a task, a decision, a
commitment she'd look for or act on — misfiled into memory because whoever wrote it judged the
save-location wrong at write-time. This pass exists to catch the second kind and move it into
Anytype, where June's task system actually lives.

**Why you're here.** You are not classifying every memory entry from scratch — you are looking
for the ones that don't belong where they are. Most entries you'll see are correctly filed
(`feedback`/`user`/`reference` entries describing how Claude should behave). Read every entry
anyway: a misfiled item was very likely also *mis-typed* by the same bad judgment that misfiled
it, so a real task of June's can be sitting there labeled `feedback` or `project`. Judge from the
actual content of each entry, using its stated `metadata.type` as one signal, never as a filter
that lets you skip entries typed a "safe" way.

**What "belongs in Anytype" means.** June would look for this, act on it, or need it surfaced to
her — a task she needs to do, a decision that changes what work happens next, a commitment with a
deadline. **What does NOT belong in Anytype:** anything that only shapes how Claude should behave
or what Claude should know about the codebase/project/June's working style — that's correctly
memory, leave it alone.

## THE THREE GUARDS — read carefully, these are not optional

1. **Minimal re-summarization.** When you flag an entry for Anytype, carry the memory's own words
   into `context_verbatim` — do not paraphrase, compress, or improve the wording. The point is to
   move the content, not re-author it. Quote the relevant text directly from the body.
2. **Do not overstretch.** If the entry doesn't say enough to confidently pick a type or a link
   (which Goal/Project it belongs to), do NOT invent one. Set `needs_clarifying: true`, still
   carry the verbatim text in `context_verbatim`, and leave `proposed_type`/`link_to` as your best
   guess but understand a human will confirm before anything is created as anything other than a
   plain flagged item. Never invent a project or goal link that isn't actually named or clearly
   implied by the text.
3. **Only flag what's genuinely June-facing.** When in doubt between "this shapes Claude's
   behavior" and "June would act on this," lean toward leaving it as memory — an under-flag here
   just means the item stays exactly where it already is (no harm); an over-flag creates Anytype
   clutter and duplicate-risk. The bar is "would June look for or act on this," not "is this
   interesting or informative."

## HOW THIS RUNS — read before producing output

You are running **headless and automated** — there is no human in the conversation to confirm
with. Produce the JSON block below for every entry you're given, even ones you conclude don't
belong in Anytype at all (mark those `proposed_type: null` so the caller knows you looked at them
and made a call, rather than silently omitting them).

- **Do NOT ask questions or wait for confirmation.** June reviews every flagged candidate before
  anything gets written to Anytype (this is a proposal, not a write) — Slice 1/2 of the pass are
  designed so nothing lands without a read-back-proven, deterministic Python step after you.
- **Live schema below.** The Anytype type/property list is injected fresh each run — use ONLY the
  types and properties listed there. Don't assume last week's schema; if a type you'd expect isn't
  in the list, it doesn't exist yet — use the closest real one or `needs_clarifying`.
- **Cross-project entries are independent.** Each entry is tagged with which project's memory
  folder it came from. Judge each on its own; don't assume two entries from different projects are
  related just because they arrived in the same run.

## REQUIRED OUTPUT — THE JSON BLOCK ONLY

Output **ONLY** one fenced ```json array — nothing before or after. One object per entry you were
given (do not skip any; do not add entries you weren't given). Shape:

```json
[
  {
    "source_entry": "the entry's `name` field, copied exactly",
    "source_project": "the project slug this entry came from, copied exactly",
    "belongs_in_anytype": true,
    "context_verbatim": "the exact quoted text from the entry's body that supports this — verbatim, not paraphrased",
    "proposed_type": "one of the live schema type names above, or null if belongs_in_anytype is false",
    "proposed_name": "a short name for the Anytype object, in June's own words where possible",
    "link_to": "the exact name of an existing Goal/Project to link to, or null if none is clearly named",
    "needs_clarifying": false,
    "reasoning": "one or two sentences: why this belongs in Anytype (or doesn't), plain language"
  }
]
```

Set `belongs_in_anytype: false` (and `proposed_type: null`, `needs_clarifying: false`) for every
entry that's correctly filed as memory — most of them will be. `needs_clarifying` is only
meaningful when `belongs_in_anytype` is true and the type/link couldn't be determined confidently.

---

## ACTUAL INPUTS FOR THIS RUN — authoritative, use ONLY these

*(injected by `scripts/memory_pass.py`: the live Anytype type/property schema, then the list of
unextracted memory entries — each with its source project, `name`, `description`,
`metadata.type`, and full body text)*

# How to write a work stream — the one spec

*This is the single canonical spec for how a work stream's name and description get written. Every place that creates or edits a work stream points here: the Orient fix-up pass, the weeding gate, the file sweep, and binding creation. If the register drifts, fix it here, once.*

*Why this exists: the map renderer is deterministic — it shows exactly what's stored. So the whole quality of the map depends on what gets written into the fields in the first place. The failure that produced this spec: instances filled the fields in whatever register made sense to them (marketing-experience names, implementation jargon, coded status words), and the map became unreadable. The fix is not in the renderer. It is here, at entry: constrain the register.*

## What June needs from the map

To **see the whole picture at once** and know she's still in the arc somewhere. Each stream has to be readable **at a glance**, in **plain words she'd use herself**. She reads it; she never decodes it.

## The format that gets stored

A work stream is an Anytype Project. Two things carry the map:

1. **The name** — the object's name.
2. **Two lines stored in `gsdo_context`**, in exactly this format (the renderer parses it):

```
what it is — [one plain sentence: what this stream is]
next step — [the single clear next move]
```

That's it. Two lines. The renderer shows them as *What it is:* and *Next step:*, and lists the stream's Tasks underneath.

For a **○ later** stream (Backburner), only `what it is` is needed — there's no active next step.
For a **finished** stream, don't write a description — mark its Engagement **Done** and it drops to the Finished section, name only.

## Register rules (the part that kept getting violated)

- **Plain language — what June would say out loud.** Not how it's built.
- **One sentence per line.** If `what it is` runs past one sentence, cut it.
- **No filenames, no function names, no module names.** "daily_plan.py", "the LLM prompt", "the parser" — none of these belong in the map. They are not how June holds the work.
- **No jargon.** "clock-time-anchored", "capacity-paced output", "scaffolded", "pipeline seam" — out.
- **No coded status words.** "held", "live edge", "horizon", "backburner" used as labels she has to translate. The circle (● / ○) already carries active-vs-later; don't restate it in words.
- **The name names the body of work, short (4–8 words).** A feature/experience description is fine *as the `what it is` line*, but it is not the name. The name answers "what is this chunk of work," the line answers "what does it do for me."
- **The name must carry meaning on its own.** Reading just the name, June should know what that stream is about — not need to read the description to decode it. If the name doesn't tell her what the work involves, it's too abstract or too compressed. Test: could you hand this name to someone unfamiliar with the project and have them know what the work is? If not, make the name more specific.
- **One concern per stream.** If a stream name has an "and" connecting two unrelated things, it's two streams. Compressing distinct concerns into one stream hides the shape of the work and makes the map unreadable. When concerns genuinely belong together (they'd never move independently), a category name is fine — but name what the category actually is, not a list of its contents.

## Good vs. bad — the same stream, both ways

GOOD:
```
Name:        Finish the daily-plan pipeline
what it is — takes a messy brain-dump and hands you back a real day
next step — build the planning half — pick what matters, fit it to your day
```

BAD (this is what kept happening):
```
Name:        Getting your thoughts in, and a usable daily plan out
what it is — finishing the daily plan pipeline: weeding is built + tested; build is
             turning system data into a clock-time-anchored, capacity-paced daily output
next step — complete and test daily_plan.py output against real use; then close the stream
```

Why the bad one fails: the name describes the *finished experience* instead of the work; `what it is` is three jargon phrases jammed into one block; `next step` has a filename and isn't a clear single move.

## When a stream is already done

Don't rewrite a finished stream's description. Confirm with June, then mark it Done:

```python
import gsdo_objects as o
o.update(stream_id, properties={"Engagement": "Done"})   # -> drops to Finished
```

## How an instance applies this

When proposing names/descriptions (Orient fix-up pass, weeding, sweep, binding), **read this file first**, then propose plain-language name + the two lines, and let June confirm or edit each. Write via `gsdo_objects.update()` (it resolves value shapes correctly). Read back, then ding.

# Reading the friction log

**Status:** first written version, 2026-07-19. Before this, triage was done by hand once and the
only record was `docs/handoff_2026-07-16_friction-log-triage.md` — a record of that one pass, not
instructions. This is the instruction. Revise it as passes teach us more.

⚠ **`tests/test_signal_record_shape.py` pins this document to the code.** If the record shape
changes, that test fails and names this file. Fix both in the same commit.

## Where it is

`scripts/data/signal_log.jsonl` — one JSON object per line, append-only, never rewritten.
Written by `scripts/signal_log.py::log_signal`. Gitignored: it carries June's real medical and
financial detail and does not go to a remote. The images it points at live in
`scripts/data/shots/`, written by `scripts/shot_store.py::save_png`, and are gitignored for the
same reason.

## What one entry looks like

Every record has exactly four keys: `ts`, `source`, `reference`, `raw`.

Friction entries are the ones with `source == "log_day"`. Other sources live in the same file and
are **not** friction — filter by source first. The full set `signal_log.py` allows is `log_day`,
`checkin_reply`, `config_authoring`, `config_correction`, and `plan_renegotiation`. Older lines
also carry `plan_deferral`, a source that was retired on 2026-07-18 because it recorded a machine
event rather than June's own words; those entries were moved to `corrections_log`, and any left in
this file are historical.

`raw` is June's own words, stored verbatim and never classified at write time. `reference` for a
friction entry:

| key | meaning |
|---|---|
| `kind` | always `"log_day"` |
| `tags` | `["issue"]` for friction, `["day"]` for how-the-day-went. Both may appear. |
| `shot` | filename of a PNG of what she was looking at. Absent on a text-only entry. |
| `view` | `{"tab": …, "detailId": …}` — which screen she was on. |
| `target` | what she pressed: `tag`, `label`, `text`, `data`, and `chain` (that element and its ancestors outward, innermost first). |
| `via` | how she opened the capture: `longpress` / `shortcut` / `rightclick` / `button`. |
| `marks` | what she drew, as geometry: `points`, `box` `[x, y, w, h]`, and `closed`. |
| `size` | the image's pixel dimensions, `{"w": …, "h": …}`. **`marks` coordinates are in these pixels and mean nothing without it.** |

Only `kind` and `tags` are always present. Everything from `shot` down is optional and additive:
an entry written without them is byte-identical to what the log held before 2026-07-19. Every one
of the 45 `log_day` entries recorded up to that date has only `kind` and `tags`, so an early pass
will be reading text alone.

A `resolved` key appears at the top level of a few entries. **No code writes it** — it is added by
hand during a triage pass to record what became of an item. Keep doing that; it is how a pass
leaves a trace in the file it read.

## How to read one

1. **Read `raw` first, and take it at face value.** It is her account of what went wrong. It is
   not a bug report to be corrected into one.
2. **Open the picture if there is one:** `http://localhost:5050/api/shot/<reference.shot>`, or
   directly at `scripts/data/shots/<name>`.
3. **Use `marks` to find where she was pointing.** `box` is the region. `closed: true` means the
   stroke ended near where it started, which usually means she drew around something;
   `closed: false` usually means she drew a line at something. This is what the geometry is for —
   a picture alone leaves the extent of a hand-drawn mark ambiguous.
4. **Treat `target` as a hint, never a claim.** Elements overlap and a finger lands slightly off.
   If `label` does not make sense, look outward along `chain`. If it still does not, ignore it —
   `raw` and the picture are the evidence, `target` is a convenience.
5. **`view` tells you which screen to go look at yourself.** Reproduce before concluding.

## What NOT to do

- **Do not classify at read time and write the classification back into the log.** The log is
  capture-only by design; categories are meant to emerge across a pass, not be stamped per entry.
- **Do not treat absence as evidence.** A missing `shot` means the render failed or she used a
  build without it, not that the friction was minor.
- **Do not aggregate her.** Counting entry-point use is fine (`scripts/friction_report.py`).
  Counting *her* — how often she logs, streaks, trends in her behaviour — is not what this is for.
- **Do not send these images anywhere.** They are pictures of her real screen.

## Related

- `scripts/signal_log.py` — the writer, and the source of truth for the four record keys.
- `scripts/server.py`, the `/api/logday` handler — the source of truth for which `reference` keys
  a friction entry can carry, and `GET /api/shot/{name}` — the read route for a stored image.
- `scripts/friction_report.py` — what the log holds and which way in gets used.
- `docs/handoff_2026-07-16_friction-log-triage.md` — the first pass, as a worked example.
- `docs/superpowers/plans/2026-07-19-snapshot-friction-capture.md` — why the capture works this way.

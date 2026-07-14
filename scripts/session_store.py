#!/usr/bin/env python3
"""The session log — the working memory beneath the overlay's capture/weed + negotiate.

The overlay's surface actions are not isolated transactions. When June captures a task at
10:23 and renegotiates her plan at 11:05, the second turn is better if it can see the first.
And her access needs live in a channel a generic CRUD log throws away: *how* she said a thing
(the raw words carry capacity/affect she doesn't always name), *why* an item landed where it
did (so she never has to re-derive it), and her *corrections* (the richest signal, and the one
that retroactively reveals a silent miscategorization). So each turn is logged with more than
the transaction. Full rationale: docs/session_layer_design.md.

Two streams share one store but never mix: "capture" (the Add tab — weed/capture) and
"negotiate" (the Today tab's ask-field renegotiation). June's call — they're different
conversations.

The log is the design's answer to the failure mode that actually kills adoption: the system
degrades, June can't attribute it to a fixable cause, forgets it could be the issue, and stops
using it. So failures are logged loudly (never silent), and because entries are timestamped and
keep raw inputs, *silent* failures become detectable after the fact — a correction that
references an earlier capture is a "that capture was wrong" signal living in the relation
between two entries. That's data a learning loop can point at.

Conventions mirror plan_store.py: atomic os.replace writes, cd_paths.config_file() for the
location (so the test sandbox redirect always applies), tolerant loads (a missing/corrupt log
is an empty log, not a crash).
"""
import os, json, threading, datetime as dt
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cd_paths

# The overlay server is multi-threaded, and append is a read-modify-write (load → append →
# write). The atomic os.replace stops a *corrupt* file, but two concurrent appends (e.g. a
# background capture's entry racing a sync /api/capture/undo) could still LOSE one — a silent
# dropped entry, the exact failure this log exists to prevent. This lock serializes the whole
# RMW in-process so no append is lost.
_WRITE_LOCK = threading.Lock()

# "deferral" holds "not today" events (a task/block June took off today's list). It rides the same
# 8h window as the conversation streams so a same-day regenerate can honor a fresh deferral and then
# let it expire — see plan_generate._recent_deferral_ids / build_context.
STREAMS = ("capture", "negotiate", "deferral")

# How much session history to hand the LLM on the next turn. The window keeps a prior day from
# bleeding in; the token budget keeps the prompt bounded as the day accumulates turns. Oldest
# entries fall off first (truncate, not summarize — simple, and enough until real volume data
# says otherwise). ~4 chars/token is the usual rough estimate; we only need it to bound, not be
# exact.
DEFAULT_WINDOW_HOURS = 8
DEFAULT_TOKEN_BUDGET = 3000
_CHARS_PER_TOKEN = 4


def _log_path():
    return cd_paths.config_file("session_log.json")


def _ensure_dir():
    os.makedirs(cd_paths.config_dir(), exist_ok=True)


def load_log():
    """Return the whole log {"version", "entries":[...]}, or an empty log if none/corrupt.

    A missing or unreadable log is a real, benign state (first run) — surfaced as empty, never
    a crash that would take the overlay down with it.
    """
    try:
        with open(_log_path()) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"version": 1, "entries": []}
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return {"version": 1, "entries": []}
    return data


def _write_log(data):
    """Atomic write — the server is multi-threaded, so a half-written log must never be read."""
    _ensure_dir()
    path = _log_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _validate_stream(stream):
    if stream not in STREAMS:
        raise ValueError(f"unknown session stream {stream!r} (expected one of {STREAMS})")


def append_entry(stream, entry):
    """Append one turn entry to a stream. Stamps `ts` (ISO, now) and `stream` if absent.

    `entry` is the rich per-turn dict — the canonical capture/weed shape is:
        {intent, raw_input,
         capacity_read: {text, source: "stated"|"inferred", reasoning} | None,
         groups: [...through-line groups...] | None,   # fits weed output, never a flat list
         created: [{id, type, name, project, alignment_reasoning}],
         corrections: [...],
         result_summary}
    Negotiate/reorder entries also carry:
        {request_type: "reorder"|"generate"|"capture"|"stuck"}
    which the learning loop uses to analyse which operations June actually reaches for.
    The store is shape-tolerant: it persists whatever dict it's given (so undo/failure
    entries and future intents need no schema change here). Returns the stamped entry.
    """
    _validate_stream(stream)
    if not isinstance(entry, dict):
        raise TypeError(f"append_entry: entry must be a dict, got {type(entry).__name__}")
    rec = dict(entry)
    rec.setdefault("ts", dt.datetime.now().isoformat())
    rec["stream"] = stream
    with _WRITE_LOCK:                 # serialize the read-modify-write so no append is lost
        data = load_log()
        data["entries"].append(rec)
        _write_log(data)
    return rec


def mark_undo(stream, target_id, detail=None):
    """Record that something was undone (a checkoff reversed, a capture removed). The undo IS
    part of the session record — the next turn's LLM should see it, and the learning loop reads
    it as a correction signal. Cheap, no LLM. Returns the appended entry."""
    return append_entry(stream, {
        "intent": "undo",
        "target_id": target_id,
        "result_summary": detail or f"undid {target_id}",
    })


def log_failure(stream, kind, detail):
    """Record a failure loudly into the log — context-window-exceeded, create-failed,
    parse-failed. NEVER silent: a silent failure is the start of the abandonment cascade this
    log exists to defeat. Excluded from recent_entries() by default (it's health data, not
    conversation); read it via failures(). Returns the appended entry."""
    return append_entry(stream, {
        "intent": "failure",
        "kind": kind,
        "detail": detail,
    })


def _estimate_tokens(entry):
    return len(json.dumps(entry)) // _CHARS_PER_TOKEN


def _within_window(entry, cutoff):
    """True if the entry is at/after the cutoff. An unparseable/absent ts is kept, not dropped —
    losing data silently would defeat the log's purpose; better to keep a stray entry."""
    ts = entry.get("ts")
    if not ts:
        return True
    try:
        return dt.datetime.fromisoformat(ts) >= cutoff
    except (ValueError, TypeError):
        return True


def _entries_in_window(stream, hours, include_failures):
    _validate_stream(stream)
    cutoff = dt.datetime.now() - dt.timedelta(hours=hours)
    return [e for e in load_log()["entries"]
            if e.get("stream") == stream
            and _within_window(e, cutoff)
            and (include_failures or e.get("intent") != "failure")]


def recent_entries(stream, hours=DEFAULT_WINDOW_HOURS, token_budget=DEFAULT_TOKEN_BUDGET,
                   include_failures=False):
    """The bounded conversation history for a stream, oldest→newest, for the next PROMPT.

    Two bounds, both load-bearing FOR AN LLM CALL: the time window stops a prior day bleeding
    in; the token budget keeps the prompt from growing without limit as turns accumulate —
    oldest entries drop first. Failure entries are excluded by default (they're for the health
    view, not the conversation); pass include_failures=True to see them.

    ⚠️ Do NOT use this for a user-facing receipt/history view — the token-budget trim silently
    drops older entries once a session's turns get verbose, which reads to June as "my earlier
    tasks got removed" (that exact confusion, 2026-07-01). Use receipt_entries() for that.
    """
    rows = _entries_in_window(stream, hours, include_failures)

    # Drop oldest until the running token estimate fits the budget. Walk newest→oldest keeping
    # what fits, then restore chronological order for the prompt.
    kept, used = [], 0
    for e in reversed(rows):
        cost = _estimate_tokens(e)
        if used + cost > token_budget and kept:
            break
        kept.append(e)
        used += cost
    kept.reverse()
    return kept


def receipt_entries(stream, hours=24, include_failures=False):
    """Every turn in the window, oldest→newest — the honest "added this session" view.

    Unlike recent_entries(), this has NO token budget: it's read by June, not fed to a model,
    so nothing should silently vanish because the JSON got big. A generous 24h window (not
    DEFAULT_WINDOW_HOURS=8) so a receipt spanning late night into morning doesn't cut itself
    off mid-session either.
    """
    return _entries_in_window(stream, hours, include_failures)


def failures(stream=None, hours=None):
    """Read failure entries — the health view a maintenance pass or the morning push uses to
    surface degradation ('capture's been erroring this week') so June never has to be the one
    who notices and diagnoses. `stream`=None reads across both; `hours`=None reads all of time.
    """
    if stream is not None:
        _validate_stream(stream)
    cutoff = (dt.datetime.now() - dt.timedelta(hours=hours)) if hours is not None else None
    out = []
    for e in load_log()["entries"]:
        if e.get("intent") != "failure":
            continue
        if stream is not None and e.get("stream") != stream:
            continue
        if cutoff is not None and not _within_window(e, cutoff):
            continue
        out.append(e)
    return out


if __name__ == "__main__":
    # Quick self-check: show where the log lives and a per-stream tally.
    log = load_log()
    print(f"session log: {_log_path()}")
    print(f"entries    : {len(log['entries'])}")
    for s in STREAMS:
        conv = recent_entries(s)
        fail = failures(s)
        print(f"  {s:9s}: {len(conv)} recent conversational, {len(fail)} failures")

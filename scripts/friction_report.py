#!/usr/bin/env python3
"""What the friction log holds, and which way in June actually uses.

⚠ WHAT THIS IS NOT. This does not measure June. It measures MECHANISMS — whether an entry point
the system offers is one she reaches for. It reports no rate of logging, no streak, no trend in
her behaviour, and it never prompts or nudges. She asked for it so an unused way in could be
found and retired instead of sitting there forever; that is the whole scope.

⚠ IT DECIDES NOTHING. Retiring an entry point is June's call, always. This prints the numbers and
says so. (Her instruction, 2026-07-19: "run it by me first though, of course.")
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import signal_log

WAYS_IN = ("longpress", "shortcut", "rightclick", "button")

# Below this, the log has not seen enough use to say anything about an entry point. Calling one
# "unused" after three captures would be inventing a finding out of noise.
MIN_FOR_A_VERDICT = 15
RARE_SHARE = 0.10


def summarise(signals):
    friction = [s for s in signals if s.get("source") == "log_day"]
    refs = [s.get("reference") or {} for s in friction]
    total = len(friction)

    by_via = {w: 0 for w in WAYS_IN}
    for r in refs:
        v = r.get("via")
        if v in by_via:
            by_via[v] += 1

    unused, rarely = [], []
    # Only entry points that EXISTED for these entries can be judged. Entries written before the
    # capture shipped carry no `via` at all, so they are excluded from the denominator rather than
    # counted as evidence against every way in.
    attributed = sum(by_via.values())
    if attributed >= MIN_FOR_A_VERDICT:
        best = max(by_via.values())
        for w in WAYS_IN:
            if by_via[w] == 0:
                unused.append(w)
            elif by_via[w] < attributed * RARE_SHARE and by_via[w] < best:
                rarely.append(w)

    stamps = sorted(s.get("ts") for s in friction if s.get("ts"))
    return {
        "total": total,
        "with_shot": sum(1 for r in refs if r.get("shot")),
        "with_marks": sum(1 for r in refs if r.get("marks")),
        "by_via": by_via,
        "unused": unused,
        "rarely_used": rarely,
        "since": stamps[0] if stamps else None,
        "until": stamps[-1] if stamps else None,
    }


def _print(out):
    print("Friction log — %d entries%s" % (
        out["total"],
        (", %s to %s" % (out["since"], out["until"])) if out["since"] else ""))
    print("  with a picture: %d    with marks drawn on it: %d" % (out["with_shot"], out["with_marks"]))
    attributed = sum(out["by_via"].values())
    print("  how they were started (%d of %d entries recorded this):" % (attributed, out["total"]))
    for w in WAYS_IN:
        print("    %-11s %d" % (w, out["by_via"][w]))
    # Without this, four zeros under a count of 45 entries reads as "she used none of them" when
    # the truth is that those entries were written before the system started recording which way
    # in was used. Same false finding the warning below guards against, from a different cause.
    if out["total"] and attributed == 0:
        print("  These entries were all written before the system started recording which way in")
        print("  was used, so the zeros above say nothing about any of them yet.")
    if out["unused"] or out["rarely_used"]:
        for w in out["unused"]:
            print("  Never used: %s" % w)
        for w in out["rarely_used"]:
            print("  Rarely used: %s" % w)
        # ⚠ Say this every time, not once in a doc. A way in that is BROKEN records zero uses and
        # looks exactly like one she does not want — and the difference is the difference between
        # fixing a bug and removing something she needs. This nearly happened: the keyboard
        # shortcut shipped-ready with a crash on every keypress (caught building Task 6, 2026-07-19).
        print("  ⚠ Check it still WORKS before reading zero as 'not wanted' — a broken way in")
        print("    counts zero too, and that is a bug to fix, not a feature to remove.")
        print("  Whether to remove any of these is your call — nothing has been changed.")
    else:
        print("  Nothing to report: every way in is getting used, or there is not enough yet to tell.")


if __name__ == "__main__":
    _print(summarise(signal_log.read_signals()))

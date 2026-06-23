#!/usr/bin/env python3
"""The keystone: the morning push — the system comes to June so she initiates nothing.

The whole reason Controlled Drift exists is that under hyperfocus June never thinks to
*go* to the system. A surface she has to open is still an invocation. This script is the
inversion: a scheduled job (launchd, see the .plist) that, each morning, generates a fresh
plan, caches it, and fires a gentle macOS notification — so the day opens with a walkable
path already waiting, no terminal, no asking.

It runs HEADLESS (no human in the loop). It reuses the verified generator and writes the
same cache the overlay reads, so "open the overlay" and "tap the notification" land on the
same plan.

Register is permission-granting, never imperative (June's design DNA): the notification
OFFERS a shape for the day — it never commands or scolds. No "you're behind", no "todo".

Run manually to test:  python3 scripts/morning_push.py
Scheduled by:          ~/Library/LaunchAgents/com.june.controlled-drift.morning.plist
"""
import sys, os, subprocess, datetime as dt
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import plan_generate
import plan_store
import cd_paths
try:
    import notify
except Exception:
    notify = None


def _notify(title, message):
    """Fire a macOS notification. Best-effort: a notification failure must never lose the
    plan (which is already safely cached by the time we get here)."""
    # Escape double-quotes for the AppleScript string literals.
    t = title.replace('"', '\\"')
    m = message.replace('"', '\\"')
    script = f'display notification "{m}" with title "{t}" sound name "Tink"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
    except Exception:
        pass


def _ntfy_topic():
    """The private ntfy topic to push to, or None. Read from ~/.controlled-drift/ntfy_topic."""
    try:
        with open(cd_paths.config_file("ntfy_topic")) as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def _push_to_phone(plan):
    """Push the plan to June's phone via ntfy (free, open-source pub/sub) — the part she
    reads in bed as she wakes. Best-effort: a push failure must never lose the cached plan.

    Sends the woven frame + this morning's moves as a readable body, in permission-granting
    register. The topic is a private unguessable secret (only her phone is subscribed)."""
    topic = _ntfy_topic()
    if not topic:
        return False
    lines = [(plan.get("woven_frame") or "").strip(), ""]
    blocks = plan.get("blocks", [])
    if blocks:
        b = blocks[0]
        lines.append(f"{b.get('label','')}  {b.get('time','')}".strip())
        import re
        for it in b.get("items", [])[:5]:
            task = re.sub(r"^\([^)]*\)\s*", "", (it.get("task") or "")).strip()
            lines.append(f"• {it.get('time','')}  {task}".strip())
    body = "\n".join(l for l in lines if l is not None).strip()
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}",
                                     data=body.encode("utf-8"), method="POST")
        req.add_header("Title", "Today, if you want it")   # ASCII title; body carries UTF-8
        req.add_header("Tags", "sunrise")
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[morning_push] phone push failed (plan is still cached): {e}", file=sys.stderr)
        return False


def _first_line_summary(plan):
    """A short, calm one-liner for the notification body — the first move of the day, if
    there is one; otherwise the opening of the woven frame. Never a count, never a nag."""
    import re
    for block in plan.get("blocks", []):
        for item in block.get("items", []):
            task = (item.get("task") or "").strip()
            # Drop a leading parenthetical aside ("(Optional, only if…) ") — it reads
            # awkwardly as the lead of a glanceable notification.
            task = re.sub(r"^\([^)]*\)\s*", "", task).strip()
            if task:
                return task if len(task) <= 90 else task[:87] + "…"
    frame = (plan.get("woven_frame") or "").strip()
    return (frame[:90] + "…") if len(frame) > 90 else frame or "A shape for today is ready."


def run():
    """Generate the morning plan, cache it, and offer it via notification."""
    try:
        plan = plan_generate.generate_plan(source="morning")
    except Exception as e:
        # Don't fire a cheerful notification on failure — surface the problem honestly,
        # and leave yesterday's cache untouched (generate_plan only writes on success).
        _notify("Controlled Drift", "Couldn't build this morning's plan — open the overlay to retry.")
        print(f"[morning_push] generation failed: {e}", file=sys.stderr)
        return 1

    summary = _first_line_summary(plan)
    # Permission-granting: "here's a possible shape", not "do this".
    _notify("Today, if you want it", summary)
    if notify:
        try:
            notify.ding()
        except Exception:
            pass

    # The keystone of the keystone: push to June's phone so she reads it in bed.
    pushed = _push_to_phone(plan)

    ts = dt.datetime.now().strftime("%A %B %d — %I:%M %p")
    print(f"[morning_push] plan generated + cached at {ts}")
    print(f"[morning_push] notification: {summary}")
    print(f"[morning_push] phone push: {'sent' if pushed else 'skipped (no ntfy topic) / failed'}")
    return 0


if __name__ == "__main__":
    sys.exit(run())

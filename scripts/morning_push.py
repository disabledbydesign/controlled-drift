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
import sys, os, subprocess, time, datetime as dt
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


def _overlay_url():
    """The URL June's phone uses to reach the always-on overlay over wifi — so tapping the
    notification opens the live surface, not just the cached text.

    The phone reaches the Mac at its LAN IP on port 5050 (server binds 0.0.0.0). The LAN IP
    is DHCP-assigned, so we DETECT it fresh each morning rather than hardcoding a value that
    silently rots. An explicit override (~/.controlled-drift/overlay_url) wins if present —
    for pinning a reserved IP, an mDNS .local name, or a tunnel. Returns None if we can't
    determine an address (then no tap-action is attached — the text push still lands)."""
    # 1. Explicit override (a full URL), if June ever pins one.
    try:
        with open(cd_paths.config_file("overlay_url")) as f:
            url = f.read().strip()
            if url:
                return url
    except FileNotFoundError:
        pass
    # 2. Auto-detect the current LAN IP (en0 = wifi on this Mac; en1 fallback).
    for iface in ("en0", "en1"):
        try:
            out = subprocess.run(["ipconfig", "getifaddr", iface],
                                 capture_output=True, text=True, timeout=5)
            ip = out.stdout.strip()
            if ip:
                return f"http://{ip}:5050"   # server.py PORT
        except Exception:
            continue
    return None


# Retry tuning. A background 9 AM job can afford to wait out a transient blip; tests set the
# delay to 0 via this module constant.
RETRY_ATTEMPTS = 3
RETRY_DELAY_S = 5

# Fallback backend, tried once if the primary (Mistral) fails every retry. `claude -p` is the
# right choice for June's plan data: it stays on the Anthropic trust boundary (same privacy ladder
# tier as Mistral — no third-party routing of her health/finance task names), and it's already
# proven to run headless here via the durable claude_token. It's slow (~160s), but a background
# fallback can afford that, and a FRESH plan beats yesterday's stale one.
FALLBACK_BACKEND = "claude"


def _generate_with_retry(attempts=None, delay=None):
    """Generate the morning plan, retrying transient failures. The 9 AM run competes with whatever
    else is using the network; a single 'connection reset' shouldn't cost June her whole morning
    push when the same call succeeds seconds later. Returns the plan, or None if every attempt
    failed. Each failure is logged (never silent).

    Defaults are read from the module constants at CALL time (not bound at def time), so tests can
    zero the delay by setting RETRY_DELAY_S."""
    attempts = RETRY_ATTEMPTS if attempts is None else attempts
    delay = RETRY_DELAY_S if delay is None else delay
    last = None
    for i in range(1, attempts + 1):
        try:
            return plan_generate.generate_plan(source="morning")
        except Exception as e:
            last = e
            print(f"[morning_push] generation attempt {i}/{attempts} failed: {e}", file=sys.stderr)
            if i < attempts:
                time.sleep(delay)
    print(f"[morning_push] generation failed after {attempts} attempts: {last}", file=sys.stderr)
    return None


def _generate_on_fallback():
    """Second-chance generation on the fallback backend when the primary fails every retry. Keeps
    June's personal plan data on the Anthropic trust boundary (no third-party routing); slow, but a
    background fallback can afford it, and a fresh plan beats a stale cached one. One attempt;
    returns the plan or None. Switches CD_BACKEND for just this call, then restores it."""
    saved = os.environ.get("CD_BACKEND")
    os.environ["CD_BACKEND"] = FALLBACK_BACKEND
    try:
        plan = plan_generate.generate_plan(source="morning")
        print(f"[morning_push] primary failed — fresh plan from fallback backend ({FALLBACK_BACKEND})",
              file=sys.stderr)
        return plan
    except Exception as e:
        print(f"[morning_push] fallback backend ({FALLBACK_BACKEND}) failed too: {e}", file=sys.stderr)
        return None
    finally:
        if saved is None:
            os.environ.pop("CD_BACKEND", None)
        else:
            os.environ["CD_BACKEND"] = saved


def _push_failure_to_phone():
    """When there's NO plan to send (generation failed AND no cache), the failure must still reach
    June's PHONE — a Mac-only notification is invisible to someone reading in bed. Honest, calm,
    permission-granting: it tells her the system tried and how to retry, never blames."""
    topic = _ntfy_topic()
    if not topic:
        return False
    body = "Couldn't build a plan this morning (a network hiccup). Tap to open the overlay and retry when you're ready."
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}",
                                     data=body.encode("utf-8"), method="POST")
        req.add_header("Title", "Controlled Drift")
        req.add_header("Tags", "cloud")
        overlay = _overlay_url()
        if overlay:
            req.add_header("Click", overlay)
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[morning_push] failure-notice push failed: {e}", file=sys.stderr)
        return False


def _push_to_phone(plan, stale=False):
    """Push the plan to June's phone via ntfy (free, open-source pub/sub) — the part she
    reads in bed as she wakes. Best-effort: a push failure must never lose the cached plan.

    `stale=True` means generation failed and this is the LAST cached plan, not a fresh one —
    the body says so plainly (its clock times may be off) so June isn't misled, and can tap to
    rebuild. A clearly-labelled stale plan beats silence on a bad-network morning.

    Sends the woven frame + this morning's moves as a readable body, in permission-granting
    register. The topic is a private unguessable secret (only her phone is subscribed)."""
    topic = _ntfy_topic()
    if not topic:
        return False
    preface = ["Couldn't refresh this morning — here's your last plan (times may be off; tap to rebuild).", ""] if stale else []
    lines = preface + [(plan.get("woven_frame") or "").strip(), ""]
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
        req.add_header("Title", "Yesterday's plan" if stale else "Today, if you want it")
        req.add_header("Tags", "cloud" if stale else "sunrise")
        # Tap the notification → open the live overlay (not just the cached text).
        overlay = _overlay_url()
        if overlay:
            req.add_header("Click", overlay)
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
    """Generate the morning plan, cache it, and offer it via notification.

    Resilience is load-bearing here — this is the keystone, and June reads it on her PHONE in bed.
    A transient network failure must not turn into silence. So: retry generation; if it still
    fails, fall back to the last cached plan (clearly labelled stale); only if there's truly
    nothing, send an honest failure notice — to the PHONE, not just the Mac."""
    stale = False
    plan = _generate_with_retry()
    if plan is None:
        # Primary (Mistral) failed every retry. Try a fresh plan on the fallback backend before
        # settling for a stale one — a right-for-today plan is worth the extra latency.
        plan = _generate_on_fallback()
    if plan is None:
        # Both backends failed. Fall back to the last good plan rather than nothing.
        cached = plan_store.load_plan()
        if cached and not cached.get("empty"):
            plan, stale = cached, True
            print("[morning_push] generation failed — falling back to last cached plan", file=sys.stderr)
        else:
            # Nothing to send. Surface it honestly, and make sure it reaches her PHONE.
            _notify("Controlled Drift", "Couldn't build this morning's plan — open the overlay to retry.")
            pushed = _push_failure_to_phone()
            print(f"[morning_push] no plan to send; failure notice to phone: "
                  f"{'sent' if pushed else 'skipped/failed'}", file=sys.stderr)
            return 1

    summary = _first_line_summary(plan)
    # Permission-granting: "here's a possible shape", not "do this".
    _notify("Yesterday's plan" if stale else "Today, if you want it", summary)
    if notify:
        try:
            notify.ding()
        except Exception:
            pass

    # The keystone of the keystone: push to June's phone so she reads it in bed.
    pushed = _push_to_phone(plan, stale=stale)

    ts = dt.datetime.now().strftime("%A %B %d — %I:%M %p")
    state = "last cached (stale)" if stale else "generated + cached"
    print(f"[morning_push] plan {state} at {ts}")
    print(f"[morning_push] notification: {summary}")
    print(f"[morning_push] phone push: {'sent' if pushed else 'skipped (no ntfy topic) / failed'}")
    return 0


if __name__ == "__main__":
    sys.exit(run())

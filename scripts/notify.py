#!/usr/bin/env python3
"""Audible confirmation for Controlled Drift. A ding when something lands in the system
removes the invisible labor of checking-whether-it-saved — June shouldn't have to worry.

NOT 'Glass' — that sound is reserved for another tool. Default is 'Tink' (light, affirmative).
Fire-and-forget + fails silently: a missing sound or no afplay must NEVER break a capture."""
import subprocess, os

ADDED_SOUND = "Tink"      # something landed in the system
ATTENTION_SOUND = "Purr"  # gentle "needs your eyes" (e.g. a Needs-Clarifying item) — not used yet

def _play(sound):
    path = f"/System/Library/Sounds/{sound}.aiff"
    try:
        if os.path.exists(path):
            subprocess.Popen(["afplay", path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass  # confirmation sound is never allowed to break the operation

def ding(sound=None):
    """Play the 'added successfully' confirmation. Call AFTER a successful create."""
    _play(sound or ADDED_SOUND)

def attention():
    """Gentle 'this needs your attention' cue (reserved for future use)."""
    _play(ATTENTION_SOUND)

if __name__ == "__main__":
    import sys
    ding(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"[played {sys.argv[1] if len(sys.argv) > 1 else ADDED_SOUND}]")

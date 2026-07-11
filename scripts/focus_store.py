#!/usr/bin/env python3
"""Two-phase state for overlay Focus Period authoring (Phase 6, Task 3/6B).

Authoring is speak -> (async LLM structures) -> reflect-back -> confirm -> write. The structure
step is an ~30s LLM call that can't block the phone, so it runs in the background and the overlay
polls — exactly like plan generation, but on its OWN status + result surface so an authoring run
never looks like a plan generation to the Today poller. The result (structured fields + the
deterministic reflect-back payload) is stashed here between the async structure call and the
synchronous confirm/commit call.

Single-user personal tool: one authoring flow at a time (the shared server _gen_lock enforces
one LLM job at a time), so one current result is enough — no per-session keying needed.
"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import cd_paths


def _status_path():
    return cd_paths.config_file("focus_auth_status.json")


def _result_path():
    return cd_paths.config_file("focus_auth_result.json")


def get_status():
    """{state: 'idle'|'running'|'error', updated_at, [error]}. 'idle' is the honest default."""
    try:
        with open(_status_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"state": "idle"}


def set_status(state, error=None):
    os.makedirs(cd_paths.config_dir(), exist_ok=True)
    rec = {"state": state, "updated_at": dt.datetime.now().isoformat()}
    if error:
        rec["error"] = error
    tmp = _status_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=2)
    os.replace(tmp, _status_path())
    return rec


def save_result(payload):
    """Stash the structured fields + reflect-back payload for the confirm step to read back."""
    os.makedirs(cd_paths.config_dir(), exist_ok=True)
    tmp = _result_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, _result_path())


def load_result():
    """The last stashed authoring result, or None if there isn't one."""
    try:
        with open(_result_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def clear():
    """Drop the stashed result once a period is committed (or the flow is abandoned)."""
    for p in (_result_path(), _status_path()):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass

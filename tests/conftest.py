"""Deterministic test isolation for Controlled Drift.

BEFORE any test runs, redirect ALL of the system's data + config to a throwaway sandbox,
via the env vars cd_paths reads. This makes "tests never touch June's real
~/.controlled-drift/ or scripts/data/" structural — true for every test, present and
future, whether or not the test author remembers to mock a path.

A session tripwire additionally FAILS the suite if the real data dir is modified during the
run — so if the redirect ever regresses, it's flagged loudly, never silent. (That's the
deterministic guard June asked for: not "remember to redirect" but "can't not redirect, and
get yelled at if you somehow don't".)
"""
import os, sys, glob, tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# 1. Redirect — set at import (before any script module resolves a path). cd_paths reads
#    these at call time, so every read/write lands in the sandbox.
_SANDBOX = tempfile.mkdtemp(prefix="cd-test-sandbox-")
os.environ["CD_DATA_DIR"] = os.path.join(_SANDBOX, "data")
os.environ["CD_CONFIG_DIR"] = os.path.join(_SANDBOX, "config")
os.makedirs(os.environ["CD_DATA_DIR"], exist_ok=True)
os.makedirs(os.environ["CD_CONFIG_DIR"], exist_ok=True)

import cd_paths  # noqa: E402  (must follow the env setup above)

# Snapshot the REAL data dir (the on-disk default, ignoring the env override) to detect
# any accidental write to it during the run.
_REAL_DATA = cd_paths._DATA_DEFAULT


def _snapshot(d):
    return {p: os.path.getmtime(p)
            for p in glob.glob(os.path.join(d, "*")) if os.path.isfile(p)}


_REAL_BEFORE = _snapshot(_REAL_DATA)


@pytest.fixture(scope="session", autouse=True)
def _guard_real_data():
    # The redirect must actually be in effect, or the whole premise is broken.
    assert cd_paths.data_dir().startswith(_SANDBOX), "test CD_DATA_DIR not redirected to sandbox"
    assert cd_paths.config_dir().startswith(_SANDBOX), "test CD_CONFIG_DIR not redirected to sandbox"
    yield
    after = _snapshot(_REAL_DATA)
    touched = [p for p in after if _REAL_BEFORE.get(p) != after[p]]
    assert not touched, f"TEST POLLUTION — real data files were modified: {touched}"


@pytest.fixture
def cd_sandbox(tmp_path, monkeypatch):
    """Per-test isolation: give one test its own clean data + config dir.

    Use when a test needs a pristine, empty store (e.g. asserting 'no plan cached yet')
    so the shared session sandbox can't leak state between tests.
    """
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path / "config"))
    return tmp_path

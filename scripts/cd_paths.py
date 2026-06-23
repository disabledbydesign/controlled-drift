#!/usr/bin/env python3
"""Single source of truth for where Controlled Drift reads + writes its own data.

Two roots, each overridable by an environment variable so any sandboxed run — the test
suite above all — is **deterministically** redirected away from June's real files:

  CD_DATA_DIR    repo-side learning data: the corrections log, the surface log, the
                 learned meal params.   default: scripts/data/
  CD_CONFIG_DIR  user-local cache + config: the current plan, the button schema.
                 default: ~/.controlled-drift/

Paths resolve at CALL time, never bound at import — so setting the env var (e.g. in the
test conftest, which sets it before any test runs) always takes effect, with no
import-order surprises. This is the mechanism that makes "tests never touch real data"
structural rather than something each test has to remember.
"""
import os

_DATA_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_CONFIG_DEFAULT = "~/.controlled-drift"


def data_dir():
    """Repo-side learning-data dir (corrections, surface log, meal params)."""
    return os.environ.get("CD_DATA_DIR") or _DATA_DEFAULT


def config_dir():
    """User-local cache/config dir (current plan, button schema)."""
    return os.path.expanduser(os.environ.get("CD_CONFIG_DIR") or _CONFIG_DEFAULT)


def data_file(name):
    return os.path.join(data_dir(), name)


def config_file(name):
    return os.path.join(config_dir(), name)

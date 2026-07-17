# tests/test_engagement_cleanup.py
"""Sprint/Hyperfixation Engagement retirement (2026-07-16).

Pure test of propose_migration only — apply_migration and delete_retired_tags touch the
live Anytype space (an update + a real, asynchronously-propagating tag delete) and are
exercised instead via the script's dry-run CLI against June's real data, under her
confirmation, never in the unit suite (tests self-clean; no artifacts in her real space)."""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import migrate_engagement_cleanup as mg


def test_proposes_steady_for_retired_values():
    projs = [
        {"id": "a", "name": "Cuffs", "engagement": "Sprint"},
        {"id": "b", "name": "Reading", "engagement": "Hyperfixation"},
        {"id": "c", "name": "Fine", "engagement": "Steady"},
    ]
    out = {p["name"]: p["proposed"] for p in mg.propose_migration(projs)}
    assert out == {"Cuffs": "Steady", "Reading": "Steady"}   # 'Fine' already off the retired values

"""Tests for plan_store — the overlay's cache + variable button schema.

All file paths are redirected into tmp_path, so tests never touch June's real
~/.controlled-drift/ data.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import plan_store


def _redirect(tmp_path, monkeypatch):
    # Redirect via the deterministic env mechanism (cd_paths reads CD_CONFIG_DIR at call
    # time) — not by patching constants. This exercises the real isolation path.
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))


# --- current plan -----------------------------------------------------------

def test_load_plan_none_when_absent(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    # None is the honest answer on first run — never a fabricated plan.
    assert plan_store.load_plan() is None


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    saved = plan_store.save_plan({"woven_frame": "hi", "blocks": [], "still_here": []},
                                 source="refresh")
    assert saved["source"] == "refresh" and "generated_at" in saved
    loaded = plan_store.load_plan()
    assert loaded["woven_frame"] == "hi" and loaded["source"] == "refresh"


def test_save_is_atomic_no_partial_on_reload(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan({"woven_frame": "first"}, source="a")
    plan_store.save_plan({"woven_frame": "second"}, source="b")
    # No leftover .tmp file; the visible plan is the last full write.
    assert not os.path.exists(str(tmp_path / "current_plan.json.tmp"))
    assert plan_store.load_plan()["woven_frame"] == "second"


def test_load_plan_survives_corrupt_json(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    (tmp_path / "current_plan.json").write_text("{ not valid json")
    # A corrupt cache reads as None (empty state), not a crash.
    assert plan_store.load_plan() is None


# --- actions (variable button schema) ---------------------------------------

def test_actions_seed_on_first_run(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    acts = plan_store.load_actions()
    ids = [p["id"] for p in acts["presets"]]
    assert "low-energy" in ids and "stuck" in ids and "add" in ids
    # Seeded to disk so it can be edited to grow/shrink the button set.
    assert os.path.exists(str(tmp_path / "actions.json"))


def test_actions_persist_edits(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.load_actions()  # seed
    # Simulate June (or the learning loop) adding a new preset.
    data = json.loads((tmp_path / "actions.json").read_text())
    data["presets"].append({"id": "horizontal", "label": "Lying down only", "payload": "..."})
    (tmp_path / "actions.json").write_text(json.dumps(data))
    assert plan_store.find_preset("horizontal")["label"] == "Lying down only"


def test_find_preset_missing_returns_none(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    assert plan_store.find_preset("does-not-exist") is None


def test_add_preset_has_no_payload(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    # "add" is UI-only (focuses the text field) — it must not carry a generation payload.
    assert plan_store.find_preset("add")["payload"] is None

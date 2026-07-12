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


# --- tap-to-place move (deterministic, no LLM) — clock shape ------------------

def _clock_plan():
    return {
        "woven_frame": "wf",
        "blocks": [
            {"label": "Morning", "time": "09:00 – 12:00",
             "items": [{"time": "09:00 – 10:30", "project": "Alpha", "task": "draft", "id": "T1"},
                       {"time": "10:30 – 11:15", "project": "Beta", "task": "email", "id": "T2"},
                       {"time": "11:15 – 12:00", "project": "Beta", "task": "forms", "id": "T3"}]},
            {"label": "Afternoon", "time": "13:00 – 17:00",
             "items": [{"time": "13:00 – 14:00", "project": "Gamma", "task": "call", "id": "T4"}]},
        ],
        "still_here": [],
    }


def test_move_append_to_later_block_recomputes_times(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    updated = plan_store.move_item_later("T1", 1)   # position None -> append
    assert "T1" not in [i.get("id") for i in updated["blocks"][0]["items"]]
    # T1 keeps its 90-min duration; T4 ends 14:00 -> T1 is 14:00 – 15:30. Never blanked.
    moved = next(i for i in updated["blocks"][1]["items"] if i.get("id") == "T1")
    assert moved["time"] == "14:00 – 15:30"


def test_move_to_start_of_later_block(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    updated = plan_store.move_item_later("T1", 1, position=0)   # the block-start tap-target
    ids = [i["id"] for i in updated["blocks"][1]["items"]]
    assert ids == ["T1", "T4"]
    times = {i["id"]: i["time"] for i in updated["blocks"][1]["items"]}
    assert times == {"T1": "13:00 – 14:30", "T4": "14:30 – 15:30"}


def test_move_closes_the_gap_in_the_source_block(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    updated = plan_store.move_item_later("T1", 1)
    # The source block re-flows from its start: T2 (45 min) now 09:00–09:45, T3 09:45–10:30.
    t2 = next(i for i in updated["blocks"][0]["items"] if i.get("id") == "T2")
    t3 = next(i for i in updated["blocks"][0]["items"] if i.get("id") == "T3")
    assert t2["time"] == "09:00 – 09:45"
    assert t3["time"] == "09:45 – 10:30"


def test_move_later_within_same_block(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    # Tap-target after T2: T1 lands at final index 1 -> [T2, T1, T3], durations kept.
    updated = plan_store.move_item_later("T1", 0, position=1)
    assert [i["id"] for i in updated["blocks"][0]["items"]] == ["T2", "T1", "T3"]
    times = {i["id"]: i["time"] for i in updated["blocks"][0]["items"]}
    assert times == {"T2": "09:00 – 09:45", "T1": "09:45 – 11:15", "T3": "11:15 – 12:00"}


def test_move_overflow_past_block_end_is_honest_arithmetic(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan = _clock_plan()
    plan["blocks"][1]["items"].append({"time": "14:00 – 16:45", "project": "Gamma",
                                       "task": "long thing", "id": "T5"})
    plan_store.save_plan(plan, source="generate")
    updated = plan_store.move_item_later("T1", 1)   # 90 min appended after 16:45
    moved = next(i for i in updated["blocks"][1]["items"] if i["id"] == "T1")
    # Runs past the block label's 17:00 end — the arithmetic tells the truth; we never
    # squeeze or invent durations to make it fit.
    assert moved["time"] == "16:45 – 18:15"


def test_move_unparseable_item_time_falls_back_to_default_duration(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan = _clock_plan()
    plan["blocks"][0]["items"][1]["time"] = ""   # T2 has no parseable time
    plan_store.save_plan(plan, source="generate")
    updated = plan_store.move_item_later("T1", 1)
    t2 = next(i for i in updated["blocks"][0]["items"] if i["id"] == "T2")
    assert t2["time"] == "09:00 – 09:30"   # default 30 min, anchored to block start


def test_move_preserves_generated_at_and_source(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    saved = plan_store.save_plan(_clock_plan(), source="refresh")
    updated = plan_store.move_item_later("T1", 1)
    # A move is not a regeneration — the timestamp/source must not be re-stamped.
    assert updated["generated_at"] == saved["generated_at"]
    assert updated["source"] == "refresh"


def test_move_persists_to_cache(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    plan_store.move_item_later("T1", 1)
    reloaded = plan_store.load_plan()
    assert "T1" in [i.get("id") for i in reloaded["blocks"][1]["items"]]
    assert not os.path.exists(str(tmp_path / "current_plan.json.tmp"))  # atomic, no leftover


def test_move_rejects_not_later(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    import pytest
    with pytest.raises(ValueError):
        plan_store.move_item_later("T4", 0)                 # earlier block
    with pytest.raises(ValueError):
        plan_store.move_item_later("T1", 0)                 # same block, no position
    with pytest.raises(ValueError):
        plan_store.move_item_later("T2", 0, position=0)     # same block, EARLIER spot
    with pytest.raises(ValueError):
        plan_store.move_item_later("T2", 0, position=1)     # same block, same spot (no-op)


def test_move_rejects_out_of_range_and_missing_id(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_clock_plan(), source="generate")
    import pytest
    with pytest.raises(ValueError):
        plan_store.move_item_later("T1", 9)                 # block out of range
    with pytest.raises(ValueError):
        plan_store.move_item_later("T1", 1, position=5)     # position out of range
    with pytest.raises(LookupError):
        plan_store.move_item_later("NOPE", 1)


def test_move_raises_when_no_cache_or_no_blocks(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    import pytest
    with pytest.raises(LookupError):
        plan_store.move_item_later("T1", 1)
    plan_store.save_plan({"shape": "priority", "items": [{"task": "x", "id": "T1"}]},
                         source="generate")
    with pytest.raises(LookupError):
        plan_store.move_item_later("T1", 1)   # priority shape has no blocks (see Task 2)


# --- tap-to-place on a fragmented (priority-shape) day — pure position change --

def _priority_plan():
    return {"shape": "priority", "header": "a short list to pull from",
            "items": [{"project": "Alpha", "task": "draft", "id": "P1"},
                      {"project": "Beta", "task": "email", "id": "P2"},
                      {"project": "Gamma", "task": "call", "id": "P3"}],
            "still_here": []}


def test_priority_move_to_later_position(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_priority_plan(), source="generate")
    updated = plan_store.move_priority_item_later("P1", 2)
    assert [i["id"] for i in updated["items"]] == ["P2", "P3", "P1"]
    # No times involved on a fragmented day — items still carry none.
    assert "time" not in updated["items"][2]


def test_priority_move_one_step(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_priority_plan(), source="generate")
    updated = plan_store.move_priority_item_later("P1", 1)
    assert [i["id"] for i in updated["items"]] == ["P2", "P1", "P3"]


def test_priority_move_persists_and_preserves_stamp(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    saved = plan_store.save_plan(_priority_plan(), source="refresh")
    plan_store.move_priority_item_later("P1", 1)
    reloaded = plan_store.load_plan()
    assert [i["id"] for i in reloaded["items"]] == ["P2", "P1", "P3"]
    assert reloaded["generated_at"] == saved["generated_at"]
    assert reloaded["source"] == "refresh"


def test_priority_move_rejects_not_later_and_out_of_range(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_priority_plan(), source="generate")
    import pytest
    with pytest.raises(ValueError):
        plan_store.move_priority_item_later("P3", 1)   # earlier spot
    with pytest.raises(ValueError):
        plan_store.move_priority_item_later("P2", 1)   # same spot (no-op)
    with pytest.raises(ValueError):
        plan_store.move_priority_item_later("P1", 9)   # out of range


def test_priority_move_raises_on_missing_id_clock_shape_or_no_cache(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    import pytest
    with pytest.raises(LookupError):
        plan_store.move_priority_item_later("P1", 1)   # no cache
    plan_store.save_plan(_priority_plan(), source="generate")
    with pytest.raises(LookupError):
        plan_store.move_priority_item_later("NOPE", 1)
    plan_store.save_plan(_clock_plan(), source="generate")
    with pytest.raises(LookupError):
        plan_store.move_priority_item_later("T1", 1)   # clock plan has no priority list

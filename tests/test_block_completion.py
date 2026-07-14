"""Block completion routing in plan_store: is_block_item + cache-only chunk flips.

The block check is cache-only (chunk_log + this cache mirror), NEVER an Anytype done-write —
these cover the routing predicate + the cache flips. The route wiring is proven live in Task 11.
"""
import os
import plan_store


def _seed_plan(items):
    os.makedirs(os.path.dirname(plan_store._plan_path()), exist_ok=True)
    plan_store._persist_plan({"blocks": [{"label": "Morning", "items": items}]})


def test_is_block_item_matches_by_project_id(cd_sandbox):
    _seed_plan([{"id": "block:lw", "block": True, "project_id": "lw", "did_chunk_today": False}])
    assert plan_store.is_block_item("lw") is True
    assert plan_store.is_block_item("nope") is False


def test_is_block_item_false_for_plain_task(cd_sandbox):
    _seed_plan([{"id": "t1", "task": "Do a thing"}])
    assert plan_store.is_block_item("t1") is False


def test_mark_block_chunked_flips_cache_both_ways(cd_sandbox):
    _seed_plan([{"id": "block:lw", "block": True, "project_id": "lw", "did_chunk_today": False}])
    plan_store.mark_block_chunked("lw", True)
    assert plan_store.load_plan()["blocks"][0]["items"][0]["did_chunk_today"] is True
    plan_store.mark_block_chunked("lw", False)
    assert plan_store.load_plan()["blocks"][0]["items"][0]["did_chunk_today"] is False


def test_set_block_chunk_updates_cached_length(cd_sandbox):
    _seed_plan([{"id": "block:lw", "block": True, "project_id": "lw", "chunk_min": 90}])
    plan_store.set_block_chunk("lw", 180)
    assert plan_store.load_plan()["blocks"][0]["items"][0]["chunk_min"] == 180


def test_set_item_duration_updates_cached_row(cd_sandbox):
    """General duration edit: a real task/recurring row's cached duration_min updates by id."""
    _seed_plan([{"id": "t1", "task": "Go on a walk", "duration_min": 30}])
    plan_store.set_item_duration("t1", 60)
    assert plan_store.load_plan()["blocks"][0]["items"][0]["duration_min"] == 60


def test_is_block_item_false_for_real_task_id(cd_sandbox):
    """A real task id must NOT match the block predicate, so /api/duration routes it to the
    task-duration path (its own Duration min field), not the block Project field."""
    _seed_plan([{"id": "t1", "task": "Go on a walk", "duration_min": 30}])
    assert plan_store.is_block_item("t1") is False

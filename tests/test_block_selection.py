"""Block selection + Daily-life gating in plan_generate._gate_and_collapse / _blockify."""
import plan_generate as pg
import grain
import block_duration


def _proj(name, eng=None, side=None):
    return {"name": name, "engagement": eng, "side": side,
            "parent_project_id": None, "is_workstream": False}


def _task(tid, name, proj):
    return {"id": tid, "name": name, "linked_projects": [proj]}


def test_daily_life_chores_all_survive_uncollapsed():
    """A Daily-life project with unset engagement surfaces EVERY chore (not one collapsed
    representative) — chores are discrete, and Daily life is exempt from the engagement gate."""
    projects = [_proj("Household", eng=None, side="Daily life")]
    tasks = [_task("t1", "Clean kitchen", "Household"),
             _task("t2", "Do dishes", "Household")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} >= {"t1", "t2"}


def test_non_daily_life_unset_engagement_task_stays_when_project_active():
    # Reconciled: the engagement hide-gate is gone. An unset-engagement project that IS in the
    # active set keeps its task (Task 9 renders it as a block at output). Only a task whose project
    # is absent from the active set (dormant) is dropped.
    projects = [_proj("Some project", eng=None, side="Wellbeing")]
    tasks = [_task("t1", "A task", "Some project")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} == {"t1"}


# ---------------------------------------------------------------------------
# grain.block_unit — the task-shaped synthetic-id block
# ---------------------------------------------------------------------------

def test_block_unit_has_synthetic_id_and_arc():
    proj = {"id": "lw", "name": "Leatherworking"}
    arc = [{"text": "Cut", "state": "done"}, {"text": "Stitch", "state": "here"}]
    u = grain.block_unit(proj, "arc", arc, 120)
    assert u["id"] == "block:lw"
    assert u["block"] is True and u["duration_min"] == 120 and u["chunk_min"] == 120
    assert u["arc"][1]["state"] == "here"
    assert u["linked_projects"] == ["Leatherworking"]


def test_container_block_is_bare_chunk():
    u = grain.block_unit({"id": "sw", "name": "Scholarly writing"}, "chunk", None, 240)
    assert u["arc"] is None and u["name"] == "Work on Scholarly writing" and u["shape"] == "chunk"


# ---------------------------------------------------------------------------
# plan_generate._blockify — real work -> blocks; discrete tasks stay tasks
# ---------------------------------------------------------------------------

def _bproj(pid, name, eng=None, side=None, ws=False, arc=None, chunk_min=None):
    return {"id": pid, "name": name, "engagement": eng, "side": side,
            "parent_project_id": None, "is_workstream": ws, "arc": arc, "chunk_min": chunk_min}


def test_blockify_block_project_tasks_pass_through_unchanged():
    # A block-project's REAL tasks stay in the list (checkoffable) — NOT replaced by a synthetic
    # unit (the shipped zero-ghost design). The block is a render grouping (Task 9), not selection.
    proj = _bproj("lw", "Leatherworking", eng="Steady", side="Wellbeing",
                  arc=[{"text": "Cut", "state": "here", "id": "t1"}], chunk_min=120)
    kept = [_task("t1", "Cut", "Leatherworking"), _task("t2", "Stitch", "Leatherworking")]
    out = pg._blockify(kept, [proj])
    assert out == kept                                   # both real tasks pass through, keep ids
    assert not any(o.get("block") for o in out)          # no synthetic block emitted


def test_blockify_daily_life_stays_task():
    proj = _bproj("hh", "Household", eng=None, side="Daily life")
    kept = [_task("t1", "Dishes", "Household")]
    assert pg._blockify(kept, [proj]) == kept


def test_blockify_container_bare_chunk_for_taskless_project():
    proj = _bproj("sw", "Scholarly writing", eng="Steady", side="Wellbeing")   # arc None, no tasks
    out = pg._blockify([], [proj])
    assert len(out) == 1 and out[0]["shape"] == "chunk" and out[0]["id"] == "block:sw"
    assert out[0]["duration_min"] == block_duration.BLOCK_DEFAULT_MIN


def test_blockify_container_surfaces_every_active_taskless_project():
    # No _surfaces gate anymore — active-only-at-load is the filter, so an Open task-less block
    # project surfaces as a container (decision 8: Open is in the input, available if-room).
    proj = _bproj("q", "Quiet project", eng="Open", side="Wellbeing")
    out = pg._blockify([], [proj])
    assert len(out) == 1 and out[0]["id"] == "block:q"


def test_blockify_container_with_a_survivor_is_not_double_emitted():
    # If a block project already has a real task in `kept`, it is NOT a task-less container -> no
    # synthetic unit (dedup at the source; no survivor row + synthetic header for one project).
    proj = _bproj("lw", "Leatherworking", eng="Steady", side="Wellbeing")   # arc None
    kept = [_task("t1", "Cut", "Leatherworking")]
    out = pg._blockify(kept, [proj])
    assert out == kept and not any(o.get("block") for o in out)


def test_blockify_paused_taskless_project_skipped():
    proj = _bproj("q", "Paused", eng="Steady", side="Wellbeing")
    assert pg._blockify([], [proj], paused={"Paused"}) == []
    assert len(pg._blockify([], [proj])) == 1             # not paused -> one container


def test_blockify_workstream_never_emitted():
    proj = _bproj("ws", "A workstream", eng="Steady", side="Wellbeing", ws=True)
    assert pg._blockify([], [proj]) == []


# ---------------------------------------------------------------------------
# Task 7: block data survives resolve -> retime -> rows, keyed by synthetic id
# ---------------------------------------------------------------------------

def test_resolve_ids_reattaches_block_data_by_id():
    arc = [{"text": "Cut", "state": "here"}]
    block = grain.block_unit({"id": "lw", "name": "Leatherworking"}, "arc", arc, 120)
    plan = {"blocks": [{"items": [{"ref": "T1", "task": "Work on Leatherworking"}]}]}
    pg._resolve_ids(plan, {"T1": "block:lw"}, [block])
    item = plan["blocks"][0]["items"][0]
    assert item["id"] == "block:lw" and item["block"] is True
    assert item["project_id"] == "lw" and item["shape"] == "arc"
    assert item["arc"] == arc and item["chunk_min"] == 120


def test_resolve_ids_name_matches_against_all_active_tasks():
    # The ghost-killer: a real task the model names that is NOT in the gated order-list but IS in the
    # full active set must resolve to its id (no uncheckoffable ghost). Exact-normalized match only.
    gated = [{"id": "t1", "name": "Organize letters"}]
    all_tasks = gated + [{"id": "t99", "name": "Verify the disability payment process"}]
    plan = {"blocks": [{"items": [{"task": "Verify the disability payment process"}]}]}
    pg._resolve_ids(plan, {}, gated, all_tasks=all_tasks)
    assert plan["blocks"][0]["items"][0]["id"] == "t99"


def test_resolve_ids_still_strict_no_loose_match():
    gated = [{"id": "t1", "name": "Organize letters"}]
    all_tasks = gated + [{"id": "t99", "name": "Verify the disability payment process"}]
    plan = {"blocks": [{"items": [{"task": "verify disability"}]}]}   # partial, not exact
    pg._resolve_ids(plan, {}, gated, all_tasks=all_tasks)
    assert plan["blocks"][0]["items"][0].get("id") is None            # no loose match → no wrong-task


def test_resolve_ids_attaches_block_project_render_data_keeping_real_id():
    arc = [{"text": "Verify disability", "state": "here", "id": "t1"}]
    task = {"id": "t1", "name": "Verify disability", "linked_projects": ["IOP and recovery"],
            "block_project": True, "project_id": "iop", "arc": arc, "chunk_min": 90}
    plan = {"blocks": [{"items": [{"ref": "T1", "task": "Verify disability"}]}]}
    pg._resolve_ids(plan, {"T1": "t1"}, [task])
    item = plan["blocks"][0]["items"][0]
    assert item["id"] == "t1"                        # keeps its REAL task id — checkoffable, no ghost
    assert item["block_project"] is True and item["project_id"] == "iop"
    assert item["arc"] == arc and item["chunk_min"] == 90


def test_retime_dur_by_id_yields_chunk_min_not_30():
    """A block's duration must be its chunk length through retime — the swarm's 30-min
    collapse guard. dur_by_id is keyed on the synthetic id."""
    block = grain.block_unit({"id": "sw", "name": "Scholarly writing"}, "chunk", None, 240)
    dur_by_id = {t["id"]: t.get("duration_min") for t in [block]}
    assert dur_by_id["block:sw"] == 240


def test_blocks_from_scheduled_tags_block_row_and_chunk_state(cd_sandbox):
    import datetime as dt
    import daily_plan, chunk_log
    s = dt.datetime(2026, 7, 14, 10, 0)
    scheduled = [{
        "_composed": True, "id": "block:lw", "task": "Work on Leatherworking",
        "project": "Leatherworking", "block": True, "project_id": "lw",
        "shape": "arc", "arc": [{"text": "Cut", "state": "here"}], "chunk_min": 120,
        "start_time": s, "end_time": s + dt.timedelta(minutes=120),
    }]
    blocks = daily_plan.blocks_from_scheduled(scheduled)
    row = blocks[0]["items"][0]
    assert row["block"] is True and row["project_id"] == "lw" and row["shape"] == "arc"
    assert row["chunk_min"] == 120 and row["arc"][0]["state"] == "here"
    assert row["did_chunk_today"] is False           # nothing logged yet

    chunk_log.log_chunk("lw")                          # mark worked-on today
    row2 = daily_plan.blocks_from_scheduled(scheduled)[0]["items"][0]
    assert row2["did_chunk_today"] is True


# ---------------------------------------------------------------------------
# Task 8: prompt ref line — a block is a chunk, not a task list
# ---------------------------------------------------------------------------

def test_task_ref_line_block_says_chunk_no_more():
    block = grain.block_unit({"id": "sw", "name": "Scholarly writing"}, "chunk", None, 240)
    line = pg._task_ref_line("T1", block)
    assert "Work on Scholarly writing" in line
    assert "chunk of time" in line
    assert "more" not in line          # a block has no held-back siblings to count


def test_task_ref_line_task_keeps_held_back_suffix():
    task = {"id": "t1", "name": "Write needs statement", "held_back": 3}
    line = pg._task_ref_line("T2", task)
    assert "· 3 more" in line and "chunk of time" not in line


# ---------------------------------------------------------------------------
# decision 2: every block scheduling event is recorded (log rich now, mine later)
# ---------------------------------------------------------------------------

def test_log_scheduled_blocks_records_one_event_per_block(monkeypatch):
    logged = []
    monkeypatch.setattr(block_duration, "log_scheduled",
                        lambda pid, mins, **k: logged.append((pid, mins)))
    plan = {"blocks": [{"items": [
        {"block": True, "project_id": "lw", "chunk_min": 120},
        {"id": "t1", "task": "a chore"},                       # non-block → no event
        {"block": True, "project_id": "sw", "chunk_min": 240},
    ]}]}
    pg._log_scheduled_blocks(plan)
    assert logged == [("lw", 120), ("sw", 240)]


# ---------------------------------------------------------------------------
# Task 9 (plan-input seam): coded output dedup — one "Work on X" block per project
# ---------------------------------------------------------------------------

def test_group_block_project_items_dedups_two_tasks_into_one_block():
    # THE dedup invariant: an LLM plan naming TWO individual tasks of one block project resolves to
    # ONE 'Work on X' block, both marked '→ here' in its arc — never two rows, never a duplicate.
    arc = [{"text": "Cut", "state": "done", "id": "t1"},
           {"text": "Dye", "state": "here", "id": "t2"},
           {"text": "Stitch", "state": "ahead", "id": "t3"}]
    items = [
        {"id": "t2", "task": "Dye", "project": "Leatherworking", "block_project": True,
         "project_id": "lw", "arc": arc, "chunk_min": 120, "_composed": True},
        {"id": "t3", "task": "Stitch", "project": "Leatherworking", "block_project": True,
         "project_id": "lw", "arc": arc, "chunk_min": 120, "_composed": True},
    ]
    out = pg._group_block_project_items(items)
    assert len(out) == 1                                  # ONE block, not two rows
    blk = out[0]
    assert blk["block"] is True and blk["project_id"] == "lw"
    assert blk["duration_min"] == 120                     # chunk_min ONCE, not 240
    assert set(blk["absorbed_ids"]) == {"t2", "t3"}       # both real ids retained (accounting)
    states = {s["id"]: s["state"] for s in blk["arc"]}
    assert states["t2"] == "here" and states["t3"] == "here" and states["t1"] == "done"


def test_group_block_project_items_passes_non_block_through():
    items = [{"id": "d", "task": "Dishes", "project": "Household"},
             {"id": "c", "task": "Call", "project": None}]
    assert pg._group_block_project_items(items) == items


def test_ensure_all_tasks_accounted_counts_block_absorbed_and_arc_ids():
    # win #1: a task a block absorbed into its arc must NOT be spammed to still_here.
    plan = {"blocks": [{"items": [{"block": True, "project_id": "lw", "absorbed_ids": ["t2"],
                                   "arc": [{"id": "t3", "state": "ahead"}]}]}], "still_here": []}
    tasks = [{"id": "t2", "name": "Dye"}, {"id": "t3", "name": "Stitch"}, {"id": "t9", "name": "Loose"}]
    pg._ensure_all_tasks_accounted(plan, tasks)
    labels = {sh["label"] for sh in plan["still_here"]}
    assert "Dye" not in labels and "Stitch" not in labels   # absorbed + in-arc -> accounted
    assert "Loose" in labels                                # genuinely unplaced -> parked

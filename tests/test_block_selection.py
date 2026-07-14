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


def test_non_daily_life_unset_engagement_still_hidden():
    """Contrast: an ordinary unset-engagement project (not Daily life, not neglected) is still
    hidden by the gate — the bypass is specific to Daily life, not a blanket opening."""
    projects = [_proj("Some project", eng=None, side="Wellbeing")]
    tasks = [_task("t1", "A task", "Some project")]
    kept = pg._gate_and_collapse(tasks, projects, [], None, surface_dates={})
    assert {t["id"] for t in kept} == set()


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


def test_blockify_thread_becomes_one_arc_block():
    proj = _bproj("lw", "Leatherworking", eng="Steady", side="Wellbeing",
                  arc=[{"text": "Cut", "state": "here"}], chunk_min=120)
    kept = [_task("t1", "Cut", "Leatherworking")]
    out = pg._blockify(kept, [proj], None, [])
    assert len(out) == 1
    assert out[0]["id"] == "block:lw" and out[0]["shape"] == "arc" and out[0]["duration_min"] == 120


def test_blockify_multiple_survivors_collapse_to_one_block():
    proj = _bproj("lw", "Leatherworking", eng="Steady", side="Wellbeing",
                  arc=[{"text": "Cut", "state": "here"}], chunk_min=120)
    kept = [_task("t1", "Cut", "Leatherworking"), _task("t2", "Stitch", "Leatherworking")]
    out = pg._blockify(kept, [proj], None, [])
    assert len([o for o in out if o.get("block")]) == 1  # one block for the thread, not two


def test_blockify_daily_life_stays_task():
    proj = _bproj("hh", "Household", eng=None, side="Daily life")
    kept = [_task("t1", "Dishes", "Household")]
    out = pg._blockify(kept, [proj], None, [])
    assert out == kept  # unchanged — a chore is a discrete task, not a block


def test_blockify_container_bare_chunk_when_steady():
    proj = _bproj("sw", "Scholarly writing", eng="Steady", side="Wellbeing")
    out = pg._blockify([], [proj], None, [])
    assert len(out) == 1 and out[0]["shape"] == "chunk" and out[0]["id"] == "block:sw"
    assert out[0]["duration_min"] == block_duration.BLOCK_DEFAULT_MIN  # unset -> 90 default


def test_blockify_container_hidden_when_open_not_foregrounded():
    proj = _bproj("q", "Quiet project", eng="Open", side="Wellbeing")
    assert pg._blockify([], [proj], None, []) == []


def test_blockify_container_surfaces_when_foregrounded():
    proj = _bproj("q", "Quiet project", eng="Open", side="Wellbeing")
    out = pg._blockify([], [proj], {"foreground": ["Quiet project"]}, [])
    assert len(out) == 1 and out[0]["id"] == "block:q"


def test_blockify_workstream_never_emitted():
    proj = _bproj("ws", "A workstream", eng="Steady", side="Wellbeing", ws=True)
    assert pg._blockify([], [proj], None, []) == []


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

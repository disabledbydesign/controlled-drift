"""format_context splits the task hierarchy into two labeled categories (REVISION decision C)."""
import daily_plan


def _proj(name, side):
    return {"id": name, "name": name, "side": side, "is_workstream": False,
            "parent_project_id": None, "engagement": "Steady"}


def _task(name, proj):
    return {"id": "t-" + name, "name": name, "linked_projects": [proj], "status": "Active"}


def test_context_splits_block_work_from_daily_tasks():
    projects = [_proj("IOP and recovery", "Wellbeing"), _proj("Household", "Daily life")]
    tasks = [_task("Verify disability", "IOP and recovery"),
             _task("Clean the kitchen", "Household")]
    ctx = daily_plan.format_context([], projects, tasks, [], [], [], None)

    assert "### Block-organized work" in ctx
    assert "### Daily tasks" in ctx
    # IOP (Wellbeing → block) sits in the block category; Household (Daily life → task) in daily.
    block_hdr = ctx.index("### Block-organized work")
    daily_hdr = ctx.index("### Daily tasks")
    assert block_hdr < ctx.index("Verify disability") < daily_hdr
    assert ctx.index("Clean the kitchen") > daily_hdr

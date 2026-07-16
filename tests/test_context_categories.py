"""format_context splits the active set into two structurally distinct categories
(plan_input_seam_design.md decisions 3 & 4): block-organized work is presented BY PROJECT (one
'Work on X' line, goal-explained, its tasks shown as an arc), daily-life work stays BY TASK. Each
project carries its [Engagement] in BOTH subsections."""
import daily_plan


def _proj(name, side, goal_name=None, arc=None, engagement="Steady"):
    return {"id": name, "name": name, "side": side, "is_workstream": False,
            "parent_project_id": None, "engagement": engagement, "goal_name": goal_name, "arc": arc}


def _task(name, proj):
    return {"id": "t-" + name, "name": name, "linked_projects": [proj], "status": "Active"}


def test_context_splits_block_work_from_daily_tasks():
    projects = [_proj("IOP and recovery", "Wellbeing"), _proj("Household", "Daily life")]
    tasks = [_task("Verify disability", "IOP and recovery"),
             _task("Clean the kitchen", "Household")]
    ctx = daily_plan.format_context([], projects, tasks, [], [], [], None)
    assert "### Block-organized work" in ctx and "### Daily tasks" in ctx
    block_hdr = ctx.index("### Block-organized work")
    daily_hdr = ctx.index("### Daily tasks")
    # the block PROJECT is listed in the block section (search FROM the header — the name also
    # appears earlier in `## Active projects`, so a plain .index finds that one).
    assert block_hdr < ctx.index("IOP and recovery", block_hdr) < daily_hdr
    assert ctx.index("Clean the kitchen") > daily_hdr    # a task name — only in Daily tasks


def test_block_work_shows_goal_and_arc():
    arc = [{"text": "Verify disability", "state": "here", "id": "t1"},
           {"text": "File paperwork", "state": "ahead", "id": "t2"}]
    projects = [_proj("IOP and recovery", "Wellbeing", goal_name="Stay stable", arc=arc)]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "goal: Stay stable" in ctx
    assert "Verify disability" in ctx and "File paperwork" in ctx


def test_block_work_container_with_no_arc_reads_as_a_bare_chunk():
    projects = [_proj("Scholarly writing", "Wellbeing", arc=None)]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "Scholarly writing" in ctx and "bare chunk of time" in ctx


def test_block_project_appears_even_with_zero_tasks_this_cycle():
    projects = [_proj("Scholarly writing", "Wellbeing")]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "### Block-organized work" in ctx and "Scholarly writing" in ctx


def test_engagement_visible_on_a_block_project_line():
    projects = [_proj("Leatherworking", "Wellbeing", engagement="Steady")]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "[Steady]" in ctx[ctx.index("### Block-organized work"):]


def test_engagement_visible_on_a_daily_life_project_header():
    projects = [_proj("Networking and relationships", "Daily life", engagement="Open")]
    tasks = [_task("Email Donna Haraway", "Networking and relationships")]
    ctx = daily_plan.format_context([], projects, tasks, [], [], [], None)
    daily_hdr = ctx.index("### Daily tasks")
    line = ctx.index("Networking and relationships", daily_hdr)
    assert "[Open]" in ctx[line:ctx.index("Email Donna Haraway")]


def test_unset_engagement_shows_open_not_steady():
    projects = [_proj("Ghost", "Wellbeing", engagement=None)]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "[Open]" in ctx and "[Steady]" not in ctx


def test_active_projects_section_shows_goal():
    projects = [_proj("Leatherworking", "Wellbeing", goal_name="Stay a scholar-builder")]
    ctx = daily_plan.format_context([], projects, [], [], [], [], None)
    assert "## Active projects" in ctx and "goal: Stay a scholar-builder" in ctx

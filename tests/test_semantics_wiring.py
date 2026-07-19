"""The field definitions reach the models that REASON about June's data — from one source.

Two seams are under test here.

PART 1 — `Relevant docs` and `AI autonomous` exist to inform an agent, and no agent could read
them: `cd_mcp_server` had no full-field read tool, and nothing populated `Relevant docs`. The
three fixes `field_semantics.DOES` already names for them are (1) an MCP tool that returns a
task's full properties, (2) a read-side rule in the drift skill (NOT in this repo's scope), and
(3) capture populating the field when an item names a file or an external system.

PART 2 — the prompts held hand-copied restatements of `Engagement`'s value meanings, in wording
that had already drifted from the module. These assert the plan context carries the definition
ONCE, rendered from `field_semantics`, so a correction there lands in the prompt too.

Both parts assert POSITIVELY (the wiring is present and sourced), never merely that a string is
absent — an absence passes against a file that was never wired at all.
"""
import sys
import types
import pytest

import field_semantics as fs
import capture_fields
import capture_generate
import daily_plan


# --- Part 2: one source for the prompt-facing field lines ---------------------

def test_prompt_legend_renders_the_module_meaning_for_a_field():
    legend = fs.prompt_legend(["Affective"])
    entry = fs.resolved("Affective")
    assert "Affective" in legend
    # The legend is the module's text, not a paraphrase of it: the distinctive clause from
    # `means` is present verbatim.
    assert "affective conditions only" in legend
    assert entry["means"].split(".")[0].strip() in " ".join(legend.split())


def test_prompt_legend_follows_junes_override_not_the_repo_default(tmp_path):
    """The whole point of one source: a correction lands everywhere. June's override is the
    correction surface, so the legend must resolve through it."""
    path = tmp_path / "ov.json"
    fs.set_override("Affective", {"means": "ONLY-A-TEST-MEANING for the affect field."},
                    path=str(path), log=False)
    legend = fs.prompt_legend(["Affective"], path=str(path))
    assert "ONLY-A-TEST-MEANING" in legend


def test_prompt_legend_carries_the_wrong_field_routing_so_text_lands_right():
    """`not_this` / `instead` are the leak-prevention half. A meaning without them is what let
    status notes land in `Affective` in the first place."""
    legend = fs.prompt_legend(["Affective"])
    assert "Blocked on" in legend        # from `instead`
    assert "Never a number" in legend or "never a number" in legend


def test_prompt_legend_emits_no_examples_by_default():
    """June's constraint: a single example gets replicated verbatim into her records. The
    legend carries no illustrations at all unless asked, so nothing can be copied from it."""
    legend = fs.prompt_legend(["Affective"])
    for ex in fs.EXAMPLES["Affective"]:
        assert ex not in legend


def test_prompt_legend_with_examples_carries_the_banner_and_all_of_them():
    legend = fs.prompt_legend(["Affective"], include_examples=True)
    assert fs.EXAMPLES_BANNER in legend
    for ex in fs.EXAMPLES["Affective"]:
        assert ex in legend


def test_prompt_legend_refuses_examples_that_would_read_as_a_template(monkeypatch):
    """Fewer than three deliberately dissimilar illustrations is a template, not a range. The
    module refuses rather than emitting one — no silent degradation."""
    monkeypatch.setitem(fs.EXAMPLES, "Blocked on", ("waiting on the referral",))
    with pytest.raises(ValueError) as e:
        fs.prompt_legend(["Blocked on"], include_examples=True)
    assert "Blocked on" in str(e.value)


def test_prompt_legend_rejects_an_unknown_field_rather_than_skipping_it():
    with pytest.raises(KeyError):
        fs.prompt_legend(["Not A Real Field"])


def test_plan_context_carries_the_field_meanings_from_the_module():
    """`format_context` prints bare `affective:` and `[Engagement]` values at the planning model
    with no statement of what either means. This asserts the legend now travels with them."""
    ctx = daily_plan.format_context([], [], [], [], [], [], None)
    assert "affective conditions only" in ctx          # Affective's meaning, from the module
    assert "Steady" in ctx and "Backburner" in ctx     # Engagement's values, from the module
    assert fs.prompt_legend(["Affective", "Engagement"]) in ctx


def test_plan_context_states_each_engagement_value_meaning_only_once():
    """The deduplication itself. What `Steady` means for the day was written out in the module
    AND restated in three `daily_plan` header strings covering the Project `Engagement` field.
    In the assembled context, the module's own sentence must now appear exactly once and the
    restatements must be gone."""
    projects = [{"id": "p", "name": "P", "engagement": "Steady", "side": "Work",
                 "reaching_for": "", "context": "", "affective": "", "engagement_notes": "",
                 "parent_project_id": None}]
    tasks = [{"id": "t", "name": "T", "linked_projects": ["P"], "status": "Ready",
              "affective": "", "access": [], "blocked_on": None, "duration_min": None}]
    ctx = daily_plan.format_context([], projects, tasks, [], [], [], None)
    steady_rule = fs.resolved("Engagement")["usage"][0].split(".")[0].strip()
    assert steady_rule in ctx
    assert ctx.count(steady_rule) == 1
    assert ctx.count("a normal daily move") == 0     # every hand-copy removed


# --- Part 1: the two agent-facing fields reach an agent ----------------------

def _mcp_server():
    """Import `cd_mcp_server` without the `mcp` package (not installed in the test env).

    A stub FastMCP whose `tool()` decorator is the identity, so each tool stays a plain callable.
    Self-cleaning: the stub modules are removed again by the fixture below.
    """
    fake = types.ModuleType("mcp")
    server = types.ModuleType("mcp.server")
    fastmcp = types.ModuleType("mcp.server.fastmcp")

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            return lambda fn: fn

        def run(self):
            raise AssertionError("the test must never run the server")

    fastmcp.FastMCP = _FastMCP
    server.fastmcp = fastmcp
    fake.server = server
    for name, mod in (("mcp", fake), ("mcp.server", server), ("mcp.server.fastmcp", fastmcp)):
        sys.modules[name] = mod
    sys.modules.pop("cd_mcp_server", None)
    import cd_mcp_server
    return cd_mcp_server


@pytest.fixture
def mcp_server():
    mod = _mcp_server()
    yield mod
    for name in ("cd_mcp_server", "mcp.server.fastmcp", "mcp.server", "mcp"):
        sys.modules.pop(name, None)


_OBJ = {
    "id": "task-1",
    "name": "Wire the persistence seam",
    "type": {"key": "task", "name": "Task"},
    "properties": [
        {"key": "gsdo_task_status", "name": "Task status", "format": "select",
         "select": {"name": "Ready"}},
        {"key": "gsdo_relevant_docs", "name": "Relevant docs", "format": "text",
         "text": "docs/superpowers/plans/2026-07-18-persistence-seam.md"},
        {"key": "gsdo_ai_autonomous", "name": "AI autonomous", "format": "checkbox",
         "checkbox": True},
        {"key": "gsdo_context", "name": "Context", "format": "text", "text": "origin note"},
    ],
}


def test_get_object_returns_the_two_agent_facing_fields(mcp_server, monkeypatch):
    """The missing seam named in `field_semantics.DOES['Relevant docs']`: `list_tasks` returns
    only id/name/status and there was no full-field read tool at all."""
    monkeypatch.setattr(mcp_server, "_read_back", lambda oid: _OBJ)
    out = mcp_server.get_object("task-1")
    assert out["properties"]["Relevant docs"] == \
        "docs/superpowers/plans/2026-07-18-persistence-seam.md"
    assert out["properties"]["AI autonomous"] is True
    assert out["properties"]["Task status"] == "Ready"


def test_get_object_explains_what_those_fields_mean_at_the_call_site(mcp_server, monkeypatch):
    """A path an agent is told to open, and a flag saying it may act unsupervised, are only
    usable with their meaning attached — and the meaning comes from the module, not the tool."""
    monkeypatch.setattr(mcp_server, "_read_back", lambda oid: _OBJ)
    out = mcp_server.get_object("task-1")
    assert out["field_meanings"]["Relevant docs"] == fs.one_line("Relevant docs")
    assert out["field_meanings"]["AI autonomous"] == fs.one_line("AI autonomous")


def test_get_object_surfaces_the_real_failure_instead_of_raising(mcp_server, monkeypatch):
    """A failed read must reach the agent as a readable reason, never a crash and never a
    generic one — an agent that can't tell 'no such object' from 'auth expired' retries blindly."""
    def _boom(oid):
        raise RuntimeError("read-back failed for 'nope': 404")
    monkeypatch.setattr(mcp_server, "_read_back", _boom)
    out = mcp_server.get_object("nope")
    assert out["error"] == "read-back failed for 'nope': 404"
    assert "properties" not in out


def test_get_object_requires_an_id(mcp_server, monkeypatch):
    """Guarded BEFORE the fetch. `_read_back` is stubbed to succeed here on purpose: without the
    guard a blank id would sail through and return someone else's object, and a test that only
    asserts `"error" in out` would pass on the incidental network failure instead."""
    monkeypatch.setattr(mcp_server, "_read_back", lambda oid: _OBJ)
    out = mcp_server.get_object("  ")
    assert out["error"] == "get_object: object_id is required"
    assert "properties" not in out


# --- Part 1, step 3: capture populates `Relevant docs` -----------------------

def test_build_optional_props_writes_relevant_docs():
    props = capture_fields.build_optional_props(relevant_docs="scripts/plan_generate.py")
    assert props["Relevant docs"] == "scripts/plan_generate.py"


def test_build_optional_props_omits_relevant_docs_when_the_item_named_no_source():
    """Bare-by-default: nothing invented, no empty key written."""
    assert "Relevant docs" not in capture_fields.build_optional_props(relevant_docs=None)
    assert "Relevant docs" not in capture_fields.build_optional_props(relevant_docs="   ")


def test_creation_props_carries_relevant_docs_onto_a_captured_task():
    props = capture_generate._creation_props(
        "Task", {"name": "Fix the seam", "relevant_docs": "docs/api_contract_v2.md"}, None)
    assert props["Relevant docs"] == "docs/api_contract_v2.md"


@pytest.mark.parametrize("prompt", ["prompts/weeding_gate.md", "prompts/daily_memory_pass.md"])
def test_the_capture_prompts_ask_for_relevant_docs(prompt):
    """The write path can carry the value only if the model is asked to produce it."""
    import os
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, prompt), encoding="utf-8") as fh:
        text = fh.read()
    assert "relevant_docs" in text

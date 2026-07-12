"""Tests for project_summary.summary_map — the per-project 'what it is / next step' the overlay
shows first when a work-stream row is expanded. Pure function over in-memory dicts; no Anytype,
no files, so nothing to clean up."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_summary


def test_parses_what_it_is_and_next_step():
    projects = [{"name": "Alpha",
                 "context": "what it is — the flagship build\nnext step — wire the overlay"}]
    sm = project_summary.summary_map(projects)
    assert sm["Alpha"]["what_it_is"] == "the flagship build"
    assert sm["Alpha"]["next_step"] == "wire the overlay"


def test_includes_partial_when_only_one_line_present():
    projects = [{"name": "Beta", "context": "what it is — just the what, no next step line"}]
    sm = project_summary.summary_map(projects)
    assert sm["Beta"] == {"what_it_is": "just the what, no next step line"}


def test_omits_projects_with_unparseable_context():
    # H2: the parse is fragile. A project whose Context isn't in the em-dash convention yields
    # NOTHING and is left OUT of the map — the overlay then falls back to the task list. We never
    # fabricate summary text.
    projects = [
        {"name": "Gamma", "context": "just some freeform notes with no structured lines"},
        {"name": "Delta", "context": ""},
        {"name": "Epsilon", "context": None},
    ]
    assert project_summary.summary_map(projects) == {}


def test_skips_nameless_projects():
    projects = [{"name": None, "context": "what it is — orphan"}]
    assert project_summary.summary_map(projects) == {}

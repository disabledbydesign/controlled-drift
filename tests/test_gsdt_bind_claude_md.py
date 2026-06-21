import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def test_write_claude_md_creates_file(tmp_path):
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "Build Controlled Drift", "Builder practice")
    path = os.path.join(str(tmp_path), "CLAUDE.md")
    assert os.path.isfile(path)
    content = open(path).read()
    assert "Controlled Drift binding" in content
    assert "Build Controlled Drift" in content
    assert "Builder practice" in content


def test_write_claude_md_appends_to_existing(tmp_path):
    claude_md = os.path.join(str(tmp_path), "CLAUDE.md")
    with open(claude_md, "w") as f:
        f.write("# My project\n\nExisting content.\n")
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "My Project", None)
    content = open(claude_md).read()
    assert "Existing content" in content
    assert "Controlled Drift binding" in content


def test_write_claude_md_idempotent(tmp_path):
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "My Project", "My Goal")
    _write_claude_md(str(tmp_path), "My Project", "My Goal")
    content = open(os.path.join(str(tmp_path), "CLAUDE.md")).read()
    assert content.count("Controlled Drift binding") == 1


def test_write_claude_md_no_goal(tmp_path):
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "My Project", None)
    content = open(os.path.join(str(tmp_path), "CLAUDE.md")).read()
    assert "My Project" in content
    assert "Goal:" not in content


def test_write_claude_md_replaces_stale_section(tmp_path):
    """Re-running with updated project name overwrites the old section."""
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "Old Name", None)
    _write_claude_md(str(tmp_path), "New Name", None)
    content = open(os.path.join(str(tmp_path), "CLAUDE.md")).read()
    assert "New Name" in content
    assert "Old Name" not in content
    assert content.count("Controlled Drift binding") == 1


def test_write_claude_md_preserves_content_before_section(tmp_path):
    """Pre-existing content before the binding section is kept."""
    claude_md = os.path.join(str(tmp_path), "CLAUDE.md")
    with open(claude_md, "w") as f:
        f.write("# Project instructions\n\nDo things this way.\n")
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "Proj", None)
    content = open(claude_md).read()
    assert "Do things this way." in content
    assert "Controlled Drift binding" in content


def test_write_claude_md_preserves_content_after_section(tmp_path):
    """Content in a section after the binding section is kept when replaced."""
    from gsdt_bind import _write_claude_md, _CLAUDE_MD_MARKER
    claude_md = os.path.join(str(tmp_path), "CLAUDE.md")
    with open(claude_md, "w") as f:
        f.write(f"# Preamble\n\n{_CLAUDE_MD_MARKER}\n\nOld content.\n\n## Other section\n\nKept.\n")
    _write_claude_md(str(tmp_path), "Proj", None)
    content = open(claude_md).read()
    assert "Kept." in content
    assert "Old content." not in content
    assert content.count("Controlled Drift binding") == 1


def test_write_claude_md_contains_arc_fields_guidance(tmp_path):
    """Generated section tells agents about Depends on and Arc position rationale."""
    from gsdt_bind import _write_claude_md
    _write_claude_md(str(tmp_path), "My Project", None)
    content = open(os.path.join(str(tmp_path), "CLAUDE.md")).read()
    assert "Depends on" in content
    assert "Arc position rationale" in content
    assert "Guard #6" in content

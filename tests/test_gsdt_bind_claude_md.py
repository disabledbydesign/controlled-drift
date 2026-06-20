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

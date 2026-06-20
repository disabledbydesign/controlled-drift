# tests/test_sweep.py
import os, json, tempfile, pytest
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

def make_tree(tmp, structure):
    """structure: {relative_path: content_string_or_None_for_dir}"""
    for path, content in structure.items():
        full = os.path.join(tmp, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if content is None:
            os.makedirs(full, exist_ok=True)
        else:
            with open(full, 'w') as f:
                f.write(content)

def test_select_includes_root_md(tmp_path):
    make_tree(str(tmp_path), {"ROADMAP.md": "# plan\nopen item", "CLAUDE.md": "notes"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    names = [os.path.basename(p) for p in files["planning"]]
    assert "ROADMAP.md" in names
    assert "CLAUDE.md" in names

def test_select_excludes_node_modules(tmp_path):
    make_tree(str(tmp_path), {"node_modules/pkg/index.js": "// code", "ROADMAP.md": "open"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    assert not any("node_modules" in p for p in files["code"])

def test_select_excludes_archive_dir(tmp_path):
    make_tree(str(tmp_path), {"archive/old.md": "done stuff", "ROADMAP.md": "open"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    # Verify the file inside archive/ is not present (check basename to avoid
    # false positive from pytest naming the tmp dir with "archive" in it)
    all_paths = files["planning"] + files["docs"]
    assert not any(
        os.path.dirname(p).endswith("archive") or os.path.dirname(p).endswith("archives")
        for p in all_paths
    )

def test_select_excludes_archive_in_filename(tmp_path):
    make_tree(str(tmp_path), {"ROADMAP_archived.md": "old", "ROADMAP.md": "open"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    names = [os.path.basename(p) for p in files["planning"]]
    assert "ROADMAP_archived.md" not in names
    assert "ROADMAP.md" in names

def test_select_excludes_completion_marker(tmp_path):
    make_tree(str(tmp_path), {
        "DONE.md": "# DONE\nnothing open",
        "ROADMAP.md": "open item",
    })
    from sweep import select_files
    files = select_files(str(tmp_path))
    names = [os.path.basename(p) for p in files["planning"]]
    assert "DONE.md" not in names
    assert "ROADMAP.md" in names

def test_select_includes_planning_subdir(tmp_path):
    make_tree(str(tmp_path), {"docs/plan.md": "TODO: something"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    assert any("plan.md" in p for p in files["docs"])

def test_select_skips_deep_code(tmp_path):
    make_tree(str(tmp_path), {"src/deep/nested/util.py": "# TODO: fix"})
    from sweep import select_files
    files = select_files(str(tmp_path))
    # two levels deep — should NOT be included (only root + one level)
    assert not any("nested" in p for p in files["code"])

def test_total_readable_count(tmp_path):
    make_tree(str(tmp_path), {"ROADMAP.md": "open", "docs/plan.md": "open", "app.py": "# TODO"})
    from sweep import select_files, total_readable_count
    files = select_files(str(tmp_path))
    assert total_readable_count(files) >= 3

def test_is_sweep_stale_no_binding(tmp_path):
    from sweep import is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == False  # unbound → not applicable

def test_is_sweep_stale_no_last_sweep(tmp_path):
    import json
    gsdot = {"system": "Controlled Drift", "binds_to": {"projects": [{"id": "x", "name": "X"}]}}
    with open(os.path.join(str(tmp_path), ".gsdot"), "w") as f:
        json.dump(gsdot, f)
    from sweep import is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == True

def test_is_sweep_stale_recent(tmp_path):
    import json, datetime
    gsdot = {"system": "Controlled Drift",
             "binds_to": {"projects": [{"id": "x", "name": "X"}]},
             "last_sweep": datetime.date.today().isoformat()}
    with open(os.path.join(str(tmp_path), ".gsdot"), "w") as f:
        json.dump(gsdot, f)
    from sweep import is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == False

def test_is_sweep_stale_old(tmp_path):
    import json, datetime
    old = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
    gsdot = {"system": "Controlled Drift",
             "binds_to": {"projects": [{"id": "x", "name": "X"}]},
             "last_sweep": old}
    with open(os.path.join(str(tmp_path), ".gsdot"), "w") as f:
        json.dump(gsdot, f)
    from sweep import is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == True

def test_extract_signals_todo(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("x = 1\n# TODO: fix the edge case\ny = 2\n")
    from sweep import extract_code_signals
    sigs = extract_code_signals(str(f))
    assert len(sigs) == 1
    assert sigs[0]["signal_type"] == "todo"
    assert "fix the edge case" in sigs[0]["source_excerpt"]

def test_extract_signals_fixme(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("# FIXME: broken on windows\npass\n")
    from sweep import extract_code_signals
    sigs = extract_code_signals(str(f))
    assert any(s["signal_type"] == "fixme" for s in sigs)

def test_extract_signals_stub(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def foo():\n    raise NotImplementedError\n")
    from sweep import extract_code_signals
    sigs = extract_code_signals(str(f))
    assert any(s["signal_type"] == "stub" for s in sigs)

def test_extract_signals_empty_file(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("def foo():\n    return 42\n")
    from sweep import extract_code_signals
    assert extract_code_signals(str(f)) == []

def test_extract_signals_includes_source_file(tmp_path):
    f = tmp_path / "util.py"
    f.write_text("# TODO: add validation\n")
    from sweep import extract_code_signals
    sigs = extract_code_signals(str(f))
    assert sigs[0]["source_file"] == str(f)

def test_select_excludes_dot_files(tmp_path):
    make_tree(str(tmp_path), {
        ".gsdot-log.md": "## 2026-06-19\n\nSomething went well.",
        ".gsdot": '{"system": "Controlled Drift"}',
        "ROADMAP.md": "open item",
    })
    from sweep import select_files
    files = select_files(str(tmp_path))
    names = [os.path.basename(p) for p in files["planning"] + files["code"] + files["docs"]]
    assert ".gsdot-log.md" not in names
    assert ".gsdot" not in names
    assert "ROADMAP.md" in names

def test_update_last_sweep_stale_becomes_fresh(tmp_path):
    import json, datetime
    old = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
    gsdot = {"system": "Controlled Drift",
             "binds_to": {"projects": [{"id": "x", "name": "X"}]},
             "last_sweep": old}
    with open(os.path.join(str(tmp_path), ".gsdot"), "w") as f:
        json.dump(gsdot, f)
    from sweep import update_last_sweep, is_sweep_stale
    assert is_sweep_stale(str(tmp_path)) == True
    update_last_sweep(str(tmp_path))
    assert is_sweep_stale(str(tmp_path)) == False

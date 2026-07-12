"""build_task must add a 'Duration source' select (stated/estimated) and link it to Task."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_task


def test_build_task_creates_and_links_duration_source(monkeypatch):
    ensured = []   # (name, fmt, options)
    linked = {}    # type_id -> list of props linked

    def fake_ensure_property(name, fmt, options=None):
        ensured.append((name, fmt, options))
        return f"prop-{name}"
    def fake_find_type(key):
        return {"id": "task-type-id", "key": "task"}
    def fake_link(type_id, props):
        linked[type_id] = props

    monkeypatch.setattr(build_task.g, "ensure_property", fake_ensure_property)
    monkeypatch.setattr(build_task.g, "find_type", fake_find_type)
    monkeypatch.setattr(build_task.g, "link_properties_to_type", fake_link)

    build_task.build_task()

    assert ("Duration source", "select", ["stated", "estimated"]) in ensured
    assert "prop-Duration source" in linked["task-type-id"]

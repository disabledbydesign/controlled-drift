# tests/test_priority_shape.py — the fragmented-day priority shape (Task 6/6D) parsing + id
# threading. Pure over the model text / plan dict — no Anytype, no LLM.
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import plan_generate as pg


def _block(shape_json):
    return "here is the plan\n```json\n" + json.dumps(shape_json) + "\n```\n"


def test_parse_plan_detects_priority_shape():
    plan = pg.parse_plan(_block({
        "shape": "priority",
        "woven_frame": "fragmented day",
        "header": "Today's fragmented — a short list to pull from.",
        "items": [{"project": "Jobs", "task": "apply", "why": "survival", "ref": "T1"}],
    }))
    assert plan["shape"] == "priority"
    assert plan["items"][0]["task"] == "apply"
    assert plan["header"].startswith("Today's fragmented")
    assert plan["still_here"] == []          # defaulted


def test_parse_plan_defaults_clock_shape():
    plan = pg.parse_plan(_block({
        "woven_frame": "normal day",
        "blocks": [{"label": "Morning", "time": "09:00 – 12:00", "items": []}],
    }))
    assert plan["shape"] == "clock"
    assert plan["blocks"][0]["label"] == "Morning"


def test_parse_plan_priority_when_items_but_no_blocks():
    # even without an explicit "shape", a flat items[] with no blocks[] is the priority shape
    plan = pg.parse_plan(_block({"woven_frame": "x", "items": []}))
    assert plan["shape"] == "priority"


def test_resolve_ids_threads_onto_flat_priority_items():
    plan = {"shape": "priority",
            "items": [{"task": "apply Acme", "ref": "T1"},
                      {"task": "Some Task", "ref": None}]}
    ref_map = {"T1": "id-acme"}
    tasks = [{"id": "id-acme", "name": "apply Acme"},
             {"id": "id-some", "name": "Some Task", "context": "notes here"}]
    pg._resolve_ids(plan, ref_map, tasks)
    assert plan["items"][0]["id"] == "id-acme"          # via ref token
    assert plan["items"][1]["id"] == "id-some"          # via exact name fallback
    assert plan["items"][1]["description"] == "notes here"
    assert "ref" not in plan["items"][0]                 # token consumed


def test_ensure_all_tasks_accounted_counts_priority_items():
    plan = {"shape": "priority", "items": [{"task": "apply Acme", "id": "id-acme"}]}
    tasks = [{"id": "id-acme", "name": "apply Acme"},
             {"id": "id-missing", "name": "Forgotten Task"}]
    pg._ensure_all_tasks_accounted(plan, tasks)
    labels = {sh["label"] for sh in plan["still_here"]}
    assert "Forgotten Task" in labels                    # the unplaced one is surfaced
    assert "apply Acme" not in labels                     # the placed one isn't duplicated

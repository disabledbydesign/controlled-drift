# tests/test_plan_corrections_log.py
import sys, os, json, tempfile, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from plan_corrections_log import log_correction

def test_appends_one_jsonl_line(tmp_path):
    path = tmp_path / "corr.jsonl"
    log_correction("move_time", {"name": "A", "start": "09:00"}, {"name": "A", "start": "11:00"}, path=str(path))
    log_correction("reject", {"name": "B"}, None, path=str(path))
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["kind"] == "move_time" and rec["before"]["start"] == "09:00" and "ts" in rec

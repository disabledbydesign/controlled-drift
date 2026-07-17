import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import engagement_log as el


def test_logs_a_real_change(cd_sandbox):
    el.log_change("oid1", "Job search", "Open", "Steady")
    recs = el.read_changes()
    assert recs and recs[-1]["old"] == "Open" and recs[-1]["new"] == "Steady"
    assert recs[-1]["project_id"] == "oid1" and recs[-1]["name"] == "Job search" and "ts" in recs[-1]


def test_noop_when_unchanged(cd_sandbox):
    el.log_change("oid1", "Job search", "Open", "Open")
    assert el.read_changes() == []


def test_read_missing_file_is_empty(cd_sandbox):
    assert el.read_changes() == []

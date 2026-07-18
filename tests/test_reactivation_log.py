import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import reactivation_log as rl


def test_logs_a_real_toggle(cd_sandbox):
    rl.log_change("rid1", "Clean the fridge", False, True)
    recs = rl.read_changes()
    assert recs and recs[-1]["old"] is False and recs[-1]["new"] is True
    assert recs[-1]["recurring_id"] == "rid1" and recs[-1]["name"] == "Clean the fridge" and "ts" in recs[-1]


def test_noop_when_unchanged(cd_sandbox):
    rl.log_change("rid1", "Clean the fridge", True, True)
    assert rl.read_changes() == []


def test_read_missing_file_is_empty(cd_sandbox):
    assert rl.read_changes() == []

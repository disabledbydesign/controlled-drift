import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import friction_report


def sig(via=None, shot=None, marks=None, ts="2026-07-19T10:00:00", source="log_day"):
    ref = {"kind": "log_day", "tags": ["issue"]}
    if via: ref["via"] = via
    if shot: ref["shot"] = shot
    if marks: ref["marks"] = marks
    return {"ts": ts, "source": source, "reference": ref, "raw": "x"}


def test_counts_only_friction_entries():
    out = friction_report.summarise([sig(via="button"), sig(source="config_authoring")])
    assert out["total"] == 1


def test_counts_each_way_in():
    out = friction_report.summarise([sig(via="button"), sig(via="button"), sig(via="longpress")])
    assert out["by_via"]["button"] == 2
    assert out["by_via"]["longpress"] == 1


def test_names_an_entry_point_that_has_never_been_used():
    # 20, not a handful: below MIN_FOR_A_VERDICT nothing is called unused at all, which is the
    # point of the guard below. This test is about naming a zero once there IS enough to go on.
    out = friction_report.summarise([sig(via="button") for _ in range(20)])
    assert "longpress" in out["unused"]
    assert "button" not in out["unused"]


def test_a_rarely_used_way_in_is_reported_but_not_called_unused():
    signals = [sig(via="button") for _ in range(19)] + [sig(via="longpress")]
    out = friction_report.summarise(signals)
    assert out["unused"] == [] or "longpress" not in out["unused"]
    assert "longpress" in out["rarely_used"]


def test_nothing_is_called_unused_before_there_is_enough_to_go_on():
    """Two entries is not evidence. Calling a way in unused on that basis would be a made-up finding."""
    out = friction_report.summarise([sig(via="button"), sig(via="button")])
    assert out["unused"] == []
    assert out["rarely_used"] == []


def test_entries_written_before_the_capture_shipped_are_not_evidence_against_anything():
    """Old entries carry no `via`. Counting them would make every way in look unused."""
    out = friction_report.summarise([sig() for _ in range(40)])
    assert out["total"] == 40
    assert out["unused"] == []
    assert out["rarely_used"] == []


def test_the_output_says_why_the_zeros_are_zero_when_nothing_recorded_a_way_in(capsys):
    """Four zeros printed under a count of 45 entries reads as 'she used none of them'. The real
    reason is that those entries predate the recording, and the output has to say which it is."""
    friction_report._print(friction_report.summarise([sig() for _ in range(45)]))
    printed = capsys.readouterr().out
    assert "0 of 45 entries recorded this" in printed
    assert "before the system started recording which way in" in printed


def test_counts_snapshots_and_marks():
    out = friction_report.summarise([
        sig(via="button", shot="a.png", marks=[{"box": [0, 0, 1, 1]}]),
        sig(via="button", shot="b.png"),
        sig(via="button"),
    ])
    assert out["total"] == 3 and out["with_shot"] == 2 and out["with_marks"] == 1


def test_empty_log_does_not_crash():
    out = friction_report.summarise([])
    assert out["total"] == 0 and out["unused"] == [] and out["since"] is None


def test_a_record_with_no_reference_at_all_does_not_crash():
    out = friction_report.summarise([{"ts": "2026-07-19T10:00:00", "source": "log_day",
                                      "reference": None, "raw": "x"}])
    assert out["total"] == 1 and out["with_shot"] == 0


def test_the_output_warns_that_a_broken_way_in_also_counts_zero(capsys):
    """A broken entry point records zero uses and looks exactly like an unwanted one. Whoever
    reads this months from now will not have the build plan open, so the output has to say it."""
    friction_report._print(friction_report.summarise([sig(via="button") for _ in range(20)]))
    printed = capsys.readouterr().out
    assert "Never used: longpress" in printed
    assert "WORKS" in printed
    assert "your call" in printed


def test_it_never_reports_on_her_rather_than_on_the_mechanisms(capsys):
    """Scope guard: entry points only. No rate of logging, no streak, no trend, no nudge."""
    friction_report._print(friction_report.summarise([sig(via="button") for _ in range(20)]))
    printed = capsys.readouterr().out.lower()
    for word in ("streak", "per day", "per week", "trend", "keep it up", "you should", "try to"):
        assert word not in printed, "the report is talking about June, not about the mechanism: %r" % word

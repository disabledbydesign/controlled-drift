"""Tests for scripts/migrate_plan_deferral_to_corrections.py.

Every test builds its OWN signal_log/corrections fixture files under tmp_path and passes their
paths explicitly to the script's functions — never against June's real scripts/data/*.jsonl, and
never even via the CD_DATA_DIR env-var redirect other tests use, so there is no path by which a
bug here could touch her real files.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import migrate_plan_deferral_to_corrections as migrate_mod
import signal_log
import corrections_log


def _write_jsonl(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


SIGNAL_FIXTURE = [
    {"ts": "2026-07-15T10:29:13", "source": "plan_deferral", "reference": "id-walk",
     "raw": "Go on a walk (was 09:00)"},
    {"ts": "2026-07-15T09:00:00", "source": "log_day", "reference": {"kind": "log_day"},
     "raw": "June's own words about the day"},
    {"ts": "2026-07-16T13:00:08", "source": "plan_deferral", "reference": "id-foodstamps",
     "raw": "Cancel food stamps"},
    {"ts": "2026-07-17T08:00:00", "source": "checkin_reply", "reference": {"flag_id": "f1"},
     "raw": "yes, that's done"},
]


def _seed(tmp_path):
    signal_path = str(tmp_path / "signal_log.jsonl")
    corrections_path = str(tmp_path / "corrections.jsonl")
    _write_jsonl(signal_path, SIGNAL_FIXTURE)
    return signal_path, corrections_path


# --- plan() / dry run: reports only, never mutates --------------------------

def test_plan_finds_the_plan_deferral_entries_and_leaves_the_rest_as_kept(tmp_path):
    signal_path, corrections_path = _seed(tmp_path)
    p = migrate_mod.plan(signal_path, corrections_path)
    assert [r["reference"] for r in p["to_move"]] == ["id-walk", "id-foodstamps"]
    assert [r["source"] for r in p["kept"]] == ["log_day", "checkin_reply"]
    assert p["pending"] == p["to_move"]          # nothing pre-migrated yet
    assert p["already_migrated"] == []


def test_dry_run_mutates_neither_file(tmp_path):
    signal_path, corrections_path = _seed(tmp_path)
    before_signal = _read_jsonl(signal_path)
    report = migrate_mod.migrate(dry_run=True, signal_path=signal_path, corrections_path=corrections_path)
    assert _read_jsonl(signal_path) == before_signal              # untouched
    assert not os.path.exists(corrections_path)                    # never created
    assert "2" in report or "Found 2" in report                    # sanity: mentions the count


def test_dry_run_report_is_plain_sentences_not_json(tmp_path):
    signal_path, corrections_path = _seed(tmp_path)
    report = migrate_mod.migrate(dry_run=True, signal_path=signal_path, corrections_path=corrections_path)
    assert "Go on a walk (was 09:00)" in report
    assert "Cancel food stamps" in report
    assert "2026-07-15" in report and "2026-07-16" in report
    assert "log_day" not in report                                 # her own-words entries not listed as moving
    assert not report.strip().startswith("{") and not report.strip().startswith("[")
    for line in report.splitlines():
        assert not line.strip().startswith("{"), "a JSON line leaked into the human report"


def test_dry_run_on_a_clean_log_says_nothing_to_move(tmp_path):
    signal_path = str(tmp_path / "signal_log.jsonl")
    corrections_path = str(tmp_path / "corrections.jsonl")
    _write_jsonl(signal_path, [SIGNAL_FIXTURE[1], SIGNAL_FIXTURE[3]])   # only non-deferral entries
    report = migrate_mod.migrate(dry_run=True, signal_path=signal_path, corrections_path=corrections_path)
    assert "nothing to move" in report.lower() or "found nothing" in report.lower()


# --- apply: actually moves them ----------------------------------------------

def test_apply_moves_entries_and_preserves_original_timestamp(tmp_path):
    signal_path, corrections_path = _seed(tmp_path)
    migrate_mod.migrate(dry_run=False, signal_path=signal_path, corrections_path=corrections_path)

    remaining = signal_log.read_signals(signal_path)
    assert [r["source"] for r in remaining] == ["log_day", "checkin_reply"]   # only these two left

    moved = corrections_log.read_records(corrections_path)
    assert [(r["kind"], r["object_id"], r["before"], r["after"], r["ts"], r["surface"])
            for r in moved] == [
        ("not_today", "id-walk", {"name": "Go on a walk (was 09:00)"}, None,
         "2026-07-15T10:29:13", "migrated_signal_log"),
        ("not_today", "id-foodstamps", {"name": "Cancel food stamps"}, None,
         "2026-07-16T13:00:08", "migrated_signal_log"),
    ]
    # nothing invented: object_type was never recorded in the old data, so it's absent, not guessed
    assert all("object_type" not in r for r in moved)


def test_apply_does_not_touch_the_entries_that_are_her_own_words(tmp_path):
    signal_path, corrections_path = _seed(tmp_path)
    migrate_mod.migrate(dry_run=False, signal_path=signal_path, corrections_path=corrections_path)
    remaining = signal_log.read_signals(signal_path)
    assert remaining == [SIGNAL_FIXTURE[1], SIGNAL_FIXTURE[3]]     # byte-identical, same order


def test_apply_is_idempotent_no_duplicates_on_a_second_run(tmp_path):
    signal_path, corrections_path = _seed(tmp_path)
    migrate_mod.migrate(dry_run=False, signal_path=signal_path, corrections_path=corrections_path)
    first_pass = corrections_log.read_records(corrections_path)

    second_report = migrate_mod.migrate(dry_run=False, signal_path=signal_path, corrections_path=corrections_path)
    second_pass = corrections_log.read_records(corrections_path)

    assert second_pass == first_pass                               # no duplicate records appended
    assert "nothing to move" in second_report.lower()
    assert signal_log.read_signals(signal_path) == [SIGNAL_FIXTURE[1], SIGNAL_FIXTURE[3]]


def test_apply_recovers_from_an_interrupted_prior_run_without_duplicating(tmp_path):
    """Simulates a crash between 'appended to corrections' and 'cleared from signal_log':
    corrections.jsonl already has one migrated record, but signal_log.jsonl still has BOTH
    plan_deferral entries. A re-run must finish the job (clear signal_log) without re-appending
    the one that's already there, and must still move the one that never made it across."""
    signal_path, corrections_path = _seed(tmp_path)
    # Pre-seed corrections.jsonl as if the first entry already made it across before the crash.
    _write_jsonl(corrections_path, [{
        "ts": "2026-07-15T10:29:13", "kind": "not_today",
        "before": {"name": "Go on a walk (was 09:00)"}, "after": None,
        "object_id": "id-walk", "surface": "migrated_signal_log",
    }])

    p = migrate_mod.plan(signal_path, corrections_path)
    assert [r["reference"] for r in p["pending"]] == ["id-foodstamps"]
    assert [r["reference"] for r in p["already_migrated"]] == ["id-walk"]

    migrate_mod.migrate(dry_run=False, signal_path=signal_path, corrections_path=corrections_path)

    moved = corrections_log.read_records(corrections_path)
    assert [r["object_id"] for r in moved] == ["id-walk", "id-foodstamps"]   # id-walk NOT duplicated
    remaining = signal_log.read_signals(signal_path)
    assert [r["source"] for r in remaining] == ["log_day", "checkin_reply"]  # cleanup still completed


def test_migration_never_writes_a_fourteenth_data_file(tmp_path):
    """The repo rule this task cites: route through an existing log, don't add a new one."""
    signal_path, corrections_path = _seed(tmp_path)
    migrate_mod.migrate(dry_run=False, signal_path=signal_path, corrections_path=corrections_path)
    assert sorted(os.listdir(tmp_path)) == ["corrections.jsonl", "signal_log.jsonl"]

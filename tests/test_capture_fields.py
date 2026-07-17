import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import capture_fields as cf


def test_duration_valid_int():
    assert cf.build_optional_props(duration_min=45) == {
        "Duration min": 45, "Duration source": "stated"}


def test_duration_coerces_numeric_string():
    assert cf.build_optional_props(duration_min="30") == {
        "Duration min": 30, "Duration source": "stated"}


def test_stated_duration_labels_source_stated():
    assert cf.build_optional_props(duration_min=90) == {
        "Duration min": 90, "Duration source": "stated"}


def test_estimated_duration_labels_source_estimated():
    assert cf.build_optional_props(duration_estimate_min=120) == {
        "Duration min": 120, "Duration source": "estimated"}


def test_stated_wins_over_estimate_fidelity_first():
    # June said 90; the model also guessed 120. Her number is truth; the estimate is discarded.
    assert cf.build_optional_props(duration_min=90, duration_estimate_min=120) == {
        "Duration min": 90, "Duration source": "stated"}


def test_no_duration_writes_neither_key():
    out = cf.build_optional_props(duration_min=None, duration_estimate_min=None)
    assert "Duration min" not in out and "Duration source" not in out


def test_invalid_estimate_writes_nothing():
    assert cf.build_optional_props(duration_estimate_min="soon") == {}
    assert cf.build_optional_props(duration_estimate_min=0) == {}
    assert cf.build_optional_props(duration_estimate_min=-5) == {}


def test_duration_priors_text_present():
    # The shared priors carry June's calibration so both prompt sites stay in sync.
    assert "1" in cf.DURATION_PRIORS and "hour" in cf.DURATION_PRIORS.lower()


def test_duration_absent_or_bad_writes_nothing():
    assert cf.build_optional_props(duration_min=None) == {}
    assert cf.build_optional_props(duration_min="") == {}
    assert cf.build_optional_props(duration_min=0) == {}
    assert cf.build_optional_props(duration_min=-10) == {}
    assert cf.build_optional_props(duration_min="soon") == {}


def test_affect_verbatim_string():
    assert cf.build_optional_props(affect="this one is heavy") == {"Affective": "this one is heavy"}


def test_affect_blank_or_none_writes_nothing():
    assert cf.build_optional_props(affect="") == {}
    assert cf.build_optional_props(affect="   ") == {}
    assert cf.build_optional_props(affect=None) == {}


def test_affect_never_flattened_to_number():
    # guard #3: a bare scalar is not a valid affect note — do not store "3"
    assert cf.build_optional_props(affect=3) == {}


def test_blocked_on():
    assert cf.build_optional_props(blocked_on="waiting on Donna's edits") == {"Blocked on": "waiting on Donna's edits"}
    assert cf.build_optional_props(blocked_on="") == {}


def test_access_conditions_filters_to_known_options():
    got = cf.build_optional_props(access_conditions=["Involves-leaving-house", "made-up-tag"])
    assert got == {"Access conditions": ["Involves-leaving-house"]}


def test_access_conditions_empty_after_filter_writes_nothing():
    assert cf.build_optional_props(access_conditions=["nope"]) == {}
    assert cf.build_optional_props(access_conditions=[]) == {}
    assert cf.build_optional_props(access_conditions=None) == {}


def test_all_fields_together():
    got = cf.build_optional_props(duration_min=20, affect="dread", blocked_on="the API key",
                                  access_conditions=["Requires-talking-to-a-person"])
    assert got == {"Duration min": 20, "Duration source": "stated",
                   "Affective": "dread", "Blocked on": "the API key",
                   "Access conditions": ["Requires-talking-to-a-person"]}


def test_engagement_valid_value_kept():
    assert cf.build_project_engagement_props(engagement="Steady")["Engagement"] == "Steady"
    assert cf.build_project_engagement_props(engagement="Backburner")["Engagement"] == "Backburner"


def test_engagement_case_insensitive():
    assert cf.build_project_engagement_props(engagement="open")["Engagement"] == "Open"


def test_engagement_absent_or_invalid_defaults_open():
    assert cf.build_project_engagement_props(engagement=None)["Engagement"] == "Open"
    assert cf.build_project_engagement_props(engagement="")["Engagement"] == "Open"
    # retired values are NOT valid engagement anymore -> fall back to Open, never written through
    assert cf.build_project_engagement_props(engagement="Sprint")["Engagement"] == "Open"
    assert cf.build_project_engagement_props(engagement="Hyperfixation")["Engagement"] == "Open"


def test_engagement_notes_written_only_when_present():
    out = cf.build_project_engagement_props(engagement="Steady", engagement_notes="deadline Friday")
    assert out["Engagement notes"] == "deadline Friday"
    assert "Engagement notes" not in cf.build_project_engagement_props(engagement="Steady", engagement_notes="")
    # guard #3: a bare number is not valid free text
    assert "Engagement notes" not in cf.build_project_engagement_props(engagement="Steady", engagement_notes=3)

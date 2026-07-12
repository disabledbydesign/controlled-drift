import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import capture_fields as cf


def test_duration_valid_int():
    assert cf.build_optional_props(duration_min=45) == {"Duration min": 45}


def test_duration_coerces_numeric_string():
    assert cf.build_optional_props(duration_min="30") == {"Duration min": 30}


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
    assert got == {"Duration min": 20, "Affective": "dread", "Blocked on": "the API key",
                   "Access conditions": ["Requires-talking-to-a-person"]}

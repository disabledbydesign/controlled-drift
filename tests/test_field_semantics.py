"""Field semantics: lookup, the two grains, June's override layer, and guard #3.

conftest redirects CD_DATA_DIR to a sandbox, so the override file and the corrections log
written here never touch June's real data. Tests that write overrides pass an explicit tmp_path
as well, so they can't collide with each other.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import field_semantics as fs


# --- lookup + the two grains -------------------------------------------------

def test_lookup_is_case_and_whitespace_insensitive():
    assert fs.lookup("  affective ") is fs.FIELDS["Affective"]
    assert fs.canonical("BLOCKED ON") == "Blocked on"


def test_lookup_returns_none_for_unknown_field():
    assert fs.lookup("Nonexistent field") is None
    assert fs.lookup(None) is None


def test_every_entry_has_meaning_and_a_citation():
    for name, e in fs.FIELDS.items():
        assert e["means"].strip(), name
        assert e["source"].strip(), name
        assert isinstance(e["types"], tuple) and e["types"], name


def test_hint_is_one_short_line_for_every_field():
    """The short grain has to fit under a form control and in describe_model's per-field line."""
    for name in fs.FIELDS:
        hint = fs.one_line(name)
        assert hint and "\n" not in hint, name
        assert len(hint) <= 110, (name, len(hint))


# --- what the field DOES -----------------------------------------------------
# These make drift structurally hard rather than a rule someone has to remember: a new field
# cannot be added without stating its runtime consequence, and a free-text field cannot ship a
# single example the model would copy.

def test_every_field_records_what_it_does():
    """A field an agent can write must say what happens when it is set, not only what it means."""
    for name in list(fs.FIELDS) + list(fs.UNDEFINED):
        d = fs.does(name)
        assert d, f"{name} has no DOES entry — say what reads/writes it, or that nothing does"
        assert d["status"] in fs.DOES_STATUSES, (name, d.get("status"))
        assert d.get("read_by", "").strip(), name
        assert d.get("written_by", "").strip(), name


def test_does_covers_undefined_fields_too():
    """No documented MEANING and no runtime FUNCTION are different gaps; both get reported."""
    assert fs.does("Last surfaced")["status"] in fs.DOES_STATUSES
    # June asked specifically: an LLM must not write this one.
    assert "never an LLM" in fs.does("Last surfaced")["written_by"]


def test_does_line_is_one_short_line():
    for name in fs.FIELDS:
        line = fs.does_line(name)
        assert line and "\n" not in line, name
        assert len(line) <= 180, (name, len(line))


def test_does_line_never_lends_one_type_s_story_to_another():
    """Caught by driving describe_model on the live space, not by any test that existed.

    `Foreground projects` drives real selection on a Focus Period and does nothing at all on a
    Goal. Printing the Focus Period story under the Goal's field would tell an agent that writing
    there changes the plan.
    """
    fp = fs.does_line("Foreground projects", type_name="Focus Period")
    goal = fs.does_line("Foreground projects", type_name="Goal")
    assert fp and fp.startswith("[live]")
    assert goal and goal.startswith("[undesigned]")
    assert fp != goal

    assert fs.does_line("Goal status", type_name="Goal").startswith("[live]")
    assert fs.does_line("Goal status", type_name="Project").startswith("[undesigned]")


def test_no_does_entry_is_invented_for_an_unknown_field():
    assert fs.does("Nonexistent field") is None


# --- examples: several, varied, never a template -----------------------------
# June, 2026-07-18: "if you give one specific example, the model may replicate your example in
# its output for the text fields." One example IS a template; several dissimilar ones are a range.

def test_free_text_fields_carry_several_varied_examples():
    for name in fs.FREE_TEXT_FIELDS:
        ex = fs.examples(name)
        assert len(ex) >= 3, f"{name}: {len(ex)} example(s) — one example gets copied verbatim"
        assert len(set(ex)) == len(ex), name
        # Varied, not one sentence rephrased: at least three distinct openings across the set.
        # (Not ALL distinct — a field whose natural form is "when X" legitimately repeats "when".)
        openings = {" ".join(x.lower().split()[:2]) for x in ex}
        assert len(openings) >= 3, (name, sorted(openings))


def test_no_definition_smuggles_a_specimen():
    """Specimens belong in EXAMPLES, under the banner — never inside the definition an LLM reads.

    Checked by containment rather than by hunting quote marks: the failure mode that matters is a
    example sitting in `means` where it reads as part of the definition and gets copied.
    """
    for name in fs.FREE_TEXT_FIELDS:
        e = fs.lookup(name)
        blob = " ".join([e["means"], e.get("not_this") or ""] + list(e.get("usage") or []))
        for ex in fs.examples(name):
            assert ex not in blob, f"{name}: example {ex!r} is duplicated into the definition"


def test_examples_are_rendered_with_the_do_not_copy_banner():
    text = fs.describe("Affective")
    assert fs.EXAMPLES_BANNER in text
    assert "NOT a template" in fs.EXAMPLES_BANNER


def test_affective_entry_routes_the_content_that_leaked():
    e = fs.lookup("Affective")
    assert "Blocked on" in e["instead"].values()
    assert "Context" in e["instead"].values()
    assert "never a scalar" in " ".join(e["usage"]).lower()


def test_describe_renders_meaning_routing_and_source():
    out = fs.describe("Affective")
    assert "MEANS:" in out and "NOT:" in out and "SOURCE:" in out and "HINT:" in out
    assert "AI_LAYER_SPEC.md" in out


def test_describe_many_skips_unknown_names():
    out = fs.describe_many(["Affective", "Not a field", "Context"])
    assert "Affective" in out and "Context" in out


def test_undefined_fields_are_reported_not_invented():
    assert fs.is_undefined("Last surfaced")
    assert fs.lookup("Last surfaced") is None          # no invented meaning
    assert fs.undefined_reason("Last surfaced")
    assert "UNDEFINED" in fs.describe("Last surfaced")


def test_describe_raises_on_a_field_it_knows_nothing_about():
    with pytest.raises(KeyError):
        fs.describe("Totally unknown field")


def test_routing_brief_names_every_free_text_target():
    brief = fs.routing_brief()
    for name in fs.FREE_TEXT_ROUTING:
        assert name in brief


# --- her override layer ------------------------------------------------------

def test_no_override_file_means_repo_defaults(tmp_path):
    p = str(tmp_path / "ov.json")
    e = fs.resolved("Affective", path=p)
    assert e["hint"] == fs.HINTS["Affective"]
    assert e["overridden"] == [] and e["default"] == {}


def test_override_wins_and_the_default_survives(tmp_path):
    p = str(tmp_path / "ov.json")
    fs.set_override("Affective", {"hint": "how I feel about it"}, path=p, log=False)
    e = fs.resolved("Affective", path=p)
    assert e["hint"] == "how I feel about it"
    assert e["overridden"] == ["hint"]
    assert e["default"]["hint"] == fs.HINTS["Affective"]      # designed value still readable
    assert fs.FIELDS["Affective"].get("hint") is None          # repo default untouched in-module
    assert fs.default_entry("Affective")["hint"] == fs.HINTS["Affective"]


def test_override_is_persisted_as_plain_json(tmp_path):
    p = str(tmp_path / "ov.json")
    fs.set_override("Context", {"means": "everything else"}, path=p, log=False)
    data = json.load(open(p))
    assert data == {"Context": {"means": "everything else"}}


def test_clear_override_restores_the_default(tmp_path):
    p = str(tmp_path / "ov.json")
    fs.set_override("Context", {"hint": "mine"}, path=p, log=False)
    fs.clear_override("Context", path=p)
    assert fs.resolved("Context", path=p)["hint"] == fs.HINTS["Context"]


def test_source_and_observed_are_not_overridable(tmp_path):
    """The citation is what lets a later reader check the original reasoning — it stays."""
    p = str(tmp_path / "ov.json")
    with pytest.raises(ValueError):
        fs.set_override("Affective", {"source": "because I said so"}, path=p, log=False)
    with pytest.raises(ValueError):
        fs.set_override("Affective", {"observed": "nope"}, path=p, log=False)


def test_set_override_rejects_an_unknown_field(tmp_path):
    with pytest.raises(ValueError):
        fs.set_override("Not a field", {"hint": "x"}, path=str(tmp_path / "ov.json"), log=False)


def test_set_override_rejects_an_empty_edit(tmp_path):
    with pytest.raises(ValueError):
        fs.set_override("Context", {}, path=str(tmp_path / "ov.json"), log=False)


def test_a_malformed_override_file_raises_rather_than_being_ignored(tmp_path):
    p = tmp_path / "ov.json"
    p.write_text('["not", "an", "object"]')
    with pytest.raises(ValueError):
        fs.read_overrides(str(p))


def test_a_revision_is_logged_through_the_existing_corrections_log(tmp_path):
    """Learning-loop signal: before/after, routed through corrections_log, not a new log."""
    import cd_paths
    import corrections_log  # noqa: F401  (the log this routes through)
    fs.set_override("Blocked on", {"hint": "what I'm waiting on"},
                    path=str(tmp_path / "ov.json"))
    lines = [json.loads(l) for l in open(cd_paths.data_file("corrections.jsonl"))
             if l.strip()]
    rec = [r for r in lines if r["kind"] == "field_semantics"][-1]
    assert rec["before"]["field"] == "Blocked on"
    assert rec["before"]["hint"] == fs.HINTS["Blocked on"]
    assert rec["after"]["hint"] == "what I'm waiting on"


# --- serialisable payload for GET /api/schema --------------------------------

def test_schema_payload_is_json_serialisable_and_carries_both_grains(tmp_path):
    payload = fs.schema_payload(path=str(tmp_path / "ov.json"))
    json.dumps(payload)                                  # raises if anything is not JSON-ready
    assert set(payload) == {"fields", "undefined", "routing_brief",
                            "examples_banner", "does_statuses"}
    aff = payload["fields"]["Affective"]
    assert aff["hint"] and aff["means"] and aff["source"]
    assert aff["field"] == "Affective"
    assert "Last surfaced" in payload["undefined"]


def test_schema_payload_reflects_her_override(tmp_path):
    p = str(tmp_path / "ov.json")
    fs.set_override("Affective", {"hint": "my words"}, path=p, log=False)
    payload = fs.schema_payload(path=p)
    assert payload["fields"]["Affective"]["hint"] == "my words"
    assert payload["fields"]["Affective"]["overridden"] == ["hint"]


# --- guard #3: the one mechanical check --------------------------------------

@pytest.mark.parametrize("value", [3, 3.5, True, "3", " 4 ", "3/5", "3 out of 5", "2.5/5"])
def test_bare_scalar_affect_is_refused(value):
    assert fs.scalar_affect_problem("Affective", value)


@pytest.mark.parametrize("value", [
    "dreading it",
    "I'm putting this off",
    "3 emails deep and still avoiding it",     # starts with a number, is a real note
    "feels like a 3-hour slog",
    "",
])
def test_real_affect_text_passes_untouched(value):
    """No semantic judgment is made — only the objectively-scalar case is refused."""
    assert fs.scalar_affect_problem("Affective", value) is None


def test_scalar_rule_applies_only_to_affect_fields():
    assert fs.scalar_affect_problem("Duration min", 90) is None
    assert fs.scalar_affect_problem("Context", "3") is None


def test_check_scalar_affect_raises_loudly_never_silently_drops():
    with pytest.raises(ValueError) as exc:
        fs.check_scalar_affect({"Affective": "3", "Context": "fine"})
    assert "guard #3" in str(exc.value)


def test_check_scalar_affect_passes_a_clean_property_dict():
    fs.check_scalar_affect({"Affective": "dreading it", "Duration min": 90})
    fs.check_scalar_affect(None)


def test_the_string_form_capture_fields_misses_is_caught():
    """capture_fields._text_prop drops a non-string, so int 3 never reaches the API — but the
    STRING "3" passes it. That is the gap this check closes on the direct write paths."""
    import capture_fields
    assert capture_fields._text_prop(3) is None            # already handled there
    assert capture_fields._text_prop("3") == "3"           # slips through
    assert fs.scalar_affect_problem("Affective", "3")      # caught here


# --- the write layer actually enforces it ------------------------------------

def test_gsdo_objects_create_refuses_a_scalar_affect_before_any_network_call(monkeypatch):
    import gsdo_objects

    def boom(*a, **k):
        raise AssertionError("should have raised before touching the space")

    monkeypatch.setattr(gsdo_objects.g, "get_space_id", boom)
    with pytest.raises(ValueError):
        gsdo_objects.create_object("task", "x", properties={"Affective": "4"})


def test_gsdo_objects_update_refuses_a_scalar_affect_before_any_network_call(monkeypatch):
    import gsdo_objects

    def boom(*a, **k):
        raise AssertionError("should have raised before touching the space")

    monkeypatch.setattr(gsdo_objects.g, "get_space_id", boom)
    with pytest.raises(ValueError):
        gsdo_objects.update("obj-1", properties={"Affective": 4})

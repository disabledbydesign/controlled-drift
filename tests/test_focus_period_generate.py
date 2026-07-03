"""focus_period_generate — the LLM-authoring backend. The LLM call itself isn't unit-tested
(non-deterministic); the pure parse + prompt-anchor are."""
import datetime as dt
import focus_period_generate as fpg


def test_parse_fields_from_fenced_json():
    text = 'Here you go:\n```json\n{"name": "Week of Jun 30", "output_format": "Auto"}\n```\nend'
    out = fpg.parse_fields(text)
    assert out["name"] == "Week of Jun 30"
    assert out["output_format"] == "Auto"


def test_parse_fields_from_bare_json():
    out = fpg.parse_fields('{"foreground_projects": ["Job Search"], "paused_projects": []}')
    assert out["foreground_projects"] == ["Job Search"]
    assert out["paused_projects"] == []


def test_prompt_carries_the_deterministic_date_anchor():
    # Python supplies today; the LLM must never guess the current date.
    prompt = fpg.build_authoring_prompt("jobs this week", dt.date(2026, 7, 2), ["Job Search"])
    assert "Thursday" in prompt and "2026-07-02" in prompt   # weekday + ISO anchor present
    assert "Job Search" in prompt                             # her real project names offered

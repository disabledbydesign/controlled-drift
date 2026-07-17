import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gsdt_bind as gb


def test_prompt_engagement_accepts_valid():
    assert gb._prompt_engagement("Proj", _input=lambda _: "Backburner") == "Backburner"
    assert gb._prompt_engagement("Proj", _input=lambda _: "steady") == "Steady"


def test_prompt_engagement_empty_returns_none():
    assert gb._prompt_engagement("Proj", _input=lambda _: "") is None


def test_prompt_engagement_invalid_returns_none():
    # an unrecognized answer is not forced into a guess — None lets the Open default apply
    assert gb._prompt_engagement("Proj", _input=lambda _: "Sprint") is None

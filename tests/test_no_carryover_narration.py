import pathlib

def test_carryover_narration_text_is_gone():
    src = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "plan_generate.py"
    text = src.read_text()
    assert "Carried over from yesterday" not in text
    assert "not everything should roll forward" not in text

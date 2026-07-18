import build_recurring


def test_fixed_appointment_property_is_ensured(monkeypatch):
    ensured = []
    monkeypatch.setattr(build_recurring.g, "ensure_property",
                        lambda name, kind, *a: ensured.append((name, kind)) or {"key": name})
    linked = {}
    monkeypatch.setattr(build_recurring.g, "ensure_type",
                        lambda k, n, props: linked.setdefault("props", [p["key"] for p in props]) or "gsdo_recurring")
    monkeypatch.setattr(build_recurring.g, "find_property", lambda name: None)
    monkeypatch.setattr(build_recurring.g, "find_type", lambda name: {"id": "t"})
    monkeypatch.setattr(build_recurring.g, "unlink_properties_from_type", lambda *a: None)
    build_recurring.build_recurring()
    assert ("Fixed appointment", "checkbox") in ensured
    assert "Fixed appointment" in linked["props"]

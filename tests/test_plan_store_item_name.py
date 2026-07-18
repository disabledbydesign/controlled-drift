import plan_store

def test_item_name_returns_cached_row_name(monkeypatch):
    monkeypatch.setattr(plan_store, "load_plan",
                        lambda: {"items": [{"id": "rec-1", "task": "Do the dishes"}]})
    assert plan_store.item_name("rec-1") == "Do the dishes"

def test_item_name_none_when_no_match(monkeypatch):
    monkeypatch.setattr(plan_store, "load_plan", lambda: {"items": []})
    assert plan_store.item_name("nope") is None

def test_item_name_none_when_no_cache(monkeypatch):
    monkeypatch.setattr(plan_store, "load_plan", lambda: None)
    assert plan_store.item_name("rec-1") is None

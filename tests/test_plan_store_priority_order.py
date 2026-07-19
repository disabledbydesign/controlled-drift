"""June's manual reordering of the fragmented-day priority list must survive a reload.

`PriorityList.tsx` let her move rows with the up/down controls and wrote the result to
`ctx.up({priOrder})` — client state only. There was no server reference anywhere
(`GET /api/plan/priority-order` answered 404), so every reordering she did was gone the next
time the surface loaded. June's decision, 2026-07-19: "Yes, should persist." That closes
`docs/api_contract_v2.md` §6 Q1.

WHERE IT LIVES, AND WHY NOT A NEW FILE. The ordering is per-plan state, exactly like the moves,
deferrals and chunk flags `plan_store` already keeps, so it rides inside the cached plan record
(`current_plan.json`) under `priority_order`. `scripts/data/` already holds thirteen .jsonl
files and the repo rule is to widen what exists rather than add a fourteenth.

KEYED BY OBJECT ID, NEVER BY SLOT POSITION. A regenerated plan reassigns slots, so a
position-keyed order reattaches to whatever now sits at that index. Commit b721103 moved block
state off slot keys for this reason and `chunked` carried the same bug before it.

WHAT HAPPENS ON A REGENERATION — the decision this file also pins down. Because the order lives
INSIDE the plan record, `save_plan` (which writes a fresh record) drops it. A regenerated plan
is a fresh ranking the generator composed from current data; carrying yesterday's manual order
over it would silently govern a set of items she never ordered. Stale ids are also the thing
the id-keying rule above exists to avoid. This is the conservative reading and it is flagged
for June rather than treated as settled.

All paths are redirected into tmp_path — tests never touch June's real ~/.controlled-drift/.
"""
import sys, os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import plan_store


def _redirect(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))


A, B, C = "bafyA", "bafyB", "bafyC"


def _plan():
    """A fragmented-day plan: a flat items[] list, no blocks, no clock times."""
    return {
        "shape": "priority",
        "header": "A short list to pull from.",
        "items": [
            {"id": A, "task": "Call the pharmacy"},
            {"id": B, "task": "Rent portal"},
            {"id": C, "task": "Water the plants"},
        ],
    }


def test_set_priority_order_persists_across_a_reload(tmp_path, monkeypatch):
    """The ordering she chose is on disk and comes back on the next read."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())

    plan_store.set_priority_order([C, A, B])

    assert plan_store.load_plan()["priority_order"] == [C, A, B]


def test_the_order_is_returned_by_the_setter_too(tmp_path, monkeypatch):
    """The setter answers with the rewritten plan, like every other plan_store mutation."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())

    written = plan_store.set_priority_order([B, C, A])

    assert written["priority_order"] == [B, C, A]


def test_setting_an_order_does_not_disturb_the_items(tmp_path, monkeypatch):
    """The order is a separate ranking. It must not silently rewrite the plan's own list —
    the plan's items stay exactly as generated, which is what makes the order droppable."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())

    plan_store.set_priority_order([C, B, A])

    assert [it["id"] for it in plan_store.load_plan()["items"]] == [A, B, C]


def test_setting_an_order_does_not_restamp_the_plan(tmp_path, monkeypatch):
    """A reorder is not a regeneration — `generated_at` must survive it, or the surface would
    report a plan built just now that was in fact built this morning."""
    _redirect(tmp_path, monkeypatch)
    stamped = plan_store.save_plan(_plan())

    plan_store.set_priority_order([C, A, B])

    assert plan_store.load_plan()["generated_at"] == stamped["generated_at"]


def test_an_unknown_id_is_refused_loudly(tmp_path, monkeypatch):
    """An id that is not in the plan cannot be ordered. Accepting it would store a ranking that
    addresses a row this plan does not have — the silent-drift failure the id-keying exists to
    stop. Raise; never a bare assert, never a quiet filter."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())

    with pytest.raises(ValueError):
        plan_store.set_priority_order([A, B, "bafyGHOST"])


def test_a_partial_order_is_refused_loudly(tmp_path, monkeypatch):
    """Every item the plan holds has to appear. A short order would leave rows with no rank,
    and the reader would have to invent one."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())

    with pytest.raises(ValueError):
        plan_store.set_priority_order([A, B])


def test_a_duplicated_id_is_refused_loudly(tmp_path, monkeypatch):
    """One row, one rank.

    ⚠ The order below names every one of the plan's three ids, so the set-equality check passes
    it — only the duplicate guard rejects it. An earlier version of this test used [A, A, B],
    which the set check caught first, so it went on passing with the duplicate guard disabled.
    Found by mutation, not by reading."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())

    with pytest.raises(ValueError):
        plan_store.set_priority_order([A, A, B, C])


def test_no_cached_plan_is_a_lookup_error(tmp_path, monkeypatch):
    """Nothing generated yet — there is no list to rank."""
    _redirect(tmp_path, monkeypatch)

    with pytest.raises(LookupError):
        plan_store.set_priority_order([A])


def test_a_clock_shape_plan_has_no_priority_list_to_rank(tmp_path, monkeypatch):
    """A clock day keeps its rows under blocks[] and reorders through move_item."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan({"shape": "clock", "blocks": [{"label": "Morning", "items": []}]})

    with pytest.raises(LookupError):
        plan_store.set_priority_order([A])


def test_a_regeneration_drops_the_saved_order(tmp_path, monkeypatch):
    """THE DECISION, asserted positively. A new plan carries no stale ranking: `save_plan`
    writes a fresh record and the order does not survive it. She sees the generator's order on a
    regenerated day, not yesterday's manual one applied to a different set of items."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.save_plan(_plan())

    assert "priority_order" not in plan_store.load_plan()


def test_a_server_side_move_clears_the_saved_order(tmp_path, monkeypatch):
    """`move_priority_item` rewrites the plan's OWN item order. If a manual ranking outlived
    that, it would keep governing the display and the move she just made would appear not to
    have taken effect — the worse of the two surprises. So the move wins and the ranking goes."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.move_priority_item(A, 2)

    after = plan_store.load_plan()
    assert [it["id"] for it in after["items"]] == [B, C, A]
    assert "priority_order" not in after


def test_checking_a_row_off_leaves_the_saved_order_alone(tmp_path, monkeypatch):
    """Ordinary day-of writes are not reorderings. Her ranking survives them."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.mark_item_done(A)

    assert plan_store.load_plan()["priority_order"] == [C, A, B]

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

WHAT HAPPENS ON A REGENERATION — SETTLED 2026-07-19, REVERSING WHAT THIS FILE USED TO SAY. The
first build dropped the ranking on a regeneration, on the reasoning that carrying it would let
yesterday's order govern items she never ranked. That was the conservative reading and it was
flagged for June rather than treated as settled. She settled it: "if the same thing recurs,
yeah it should be in the same spot." The ranking is now CARRIED ACROSS a regeneration and
merged BY ID — an item in both keeps its rank, a row the generator just added goes after.

An item that is not on today's list is REMEMBERED rather than dropped, because "the same thing
recurs" is exactly the chore that appears most days and not every day; dropping it would let one
missing day demote it permanently. The cost is that an item gone for weeks can come back
carrying a rank she no longer remembers. June: "we can log the friction to see if its a problem
pretty easily" — so each return goes to `corrections_log` and the question stays answerable
with evidence instead of being engineered away on a guess.

All paths are redirected into tmp_path — tests never touch June's real ~/.controlled-drift/.
"""
import sys, os, json, datetime as dt

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import plan_store


def _redirect(tmp_path, monkeypatch):
    monkeypatch.setenv("CD_CONFIG_DIR", str(tmp_path))
    # CD_DATA_DIR too, because the returning-item record below writes to `corrections.jsonl`,
    # which resolves through `cd_paths.data_file` — a different root from the plan cache.
    monkeypatch.setenv("CD_DATA_DIR", str(tmp_path))


def _corrections(tmp_path):
    """Every record in the sandboxed corrections log, oldest first."""
    path = os.path.join(str(tmp_path), "corrections.jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


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


D = "bafyD"


def _plan_with(*ids):
    """A fragmented-day plan holding exactly these ids, in this order."""
    titles = {A: "Call the pharmacy", B: "Rent portal", C: "Water the plants", D: "Sweep"}
    return {
        "shape": "priority",
        "header": "A short list to pull from.",
        "items": [{"id": i, "task": titles[i]} for i in ids],
    }


def test_a_regeneration_keeps_the_rank_of_an_item_that_is_still_there(tmp_path, monkeypatch):
    """THE DECISION, REVERSED 2026-07-19 — June: "if the same thing recurs, yeah it should be in
    the same spot." A regeneration used to drop the ranking outright (the conservative reading
    this file's header used to record, flagged for her rather than settled). She has now settled
    it: an item in both the saved order and the new plan keeps the rank she gave it."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.save_plan(_plan())

    assert plan_store.load_plan()["priority_order"] == [C, A, B]


def test_an_item_the_generator_just_added_goes_after_the_ones_she_ranked(tmp_path, monkeypatch):
    """"Anything new goes after" — a row she has never seen cannot claim a rank she chose, so it
    lands below every one she did, in the generator's own order."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.save_plan(_plan_with(A, B, C, D))

    assert plan_store.load_plan()["priority_order"] == [C, A, B, D]


def test_the_merge_is_by_id_never_wholesale(tmp_path, monkeypatch):
    """A saved ranking is NOT reapplied to a different item set as a block. Only the ids that are
    genuinely in both plans carry a rank across; the rest of the list is the generator's."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    # A completely different day: only C survives from the ranked set.
    plan_store.save_plan(_plan_with(D, C))

    order = plan_store.load_plan()["priority_order"]
    # C keeps its rank ahead of everything she ranked below it; D is new, so it goes after.
    assert order.index(C) < order.index(D)
    assert set(order) >= {C, D}


def test_an_item_that_leaves_the_plan_still_has_its_spot_when_it_comes_back(
        tmp_path, monkeypatch):
    """The point of "if the same thing recurs, it should be in the same spot". A chore that is
    not on today's list must not lose the rank she gave it — otherwise one missing day silently
    demotes it forever. Its id is RETAINED in the saved order while it is away.

    `PriorityList.tsx` already drops ids that are not in the plan when it renders, so a retained
    id is invisible to her until the item itself is back."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.save_plan(_plan_with(C, A))       # B is not on today's list
    assert B in plan_store.load_plan()["priority_order"]

    plan_store.save_plan(_plan_with(A, B, C))    # B is back
    assert plan_store.load_plan()["priority_order"] == [C, A, B]


def test_a_returning_item_is_recorded_with_how_long_it_was_gone_and_where_it_landed(
        tmp_path, monkeypatch):
    """June: "we can log the friction to see if its a problem pretty easily."

    An item can come back after weeks still carrying a rank from a plan she no longer remembers.
    That is not engineered away — it is RECORDED, so whether it actually feels wrong is a
    question with evidence behind it rather than a guess. A bare "reapplied a rank" would answer
    nothing, so the record names the item, how long it had been away, and both the rank it took
    and the rank the generator would have given it."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])
    plan_store.save_plan(_plan_with(C, A))       # B goes away

    plan_store.save_plan(_plan_with(A, B, C))    # B comes back

    rec = [r for r in _corrections(tmp_path) if r["kind"] == "priority_rank_returned"]
    assert len(rec) == 1
    assert rec[0]["object_id"] == B
    assert rec[0]["before"]["task"] == "Rent portal"
    assert rec[0]["before"]["days_away"] == 0          # same test run, so: today
    assert rec[0]["before"]["last_ranked_in_a_plan_from"]
    assert rec[0]["after"]["rank"] == 2                # [C, A, B]
    assert rec[0]["after"]["generator_rank"] == 1      # the plan itself had it second


def test_an_item_that_never_left_is_not_recorded_as_returning(tmp_path, monkeypatch):
    """Only a genuine return is worth recording. Logging every carried rank would bury the one
    case June asked about under one record per row per regeneration."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.save_plan(_plan())

    assert [r for r in _corrections(tmp_path) if r["kind"] == "priority_rank_returned"] == []


def test_a_block_row_keeps_its_rank_across_a_regeneration(tmp_path, monkeypatch):
    """⚠ A BLOCK ROW HAS NO `id` — its id is in `project_id`. This fixture is June's real
    fragmented-day shape, read off the live server, where three of seven rows were blocks. The
    merge resolves a row's identity the same way `set_priority_order` does; reading `id` alone
    would carry no rank at all for a block and would put `None` in the merged list."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_real_shape_plan())
    plan_store.set_priority_order([B, C, A])     # B is the BLOCK row

    plan_store.save_plan(_real_shape_plan())

    assert plan_store.load_plan()["priority_order"] == [B, C, A]


def test_a_clock_day_in_between_does_not_wipe_the_ranking(tmp_path, monkeypatch):
    """A clock-shape day has no priority list to rank, but it must not erase one either — a
    single scheduled day would otherwise throw away everything she had ordered."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.save_plan({"shape": "clock", "blocks": [{"label": "Morning", "items": []}]})
    plan_store.save_plan(_plan())

    assert plan_store.load_plan()["priority_order"] == [C, A, B]


def test_reordering_keeps_a_remembered_item_that_is_not_on_screen(tmp_path, monkeypatch):
    """She can only reorder what is in front of her, so her order names today's rows and nothing
    else. Storing it verbatim would delete every remembered rank for an item that happens to be
    away — one reorder on a day a chore is missing, and the chore's spot is gone.

    A remembered id keeps the row it sat BEHIND. That is the only anchor available: its position
    relative to rows she can see is the one fact her new order does not restate."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])
    plan_store.save_plan(_plan_with(C, A))       # B is away, remembered behind A

    plan_store.set_priority_order([A, C])        # she reorders the two rows she can see

    assert plan_store.load_plan()["priority_order"] == [A, B, C]


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


def _real_shape_plan():
    """June's ACTUAL fragmented-day plan shape, read off the live server 2026-07-19.

    ⚠ A BLOCK ROW CARRIES ITS ID IN `project_id`, AND HAS NO `id` AT ALL. Three of the seven rows
    on her real plan that day were blocks ("Work on Life admin", "Work on IOP and recovery",
    "Work on Leatherworking"), each with `id` absent. `api/adapt.ts` already records this in a
    ⚠ of its own — `planFromLive` reads `it.id ?? it.project_id` — and the surface therefore
    sends a block's project_id as its id.

    The plan fixture above gives every row an `id`, so it could not see this. Reading `id` alone
    put `None` in the known-ids list, and `set_priority_order` raised
    `TypeError: '<' not supported between instances of 'str' and 'NoneType'` from `sorted()`.
    That was found by POSTing to the running server, not by any test.
    """
    return {
        "shape": "priority",
        "items": [
            {"id": A, "task": "Clean the kitchen"},
            {"project_id": B, "block": True, "task": "Work on Life admin"},
            {"id": C, "task": "Go on a long walk"},
        ],
    }


def test_a_block_row_can_be_ranked_by_the_id_the_surface_sends(tmp_path, monkeypatch):
    """A block is addressed by its `project_id`, because that is the id it has."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_real_shape_plan())

    plan_store.set_priority_order([B, C, A])

    assert plan_store.load_plan()["priority_order"] == [B, C, A]


def test_a_plan_holding_a_block_does_not_crash_the_refusal_path(tmp_path, monkeypatch):
    """The exact live failure: a bad id on a plan containing a block row must come back as an
    ordinary refusal naming the id, not a TypeError out of `sorted()`."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_real_shape_plan())

    with pytest.raises(ValueError) as e:
        plan_store.set_priority_order(["bafyGHOST"])

    assert "bafyGHOST" in str(e.value)


def test_a_row_with_no_id_of_any_kind_is_refused_not_ranked(tmp_path, monkeypatch):
    """If a row carries neither `id` nor `project_id` there is nothing to rank it by, and a
    ranking that silently skipped it would put a row on screen with no position. Say so.

    ⚠ THREE rows, not two, and that matters. With only one other row the id-less row is the sole
    entry in the mismatch set, `sorted()` of a one-element set never compares anything, and the
    refusal comes out cleanly even with the guard deleted — so the test passed against the
    unguarded code. With two named rows left out, `sorted()` has to compare a string against
    `None` and raises TypeError instead of refusing. Found by mutation.
    """
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(
        {"shape": "priority", "items": [{"id": A}, {"id": C}, {"task": "nameless"}]}
    )

    with pytest.raises(ValueError):
        plan_store.set_priority_order([A])


def test_checking_a_row_off_leaves_the_saved_order_alone(tmp_path, monkeypatch):
    """Ordinary day-of writes are not reorderings. Her ranking survives them."""
    _redirect(tmp_path, monkeypatch)
    plan_store.save_plan(_plan())
    plan_store.set_priority_order([C, A, B])

    plan_store.mark_item_done(A)

    assert plan_store.load_plan()["priority_order"] == [C, A, B]

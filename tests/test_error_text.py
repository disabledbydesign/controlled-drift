"""What crosses to the failure bar, and what stays in the log.

BUILD_DOC §9.6. The bar is the one place an error reaches June directly. Live-verify caught a
raw Python dict arriving there:

    Could not save engagement — it is NOT saved. could not read object 'bafyrei…' 500
    {'object': 'error', …}

None of that tail is readable, and the id is the kind of routing number she has said she cannot
use. These pin the split: a sentence on screen, the whole exception in the log.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import server
import api_write


def test_the_dict_that_actually_leaked_does_not_reach_her(capsys):
    e = LookupError("could not read object 'bafyreid4x': 500 {'object': 'error', 'code': 3}")
    text = server._client_error(e)
    assert "{" not in text and "bafyreid4x" not in text and "500" not in text
    assert text == "Anytype could not find that item. It may have been deleted or archived."


def test_the_full_detail_is_kept_in_the_log(capsys):
    server._client_error(LookupError("could not read object 'bafyreid4x': 500 {'x': 1}"))
    err = capsys.readouterr().err
    assert "bafyreid4x" in err and "{'x': 1}" in err, "debugging detail must not be thrown away"


def test_a_refusal_written_for_her_is_passed_through_whole(capsys):
    """WriteRefused messages are already sentences that say what to do — flattening them to a
    generic apology would LOSE information she needs, which is the opposite of the goal."""
    e = api_write.WriteRefused("Move that has children into a task first — a task cannot hold them.")
    assert server._client_error(e) == str(e)


def test_an_unknown_failure_still_says_something_rather_than_nothing(capsys):
    assert server._client_error(RuntimeError("")).endswith("server log has the detail.")


def test_a_machine_tail_is_cut_off_any_message_not_just_known_ones(capsys):
    """The backstop. A raise site written next year gets the same treatment with no new code."""
    text = server._client_error(RuntimeError("Anytype rejected the write: {'code': 9}"))
    assert text == "Anytype rejected the write"


def test_a_multiline_traceback_style_message_is_cut_at_the_first_line(capsys):
    text = server._client_error(RuntimeError("Could not save that.\nTraceback blah"))
    assert text == "Could not save that."

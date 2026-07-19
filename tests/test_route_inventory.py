"""The route inventory in scripts/server.py must not drift from the real routes.

WHY THIS TEST EXISTS — do not delete it as pedantic bookkeeping.

`scripts/server.py` opens with a module docstring listing every HTTP route the server
serves. That inventory is not decoration: it is how AI agents (and humans) orient
themselves when they need to know what the backend can already do. The repo's build
instructions point agents at it. An agent that reads the inventory and does not find a
route concludes the route does not exist — and then builds it again, or builds a UI that
never calls it.

This project has already paid for that failure once. At one point 14 of 19 write endpoints
existed in the server and NOTHING in the UI could reach them: built, working, dead. A
stale inventory does not merely mislead, it actively reproduces the built-but-dead
pattern.

The inventory is hand-maintained prose, so it drifts silently — nothing in the system was
capable of noticing. On 2026-07-19 an audit found 16 undocumented routes. That is the
mechanism this test closes: add a route without documenting it and the suite goes red,
naming the route.

The routes are derived from server.py's own source, never from a list kept here. A
hardcoded list would be the same hand-maintained-thing-that-drifts, one layer down.
"""
import ast
import os
import re

import pytest

SERVER_PY = os.path.join(os.path.dirname(__file__), "..", "scripts", "server.py")

# A route path as written in either the source or the docstring. Allows the `{id}` /
# `{name}` placeholder form the docstring uses for parameterized routes.
_ROUTE_RE = re.compile(r"/api[A-Za-z0-9_/{}-]*")


def _normalize(route):
    """Reduce a route to a comparable form.

    Parameterized routes are written two different ways on purpose. The source matches
    them by prefix or by parsing the remainder (`startswith("/api/object/")`), while the
    docstring names the parameter for the reader (`/api/object/{id}`). Dropping the
    `{...}` segments and collapsing the resulting empty path segments makes the two
    spellings meet, so a parameterized route is not reported as undocumented.
    """
    route = re.sub(r"\{[^}]*\}", "", route)
    route = re.sub(r"/+", "/", route)
    return route.rstrip("/") or route


def _load():
    with open(SERVER_PY, encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree)
    if not docstring:
        raise RuntimeError(
            f"{SERVER_PY} has no module docstring — the route inventory this test "
            "guards has been removed entirely. Restore it (see the docstring of this "
            "test for why it exists)."
        )
    return tree, docstring


def _source_routes(tree, docstring):
    """Every `/api...` path literal in server.py, excluding the docstring itself.

    Reading string literals off the AST rather than pattern-matching the dispatch lines
    keeps the extraction independent of HOW a route is matched. `self.path == "/api/x"`,
    `urlparse(self.path).path == "/api/x"`, and `startswith("/api/x/")` are all spellings
    already in use in this file, and a future one will be picked up for free.
    """
    routes = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        value = node.value
        if value == docstring:
            continue
        if _ROUTE_RE.fullmatch(value):
            routes.add(value)
    return routes


def _documented_routes(docstring):
    return {_normalize(m) for m in _ROUTE_RE.findall(docstring)}


def test_source_has_routes_to_check():
    """Guard the guard: an extraction that silently finds nothing would pass forever."""
    tree, docstring = _load()
    routes = _source_routes(tree, docstring)
    assert len(routes) > 20, (
        f"Only found {len(routes)} route literals in server.py, which is implausibly few. "
        "The extraction in this test is probably broken — a route inventory check that "
        "finds no routes passes vacuously and guards nothing."
    )


def test_every_route_appears_in_the_module_docstring():
    tree, docstring = _load()
    documented = _documented_routes(docstring)
    undocumented = sorted(
        route for route in _source_routes(tree, docstring)
        if _normalize(route) not in documented
    )
    if undocumented:
        listed = "\n".join(f"    {route}" for route in undocumented)
        pytest.fail(
            "These routes are served by scripts/server.py but are MISSING from its "
            "module docstring's route inventory:\n"
            f"{listed}\n\n"
            "Add a line for each to the `Routes:` block at the top of scripts/server.py, "
            "matching the surrounding entries: the HTTP method(s) it accepts, the path, "
            "the request shape it expects and what it returns. Describe what the handler "
            "actually does, not what the path name suggests.\n\n"
            "Why this is a test failure and not a nit: agents orient from that inventory. "
            "An undocumented route reads as a route that does not exist, and gets built "
            "a second time or shipped with nothing able to reach it — the built-but-dead "
            "failure this repo has already paid for once."
        )

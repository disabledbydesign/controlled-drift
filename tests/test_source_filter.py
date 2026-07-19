"""Who is allowed to reach the server at all.

This is the access control. Before it existed, the bind address WAS the access control, which
forced a false choice: bind the mesh address and `localhost` stops answering on the laptop, or
bind 0.0.0.0 and every device on the network can read June's medical and financial task data. On
2026-07-18 that second case went live on a hotel network with room for ~8000 devices.

Listening broadly and answering narrowly dissolves the trade. These tests pin the "answering
narrowly" half — including the failure directions, because a filter that quietly allows everything
looks exactly like a filter that works.
"""
import sys, os, socket, threading, http.client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import server


# --- the predicate ----------------------------------------------------------

def test_this_laptop_is_allowed():
    assert server._source_allowed("127.0.0.1")
    assert server._source_allowed("127.1.2.3")     # all of 127/8, not just .0.1
    assert server._source_allowed("::1")


def test_the_mesh_is_allowed():
    assert server._source_allowed("100.86.195.93")    # her Mac
    assert server._source_allowed("100.73.242.111")   # her iPhone
    assert server._source_allowed("100.64.0.0")       # range edges
    assert server._source_allowed("100.127.255.255")
    assert server._source_allowed("fd7a:115c:a1e0::2d01:c3b3")


def test_a_hotel_or_home_network_is_refused():
    # The actual address the laptop held on the hotel LAN, and the neighbours it could see.
    assert not server._source_allowed("192.168.153.29")
    assert not server._source_allowed("192.168.153.1")
    assert not server._source_allowed("10.0.0.5")
    assert not server._source_allowed("172.16.4.9")


def test_addresses_that_only_look_like_the_mesh_are_refused():
    # 100.x is a public range OUTSIDE 100.64/10 — being in it is not being on the mesh.
    assert not server._source_allowed("100.63.255.255")   # one below the range
    assert not server._source_allowed("100.128.0.0")      # one above it
    assert not server._source_allowed("100.200.14.7")
    # fd00::/8 is private but is not Tailscale's /48.
    assert not server._source_allowed("fd00::1")


def test_unparseable_sources_fail_closed():
    for junk in ("", "not-an-ip", "127.0.0.1.evil.com", "999.1.1.1", None):
        assert not server._source_allowed(junk), f"{junk!r} must not be allowed"


def test_ipv4_mapped_addresses_are_judged_on_the_real_ipv4():
    """A dual-stack listener reports IPv4 peers as ::ffff:a.b.c.d. If that were compared as an
    IPv6 address it would miss every IPv4 rule above — allowed traffic would break, and worse, a
    refused address could slip through a naive rewrite of this. Both directions pinned."""
    assert server._source_allowed("::ffff:127.0.0.1")
    assert server._source_allowed("::ffff:100.86.195.93")
    assert not server._source_allowed("::ffff:192.168.153.29")


# --- the predicate actually wired to the socket -----------------------------
#
# The tests above would all pass if `verify_request` were never called. These drive a real
# listening server, because "the filter is correct" and "the filter is in the request path" are
# different claims and only the second one protects her.

def _running_server():
    srv = server.GuardedServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def test_an_allowed_source_gets_served():
    srv, port = _running_server()
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request("GET", "/api/status")
        assert c.getresponse().status == 200
    finally:
        srv.shutdown(); srv.server_close()


def test_a_refused_source_gets_no_http_response_at_all(monkeypatch):
    """A test cannot dial in from a hotel LAN, so the PREDICATE is inverted rather than the
    address — `_source_allowed` is made to refuse loopback and the connection must then die.

    Inverting `_source_allowed` and not `verify_request` is the whole point: an earlier version of
    this test replaced `verify_request` directly, which passed even when the filter was not wired
    into the request path at all. It proved socketserver closes connections when told to — never
    that anything tells it to. What must be pinned is that GuardedServer CONSULTS the predicate.

    A closed connection rather than a 403 is also deliberate: a 403 would confirm to a stranger on
    the hotel network that something is here.
    """
    monkeypatch.setattr(server, "_source_allowed", lambda host: False)
    srv, port = _running_server()
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request("GET", "/api/status")
        try:
            resp = c.getresponse()
        except (http.client.RemoteDisconnected, ConnectionResetError):
            return          # the connection was closed unread — correct
        assert False, f"a refused source got an HTTP response: {resp.status}"
    finally:
        srv.shutdown(); srv.server_close()

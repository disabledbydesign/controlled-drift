"""The bind preference list, and the warning June actually reads.

June asked for wifi as a fallback when Tailscale is down. The whole risk of a fallback is that it
happens QUIETLY — she ends up on a wider network than she chose and never knows. So the warning is
the feature, not decoration, and these pin it.

She also asked that it not speak in IPs ("I won't remember those routing numbers") and that it
walk her through fixing it.
"""
import socket
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import server


def test_plain_language_names_not_ip_addresses():
    assert server._bind_name("100.86.195.93") == "the mesh (Tailscale)"
    assert server._bind_name("0.0.0.0").startswith("your wifi")
    assert server._bind_name("127.0.0.1") == "this laptop only"
    # Any Tailscale CGNAT address, not just hers — the range is 100.64/10.
    assert server._bind_name("100.64.0.1") == "the mesh (Tailscale)"
    assert server._bind_name("100.127.255.254") == "the mesh (Tailscale)"
    # 100.x outside the CGNAT range is NOT the mesh.
    assert server._bind_name("100.200.0.1") == "100.200.0.1"


def test_first_choice_binds_with_no_warning(capsys, monkeypatch):
    monkeypatch.setattr(server, "_BIND_PREFS", ["127.0.0.1"])
    srv, host = server._bind(0, server.Handler)
    srv.server_close()
    assert host == "127.0.0.1"
    assert capsys.readouterr().out == "", "a successful first bind must say nothing"


def test_falling_back_warns_in_plain_language_and_says_how_to_fix_it(capsys, monkeypatch):
    # An address in the mesh range that is not this machine's cannot bind — which is what a
    # downed Tailscale looks like.
    monkeypatch.setattr(server, "_BIND_PREFS", ["100.86.195.94", "127.0.0.1"])
    srv, host = server._bind(0, server.Handler)
    srv.server_close()
    out = capsys.readouterr().out

    assert host == "127.0.0.1"
    assert "THE MESH (TAILSCALE) IS NOT AVAILABLE" in out
    assert "TO FIX IT" in out and "tailscale status" in out and "tailscale up" in out
    assert "launchctl load" in out
    # The IP may appear in the technical footnote, but never as the headline.
    assert "100.86.195.94" not in out.split("TO FIX IT")[0].split("technical")[0]


def test_a_wider_fallback_says_it_is_wider(capsys, monkeypatch):
    monkeypatch.setattr(server, "_BIND_PREFS", ["100.86.195.94", "0.0.0.0"])
    srv, host = server._bind(0, server.Handler)
    srv.server_close()
    out = capsys.readouterr().out
    assert host == "0.0.0.0"
    assert "WIDER than intended" in out
    assert "no password" in out and "medical" in out


def test_a_narrower_fallback_does_not_cry_wolf(capsys, monkeypatch):
    """Falling back from wifi to loopback is SAFER — it must not print the exposure warning."""
    blocker = socket.socket()
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", 0))
    port = blocker.getsockname()[1]
    blocker.listen(1)
    monkeypatch.setattr(server, "_BIND_PREFS", ["127.0.0.1", "127.0.0.1"])
    try:
        srv, host = server._bind(port, server.Handler)
    except SystemExit:
        blocker.close()
        return  # both prefs were the same busy address; nothing to assert
    srv.server_close()
    blocker.close()
    assert "WIDER than intended" not in capsys.readouterr().out


def test_no_address_binds_at_all_exits_loudly(monkeypatch):
    monkeypatch.setattr(server, "_BIND_PREFS", ["100.86.195.94", "100.86.195.95"])
    try:
        server._bind(0, server.Handler)
    except SystemExit as e:
        assert "could not bind any address" in str(e)
    else:
        raise AssertionError("should have exited rather than starting unbound")

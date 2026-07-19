# Running Controlled Drift

The new surface is now what the server serves by default (you promoted it 2026-07-18). The old overlay is **moved, not deleted** — it is at `/old/` if something turns out to be missing from the new one.

| What | Where |
|---|---|
| **The new surface** (your daily driver) | `http://localhost:5050/` |
| The same surface, at its old address | `http://localhost:5050/app/` |
| The token / component reference page | `http://localhost:5050/app/#/check` |
| **The old overlay** (kept as a way back) | `http://localhost:5050/old/` |

`/app/` is not a leftover alias — the built bundle asks for its own scripts at `/app/assets/...`, so `/` depends on `/app/` staying mounted. Removing it would leave the root serving a blank page.

---

## Starting it

It runs automatically at login via `~/Library/LaunchAgents/com.june.controlled-drift.server.plist`.

To start it by hand, or after editing the server:

```bash
cd ~/Documents/GitHub/cyborg-memory/controlled-drift
python3 scripts/server.py
```

To restart the background service:

```bash
launchctl unload ~/Library/LaunchAgents/com.june.controlled-drift.server.plist
launchctl load   ~/Library/LaunchAgents/com.june.controlled-drift.server.plist
```

**After changing anything under `app/`, rebuild** — the server serves the built files, not the source:

```bash
cd app && npx vite build
```

For frontend work, the dev server has hot reload and proxies the API through, so you don't need to rebuild between edits:

```bash
cd app && npx vite          # then http://localhost:5173/app/
```

---

## Reaching it from your phone

Your phone reaches the laptop over Tailscale:

**`http://100.86.195.93:5050/`**

Use the numeric address, not `lauras-macbook-air.tail2905c9.ts.net`. The name depends on a DNS lookup that many networks interfere with — on a hotel network (2026-07-18) the name failed and the number worked immediately. The number is your Mac's Tailscale address and does not change.

Two things have to be true:

1. **The laptop is awake.** Anytype holds your data locally, so the machine must be running to answer. A closed, unplugged laptop means the phone gets nothing — that is architectural, not a setting.
2. **Tailscale is up on both devices.**

If you want it reachable while the laptop stays home, leave it **plugged in** and stop it sleeping — System Settings → Battery → Options → *"Prevent automatic sleeping when the display is off"*, or run `caffeinate -s` in a terminal and leave that terminal open.

### Who can reach it

**Only this laptop and the mesh.** Everything else is refused at the socket, before any HTTP is read — so being on the same wifi as the laptop does not get you in.

This replaced an earlier arrangement where the bind address *was* the access control, which forced a choice that was never actually necessary: bind the mesh address and `localhost` stops answering on the laptop (and the Vite dev proxy breaks, since it talks to `127.0.0.1:5050`), or bind `0.0.0.0` and every device on the network can read your medical and financial task data. Those turned out to be two separate questions — *which interface do we listen on* and *whose requests do we answer*. Listening broadly while answering narrowly gets both halves: `localhost` works, the phone works, the network is shut out.

Allowed sources are `127.0.0.0/8` and `::1` (this laptop) and `100.64.0.0/10` and `fd7a:115c:a1e0::/48` (Tailscale). See `_ALLOWED_SOURCES` in `scripts/server.py`; the tests are `tests/test_source_filter.py`.

A refused request is logged in plain language to `~/.controlled-drift/server.log`, naming the address and reminding you the phone needs Tailscale open. Rejected callers get a dropped connection rather than a "403 Forbidden". Note the limit of that: the check runs after the TCP connection is accepted, so a port scanner still sees 5050 open. What a stranger cannot get is any response — so nothing about what is running or that it is worth attacking.

**What this is not:** authentication. There is still no password. Anything already on the mesh can read everything, and anything able to forge a source address in those ranges is not stopped by this. What it does stop is the hazard that actually occurred — on 2026-07-18 the laptop sat on a hotel network with room for about 8,000 devices, serving your task data to all of them with no password. A password becomes worth building if you ever want the wifi to be a real fallback; on the mesh alone it adds little.

---

## Installing it as a laptop app

The new surface ships a web-app manifest, so Chrome or Edge can install it as a standalone window with its own dock icon and no browser chrome.

Open `http://localhost:5050/` in Chrome → the install icon in the address bar, or ⋮ → *Cast, save and share* → *Install page as app*.

That gets you the "it's just there" feeling without wrapping it in Electron. If it turns out to fall short — you want a global hotkey, or it to survive a browser restart differently — that's the point to consider a native wrapper, not before.

---

## When something looks wrong

- **A write failed** — the surface shows a red bar that stays until you dismiss it and names what did not save. That is deliberate: successes are quiet, failures are loud.
- **Want the verbose confirmations back** (useful while developing) — add `?verbose=1` to the URL, or run `localStorage.setItem('cd.verboseSignals','1')` in the browser console.
- **The page loads but has no data** — check the server is running (`curl -s -o /dev/null -w "%{http_code}" http://localhost:5050/api/tree`) and that Anytype is open.
- **Logs** — `scripts/data/*.jsonl`. Corrections and authorship go to `corrections.jsonl`.

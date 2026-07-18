# Running Controlled Drift

Two surfaces run from one server. **The old overlay is untouched** — the new one comes up beside it, and only comes down when you decide it should.

| What | Where |
|---|---|
| **The old overlay** (unchanged, still your daily driver) | `http://localhost:5050/` |
| **The new surface** | `http://localhost:5050/app/` |
| The token / component reference page | `http://localhost:5050/app/#/check` |

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

**`http://lauras-macbook-air.tail2905c9.ts.net:5050/app/`**

Two things have to be true:

1. **The laptop is awake.** Anytype holds your data locally, so the machine must be running to answer. A closed, unplugged laptop means the phone gets nothing — that is architectural, not a setting.
2. **Tailscale is up on both devices.**

If you want it reachable while the laptop stays home, leave it **plugged in** and stop it sleeping — System Settings → Battery → Options → *"Prevent automatic sleeping when the display is off"*, or run `caffeinate -s` in a terminal and leave that terminal open.

### ⚠ One security note worth acting on

The server currently binds `0.0.0.0` — **every interface, including your wifi.** It has no authentication of any kind and serves your medical and financial task data. Anything on your home network can read it.

Tailscale makes that unnecessary. In the plist, change:

```xml
<key>CD_BIND</key>
<string>0.0.0.0</string>     <!-- change to: 100.86.195.93 -->
```

Then nothing on your wifi can reach it, and your phone still can over the mesh. **Trade-off:** `http://localhost:5050` stops working on the laptop — you'd use the Tailscale name from both devices instead. And if Tailscale is ever down, the server won't start at all. That's a real fragility, which is why this is your call rather than a change already made.

---

## Installing it as a laptop app

The new surface ships a web-app manifest, so Chrome or Edge can install it as a standalone window with its own dock icon and no browser chrome.

Open `http://localhost:5050/app/` in Chrome → the install icon in the address bar, or ⋮ → *Cast, save and share* → *Install page as app*.

That gets you the "it's just there" feeling without wrapping it in Electron. If it turns out to fall short — you want a global hotkey, or it to survive a browser restart differently — that's the point to consider a native wrapper, not before.

---

## When something looks wrong

- **A write failed** — the surface shows a red bar that stays until you dismiss it and names what did not save. That is deliberate: successes are quiet, failures are loud.
- **Want the verbose confirmations back** (useful while developing) — add `?verbose=1` to the URL, or run `localStorage.setItem('cd.verboseSignals','1')` in the browser console.
- **The page loads but has no data** — check the server is running (`curl -s -o /dev/null -w "%{http_code}" http://localhost:5050/api/tree`) and that Anytype is open.
- **Logs** — `scripts/data/*.jsonl`. Corrections and authorship go to `corrections.jsonl`.

# Controlled Drift overlay — setup

The overlay is a local web surface that shows your daily plan + map, generated from your
Anytype data through Claude. Two ways to use it; the second (morning push) is the keystone.

## Backend = your Claude subscription (single source)

Generation rides your Claude subscription, so there's only ever **one thing to migrate** if
billing changes. The pluggable seam keeps an open-source API and a local model available as
backups (not wired yet — see "Backups" below).

## Run it yourself (works today)

From your terminal. **First `cd` into the repo** (the scripts are there, not in your home
folder), then start the server:

```
cd ~/Documents/GitHub/cyborg-memory/controlled-drift
python3 scripts/server.py
```

Then open `http://localhost:5050` in a browser.

(zsh note: don't paste commands with `# ...` comments after them on the same line — zsh
tries to run the comment. All blocks here are comment-free so you can paste them whole.)

This works right now because your terminal is already logged into Claude. Press a button or
type a request; the plan regenerates (~35s) and your correction is logged.

## The morning push (it comes to you) — one setup step

A scheduled job can't use your terminal's login, so it needs a **durable token** (tied to
your subscription, made for headless use). One time:

```
claude setup-token
```

Follow the prompt and **copy the token it prints**. Then save it to the file the push
reads (paste this whole block; it assumes the token is on your clipboard):

```
mkdir -p ~/.controlled-drift
pbpaste > ~/.controlled-drift/claude_token
chmod 600 ~/.controlled-drift/claude_token
```

Verify it landed (should print your token, not nothing):

```
cat ~/.controlled-drift/claude_token
```

Then enable the 9 AM push (paste the whole block):

```
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.june.controlled-drift.morning.plist
launchctl kickstart -k gui/$(id -u)/com.june.controlled-drift.morning
```

Check it worked (should show "plan generated + cached"):

```
cat ~/.controlled-drift/morning.log
```

To turn it off:

```
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.june.controlled-drift.morning.plist
```

To change the time: edit `Hour`/`Minute` in the plist, then bootout + bootstrap again.

## Token renewal

The `claude setup-token` token is valid ~1 year — **renew around June 2027** (re-run
`claude setup-token`, then the `pbpaste > ~/.controlled-drift/claude_token` block again).
If a morning push ever stops working, an expired token is the first thing to check:
`cat ~/.controlled-drift/morning.err.log`. (Worth turning into a Recurring item in Anytype.)

## Backups (pluggable, not wired yet)

`scripts/plan_generate.py` routes the LLM call through one seam (`generate()`), selected by
the `CD_BACKEND` env var:
- `claude` (default) — your subscription, as above.
- `local` — a local model (Ollama/MLX). Free, offline, billing-proof. Stubbed; bring up a
  warm local server so it isn't reloaded per call (the inference-time worry).
- an open-source API (e.g. OpenRouter, OpenAI-compatible) — a hosted backup; point it at a
  token (you have one in `reframe/.env`).

The point of the seam: switching backends is a one-file change, never a rebuild.

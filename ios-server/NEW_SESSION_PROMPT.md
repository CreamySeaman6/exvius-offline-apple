# Prompt for a new Claude session

Paste this into a new session to pick up the Exvius Offline iPhone work.

---

I'm continuing my Exvius Offline iPhone project (offline Final Fantasy Brave Exvius). The game server runs in Docker on my Unraid NAS (ThousandSunny), and the stock iOS app connects to it over Tailscale.

The code is my fork **CreamySeaman6/exvius-offline-apple**, branch **`ios-server`**. Add the repo to this session with push access, clone it, check out `ios-server`, and read **`ios-server/HANDOFF.md`** before anything else. Start with its "Current state" section, which covers how I like to work, how I update the NAS, what's confirmed on my phone, what's pushed but untested, and the known limits. The rest of the file is the history and the technical details. `ios-server/README.md` is the setup, settings and removal guide.

Ground rules:
- Push fixes to `ios-server` on GitHub. I update the NAS with `git fetch origin && git reset --hard origin/ios-server`, then `docker compose build && docker compose up -d`, then open the game twice.
- Add a short dated section to HANDOFF.md for anything you change, and keep README's settings and removal sections current.
- Ask me questions in plain text, not with the question-picker tool.

Once you've read the handoff, tell me in a few lines that you're up to speed. Then I'll describe two new, big things I want to work on. Don't start on anything else first.

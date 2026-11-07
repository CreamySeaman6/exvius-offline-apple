# Handoff: Exvius Offline on the iPhone

Notes for a new Claude session picking up this work. Last updated 2026-11-07 (morning). **Start with "Open problems (2026-11-07)" just below.**

Read **Current state** first. The dated sections below it are the history: each records what was found and why, and later sections can supersede earlier ones (noted where they do).

## Open problems (2026-11-07) — read first

The 2026-11-07 session ran out of context mid-debugging. Its notes below ("Story text keys, expeditions") were written quickly; **check them against the code and the repo history (`git log -p` for commits 1442ed0, 3e33480, 5ac9a60) before relying on them.** Nothing from that session is confirmed on the phone, and the operator reports things got worse, not better.

1. **Port City Lodin (town 1103): "A loading error has occurred", back to Home. Still happening after 5ac9a60.** It started after 1442ed0. His log (07:59, 2026-11-07): login fetched the patched map version table (`Ver205869_YIgCpDKW.dat`, "3 story pack(s) with missing lines"), then entering Lodin fetched the rebuilt scene `common_lang/sd/event/11/Ver1048_111020301.cpk` (104448 B), then TownIn 1103, then the error. 5ac9a60 set the rebuilt pack's header `FileSize`/`TotalDataSize` (version now Ver1049) and did **not** fix it. Unknown whether his phone had re-fetched the table and the Ver1049 pack when he retried. First steps: get the matching client report (`FFBE_DIR/server/client-reports/`, uploaded at the next launch) and the log of a retry; quickest test of the cause is `EXVIUS_STORY_TEXT_FIX=0` (serves the shipped scene; if Lodin loads, the rebuilt pack is the cause). Other suspects: the client checking `F_RESOURCE_MAP_CHECKSUM_MST` (`JwbkKrjA`/`mYtcPkQQ`, 28064 for this pack, not changed) against the download; something in `story_text.rebuild` (it re-lays the files at 2048 alignment and moves the ETOC; compare byte-for-byte with the original apart from the two text files). Reverting `story_text.py` (and its hooks in `ios_tables.py`) is a reasonable fallback; the operator prefers working over complete.
2. **"Download while playing tutorial?" prompt is back** at launch (it was gone after the 2026-11-06 drop-unversioned fix). Suspect, unverified: real files to fetch, not the old 0 KB rows: 5ac9a60 bumped `ios_art.BUILDER` to 2, so the Vortex banner pack (`spdungeon1.cpk`, about 240 MB, class TUTO so up-front) was rebuilt under a new version, and the three story packs got new versions. Check what size the prompt shows and what the next CDN requests are. If the `ios_art` change is the cause and not needed, revert it (it added `FileSize`/`TotalDataSize` to that pack's header; the Vortex tiles were never confirmed either way).
3. **Freezes, not investigated** (no log yet): tapping Details on the VIP Shop's vision card "Metal Gigantuar's Here!" (product 940000012, reward `27:900020101:1`; opens `VisionCardDetailScene`); talking for the first time to a woman NPC in Port City Lodin (screenshot: blue dress, by a lamp post; music plays, input dead).
4. **Farplane monument** always replays the first Farplane scene and returns him to Mitra. Not fixed; findings in the 2026-11-07 section (switches 10004001/10005001/10009001/10009002, map/event opcodes). Needs the server log of one monument touch.
5. **Unconfirmed from 2026-11-07:** expedition offers rework (tutorial chain, then 3 random regular offers, daily free refresh, supercites, Moogle Cave), shop product names (`ios_texts.py` GENERATION 3, `F_TEXT_NV_SHOP_PRODUCT_*` tables).

He still runs the container with `docker compose up -d` (not yet moved to the Unraid template).

## Current state (2026-11-06)

### How the operator works

- Brando, the repo owner. He plays on his iPhone and reports back with screenshots and pasted `docker logs`. He doesn't read code.
- Plain, direct communication. Short updates in plain words; no internal jargon in messages to him.
- Ask questions in plain text, not with the question-picker tool (it covers the write-up on his phone).
- Don't suggest sending fixes or reports upstream (Elvlin/exvius-offline). This fork is his.
- Keep side tasks to a minimum; don't add extra test harnesses or chores to his list.
- Anything installed on his machines needs a documented way to remove it (README's removal section).
- Decisions he has made are recorded in the sections below ("operator's request/choice"). Don't reverse them without asking.

### Updating the server (the NAS, ThousandSunny, Unraid)

Push to `ios-server` on GitHub, then he runs:

```bash
cd /mnt/user/appdata/ffbe/repo && git fetch origin && git reset --hard origin/ios-server
cd ios-server && docker compose build
```

then Docker tab → `ffbe` → **Edit** → **Apply** (recreates it from the new image). This assumes he has moved `ffbe` to the Unraid template (`unraid/my-ffbe.xml`, README "Unraid: run it from the Docker tab"; sent 2026-11-06 evening, not yet confirmed). Until he has, the update is `docker compose build && docker compose up -d`. Once he has, never tell him to run `docker compose up` (a second container with the same name); `docker compose exec server …` becomes `docker exec ffbe …`.

When a change adds or renames an environment variable in `docker-compose.yml`, also add it to `unraid/my-ffbe.xml` and tell him to add it on the Edit page (re-copying the template resets his own edits).

He has switched to the single container (confirmed 2026-11-06), so the `docker rm -f ffbe-tailscale-1 ffbe-server-1` migration step (README, Everyday use) is done.

Then he opens the game twice (some table changes only take effect on the second launch). The stack is one container, `ffbe`, which he can also start and stop from Unraid's Docker tab; logs are `docker logs --tail 50 ffbe`. The NAS checkout once had no `origin` remote; it was re-added with the GitHub URL. Use `git --no-pager log`, since plain `git log` opens a pager in his terminal.

### Confirmed working on the phone

Boot, login, downloads, tutorial battles, audio (music, effects and movies), the Shop bundle names, the historical replay (the News board showed "Week of November 1 — Global history Dec 16, 2016 – Jan 5, 2017" with the Noctis set), notice pages, the earlier text fixes, and the Lapis economy (it paid; it also caused the repeat-clear bug below, now fixed).

### Pushed but not yet confirmed on the phone (as of commit bc046b2, 2026-11-06)

1. **Summon detail art** (`-fit1` names, blurred side padding). See "Fixed: summon detail art still squashed…" below. On 2026-11-05 he still saw the squashed Noctis art, because the phone had cached the old image.
2. **News page art**: banner path and wiki sprites (same section).
3. **Connection error on repeat clears** (Lapis multiplier vs `exvius_repeat` check). See "Fixed: connection error…".
4. **Banner deals**: 107 banners pay their printed bonuses. See "Banner deals…". In his replay, the first Trust Moogle deals arrive around summer 2017 history.
5. **Other players** (200 friends to add and remove), **home marquee** (first dated events reach the replay around 7 real weeks in; a home-screen crash after that means `MARQUEE_FLAG=0`), **weekly summon gift** mail, **Lapis daily quests**.
6. **Vortex tile art and the Enhance tab** (spdungeon1.cpk rebuild).
7. **Single container** `ffbe` (Tailscale + server; fixes the dead network after Unraid's 4 AM Appdata Backup). He has switched to it (2026-11-06); not yet confirmed that it survives the nightly backup. See "One container…" at the end.
8. **Rookie friend quests**: "Send a friend invite!" and "Go on a quest with a friend!". See "Fixed: Rookie friend quests…".
10. **Arena ladder** (2026-11-06): five-unit opponent teams, 0.50-1.50 ratios, weekly leaderboard and placement rewards, the replay's weekly season. Not yet seen on the phone. See "Arena: full teams…" at the end.
9. **Event history** (2026-11-06): events open at every Global run (first runs and reruns), and nine missing events were added (two of them, Return to the Halloween Castle, with rebuilt battles). Replay week 0 gains The Hanging Edge and Dread Frost Arrives; week 1 (from Sunday 2026-11-08) Memories from the Aquapolis, Akademeia, Dangerous Woman Tour, Mana Mystery. Open the game twice before opening the Vortex (the banner pack changes). See "Event history: real run dates…" at the end.

11. **Vortex polish, home banner taps, panel chests** (2026-11-06): holiday events follow the holiday banners, Clash of Wills and Dark Visions only in their Global periods, no look-alike tiles, home banners open their event, the panel's line chests claim. See "Vortex polish…" at the end.

12. **Tile order, holiday chambers, the 0 KB download prompt** (2026-11-06, afternoon): events listed first in the Vortex, Chamber of Challenges' Halloween/Christmas battles only in those weeks, and the seven file-less resource rows left out so the phone stops asking "Download while playing tutorial?" on every start. See "Vortex order, holiday chambers, 0 KB prompt…" at the end.

13. **Random battles in explorations** and **Standard Summon art** (2026-11-06, evening): exploration loads now carry encounter rows, built from the wiki's monster lists for 240 explorations; the Standard and free summons' detail art is fitted to their 640x392 frame. See "Random battles in explorations…" and "Exploration battles from the wiki" at the end.

14. **Story text keys and expeditions** (2026-11-07): three scenes' missing lines filled in (chapter 1 with Fina shows Lasswell's and Rain's lines instead of `MAP_TEXT_…`); expeditions as in Global (tutorial chain one at a time, then three random regular offers with a daily free refresh, the day's supercites and the Moogle Cave). See "Story text keys, expeditions" at the end.

**What to ask him to check first after he updates** (open the game twice): random battles while walking the Earth Shrine exploration, and that the exploration's result screen lists what they dropped; the Standard Summon art fills its frame; no "Download while playing tutorial?" prompt on the second start; the Rookie Panel's 1-line chest claims; tapping a home banner opens the event's stages; the Vortex lists this week's events at the top with no repeated tiles; the Arena opponent list and ranking tab.

### Open issues and known limits

- **Unverified client reading.** Two of today's fixes rest on reading the Android binary (the iPhone binary is encrypted): home banner type 6 links and the 0 KB prompt. If home banners vanish, set `EXVIUS_REPLAY_MARQUEE_TAP=0`; if startup downloads misbehave, `EXVIUS_IOS_DROP_UNVERSIONED=0`. The prompt's iOS-only text (`DLC_BACKGROUND_DOWNLOAD_CONTENT`) isn't in the Android binary, so the cause (rows with no file version) is inferred from the tables, not from the iPhone's code. If it still appears, get `docker logs` from a start: the files the phone asks for right after startup are the pending ones.
- His **two big things** of 2026-11-06 are built: event content with the banners ("Event history…", "Rebuilt: Return to the Halloween Castle") and Arena parity ("Arena: full teams…"). Neither is confirmed on the phone yet.
- Early history is still lighter than the banners suggest, because Global itself had no story events before June 2017 (exploration, King Mog, raid and trial events only). Lunar New Year (Jan 2017), Eternal Winter and The Spearmaiden are missing for lack of battle data; they could be rebuilt the way Halloween Castle was (see "Rebuilt: Return to the Halloween Castle"). That event's Castle Keep has no mission rows; its rewards are sold in the Skeleton Key Exchange instead.
- Explorations with no wiki record have no random battles; the list sent to the operator is in "Exploration battles from the wiki" (his call whether to fill them from the area's story battles). Battles are placed per zone, not per area within a zone, and a zone whose map uses several encounter fields gets its battles on each (so possibly more battles than the original there). Monsters without a drop list get the generic fallback drop (keep-one rule).
- The mission result screen shows base Lapis, not the 1.5× amount actually credited.
- Tall 640x392 detail art is padded to the frame, so it shows narrower than the frame (with blurred sides).
- A unit from the NV SP ticket arrives at level 1 although the banner says 120. Offered to look at it; not requested.
- Banner deals left out: FFBE Heroes Coin, Special FFXV Ticket, OCTOPATH exchange ticket (nothing spends them), the Rain NV ticket (unidentified), NV "panel rewards", and the 9100274 "three 11 summons give a free one".

### Where the 2026-11 systems live (`source/server/`)

| What | Files | Section in this file |
| --- | --- | --- |
| Historical replay (banners, Vortex and shops follow Global history; pace 3 weeks per real week, 2 from the NV era; holidays line up) | `replay.py`, `unit_release.json`, `gacha_rotation.py` (`_replay_plan`), `event_archive.py`, `exvius_shop_catalogue.py`, `player_state.expand_pool` | Done: historical replay |
| News board notice pages with art, home marquee | `replay_notices.py`, routes in `capture_server.py`, `ffbe_banner.py` | Done: historical replay (notice and marquee bullets); Fixed: summon detail art… |
| Summon detail art padding | `banner_fit.py`, `ffbe_gacha._gacha_schedule_banner_string` | Done: historical replay (summon detail art bullet); Fixed: summon detail art… |
| NV SP tickets (once per save, full pool) | `replay.full_pool`, `gacha_archive.held_ticket_ids`, `global_bundles.json` | Done: historical replay (one-off/SP ticket bullets) |
| Item/bundle text | `ios_texts.py` (`GENERATION`), `ios_text_items.json` | Done: historical replay (iPhone text bullet) |
| 200 made-up players | `friend_players.py`, `ffbe_friends.py` | Done: historical replay (other players bullet); Fixed: Rookie friend quests… |
| Lapis economy (1.5× earned, daily quests, weekly gift) | `lapis_economy.py`, `player_state._grant_items`, `ffbe_battle.py`, `ffbe_player.py`, `ffbe_pipeline.py` | Done: historical replay (earned Lapis bullet); Fixed: connection error… |
| Banner deals printed on art | `banner_deals.py`, `banner_deals.json`, `player_state.roll_gacha` | Banner deals… |
| Rookie friend quests | `ffbe_friends.local_friend_action`, `exvius_repeat.observe_load`, `ffbe_player.score_completed_quest_mission` | Fixed: Rookie friend quests… |
| One container | `ios-server/Dockerfile`, `entrypoint.sh`, `docker-compose.yml` | One container… |
| Event run dates and added events | `event_history.json`, `event_archive.py` (`document`, `weekly_events`, `added_art`, `fetch_added_art`) | Event history… |
| Rebuilt battles (Halloween Castle) | `event_encounters_added.json` (merged in `battle_content.event_encounter`), `ios-server/devtools/build_halloween_castle.py` | Rebuilt: Return to the Halloween Castle |
| Arena ladder (teams, ratios, weekly leaderboard, placement, seasons) | `arena_ladder.py`, `exvius_arena.py` (`roll_week`, `settle_week`, `matching`, `end`), `exvius_actions_arena.py` (`rb_entry`, `rb_ranking`, `_arena_rows`) | Arena: full teams, ratios, weekly leaderboard |
| Holiday events, ranked-event periods, one tile per look | `event_archive.py` (`HOLIDAY_EVENTS`, `weekly_events`, `_one_per_look`), `gacha_rotation.vortex_week`, `event_history.json` (`windows`) | Vortex polish… |
| Home banner taps | `ffbe_banner.event_link`, `replay_notices.marquee_entries` | Vortex polish… |
| Panel line chests | `exvius_actions_expedition.panel_extra_rows`, `ffbe_player.serve_panel_quest` | Vortex polish… |
| Exploration random battles (`6v0LPiRe` encounter rows) | `battle_content.encount_rows` / `field_mission_bundle` / `field_zone`, `content/exploration_encounters.json` (built by `ios-server/devtools/build_exploration_encounters.py` from `content/exploration_wiki.json`), `ffbe_battle._roll_items` | Random battles in explorations…; Exploration battles from the wiki |
| Detail art frame per summon screen (`-fit1` wide, `-full1` 640x392) | `banner_fit.py` (`BASE_FRAME`, `PLAIN_SUFFIX`), `ffbe_gacha._gacha_schedule_banner_string(pad=)`, `capture_server._cdn_fetch` | Random battles in explorations… (Standard Summon art bullet) |
| Event exchanges (Skeleton Key Exchange) | `content/event_shops.json`, `exvius_shop_catalogue.py` (`EVENT_SHOPS`, `hidden_details`) | Rebuilt: Return to the Halloween Castle |

## The goal

Play Final Fantasy Brave Exvius on an iPhone, offline from Square Enix/gumi, using this fork of Exvius Offline.

The approach:

- The game server from this repo (`source/server/`) runs in Docker (developed on an Unraid NAS).
- The **stock, unmodified iOS app** connects to it, installed from App Store → Purchased. Tested: build 1167, version string `ver.9100`, on an iPhone 17 Pro (`iPhone18,2`) running iOS 27.0.1.
- Tailscale routes the phone to the server from anywhere.

A decrypted, re-signed IPA is the fallback if a client-side change is ever needed.

Also done on the server side: a weekly summon rotation (Sunday 10 PM Eastern) that now follows Global's history week by week ("historical replay", below). Standard, Rare and other permanent banners are always shown.

Anything new the stack installs needs a documented way to remove it completely. The removal section in `README.md` covers this stack; keep it current.

## Where things live

| What | Where |
| --- | --- |
| Code | Branch `ios-server` of `CreamySeaman6/exvius-offline-apple` (on GitHub). |
| Checkout | `FFBE_DIR/repo`; compose files in `repo/ios-server` |
| Data (`FFBE_DIR`) | `data/` (game data, ~15 GB), `server/` (save, certificates, request logs, client reports), `tailscale/` |
| Container paths | `/srv/ffbe/data` and `/srv/ffbe/server-root` |
| Tailscale node | `ffbe`. Split DNS sends `gumi.sg` and `exvius.com` to its address. |

### Getting the code

The `ios-server` branch is on GitHub: clone the repo and check out `ios-server`. Pushing from a Claude session works once the repo is added to the session (the `add_repo` tool with push access); before that, the git proxy returns 403.

### Delivering updates

Normally: push to GitHub and have him run the commands under **Updating the server** above. Fallback: build a git bundle, send it as a file, and have it pulled on the server machine:

```bash
cd FFBE_DIR/repo/ios-server
git pull FFBE_DIR/exvius-ios-server.bundle ios-server && docker compose build && docker compose up -d
```

Build the bundle relative to `main` (`git bundle create X.bundle origin/main..refs/heads/ios-server`) unless you know exactly which commit the other side has; a bundle based on a commit it lacks fails with "Repository lacks these prerequisite commits". Use `refs/heads/ios-server`, because plain `ios-server` is ambiguous with the folder name.

### Commits

- Author: the repo owner's identity, as in the existing `ios-server` commits.
- These files in `source/server/` use **CRLF** line endings: `capture_server.py`, `event_archive.py`, `exvius_actions.py`, `ffbe_config.py`, `ffbe_player.py`. Preserve them; edit with a byte-level replace (`open(p, newline='')`) if needed.

## What the iPhone stack is

`ios-server/`:

- `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`: one container, `ffbe` (service `server`), running tailscaled and the game server together since 2026-11-06 (see the section at the end). Before that: a Tailscale sidecar plus `server` on `network_mode: service:tailscale`.
- `ffbe.py`: CLI with `serve`, `fetch-data`, `rotation`, `status` and `new-game`.
- `serve.py`: TLS on 443 (deferred handshake), HTTP on 80 (serves `/ca.mobileconfig` and `/ca.crt`), and a DNS responder that answers only gumi.sg/exvius.com. It also has `/__exvius/hello` and `configure_engine()`, which sets env defaults for the engine (list below).
- `certs.py`: private root CA, name-constrained to gumi.sg/exvius.com, plus the leaf certificate.
- `fetch_data.py`: downloads and unpacks the data packs listed in `data/latest.json` (GitHub releases).
- `README.md`: setup, everyday-use and removal guide.
- `devtools/`: debugging tools from the last session (described below).

Engine changes for the iPhone, in `source/server/`:

| File | Purpose |
| --- | --- |
| `gacha_rotation.py` | Weekly rotation. Used by `gacha_archive.visible_banners()` and `menu()`. |
| `ffbe_battle.serve_version_table` | Advertises every `F_*` table at `real + EXVIUS_TABLE_VERSION_OFFSET` (200000), so the stock client replaces all of its own tables. `F_RESOURCE_MST` gets an extra bump from `ios_tables.version_bump()`. |
| `capture_server._cdn_fetch` | Maps the inflated `Ver<N>` back to the real file and strips the `banner/` prefix. Serves `/ios/` sound paths from the Android folder ("android twin"), optionally re-flagging HCA-MX. Converts CRLF tables to LF. Serves the patched resource table. |
| `client_reports.py` | Makes the game upload its own encrypted debug log. This is how we get logs from the phone, since iOS Console redacts them. |
| `sound_compat.py` | `plain_bank()`: removes HCA cipher type 1. `hcamx_to_hca()`: flips ACB waveform EncodeType 6 (HCA-MX) to 2 (HCA). `apply_ios()` runs whichever are on. |
| `ios_tables.py` | Serves `F_RESOURCE_MST` with `resources_common.cpk` and `resources.cpk` moved into the first (`TUTO`) download, and the two resource version tables with new sound file versions. |

Env defaults set in `serve.py`:

- `EXVIUS_TABLE_VERSION_OFFSET=200000`
- `EXVIUS_CLIENT_REPORTS=1`
- `EXVIUS_TABLE_LF=1`
- `EXVIUS_IOS_HCA=1`
- `EXVIUS_IOS_HCA_PLAIN=1` (also in `docker-compose.yml`, next to `EXVIUS_IOS_SOUND_REFETCH`)
- `EXVIUS_EARLY_RESOURCES=resources_common.cpk,resources.cpk` (also set in `docker-compose.yml`)
- The summon archive and rotation flags

## Problems solved so far

1. Connectivity, DNS split, and certificate trust. The fix was the Certificate Trust Settings toggle on the phone.
2. **MST_LOAD_FAILURE.** First the stock client's own tables mixed with ours; fixed by the version offset. Then the iOS base64 decoder rejected the CRLF line endings of rebuilt tables (`LOAD_ERROR_DECODE_FAILED`); fixed by `EXVIUS_TABLE_LF`.
3. **Sound files 404.** The client asks for `common_lang/sound/*/ios/...`, and the preserved data only has `.../android/...`. The server now serves the Android twin.

Result: the game boots, logs in, downloads data with sizes shown, and plays the intro. Then:

## Solved: crash entering the first battle (mission 1110100)

Symptom: the intro plays, the party appears, and the game crashes on the cut to combat. The client log shows
`CriFileLoader::load Failed to load file. FILENAME=layout/timer/layout_questCounter.csv` and
`spritestudio/timer_animation/Timer_animation.ssbp` right after `WaveBattleScene::initialize -- 05`.

- Those files ship only in `common_lang/sd/resources/Ver273_resources_common.cpk` and `en/sd/resources/Ver202_resources.cpk`.
- `F_RESOURCE_MST` (token `ZQqB38Ns`, key `u6q3F02d`) gives those packs an empty class in `81fTkEDP`, so they sit about 340 files deep in the background queue (358-370 files), which is still downloading LBMovie packs when the battle starts.
- Commit 2d0cc74 (`ios_tables.py`) marks both packs `TUTO`, so the blocking up-front download fetches them.

**What the 2026-11-05 logs showed after 2d0cc74:** the launch that received the patched table (it arrives at login, `STATE_MST_DL`) still crashed: its download check list had already been built, and the packs were queued `MODE=bg` at position ~344. The next launch fetched exactly those two packs first (server log: `Ver273_resources_common.cpk` and `Ver202_resources.cpk`, full size, right after startup), which matches the pre-login `DownloadSequencePopup` check using the table cached the launch before. So the fix needs one extra launch after the table changes. Confirmed working: the tutorial battles (bats, then the Earth Shrine rat) load.

**If it still crashes:**

1. Get the new client log.
2. If other files are missing, set `EXVIUS_EARLY_RESOURCES: "all"` in `docker-compose.yml`, run `docker compose up -d`, and launch the game twice.
3. If it crashes with no missing files, look at the battle code path again.

## Solved: garbled audio

**Status: fixed and confirmed on the phone (2026-11-05).** Music, sound effects and movie/cutscene audio play cleanly.

Findings from the 2026-11-05 second session:

- Every Android bank (all BGM, `SE.acb`, `System.acb`, and the bundled `Builtin.acb`, `SE_tutorial.acb`, `System_tutorial.acb`) is **HCA cipher type 1** (CRI's fixed keyless table). The earlier note that BGM is `ciph 0` was wrong.
- vgmstream (built from GitHub in the sandbox) decodes the Android banks cleanly. FFmpeg 6.1's HCA decoder ignores cipher type 1 and produces full-scale clipping noise from the same bytes (RMS ~14-17k vs ~3-5k). That is the same "loud glitch noise" the phone played. So the bank contents are fine, and the noise looks like a decode without the type-1 table rather than an output-rate problem.
- The re-flag to plain HCA (6e5b2cc) didn't fix it, which fits: it doesn't touch the cipher.
- **Fix:** `sound_compat.plain_bank()` decrypts every type-1 frame, sets the header to cipher 0, and rewrites the header and frame CRC16s. The size doesn't change (the client's `F_RESOURCE_CHECKSUM_MST` holds file sizes only). Checked locally: vgmstream decodes original and rewritten banks bit-identically, and FFmpeg (no cipher support) now decodes the rewritten ones at the right level. On by default with `EXVIUS_IOS_HCA_PLAIN=1`. `apply_ios()` runs it, then the HCA-MX re-flag.
- **Re-download:** the phone never refetches a `Ver<N>_` name it already has, so `ios_tables.py` now also serves `F_RESOURCE_VERSION_MST_LOCALIZE` (`A1L1GlaQ`/`JchlFPWK`, 81 sound rows) and `F_RESOURCE_MAP_VERSION_MST_LOCALIZE` (`YIgCpDKW`/`geHlpoos`, 701 sound rows) with `OzT5lSz3` (the version in the file name; checked against all 81 sound names in the logs) raised by `1000 + crc32(signature) % 1000`. The signature is `sound_compat.ios_signature()`: the transforms that are on, plus `EXVIUS_IOS_SOUND_REFETCH`. The sound rows are found via `F_RESOURCE_MST` / `F_RESOURCE_MAP_MST` (`B7LnP2TH`/`U0Vd7AfQ`) rows whose `3LHdc6Qa` starts with `sound/`. `_cdn_fetch` answers any `Ver<N>_` from the Android folder.
- Real iOS banks placed in `data/native/common_lang/sound/<bgm|se>/ios/` are now served as-is at any requested version, ahead of the Android twin.

**ExviusReborn assets:** The project (Hirurawa/ExviusReborn) is a Godot remake. Its code loads decoded WAVs (`res://assets/audio/bgm/la001_prelude.wav`, `assets/audio/sfx/se_system_common_ok_1.wav`), and its assets come from DaddyRaegen's ffbe_asset_dump. So they most likely hold no ACB banks or ACF. 

**If garbled audio ever comes back:**

1. Check the CDN lines show `… HCA decrypted` for `.../ios/Ver1xxx_*.acb` requests (new version names). If the phone is still asking for the old `Ver3_`-style names, it hasn't taken the new version tables.
2. Ask whether the opening movie's sound (ADX audio in `op_clip.usm`, before the "Download while playing tutorial?" prompt) is clean. If the movie is clean and banks are still noise, try converting the banks to ADX (encode type 0). vgmstream can decode, and a new ACB writer would be needed. If the movie is garbled too, the problem is the output layer on iOS 27, which means the decrypted-IPA route.
3. The iOS app bundle has its own `Builtin.acb` / `*_tutorial.acb` and `Lapis_sound.acf`. If the bundled sounds play cleanly, the runtime can decode iOS banks; comparing them with the Android ones (via an IPA from Apple Configurator) would show what differs.

## Resolved: no music in some scenes (2026-11-05)

Battle music was confirmed working by the operator later on 2026-11-05 (the tracks had still been downloading). Kept for reference:

After the cipher fix, the first tutorial battles had sound effects but no music. Most likely the tracks hadn't downloaded yet: the new sound versions (`Ver13xx_`) give every bank a new name, the game won't play an older copy, and the battle and dungeon BGM sit in the background queue (the server log showed it working through the map BGM list). Not yet confirmed, because the newest client report ended before those battles (the game uploads each session's log at the next launch).

- `… 0 HCA decrypted, 1 HCA-MX->HCA` on a CDN line is normal: those banks (mostly newer collab tracks, e.g. `la935`, `la0042`) are already cipher 0.
- To check: `docker compose logs server | grep -E "la005_battle1|la006_battle|la301_dungeon"` should show `Ver13xx_` requests, and the next client report should show `Playing BGM` or `BGM playback failed REASON=Missing file` for the battle.
- If it's the queue and the wait matters, move the BGM rows up front: add their file names to `EXVIUS_EARLY_RESOURCES` (only `F_RESOURCE_MST` rows; map BGM in `F_RESOURCE_MAP_MST` would need its own change).

## Android-only client hooks (important background)

The Android build is the stock gumi `libgame.so` plus about 4,000 lines of Frida-style hooks in `source/exvius/*.js` (`summon_menu.js`, `menu_assets.js`, `home_carousel.js`, `raid_menu.js`, `android_display.js`, ...), which call back into Python through `LocalGameBridge.java` / `source/memorial/android/src/main/python/android_game.py`. The stock iPhone app has none of this. Any iOS bug that works on Android should first be checked against those hooks; the fix is a server-side equivalent.

- Done: missing text. `ios_texts.py` adds the names `summon_menu.js` injects (local Shop bundles `990000xxx`, tickets `1062130x0`, banner names from `ffbe_gacha.missing_gacha_names`, explanations for banners without one) into `F_TEXT_BUNDLE` / `F_TEXT_ITEM_NAME` / `F_TEXT_GACHA`, and serves the localized-text index (`F_LOCALIZED_TEXT_MST`, `i5QEJpua`/`R8PYPnJ9`) with new versions plus each file's MD5 and size. `EXVIUS_IOS_TEXT=1` (default).
- Not done: area/dungeon names for Clash of Wills / Dark Visions and the parade party headers (`summon_menu.js` `nameFor`), the Vortex event filter and art (`menu_assets.js`, `summon_menu.js` GateScene hooks), the home carousel.

## Vortex (2026-11-05)

- **Crash: not reproduced.** Tapping Vortex crashed right after `GateEntryScene` early in the session (`GateEntryScene::initialize`, GL `0x2195578`: `DefineMst OTHER_WORLD_TOWN_ID` 9001 -> `TownMstList` -> request the town's map resource -> scene 604 `GateScene`). An hour later, after the background download had run, it opened normally. Most likely a file still in the download queue. If it recurs, get the `.ips` crash report.
- **Fix built (not yet tested on the phone): blank event tiles and the Enhance-tab crash.** `serve_event_gate` (ffbe_player.py) sets every archived area's tile art to the archive's banner (`event_<area>.png`, `event_art.json`), including permanent Enhance-tab dungeons whose shipped art was loadable. `GateScene` loads tile art by name through the CRI loader, which only searches mounted CPKs, and the archive's PNGs ship loose in `en/sd/area/`. Android supplies them with `menu_assets.js`. On the iPhone the Event tab drew empty frames and the Enhance tab crashed: the `.ips` from 2026-11-05 17:17 shows SIGSEGV at address 0 with `x2 = 21104` (Chamber of Experience, art `event_226.png`). `ios_art.py` rebuilds `en/sd/area/spdungeon1.cpk` (resource 6108101, 1,237 original files) with the 692 loose banners added. `ios_tables.py` raises its English version (`86SWOBTb`) and size (`MLOSu5E0` in `F_RESOURCE_CHECKSUM_MST`), and moves it into the up-front (`TUTO`) download. serve.py builds it at startup into `server-root/ios-cache/`. Verified locally: every original file byte-identical, added files byte-identical, TOC sorted upper-case like the original.
- **Done: weekly rotation** of archived events, tied to the summon rotation (see below).

## Getting logs from the phone

The server makes the game upload its own log. Files land in `FFBE_DIR/server/client-reports/<timestamp>.txt`, and the server log prints `CLIENT REPORT:` lines. Tar the folder and attach it.

To decode one:

```bash
python3 devtools/decode_reports.py <report.txt>
```

The log lines are AES-CBC with key `FFBE2020DevsRGod`, IV `dZMjkk8gFDzKHlsx`, double PKCS padding, base64, one entry per line. The script needs `cryptography`. The largest reports hold the most history; the crash shows near the end.

Server logs: `docker compose logs server | grep -E "CDN|CLIENT REPORT|ERROR"`. Every `CDN` line shows how the file was answered: `exact`, `overlay`, `android twin`, `CRLF->LF`, `… pack(s) moved…`.

## Reverse-engineering references

- **Android game library:** `release/exvius-offline-v0.1.18.apk` → `lib/arm64-v8a/libgame.so` (GL 9.0.9). It has symbols: `llvm-nm -D -C` and `llvm-objdump -d -C` work. All addresses in this doc refer to it.
- **Table name/token/key triplets** sit in libgame as `F_NAME\0token\0key\0`. Search the bytes for the token.
- **The iOS binary** is FairPlay-encrypted, so it can't be disassembled without a decrypted IPA. The resources in the .app are not encrypted. Apple Configurator on a Mac can download a purchased IPA to get them.
- **Data packs:** `data/latest.json` lists GitHub-release zips. `devtools/zip_list.py` (`RemoteFile`) reads single entries over HTTP range requests without downloading 1.4 GB packs. Example: `zipfile.ZipFile(io.BufferedReader(RemoteFile(url), buffer_size=1<<20)).read(name)`.
- **Decoded tables** are in the data packs under `static/mst_decoded/*.ndjson`, e.g. `F_SWITCH_MST`, `F_DEFINE_MST`, `F_RESOURCE_MST`.
- `devtools/cpk.py` lists a CPK, including XOR-masked TOCs.
- `devtools/acb.py` prints an ACB's waveform encode types.

## Testing locally (in a Claude sandbox)

### Quick in-process tests (what the 2026-11-05 sessions used)

Most changes can be tested by importing the engine modules directly, without starting the server:

1. **Data.** Pull `static/mst_decoded/*.ndjson` and `static/text_decoded/*.ndjson` out of the data packs (`data/latest.json`; `devtools/zip_list.py`'s `RemoteFile` reads single zip entries by HTTP range) into e.g. `~/t/data/static/` (~255 MB). The sandbox's work folder is not kept between sessions, so this has to be redone in a new one.
2. **Env**, then run Python from `source/server`:

   ```bash
   export FFBE_DATA=~/t/data MST_DIR=~/t/data/static/mst_decoded TEXT_DIR=~/t/data/static/text_decoded \
     GACHA_ONLY=all GACHA_CAMPAIGN=all EXVIUS_SUMMON_ARCHIVE=1 EXVIUS_EVENT_ARCHIVE=1 GACHA_STANDARD=1 \
     GACHA_CATALOGUE=1 EXVIUS_SUMMON_ROTATION=1 FFBE_SERVER_ROOT=<scratch dir>
   ```

3. **Examples:** `ffbe_gacha.all_banners()` (about 4,000 banners); a test save is `player_state.PlayerState(player_state.default_state())`, then `add_currency('lapis_free', n)` and `roll_gacha(banner, 1, offer=banner['secondary_offer'])`. For a CDN path, subclass `capture_server.Handler` with a stub `path`/`wfile` and call `_cdn_fetch()` (set `CDN_ROOT`/`CDN_OVERLAY` and `State.cdn_root`).
4. Running the replay records an anchor in `<data>/static/state/replay.json`; delete it after tests.

### Full server run

Docker Hub is blocked in the sandbox, so run the server directly:

1. **Make a Python 3.12 venv** with `cryptography`.
2. **Get data.** Use a partial data dir (`native/mst`, `native/localized_texts`, the needed `common_lang` bits, `static/mst_decoded`, `static/client/shared_prefs/gamedata.xml`) taken from the packs.
3. **Start the server:**

   ```bash
   env -i PATH=/usr/bin:/bin FFBE_ENGINE=<repo>/source/server FFBE_DATA_DIR=<data> \
     FFBE_SERVER_ROOT=<root> FFBE_HTTPS_PORT=8443 FFBE_HTTP_PORT=8080 FFBE_DNS_PORT=5353 \
     FFBE_ADVERTISE_IP=100.101.102.103 <venv>/bin/python <repo>/ios-server/ffbe.py serve
   ```

4. **Point the hostnames at localhost:** add `127.0.0.1 v900-lapis.gumi.sg v910-lapis.gumi.sg` to `/etc/hosts`.
5. **Get past the sandbox proxy:** use `curl --noproxy '*' --cacert <root>/certs/ca.pem`, and `NO_PROXY='*'` for Python. `ca.crt` is DER; use `ca.pem`.
6. **Replay requests:**
   - `devtools/replay_init.py <engine-parent-dir> 8443 <ca.pem>` sends the iPhone's InitializeRequest and prints advertised table versions.
   - `devtools/replay_all.py <same args> <captured request json…>` replays captured requests from the server's `server/requests/` and prints the switch containers in each reply.

## Fixed: quest ticker announcing the wrong quests (2026-11-05)

After every battle the phone scrolled "Get Lightning! Clear Lanzelt Ruins - Interior!" (SP challenge 9000000) and "Clear Attack of Gilgamesh..." (110101). Those are the first rows of the two served schedules (1001 Rookie, 1101 Advanced), and `serve_sp_challenge` put each schedule's first row into the ticker (`cT7S0ikb`) whatever its state. The ticker now carries only a cleared, unclaimed quest per schedule, or nothing, and the tag is always sent so the phone's old list is replaced. The quests themselves were never marked cleared.

## Economy audit (2026-11-05)

Requested: keep the game a long, slow playthrough with no shortcuts. Findings (all verified in code and data):

- CRITICAL: `exvius_shop_catalogue.catalogue()` serves category-6 shops in Lapis 1:1 (`if category == 6: kind, currency = 50, '1'`): the Daily Coin Shop (King Metal Minituar for 3 Lapis, unlimited; Gil Snapper Family 3 Lapis, unlimited), the VIP Shop (10 KMM for 70 Lapis, 20/month) and the EX Coin Shop (unit fragments). Daily Coins (1209001163) have no source on this server; EX Coins (1209001380) do (fortuna, field treasures).
- CRITICAL: `exvius_repeat.complete_attempt` pays challenge Lapis (kind 50) on every clear; other rewards once. Some event missions pay 3,000 Lapis per clear.
- HIGH: Early Bird Offer (`global_bundles.json` 990000101) costs 242 Lapis and contains 5,000. `serve_lapis_shop` applies `max(price, lapis inside)` only to shipped cash bundles, not to `global_bundles.json`.
- HIGH: daily 8th-Anniversary 10+1 ticket by mail. **Turned off** (`ANNIVERSARY_TICKET=0` in serve.py and docker-compose.yml), at the operator's request.
- King Metal Minituars are removed from the Lapis-priced shops (Daily Coin Shop, VIP Shop) by `EXVIUS_LAPIS_SHOP_EXCLUDE` (default `10:900020401`) in `exvius_shop_catalogue.catalogue()`, at the operator's request. The EX Coin Shop fragments stay: the operator wants them.
- The operator chose to leave the other findings as they are for now (repeat Lapis, Early Bird, bundles). Don't change them without asking.
- Vortex: the operator wants archived events rotated weekly, like the summon rotation, instead of all 757 at once. Build after the Vortex crash is fixed.

## Done: holiday-aware summon rotation and weekly Vortex (2026-11-05)

- `gacha_rotation.py`: a set is a holiday set when it was released in that holiday's season and one of its banners carries the holiday's mark (`HOLIDAYS`: Valentine's Day, Easter, Halloween, Christmas). Holiday sets leave the random pool and appear in the week before the holiday and the holiday's own week (changed from "the 14 days before" at the operator's request), one original year per occurrence, oldest first (the n-th occurrence since the save's first week shows the n-th year). `EXVIUS_ROTATION_HOLIDAYS=1`. `python3 gacha_rotation.py --weeks 8` lists them.
- `event_archive.weekly_events`: the Vortex shows the 90 permanent dungeons, every event released from 3 days before to 13 days after one of this week's summon sets (478 of the 626 dated events launched the same day as a set), and `EXVIUS_VORTEX_EXTRA` (2) undated recurring events. `serve_event_gate` uses it when `EXVIUS_SUMMON_ROTATION=1` and `EXVIUS_VORTEX_ROTATION=1`. Typical week: ~10 events plus the permanent ones.

## Done: historical replay (2026-11-05)

Requested: content arrives in Global's original order, so late-game units don't make early play trivial. Operator's choices: start at Noctis (2016-12-16), 3 historical weeks per real week, then 2 from the first Neo Vision banner (Global 2020-08-20, Cloud FFVII Remake). Holidays line up with real holidays; skipped holiday years are stacked into the next real holiday. Holiday banners run the week before the holiday plus the holiday's own week. News-board notices wanted; the home marquee is a separate future job (art would have to be made or found).

- `replay.py`: the clock. Replay week 0 = the rotation week of the first summon serve with `EXVIUS_REPLAY=1` (recorded in `state/replay.json`). `window()` gives each real week's slice of history. `python3 replay.py --weeks 8` previews; `ffbe.py rotation` uses it when the replay is on.
- Unit release dates: `unit_release.json`, from `python3 replay.py --write-units`. First Global banner featuring the unit (JP-only `translated-jp` banners only count for units Global never featured). Units no banner featured take the next dated unit of the same series (first three id digits) or the end of history; undated rarity-7 (NV) units are never before the NV era. Full reward lists of banners are not used for dating.
- `gacha_rotation.plan` → `_replay_plan`: every non-holiday, non-JP-only set released in the slice. Holidays: `_replay_holiday_years` walks each real occurrence since replay week 0 and shows years history went past without showing, plus the next year if it is within 365 days of history; several years are split across the two holiday weeks. NV EXVIUS is hidden until `EXVIUS_REPLAY_NV_ERA`.
- `player_state.expand_pool`: every pool (permanent and featured) is limited to units released by the end of the slice (`replay.pool_cutoff`); a banner's featured units always stay. At Noctis week Rare Summon draws 14 five-star, 23 four-star and 55 three-star units (was 358/187/161).
- `event_archive.weekly_events`: also events released inside the slice; events launched with a withheld holiday set (0 to 3 days after it) wait for it. The archive has no dated events before 2017-05-12 (the final client only kept events still in the game), so the first ~7 real weeks show only permanent and undated events.
- `exvius_shop_catalogue`: products granting a unit (kind 10) not yet released are left out (Obnixus exchanges, some EX Coin items). Catalogue cached per cutoff.
- `replay_notices.py`: News board. `InformationListScene::initConnect` sends `NoticeUpdateRequest` kind 4 (`CQ4jTm2F`); the list reads NoticeMstList buckets 0 and 1; reply tag `tN8f0PSB` fills bucket 0. Row fields from `NoticeMstResponse::readParam` (libgame 0x197d464) are listed in the module docstring. Caption is JSON `{"en": ...}` (`getLanguageCaption`), page type 1 opens the row's URL (`InformationDetailScene::getUrl`). Each replay week gets notice id 880000+week, read index 500+week; page `/exvius/notices/<week>.html` (future weeks 404). Not yet seen on the phone.
- iPhone text, second pass (2026-11-05): `ios_texts.py` now patches 20 text tables. It writes everything the Android hooks supply at run time (exbonus abilities, battle/colosseum monster and skill names, `MST_DUNGEONS_NAME_99999`, Clash of Wills / Dark Visions area names), the SP tickets' descriptions, and the obtainable items with no English text listed in `ios_text_items.json`. That list came from an audit of every `kind:id:count` reward list in the shipped tables and the server's JSON files; items tied only to JP-only units were left out (those units are never offered). Names there are translated from the JP item names. `GENERATION` in `ios_texts.py` must go up by one whenever the additions change, or the phone may not re-download.
- Other players (2026-11-05): `friend_players.py` makes 200 players (ids 910000001+, handles of at most 12 characters), each lending a weekly unit picked from named base forms released by the replay cutoff (rank decides 4★/5★/NV). `ffbe_friends.all_friends()` = friends.yaml (minus `yaml_removed`) + `players_added` (starts with 15 random ones); every caller that used `load_friends()` for the player's friends now uses it (gifts, helpers, arena, raids). New handlers in `exvius_actions.HANDLERS`: FriendRequest `j0A5vQd8` and FriendAgree `kx13SLUY` add (accepted at once; reply `I53AVzSo` + the new row on `2vuhy0Ex`), FriendDelete `a2d6omAy` and FriendRefuse `1nbWRV9w` remove (reply `I53AVzSo` with `0NVFk2fD` = the removed id). Request bodies are `I53AVzSo: [{m3Wghr1j: friend id, 8zE6w9RP, 0b6e9cwr}]` (FriendRequest::createBody 0x199d590). Reply tags from the response factory (0x1918f30..): `56gJBnVh` full friend list (kind 1), `2vuhy0Ex` friend rows added (kind 1, non-clearing), `9Qt5cI0n` kind 3 and `hZR64mDe` kind 2 (pending requests, left empty), `f6yGgCj2` kind 5 suggestions (now 10 a day), `2K05IxtX` search result. Not yet tried on the phone.
- Notice pages with art (2026-11-05; the image paths and sprite fetching were fixed later, see "Fixed: summon detail art still squashed…"): `replay_notices.render(summary, src)` is the page template (summon banner art from `/banner/<file>`, unit sprites from `/exvius/notice-art/unit/<id>.png`, event banners from `/en/sd/area/<file>`). Unit sprites are the wiki's `Unit-<Name>-<stars>.png` (tries base+1, base, base+2, 7), fetched once by the server into `ios-cache/notice-art/` (`unit_sprite`); misses are remembered for a week. Preview published as an artifact ("This Week in Exvius").
- Earned Lapis (operator's request, 2026-11-05; he chose all three options): `lapis_economy.py`. (1) daily quests all pay `EXVIUS_DAILY_QUEST_LAPIS` (150) plus `EXVIUS_DAILY_ALL_BONUS` (200) once all of the day's are claimed (`ffbe_player` claim path; the original daily rewards were never preserved, the catalogue's are authored); (2) `EXVIUS_LAPIS_MULTIPLIER` (1.5) applied in `PlayerState._grant_items` for kind 50 (skipped while `player._purchase` is set, which the Lapis Shop bundle path and the exchange shop `_grant` set) and in `ffbe_battle` for mission-challenge and rank-up Lapis (the result screen still shows the base amount); (3) `deliver_weekly_gift` pipeline step mails `EXVIUS_WEEKLY_GIFT` (10 Rare Summon Tickets 23:50 + Guaranteed Ticket 23:70, both in ticket group 10020 that 648 banners accept) once per rotation week (`player.data["weekly_gift"]["last_week"]`). Operator's view: the "scammy" step-up and bonus deals are part of the fun.
- One-off ticket summons (2026-11-05): `replay.full_pool(banner)` exempts any banner paid only with an item/important ticket that `global_bundles.json` doesn't sell without a limit (e.g. 9200026 Guaranteed NV Summon, ticket 1209001319 from the Early Bird Offer). Before, the replay limit emptied its NV-only pool and the ticket's rarity floor refused the pull (white crystal).
- Summon detail art (2026-11-05): the stock app stretches `gacha/sub/` art into a ~3.5:1 frame (measured 848x242 on the phone). `banner_fit.py` letterboxes each such image to 640:183 (now on a blurred copy of the art, and under new `-fit1` names; see the later section) before serving (Pillow, added to the Dockerfile), cached in `ios-cache/banner-fit/`. `gacha/main/` list art is untouched (rows size to the image).
- SP ticket pull fix (2026-11-05): the phone's summon request named the SP ticket by an id `F_TICKET_MST` doesn't have, so `roll_gacha` refused ("unknown ticket") and the client drew the decline reply (white crystal, no unit, ticket kept). For an item-paid banner the unknown id now falls back to the banner's cost item.
- SP ticket summons (operator's request, 2026-11-05): the Shop's 4★/5★/NV (1,000 Lapis) and 5★/NV (3,000 Lapis) SP Summon Tickets are once per save (`global_bundles.json` 990000108/109 `limit: once`). `gacha_archive.held_ticket_ids` adds any ticket-paid banner the player holds a ticket for to the rotation's list (their JP-only sets are otherwise excluded from the replay). `replay.full_pool_ids` (`EXVIUS_REPLAY_FULL_POOL`, default 9200107,9200108) exempts those two from the unit limit, so a ticket is one real NV chance. The unlimited 300-Lapis SP Summon Ticket (9200106) keeps the replay limit.
- Home banners (marquee): `replay_notices.marquee_entries` picks this week's dated Vortex events (newest first, max 6) and `ffbe_banner.banner_selection` serves them instead of the era table. Art = the event's original wiki banner already used for its Vortex tile (`event_art.json`, all 626 dated events covered, 640x240), served from `en/sd/area/<file>`; the row URL ends in `HomeBanner_<7000000+area>.png` and `capture_server` maps that name back to the art. iPhone turns the strip on with `MARQUEE_FLAG=1` (serve.py, compose); the engine default stays 0 (upstream's Android home has no marquee). Not yet seen on the phone: the marquee code path has never run on a device, so a home-screen crash after this change means `MARQUEE_FLAG=0`.
- Not gated, by the operator's choice (2026-11-05): 7★ awakening (Global mid-2018), NV awakening rules and old units' later enhancements stay available ("a little edge"). The final patch's new-player login ladder is not gated either. Don't gate these without asking.

## Next steps (superseded 2026-11-06)

The list that stood here is now under **Current state** at the top.

## Fixed: summon detail art still squashed, notice page art missing (2026-11-05, evening)

- **Summon detail art.** The padding (banner_fit.py) was working, but the phone never saw it: the app keeps every banner image it has downloaded and never requests that file again. The summon tables now name each detail image `<name>-fit1.png` (`banner_fit.fit_name`, on when `EXVIUS_IOS_BANNER_FIT_NAMES=1`, the iPhone default), and `capture_server` maps the name back (`banner_fit.real_rel`) before the lookup. To force phones to fetch again, raise `FIT_SUFFIX`. The padding is now a blurred, darkened copy of the art instead of transparent bars (`STYLE` is part of the cache key).
- **Notice page banner art** showed a broken image. Its src was `/banner/<file>`, which has no folder, and the CDN's by-name lookup only runs for paths that name a banner folder. It now uses the summon list's own path `/banner/en/sd/static_banner/gacha/main/<file>`. Broken art hides itself.
- **Notice page unit sprites** were blank. The wiki's image CDN answers WebP unless the URL says `?format=original`, and the server rejected anything that wasn't a PNG, then marked the unit missing for a week. URLs now carry `format=original`, WebP is converted with Pillow, and a miss is retried after an hour (new `.miss2` marker, so the old week-long `.missing` markers are ignored). If the server still can't fetch a sprite, the page has the phone try the wiki itself (`data-alt`, skipping the wiki's 300x171 "not found" picture). Fetch errors are logged as `NOTICE-ART`.

## Fixed: connection error after replaying a cleared mission (2026-11-05, evening)

`docker logs` showed `RuntimeError: partial upstream reward grant; transaction rolled back` from `exvius_repeat.complete_attempt` on every repeat clear that pays Lapis, so the battle-result request got no reply and the phone showed a connection error. Cause: the earned-Lapis multiplier (lapis_economy.py) changed the `count` of the row `_grant_items` returns, and callers check `_grant_items([row]) == [row]`. The multiplier now changes only the amount credited, and the returned row keeps the reward's own count. Tested: a 10 Lapis row credits 15 and comes back equal; a purchase credits 10.

## Banner deals: bonuses printed on the art are paid (2026-11-05)

The operator asked that the summon deals advertised on banners be honoured ("every 10+1 gives a Trust Moogle", step-ups and the like). The wiki's yearly summon pages barely record them, so all 362 banner arts for banners without bonus data were read by hand. `banner_deals.json` lists what was found for 107 banners; `banner_deals.apply` (called at the end of `ffbe_gacha.all_banners`) adds it to the banner's 10+1 offer (`secondary_offer`) or, for "with every summon", to the banner itself. Data a banner already carries always wins, and a guarantee is only raised.

- **Trust Moogles with every 10+1** (2017-2020, 16 banners): any-unit moogles (`affinity_points` only) or unit-specific moogles (`affinity_info` = the unit's own `9mu4boy7` trust reward string, as the catalogue already does). The "free 3★/4★/5★" choice weights are not printed; used 70/25/5 (60/30/10 for the 2017 summer 1★/3★/4★ banner). Recorded in the file's `_meta`.
- **Items with every 10+1/summon:** Star Quartz on every summon (801390), DQXI S Key #2 Gold (801980), 20 Summon Coins (Spooktacular, 802050), 5★ flexible tickets (802140, 802150), 10 Summon Coins (810500, 810540). Each is taken by one of the summon screen's exchange shops (`archived_store_schedules`).
- **NV era** (from 2020-10-01, 84 banners): the 10+1 guarantee is raised to 5★/NV (`{"rarity": 5}`, drawn from the banner's pool at or above 5★ by rate), plus that banner's Summon Coin x1 where one could be matched. Matching uses the coin's exchange rows (units, prisms and fragments named after the featured units); 7 ties were settled by date, and 13 banners got no coin.
- **Left out:** FFBE Heroes Coin (801090/801100/801110), Special FFXV Ticket (801310) and the OCTOPATH exchange ticket (801900), because nothing in the data spends them (their summon/exchange screens are missing). Also left out: the Rain NV ticket (810700), which could not be identified; the "panel reward" and extra tickets on NV banners; and the "three 11 summons give a free one" on 9100274. Step-up, once-a-day and per-player limits were already in the banner data where those banners exist.
- `player_state.roll_gacha` now reads `bonus_choice` from the 10+1 offer too (before, only from the step or banner).
- Tested: a 10+1 on each of the 107 banners succeeds and pays its bonus. A single on a 10+1-only deal pays nothing extra; Star Quartz pays on singles too.

## One container: Tailscale and the server together (2026-11-06)

Symptom: the morning after, the phone couldn't connect, and the server log had nothing after 11:13 PM. The operator suspected Unraid's Appdata Backup, which stops and starts containers overnight. With the old layout (Tailscale container + `server` on `network_mode: service:tailscale`), restarting the Tailscale container leaves the server attached to a dead network namespace: it keeps running, but nothing can reach it until it's recreated (`docker compose up -d --force-recreate`). The cause wasn't confirmed from logs.

He asked for one container he can control from Unraid. Now:

- `Dockerfile` copies `tailscaled`/`tailscale` from `tailscale/tailscale:stable` (a build stage) and installs `iptables iproute2 ca-certificates`.
- `entrypoint.sh` (the image's entrypoint): `serve` (default) starts tailscaled with `--statedir=/var/lib/tailscale` (the same folder and file the old container's containerboot used, so the node stays `ffbe` with the same IP), waits for the backend state, runs `tailscale up` with `TS_AUTHKEY` only if it needs a login (otherwise `tailscale set --accept-dns=false --hostname=ffbe`), then starts `ffbe.py serve`. If either process stops, the other is stopped and the container exits with that code, so `restart: unless-stopped` brings both back together. SIGTERM stops both cleanly. Any other command (`fetch-data`, `rotation`, ...) goes straight to `ffbe.py`, so `docker compose run --rm server fetch-data` and `docker compose exec server ...` still work.
- `docker-compose.yml`: one service `server` with `container_name: ffbe`, `hostname: ffbe`, `/dev/net/tun`, `NET_ADMIN`, and `${FFBE_DIR}/tailscale:/var/lib/tailscale`.
- Migration (README, Everyday use): `docker rm -f ffbe-tailscale-1 ffbe-server-1`, then build and `up -d`.
- Tested in the sandbox with stub tailscale binaries (pass-through commands, tailscaled dying, docker stop). Not yet run on the NAS.

## Fixed: Rookie friend quests didn't count (2026-11-06)

Reported: "Send a friend invite!" and "Go on a quest with a friend!" (Rookie Quests 100106/100107, Rookie Panel 1000103/1000102 and 1020103/1020102) never ticked.

- **Invite** (condition code 14): nothing scored it. `ffbe_friends.local_friend_action` now calls `score_quest_action('14')` when a FriendRequest (`j0A5vQd8`) is accepted, including to the made-up players. Agreeing to a request doesn't count.
- **Quest with a friend** (condition code 17): it was scored only when the mission END request carried `qLke7K8f` plus `dUX7Pt5i`/`w40YsHIz`, which the iPhone apparently doesn't send (no capture checked). Now `exvius_repeat.observe_load` (mission load, pipeline step `roll_drops`, which now passes the request body) records the friend/guest id from the START request on the attempt (`attempt['helper']`). `score_completed_quest_mission` scores 17 if the end request names a helper or the attempt recorded one.
- Tested in the sandbox: inviting a made-up player sets both invite quests to 1; a load with a friend then a clear whose end body names no helper sets both friend-quest rows to 1; a load without a friend leaves them at 0. Saves where these quests were already done before the fix don't get them retroactively; doing them once more counts.
- `source/exvius/test_*.py` doesn't import in the sandbox (it needs the Android build's modules), before or after this change.

## Event history: real run dates, and the missing events (2026-11-06)

Requested: the story/event content that went with each week's banners, which gave Lapis, event items and equipment. The Vortex was empty of dated events before May 2017 history.

Findings:

- Global's own schedule (the Brave Exvius wiki, Update Schedule, section "Global Update History") has an event or raid almost every week from December 2016. Global's first story event was The Gathering (June 2017); before that it ran exploration, King Mog (exchange), raid, challenge and trial events.
- 12 of the 18 events from Dec 2016 to May 2017 were already in `event_archive.json`, but undated (Dread Frost Arrives, Mana Mystery, March on Ifrit, The Egg Seekers, The Psycho Clown, Dangerous Woman Tour) or dated by a later rerun (The Hanging Edge, Akademeia, The Dreadnought, Operation MA Demolition, The Floating Continent, Shadow of the Empire), so the replay never opened them then.
- Some events the archive lacks are still in the shipped tables, with battles in the JP battle index. Every mission was checked with the same bundle choice and checks as `capture_server` (exploration field bundle, story phases, or `battle_content.assemble`).

Changes:

- `event_history.json`: `runs` (58 areas): Global run dates the archive lacks, read from that schedule. Dates within 45 days of the archive's release, or the same day a year apart, are treated as typos and listed in `provenance.skipped_runs`. `added` (7 events, archive row shape plus `art_url`): Memories from the Aquapolis (711, dungeon 71101 only; 71102 has no field battles; 2017-01-06, rerun 2017-07-14), The Auracite Chosen (712, 2017-03-24), Guardian of the Order (746, story event #5, 84 missions, 2017-11-03), The Web-Weaving Princess (749, 2017-12-01), King of Darkness (747, raid, 2017-12-08), Dracotaur Lancer (797, raid, 2018-05-25), Orbonne Monastery Vaults (703, 2016-09-30, rerun 2018-07-20). Together about 2,500 Lapis in mission challenges plus items and equipment.
- `ios-server/devtools/build_event_history.py` writes that file (the schedule lines and added events are in it; run it from `source/server` with `MST_DIR` set).
- `event_archive.document()` appends `added` and gives every row `runs` (release plus history). `weekly_events` opens an event when any run qualifies (same set-proximity and replay-slice rules as before). It returns the row with `release` set to that run (`first_release` keeps the original), so the News board and home banners date reruns correctly. Replay week 0 also reaches back 14 days (`REPLAY_LOOKBACK_DAYS`) for events running when the replay starts (The Hanging Edge, 2016-12-02).
- The two raids have no `raid_archive.json` data, so they play as normal battles (mission rewards, no raid coin scoring).
- Art: the added events' banners aren't in the data packs. `serve.py`'s art thread calls `event_archive.fetch_added_art()` before building the banner pack. It downloads each banner once from the wiki (`?format=original`, converted to a 640x240 PNG if needed) into `data/native/en/sd/area/`, and logs `EVENT-ART` on failure, retrying at the next start. `event_archive.added_art(area)` names the file only once it exists. `ffbe_player.event_gate_art`, `replay_notices._event_art` and `ios_art.art_names` use it, so a tile never names art the banner pack lacks; until then it shows the default tile picture.
- Left out (no battle data): Lunar New Year (907/908: the Nian Beast challenges are exploration missions with no field groups), The Spearmaiden (701), Eternal Winter (923), Trials of Love (no missions). Not checked: whether The Auracite Chosen's King Mog exchange shop shows (other King Mog events use the same path).
- Tested in the sandbox: all missions of the added areas pass the load checks; a 9-week replay preview before/after; the Vortex reply for weeks 1 and 4 (gate rows for every mission, default art without the file); News board summaries; the art download (PNG, WebP resized, network error, retry). Not yet on the phone.

## Rebuilt: Return to the Halloween Castle (2026-11-06)

Requested: make the 2017 Halloween event playable even though its enemies were never shipped, as close to the original as possible.

What the shipped data keeps:

- The missions, first-clear rewards and challenge rewards. Castle Dungeon BGN/ADV/ELT (9190001-3, area 919): 3/4/5 waves, Rare Summon Ticket + Skeleton Keys. Castle Inner Chamber INT/ELT/NIGHTMARE (9210001-3, area 921): Trust Moogles, Kitchen Knife, Candy Basket, Cloak of the Ghoul, Creepy Mask, Reaper's Shaft, Necro Dagger, Collar of the Blessed, ATK +15% / MAG +30% materia, Lapis.
- Every original Global monster id and name (900010339-900010377), the bosses' skill sets and AI scripts (Skeleton Wright 900010377, Skeleton King 900010340, Pumpking Reaper set 900010339 with AI 900000000 "PumpkinKnight", which matches the wiki's turn pattern), and every animated sprite (dictionary 10000000/10000001/10000002/10000020/10000021 in `monster_sg_common.cpk`).

What was rebuilt (`build_halloween_castle.py` -> `source/server/event_encounters_added.json`):

- Bosses: wiki boss infobox stats (Wright L70 3.5M HP; Reaper L99 38M; King L99 48.75M), resistances, actions per turn. Skill rows come from the Global datamine `aEnigmatic/ffbe` `monster_skills.json` (raw.githubusercontent.com, ~11 MB; pass its path to the script), converted like upstream's `reconstruct_event_battles.recover_skills`. Part-row template: upstream's 2016 Global Pumpking Reaper (encounter 9000401). Debuff-resist order assumed ATK, DEF, MAG, SPR, stop, charm, berserk (`Rcqa1Zt7`).
- Castle Dungeon: the wiki roster per difficulty (BGN Zombie/Ghoul + Revenant; ADV Mage/Shadow/Ghost + Pumpkin Kid; ELT Woodwatcher/Mammon/Treant + Pumpkin Rider) under the original ids. Each monster's combat profile comes from a same-species JP monster whose AI and skill set are in the client's tables (Pumpkin Kid/Rider: their 2016 Global profiles). Stats are scaled to Global's mid-2017 King Mog events at the same energy (Henne Mines, In the Name of Love, Castle Hein): L15 ~1.6-1.9k HP and a ~6k boss; L40 30-38k and a 110k boss; L70 150-190k and a 480k boss. Formations are local.
- `battle_content.event_encounter` merges `event_encounters_added.json` over `event_encounters.json`.
- `event_history.json` adds areas 919 and 921 (dungeons 91900 and 92100 only; area 921 also holds Dark Visions stages, which stay out), dated 2017-10-20 with the 2018-10-26 rerun, with the original banners (Banner-Halloween Dungeon, Banner-Inner Chamber).
- Not rebuilt: the Castle Keep (key-spending stages: materials, Purecrysts, Metal Cactuars). It has no mission or dungeon rows in the shipped tables. Its rewards go to a shop instead (below).
- Skeleton Keys (item 1209000838) drop in the Castle Dungeon: floor bosses always drop the floor's original key reward (1/2/3), other waves 35% (Hi-Potion as the fallback drop, since `roll_drops` always keeps one item).
- **Skeleton Key Exchange** (operator's request, 2026-11-06): `content/event_shops.json`, read by `exvius_shop_catalogue._catalogue` after the permanent shops (detail ids 850002000+, product ids 950000000+). Category 4, the same exchange list as the Obnixus Drop and Xenostone Shard exchanges. Stock: the Keep's challenge rewards from the Global datamine (missions 9200001-3: 1-star Trust Moogle, Chilling Aura, Spooky Aura, Mini Burst Pot), its first-clear Purecrysts (one each, 3/4/5 keys like the Keep stages), and the wiki's Keep drops (materials, Megacites, Metal Cactuar/Gigantuar, 2 King Metal Minituars at 10 keys each, Gil Snapper Family, Heavicrysts/Giancrysts, Elixir, Phoenix Down, Scrolls). Prices and limits are local. `hidden_details()` leaves an event exchange out of the list unless one of its `event_areas` is in this week's Vortex or the player still holds its currency, so leftover keys stay spendable. Tested: hidden/shown cases, purchases pay keys and grant items, purchase limits refuse.
- When it shows: the event launched with the 2017 Halloween banners, which the replay holds for the real holiday, so it opens in the Halloween weeks of 2027. It also opens at the 2018 rerun (around June 2027 at the current pace).
- Tested in the sandbox: all six missions pass the mission-load checks (`capture_server` bundle choice and wave checks). Not yet played on the phone. If a boss misbehaves (wrong sprite position, missing skill), the boss row's `7KYufEd5`/`a9DvZ70c`/`5A8SmwyC` come from the 2016 Reaper template and are the first suspects.

## Fixed: panel line rewards (2026-11-06)

Reported: the Rookie Panel's "1 line" reward could not be claimed after completing the middle row.

- The board's line rewards `L1`..`L8` mean "Lines Completed: n" (the game's own text, `PANEL_QUEST_LINE_COMPLETE_<n>`): any n of the eight lines. `panel_extra` (exvius_actions_expedition.py) read `L1` as the top row, `L2` as the middle row, and so on, so a middle row never satisfied `L1`. It now counts completed lines.
- Line and board rewards that are units with extra fields (the Rookie board's 4-line Trust Moogle `10:904000105:1:100:1:0:100000006` and the board-complete unit) were refused by `_reward_rows`. They are now parsed like the panel quests' own rewards (`_panel_rewards`, same grammar as `ffbe_player._quest_reward`) and checked with `_can_credit`.
- Tested in the sandbox: middle row only -> L1 pays, L2 refused; full board -> L4 (Trust Moogle), L8 and COMPLETED pay; repeated claims don't pay again.

## Arena: full teams, ratios, weekly leaderboard (2026-11-06)

Requested: Arena parity with Global (opponents with their full teams, a leaderboard you can climb to first place, rotating weekly, scores that push but aren't absurd, rewards for placement).

Global's last Arena (the client's, wiki "Arena" rev 313327): opponents are other players' teams (AI, up to five units, use their LBs), each with a 0.50-1.50 ratio; a win pays ratio x 100 (+ streak and unit bonuses), a loss 10; the opponent list changes every 10 minutes; points reset weekly and the week's rank pays a bracket reward (1-3000, 3001-30000, 30001-90000, 90001-150000, 150001-300000). There is one Arena mode; the Colosseum is the separate PvE mode (`exvius_colosseum.py`, unchanged).

Before: opponents were your friends' single lent units at ratio 1.00 (every win 100), the ranking list was empty, points never reset, the weekly reward was always the lowest bracket, and the season was the last shipped one forever.

Now (`arena_ladder.py`, with the made-up players on; `EXVIUS_PLAYERS=0` keeps the old behaviour):

- **Teams.** Each made-up player fields five units for the week: their lent unit as leader plus four from their `friend_players._unit_pool` (released units with the replay). Wire: `Jc4udh7x` (UserRbVsInfo VsBattleInfo) is one `:`-separated entry per unit with `;` between units (`UserRbVsInfoResponse::readParam` 0x1928fac, delimiters at 0x3044786 `;`, 0x2fa40f1 `:`). Per unit: instance id, unit id x2, level, six `base-bonus` stat pairs, LB level, equipment and materia slots (empty), two empty esper fields, member type (0 leader, `RbRivalUnitInfo::isLeader` reads +0x520 == 0; others 1), display order, AI pattern (F_RB_AI_PATTERN_MST weights). The stat bonus stands in for gear: 25-60% of base by the player's strength. Instance ids are `friend_id * 10 + order + 1`. `end()` validates every rival unit in the result.
- **Ratio.** Their team power over yours (`hp/10 + mp/10 + atk + def + mag + spr`; yours from `owned_unit_stats` plus equipment from F_EQUIP_ITEM_MST), clamped to 50..150 in steps of 5. A win pays the ratio (stored as `matched.rate`) instead of 100.
- **Opponent list.** `EXVIUS_ARENA_RIVALS` (5) per 10-minute window, spread from the weakest to the strongest ratio among 15 drawn players. Rows (`Tr9m32i1`/`TI6deE8P`) now carry each player's weekly points and rank: field layout from `RbMatchingListInfoResponse::readParam` 0x197fbb8 (`id:name:unitId:unitLv:points:rank:playerLv:rate:emblem:frame:unitExLv`).
- **Leaderboard.** Each player has a weekly target score (`_targets`: a stable persona plus weekly variation, heavy-tailed, the best scaled to about `EXVIUS_ARENA_TOP`, default 12000) and reaches it through the week at their own pace (`points`). Sandbox numbers at week's end: #1 ~11.6k, #10 ~8.9k, #50 ~5.9k, #100 ~2.5k, the least active 0. `rb_ranking` serves the top 100 and you in `CLg9j1sh` (`RbRankingListInfoResponse::readParam` 0x197f1a4: `id:name:unitId:unitLv:points:rank:playerLv:rate:emblem:frame`, ten fields minimum). Your rank goes in UserRbInfo `52ibRBqw`.
- **Week and season.** Weeks follow the summon rotation. `exvius_arena.roll_week` (from `_model`, so on the next Arena request) settles the finished week and resets the weekly points; it waits while a battle is pending. `settle_week` ranks you against the board at the last second of that week, places the rank on Global's scale (`rank / players x 300000`; with 200 players ranks 1-2 are the top bracket, 3-20 the next, 21-60, 61-100, the rest), and pays that week's season row from F_RB_SS_REWARD_MST (granted at once, with a mail saying the rank). The season is the F_RB_SS_MST weekly season running at the start of the replay week's slice of history (424 seasons, 2016-11-10 to 2024-10), so banned abilities, bonus units, daily rewards and ranking rewards follow history; without the replay, the last shipped season.
- **Migration.** A save's first Arena request after this update moves its all-time points to `lifetime_points` and starts the week at 0. `settle_weekly_reward` (the old participation reward) does nothing when the ladder is on.
- Tested in the sandbox: entry list, match (5-unit rival string), start, win (150 points at ratio 1.50), ranking list, week rollover (9,000 points -> rank 10 of 201 -> bracket 3001-30000 paid by mail, points reset, next season). Ratio spread for a mid-game team with pots: 0.75-1.35. Not yet seen on the phone: the first things to check are the opponent list, the rival party screen (five units), and the ranking tab.

## Vortex polish, home banner taps, panel chests (2026-11-06)

Reported after the event-history update: the panel line chest only previewed its rewards; tapping a home banner didn't open its event; the Vortex had dozens of "Clash of Wills" and "Dark Visions - The Advent of Chaos" tiles; holiday events opened on their history dates instead of with the holiday banners; and (follow-up) no duplicate tiles anywhere.

- **Holiday events** (`event_archive.HOLIDAY_EVENTS`, picked by name and theme from the events that ran in each holiday's season: Dread Frost Arrives, Season of Mayhem, Save Your Elf, the Egg/Hare events, Halloween Castle, Grave Hexvius, Mean Ghouls, Hallowed Eve, No Bed of Roses, ...). A run within -30..+14 days of its holiday belongs to that year. They open only in the week before and the week of the holiday, in the original years the rotation picks for that week (`gacha_rotation.vortex_week`, which runs `_replay_holiday_years` over the holiday's set years plus its event years, so a year with events but no holiday units still comes round). Story events that merely launched beside a holiday set are not holiday events and keep their history dates; holiday sets no longer pull nearby events into the Vortex (`vortex_week` returns non-holiday set dates only), and the old "skip events launched with a withheld holiday set" rule is gone. Preview: Dread Frost Arrives left replay week 0 and opens the week before Christmas 2026 with the 2016 Christmas units.
- **Clash of Wills and Dark Visions** were 67 `permanent` rows. `event_history.json` `windows` now holds the periods Global ran them (wiki: the 32 "Dark Visions - The Advent of Chaos" pages and Category:Clash of Wills, read 2026-11-06; DV areas run in area order, checked against each run's area elements; CoW areas by boss name). With the replay a row opens while one of its periods overlaps the week's history; only the newest run of each shows, and where Global ran two Clash of Wills bosses at once they take turns a week each. History reaches Dark Visions 1 (April 2020) about 58 real weeks in and Clash of Wills (July 2021) about 86 weeks in. They now appear on the News board and as home banners (their banners open the Vortex, not the event: they use their own scenes). Whether their modes play right on the iPhone has not been checked here (`exvius_actions_modes.py`).
- **One tile per look.** Tiles with the same name and banner art (`art_key`: `event_art.json` `runtime_sha256`, or the added event's art URL) are duplicates to the player. Permanent ones take turns, one a week (Chamber of Challenges' 8 areas, Chamber of Crysts' 2); dated ones keep the lowest area id (later copies of an event: Vault of Hidden Treasures' 12 areas, Grand Gaia Chronicles 913, The Big Bridge 6193, DQ Dai 9948, ...); undated extras show one area per name, the next one each time the name comes round. Permanent tiles went from 90 to 15. A 165-week preview has no repeated look in any week. Two that are different content but share art now show one (FFBE 5th Anniversary Livestream 1068 "Vs. Starlight Elena", Destroy the Machine Lifeform 843 "Abandoned Factory"); the Halloween Castle's two areas have different banners and both show.
- **Home banner taps.** `HomeScene::onTouchGateEventBanner` (0x1e51110) switches on the banner type (the int half of `uP4695k3`, jump table 0x2f5a410). Type 10 (what we sent, "10:601") opens scene 601, the Vortex. Type 6 takes "2,_,area,dungeon,mission" and opens `GateMissionScene` for that dungeon when the mission is in `GateUtil::getInSessionMissionList(dungeon)`, else the Vortex. `_canTransit` only checks a location for type 10 (`isLocationValid(-1)` is true), so type-6 rows still show. Event banners now send "6:2,0,<area>,<first dungeon>,<first mission>" (`ffbe_banner.event_link`); `EXVIUS_REPLAY_MARQUEE_TAP=0` goes back to "10:601". The old note in ffbe_config.py says the type must be 10; that only holds for type 10 rows. If the banners disappear after this update, that is the first suspect.
- **Panel line chest.** `sgPanelQuestScene::checkExtraRewardOnTouched` (0x24c8400) looks up `sgPanelQuestUserQuestExtraInfoList::getUserQuestExtraInfo(schedule, group, key)`: no row opens the reward preview; a row with `QCLs6SV8`=1 does nothing (claimed); a row with 0 sends `sgPanelQuestExtraRewardRequest`. The screen's reply sent no rows (`jksIZE9U`), so every chest previewed and the claim (fixed earlier today) was never requested. `serve_panel_quest` now sends a row for every reached line/board reward with its claim flag (`panel_extra_rows`), and the claim reply sends the full set too (each reply clears the client's list, `onReadStarted` 0x19590c4). Sandbox: fresh board no rows; middle row -> L1 unclaimed; claim -> L1 claimed; full board -> L2..L8 and COMPLETED unclaimed.

## Vortex order, holiday chambers, 0 KB prompt (2026-11-06, afternoon)

Reported: every start asks "Download while playing tutorial?" with 0 KB; this week's events sit at the bottom of the Vortex list; Chamber of Challenges shows its Christmas battle.

- **0 KB prompt.** Seven `F_RESOURCE_MST` rows have no file version in any language (`OzT5lSz3` and English `86SWOBTb` both 0): `character.cpk` (id 115001, class `tuto`, the class downloaded during the tutorial) and `6th_story1..4/4_a/4_b.usm` (101614-101623, background). There is nothing to download for them, so the phone can never mark them done, and their sizes are 0, which matches "0 KB". `ios_tables.drop_unversioned` (`EXVIUS_IOS_DROP_UNVERSIONED`, default 1) leaves them out of the served table and raises its advertised version by 2000 more (now 4837 with the default settings), so the phone fetches it. The table arrives at login, so the first start after updating may still ask; the second shouldn't. Tested on the decoded tables (521 of 528 rows served). Not confirmed on the phone; see Open issues.
- **Order.** The Vortex shows gate rows in the order served. `weekly_events` now returns events first (holiday events, then newest first, undated extras last among them), then Clash of Wills/Dark Visions, then permanent dungeons; `serve_event_gate` sorts its rows (including the carrier's own) by that order, with other areas after.
- **Holiday chambers.** Chamber of Challenges 902-904 (Castle of the Dead, Pumpkin Rider Strikes, Pumpking Reaper Arrives) are Halloween and 905 (A Frosty Offensive) Christmas (`HOLIDAY_PERMANENT`). Outside those holidays' two weeks the chamber rotates 930-933 (the elemental challenges); in them it shows the holiday ones. Preview: replay weeks 6-7 (December 2026) show 905, weeks 50-51 (late October 2027) 902/903, other weeks 930-933.

## Random battles in explorations; Standard Summon art (2026-11-06, evening)

Reported: no random encounters while exploring the Earth Shrine; the Standard Summon's detail art drawn narrow and tall in the middle of blurred sides (screenshot).

- **Encounters.** No exploration ever had random battles, on Android either. The client only starts one from `EncountInfo` rows in the mission-load reply, tag `6v0LPiRe` (`GameResponseFactory` -> `EncountInfoResponse::readParam` 0x1977dac), which the server never sent. Path: `MapManager::checkEncount` (0x1fb3f40) maps the chip's field index through the map's own field list (`EncountFieldIndexList`, read from `map.bin` in `MapDrawManager::initMapData` 0x1fa9d74) to an `F_ENCOUNT_FIELD_MST` rate, then `checkEncountFiled` (0x1fb43d4) draws a group among the rows with that field id (`EncountInfoList::drawing` 0x1e09190, uniform over distinct groups) and needs a row for (field, group, n) where n is how often that group was met there this run (`EncountLogList::getEncountNum`, 0 when none; cleared in `MissionStartScene::moveMapInit`). Three draws, then no battle.
- Row fields: `qo3PECw6` mission, `YzGa63QM` field id (+0xfc), `2fY1IomW` group (+0x28), `h4Sjf96p` n (+0x100), `Z0EN6jSh`/`xqartN26`/`6Yc4RkdM`/`9BetM2Ds`/`MZn8LC6H`/`g4voc2Aw`/`Vf5DGw07` as in the wave drop rows (`EncountInfo` derives from `MissionDropInfo`), `4K8t5dVh`, `V2mCH5UR` battle script (empty), `14FMQseU` (0 = escape allowed, +0x120).
- (Superseded the same evening by "Exploration battles from the wiki" below: own groups are no longer used.) `battle_content.encount_rows` (called from `field_mission_bundle`): the mission's own groups (`<mission><nn>`), minus any group in `field_group_bindings.json` `scenario_links` (map-script battles: bosses, fixed fights), on every field id the map can list, `max(2, ceil(48 / groups))` rows per field and group. Field ids: 159 of the 169 map lists readable without decompression are `10-14, 20-22, 30-32, 40, 50` (`ENCOUNT_FIELDS`); The Crystal Tower's map adds 70-75 (`ENCOUNT_FIELDS_EXTRA`); eight `18301xx00` maps list 210-282, but no exploration with groups uses them. The other 225 maps are CRILAYLA-compressed and weren't read. The retail per-area group lists aren't preserved, so every group appears everywhere.
- Drops: each row's `9BetM2Ds` is the union of its monsters' part drop lists from the battle index, rolled per row in `ffbe_battle.roll_drops` (`_roll_items`, same keep-one rule as waves; never touches `LAST_DROPS`). What the client fought and picked up comes back at MissionEnd (`xF9Sr1a6`, gil, exp) and is credited by `credit_mission_rewards` as before.
- Coverage: 155 of 437 exploration-type missions have their own groups (Earth Shrine 28, Dalnakya Cavern, Siren's Tower, Ancient Ruins, Eternal Summit, most event explorations). Many story explorations (Latius Woods, Grandshelt Catacombs, Phantom Forest, Zadehl Westersands ...) have none in the data beyond their boss, so they still have no random battles. They could borrow their area's story-battle groups; not done (operator's call).
- Size: about 600-950 rows, 180-280 KB of JSON per exploration load. `EXVIUS_FIELD_ENCOUNTERS=0` turns it off.
- Tested in the sandbox: rows for Earth Shrine (728), The Crystal Tower ELT (950), Destroy the Reactor (624); every row's group is in the served `Bi6hVv34`; the full reply pipeline keeps the tag; rolls vary per row. Not yet on the phone. Not checked: whether anything after a field battle (suspend saves) needs a server reply.
- **Standard Summon art.** `GachaUtil::changeSummonSecondScene` sends `layout == 1` banners to `GachaPayDetailScene` (the 3.5:1 frame banner_fit was measured on) and the rest to the base `GachaDetailScene`, whose frame is 640x392. The Standard Summon's 640x392 art was padded to 1371x392 and then drawn into 640x392. Now `_gacha_schedule_banner_string(pad=layout in (1, 2))`: layout-0 banners (Standard, Arena, EXVIUS, NV EXVIUS, the free/daily summons; 24 rows) name their detail art `<name>-full1.png` (`banner_fit.PLAIN_SUFFIX`), and `capture_server` fits those to `banner_fit.BASE_FRAME` (640x392 art unchanged, 640x160 padded to 640x392). Step-ups (layout 2) keep the wide frame; not checked on the phone. Tested through `_cdn_fetch`: `-full1` 640x392 served as is, `-fit1` padded, a 640x160 `-full1` padded to 640x392.

## Exploration battles from the wiki (2026-11-06, night)

Operator's request: random battles as close to the original as possible, sourced from walkthroughs or wikis (he offered Claude in Chrome), then a list of what's left for him to decide on.

- **Why not the battle data's own groups.** The battle index is the Japanese oracle. Earth Shrine's own groups (1110104xx: Wild Rat, Mercury Bat, Gloom Widow, Goblin Mage, Scorpion, Peeper, Skuldier) are a later line-up; Global's Earth Shrine exploration had Dire Rat 12, Steel Bat 11, Tarantula 2 in 13 battles. And the esper dungeons that have own groups (Siren's Tower - Top Floor, Inferno Hollow - Fire Beast's Lair, Zadehl Southersands - Sealed Zone, Lanzelt Mountains - Demon's Den, Eroded Castle, Cave of the Titan, Eternal Summit, ...) are a single boss battle on the wiki. Own groups are no longer used (the earlier section's behaviour is gone).
- **Source.** The FFBE wiki (exvius.fandom.com) read through its MediaWiki API from a Chrome tab: all 84 pages of Category:Explorations, the event pages of the 63 archived events that contain exploration missions, the "(Update)" rerun pages, Ancient Ruins 1-5, the Six Realms, the Realm of the Dragon King areas. Kept in `source/server/content/exploration_wiki.json`: each Battle Infobox's monster list with per-zone counts ("Dire Rat (12)", "Abtu (6)(9)" = zone 1 and zone 2), its battle total and bosses, and the Unit EXP Guide's battles per zone. WebFetch can't reach fandom from the sandbox; Claude in Chrome's `get_page_text` returns a long page body, so results were written into the tab and read back that way.
- **Zones = encounter fields.** `F_ENCOUNT_FIELD_MST` names its rows by zone (10-14 zone 1, 20-22 zone 2, 30-32 zone 3, 60-63/64-67/70-75 "another floor" 1-n, 110-150 and 210-282 "area N"). `battle_content.field_zone` maps them; a plan's zone N goes on zone N's fields, zone 0 (one-zone or count-less pages) on all. Assumed from the names, not seen in the client.
- **Builder** (`ios-server/devtools/build_exploration_encounters.py`, run from `source/server` with `TEXT_DIR`): matches missions to records by mission name (events), "X - Exploration" -> "X/Exploration", the dungeon name for explorations/realms/"X - Base", and the page name for one-mission event pages. Wiki monster names -> monster ids by English name (`F_TEXT_MONSTER_NAME`), choosing the variant used by the groups whose ids share the longest prefix with the mission. Per zone it picks real index groups made only of those monsters (closest groups first, sized to keep the wiki's battle count) until the counts are used up, then made-up one-monster groups (ids `900000001`+, laid out like a real group with that monster; stored under `groups`). Counts given for only some monsters (Kilika Woods' one Mini Mogcaptor) become that many single battles. Pages without counts get the listed monsters in the page's battle count less the boss, else 15.
- **Result:** 240 missions planned (67 story explorations, the Six Realms, Ancient Ruins, Realm of the Dragon King areas, and the archived event explorations), 283 made-up groups. Counts match the wiki exactly where it has them (Earth Shrine 13 battles: rats 12, bats 11, tarantulas 2; Zoldaad Castle Grounds zone 1/2 14/15 -> 14/16). Every plan builds through `derive_mission` and the full reply pipeline (replies 350-710 KB, most of it the carrier). Monsters on the wiki with no battle data: Fledgling Rukh (Ancient Ruins 1, Latius Woods - Past HARD, Petra), Roborg and Will O' Wisp (The Young Acacia Dragoon); those explorations have the others.
- **Left without random battles** (no wiki record of random monsters), sent to the operator: Expedition - Into the Abyss; The Kingdom's Light of Hope (+ Provisions); Visitors from Beyond (Dalnakya, Fulan Pass, Zadehl Westersands, Lanzelt Ruins); The Knight of Heart / Solice / Hardship; Aileen's 2/3/5, Roy's 1/3/5, Silvia's 2/4/6 episodes; Electric Tower - Pursuit (4 scripted battles on the wiki); The Dreadnought BGN-ELT (wiki lists only the Captain; the battle data has Mine, Ghast, Stunner, Balloon, Shadow, Dire Rat ... groups for it); Save the Choco-Chocobos!; The Palace of Wisdom (5); A Game of Cat and Mouse; Megacrysts Map; Asura's Palace. Confirmed boss-only on the wiki, so none by design: the esper dungeons listed above plus Thunder Summit, Wicked Peaks, Carbuncle Grove, The Isolated Goddess, Raven Falls Basin, Sylph's Cavern, Pitch Black - With Friends, Howling Mountains, Cave of Rebirth, Sacred Valley, Pit of Chains, Eternal Summit, and all Trials. 106 exploration-type missions with no English name or outside the archive are ignored.
- Not yet on the phone. First checks: Earth Shrine (13 battles of rats/bats/tarantulas, then none), a two-zone exploration (Lanzelt Highlands or Zoldaad Castle Grounds: battles in both zones).
- **Follow-up, operator's request: confirm whether the leftovers should have enemies at all** (wiki, same day). Added: The Dreadnought INT-ELT (an exploration event; the wiki gives 21-23 / 26-27 / 31-33 / 35-36 battles but no monster list, so the monsters are those of its own groups 71301xx01-24, the 80-90 groups being the Captain fights; BGN is the Captain alone); Expedition - Into the Abyss (the Aug 2016 Vortex exploration "Into the Abyss": 30 battles, Wild Rat, Mercury Bat, Gloom Widow, Goblin Mage, Scorpion, Peeper, Skuldier, Bomb, Golden Bomb, Ainsel, King Gil Snapper, Metal Gigantuar; boss Belmodar x3); The Knight of Heart / Solice / Hardship (Aquapolis Olderion quest: "based on" the Grandshelt Catacombs / Zadehl Westersands / Dwarves' Forge exploration "however there are no chests", so they use those plans; `same_as` in exploration_wiki.json). Confirmed none: the episode missions left over are the cutscene parts (Aileen 2/3/5, Roy 1/3/5, Silvia 2/4/6), Electric Tower - Pursuit (4 set battles, X-ATM092), A Game of Cat and Mouse (3 visible rat chases), Megacrysts Map (collection points, no battles), Asura's Palace (1 battle). No trace on the Global wiki (probably Japan-only content left in the tables): The Kingdom's Light of Hope (+ Provisions), Visitors from Beyond (4), Save the Choco-Chocobos!, The Palace of Wisdom (5); left without battles. 248 missions planned.

## Unraid template for the container (2026-11-06, evening)

Operator's request: run `ffbe` as a normal Unraid Docker-tab container (GUI control, survives reboots and the Appdata Backup plugin) instead of from `docker compose up` in the terminal.

- Compose-started containers show in the Docker tab but aren't dockerMan's: no Autostart, no Edit, and the backup plugin's stop/start doesn't treat them like apps. Fix: `ios-server/unraid/my-ffbe.xml`, a dockerMan template (copied to `/boot/config/plugins/dockerMan/templates-user/`) for the same container: image `ffbe-ios-server:local` (still built with `docker compose build`), bridge network, `/dev/net/tun` as a Device, ExtraParams `--hostname=ffbe --cap-add=NET_ADMIN --restart=unless-stopped --log-opt max-size=20m --log-opt max-file=3` (the restart policy matters: entrypoint.sh exits when Tailscale or the server dies so both restart together), the three folders under `/mnt/user/appdata/ffbe`, and every environment variable from `docker-compose.yml` with its compose comment as the description (generated from the compose file; TS_AUTHKEY masked and empty).
- A local image needs an explicit tag in a template (Unraid forum: untagged names become `:latest` and Unraid tries to pull); `:local` is explicit. Its update status shows "not available", which is cosmetic.
- Steps (README "Unraid: run it from the Docker tab"): build, `docker compose down`, copy the template, Add Container from the user template, Apply, Autostart on. Updating: git reset + `docker compose build`, then Edit → Apply. Removal notes added to "Removing everything".
- Not tried on his server yet.

## Story text keys, expeditions (2026-11-07)

Operator's reports: two chapter 1 lines shown as `MAP_TEXT_111020301210134` / `...210135`; expeditions "incredibly sparse" (the same relic expedition again and again, 10 seconds each); the Farplane monument always replays the first Farplane scene and sends him back to Mitra (not fixed yet, see the end).

- **Missing story lines** (`story_text.py`). A scene pack (`common_lang/sd/event/<nn>/Ver<v>_<scene>.cpk`) holds the script (`<scene>_event.bin`, a line is named by `?? 08 00 04` + 4-byte id) and its lines (`_event_text.txt` `id,text`; `_event_text_sg.txt` `id^...` 9 language columns). A missing id is drawn as `MAP_TEXT_<scene><id>`. A scan of all 1,121 shipped scenes (`/root/ev`, scratch) found three, all the same shape: the script has two copies of a passage (two branches), the second copy was renumbered, and the new ids never reached the English text. The commands between lines are byte-identical in both copies, so each missing line is the line at the same place in the first copy: 111020301 210134 = 210096, 210135 = 210023; 121020102 210005 = 210015 (the pack has 210015, unreferenced, exactly where 210005 is spoken); 18301010101 210016-23 = 210014, 210015, 210008-13. No transcript found to check against. The server rebuilds those packs with the lines added (header/TOC cells patched in place, files re-laid at the pack's 2048 alignment, ETOC moved to the end; verified by re-reading every file) and `ios_tables.py` gives them new file versions in `F_RESOURCE_MAP_VERSION_MST_LOCALIZE` (`OzT5lSz3` + 1001; the table itself is advertised +3000 above the sound bump so phones fetch it). `F_RESOURCE_MAP_CHECKSUM_MST` is left alone: its sizes already disagree with many shipped packs. `EXVIUS_STORY_TEXT_FIX=0` turns it off. CRILAYLA decompression for compressed CPK entries: `devtools/crilayla.py`.
- **Expeditions** (`exvius_actions_expedition.py`). The old code dealt `F_EXPEDITION_MST` in id order, three at a time, so the first list was the tutorial chain (Relic Hunting Craze I/II/III, difficulty row 21 = 10 s) all at once, finishing I added a second II, and the next refresh came 24 h later with ids 4-6. Now, as in Global (wiki "Expedition", "Basic Information"): the tutorial chain one at a time (`sZ4964o7` = next), then `EXPEDITION_MAX_AVAILABLE` (3) regular offers (`sx4kyW0i` 2, ranks D-S, 3-24 h) dealt at random from all regular expeditions (Global's weights weren't recovered: uniform), the free refresh once a day at the daily reset (04:00 UTC, the same anchor as the attempt limits), paid refresh any time; plus, outside the three, the day's supercite expeditions (`sx4kyW0i` 1, weekdays in `5BsSnrD4`: red/blue and violet/yellow Mon-Thu, orange/white and green/black Fri-Mon) and the Moogle Cave (`sx4kyW0i` 3, 3 a day). Old saves are re-dealt once (`offers` = 2): running jobs stay, a tutorial under way continues, duplicates are dropped. Tests in `source/exvius/test_actions_expedition.py` (the panel and endpoint-coverage failures there predate this).
- **Fixed the same day: "a loading error has occurred" entering Port City Lodin.** Lodin's arrival downloads 111020301, and the first rebuilt pack (`BUILDER` 1, Ver1048) kept the header's `FileSize` (102400) and `TotalDataSize` at the original's; the log shows the download right before the error. The CRI header's `FileSize` must equal the pack's size and `TotalDataSize` its `ContentSize`. `BUILDER` 2 sets both (new version Ver1049, so the phone fetches it again). `ios_art.py`'s Vortex pack had the same gap (it never set `FileSize`), also fixed (`BUILDER` 2, rebuilt at startup), which may be why its tiles weren't confirmed.
- **Shop product names** (`ios_texts.py`, GENERATION 3). Operator's screenshot: the VIP Shop's vision card "Metal Gigantuar's Here!" (product 940000012, reward `27:900020101:1`) listed as `MST_NVSHOP_PRODUCT_NAME_940000012` / `..._LONG_DES_...`. Every exchange shop product is this server's own (`exvius_shop_catalogue.py`), and the client prints `F_TEXT_NV_SHOP_PRODUCT_*` for at least some reward kinds. The three tables (`s5K4EzVy`/`spxNTzFX`, `39tuQBKk`/`bLUjnqGk`, `jhDV9jT6`/`uaCuMXaq`) are now patched: all 2,033 products named after their rewards (units, items, equipment, materia, key items, vision cards, recipes "<name> Recipe"), replacing the shipped text where the ids collide (900000xxx was other products in the shipped tables).
- **Two freezes, not fixed yet** (2026-11-07, waiting on the log): tapping Details on that vision card product (`NVShopItemListScene_sg::pushItemDetailScene` opens `VisionCardDetailScene` with `GameUtils::createVisionCardInfo`); and talking for the first time to a woman NPC in Port City Lodin (town 1103, whose town quests are 1003004 "Coexistence" and 1003005): music keeps playing, nothing responds. Suspects: a file the scene needs that the phone can't get (CDN 404), or a reply the client waits on.
- **Farplane monument: not fixed.** What's known: Mitra's monument (`F_TELEPO_MST` 110199 "異界の石碑") always asks "Touch the Farplane monument?", sets 61110109 and moves to town 9001 (map op `59 00 05 01 <town u32> 01`). The first Farplane scene is event 211020101 (resource 390001001): its default page plays the intro, sets 10005001 (`0a 00 05 00 <id u24> <value>`) and moves to town 1101 (Mitra); a second page (10009001 on, 10009002 off) sets 10009002. `F_MAP_EXT_RESOURCE_MST` gives town 9001 that scene while 10004001 is on and 10005001 off (Mitra's arrival scene 111020101 sets 10004001), the same pattern as Mitra's own arrival scene (ignored once 10004003 is set). So the phone apparently sees 10005001 off when it enters the Farplane, although `serve_switches` grants 10005001 (the Vortex function switch) to every save. Waiting on the server log of one monument touch.

## Starting a fresh session

Paste this as the first message of a new session:

> I'm continuing my Exvius Offline iPhone project. Add CreamySeaman6/exvius-offline-apple to this session with push access, clone it, check out `ios-server`, and read `ios-server/HANDOFF.md` (Current state first, then the dated sections as needed). Ground rules are in the handoff: push fixes to `ios-server`, add a short dated section to HANDOFF.md for anything you change, keep README's settings and removal sections current, ask me questions in plain text, plain direct communication, no suggestions to send anything upstream, keep side tasks to a minimum. Once you've read it, tell me in a few lines that you're up to speed, then wait for what I report from the phone.


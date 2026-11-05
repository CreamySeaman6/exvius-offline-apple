# Handoff: Exvius Offline on the iPhone

Notes for a new Claude session picking up this work. Last updated 2026-11-05.

## The goal

Play Final Fantasy Brave Exvius on an iPhone, offline from Square Enix/gumi, using this fork of Exvius Offline.

The approach:

- The game server from this repo (`source/server/`) runs in Docker (developed on an Unraid NAS).
- The **stock, unmodified iOS app** connects to it, installed from App Store → Purchased. Tested: build 1167, version string `ver.9100`, on an iPhone 17 Pro (`iPhone18,2`) running iOS 27.0.1.
- Tailscale routes the phone to the server from anywhere.

A decrypted, re-signed IPA is the fallback if a client-side change is ever needed.

Also done and working on the server side: a weekly summon rotation. Standard, Rare and other permanent banners are always shown. Release sets rotate every Sunday at 10 PM Eastern. The first week opens with Noctis's December 2016 debut banner.

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

Either push to GitHub (the server machine runs `git pull origin ios-server`), or build a git bundle, send it as a file, and have it pulled on the server machine:

```bash
cd FFBE_DIR/repo/ios-server
git pull FFBE_DIR/exvius-ios-server.bundle ios-server && docker compose build && docker compose up -d
```

Build the bundle relative to `main` (`git bundle create X.bundle origin/main..refs/heads/ios-server`) unless you know exactly which commit the other side has; a bundle based on a commit it lacks fails with "Repository lacks these prerequisite commits". Use `refs/heads/ios-server`, because plain `ios-server` is ambiguous with the folder name.

### Commits

- Author: the repo owner's identity, as in the existing `ios-server` commits.
- `source/server/capture_server.py` and `gacha_archive.py` use **CRLF** line endings. Preserve them; edit with a byte-level replace if needed.

## What the iPhone stack is

`ios-server/`:

- `Dockerfile`, `docker-compose.yml`: two containers, a Tailscale sidecar plus `server`, which uses `network_mode: service:tailscale`.
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

## Open problem: no music in some scenes (2026-11-05)

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
- Home banners (marquee): `replay_notices.marquee_entries` picks this week's dated Vortex events (newest first, max 6) and `ffbe_banner.banner_selection` serves them instead of the era table. Art = the event's original wiki banner already used for its Vortex tile (`event_art.json`, all 626 dated events covered, 640x240), served from `en/sd/area/<file>`; the row URL ends in `HomeBanner_<7000000+area>.png` and `capture_server` maps that name back to the art. iPhone turns the strip on with `MARQUEE_FLAG=1` (serve.py, compose); the engine default stays 0 (upstream's Android home has no marquee). Not yet seen on the phone: the marquee code path has never run on a device, so a home-screen crash after this change means `MARQUEE_FLAG=0`.
- Not gated, by the operator's choice (2026-11-05): 7★ awakening (Global mid-2018), NV awakening rules and old units' later enhancements stay available ("a little edge"). The final patch's new-player login ladder is not gated either. Don't gate these without asking.

## Next steps, in order

1. Confirm the Shop bundle names now show.
2. Confirm Vortex tile art and the Enhance tab (see "Vortex" above), and that the Vortex shows this week's events.
3. Confirm the replay on the phone: this week shows only the Noctis set plus permanent summons, Rare Summon rates list early units only, and the News board shows a "This week" notice that opens. From the week of Dec 20, 2026 the home banner strip should show event banners.
(Battle music: confirmed working by the operator on 2026-11-05.)

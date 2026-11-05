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

## Open problem: Vortex crash (2026-11-05)

Tapping Vortex crashes the app right after `NAVIGATION > Current Scene=GateEntryScene`, with no further client log lines and no server request. `GateEntryScene::initialize` (GL `0x2195578`) reads `DefineMst OTHER_WORLD_TOWN_ID` (9001), looks up the town in `TownMstList`, then requests the town's map resource and changes to scene 604 (`GateScene`). Town 9001 is present in the shipped `F_TOWN_MST` (Ver64), and the `area_vw*` packs were downloaded. Next: the iPhone's own crash report (`Settings → Privacy & Security → Analytics & Improvements → Analytics Data`, the `.ips` from the crash) for the faulting frame, and compare with the GateScene hooks in `menu_assets.js`.

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

## Next steps, in order

1. Confirm the Shop bundle names now show.
2. Vortex crash: get the `.ips` crash report (see above).
3. Confirm whether the missing battle music is just the download queue. The 2026-11-05 server log showed `Ver1309_la301_dungeon_temple1.acb` fetched on entering the Earth Shrine, so map BGM downloads on demand.

# Exvius Offline for iPhone

Play **Final Fantasy Brave Exvius** (Global) on an iPhone again, with the **unmodified App Store app**, against a game server you run yourself.

This folder runs the [Exvius Offline](https://github.com/Elvlin/exvius-offline) game engine as a server in Docker. The iPhone app thinks it's talking to the original servers. Nothing on the phone is modified apart from trusting one private certificate.

It also adds a **historical replay**: summons, Vortex events and shops follow Global's own release history, starting at Noctis's December 2016 banner and moving three historical weeks per real week (two per week from the first Neo Vision banner in August 2020). The permanent summons only draw units that had come out by then, holiday banners arrive the week before each real holiday, and a "This week" notice on the News board lists what just arrived, and the home screen banners show that week's events. The week changes on Sunday at 10 PM US Eastern by default. With the replay off, banners rotate randomly every week instead.

> Tested with the Global app at build 1167 (`ver.9100`) on an iPhone 17 Pro running iOS 27, with the server on an Unraid NAS. The same Docker setup is meant to run on any computer that runs Docker.

---

## What you need

- **The app on your iPhone.** FFBE is no longer in the App Store, but if your Apple account ever downloaded it, it's under **App Store → your account → Purchased**.
- **A computer to run the server**, on whenever you want to play. The default below is a Windows, Mac or Linux PC with **Docker Desktop**. A NAS or home server works the same way (see [Other hosts](#other-hosts)).
- **About 17 GB of free disk space** during setup, 15 GB afterwards.
- **A free [Tailscale](https://tailscale.com) account.** Tailscale connects the phone to the server, at home or away, without opening anything on your router.

## How it works

```
iPhone (stock FFBE app, Tailscale on)
   │  "where is v900-lapis.gumi.sg?"
   ▼
Tailscale split DNS ── only gumi.sg / exvius.com questions ──▶  ffbe (your server's own Tailscale address)
   │                                                               ├─ DNS: answers gumi.sg / exvius.com with its own address
   │  HTTPS to v900-lapis.gumi.sg                                  ├─ HTTPS 443: game API and game file downloads
   └──────────────────────────────────────────────────────────▶  └─ HTTP 80: the certificate profile for the phone
```

- **Its own Tailscale address.** A Tailscale container joins your tailnet as a machine called `ffbe`, and the game server shares its network. Nothing listens on your computer's own ports, so it can't clash with anything else you run.
- **A tiny DNS responder.** It answers only `gumi.sg` and `exvius.com` names. A Tailscale split-DNS rule sends the phone's lookups for those names to it. Nothing else about your phone's or tailnet's DNS changes.
- **A private certificate** that can only vouch for `gumi.sg` and `exvius.com` (an X.509 name constraint). You install it on the phone once, and it can't be used for any other site.
- **The game data** (about 14.6 GB) is downloaded from the Exvius Offline GitHub releases during setup.

Everything the stack creates lives in one folder (`FFBE_DIR`). [Removing everything](#removing-everything) is at the end.

---

## Setup

The commands are the same on Windows (PowerShell), macOS (Terminal) and Linux unless noted.

### 1. Install Docker and get the files

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it. On Linux, Docker Engine with the Compose plugin also works.
2. Make a folder for everything, for example `exvius` in your home folder, and download this repository into it as `repo`:

   ```bash
   mkdir exvius
   cd exvius
   git clone --depth 1 -b ios-server https://github.com/CreamySeaman6/exvius-offline-apple.git repo
   cd repo/ios-server
   ```

   If you don't have `git`, download the `ios-server` branch as a ZIP from GitHub and unzip it so that the files are in `exvius/repo`.

All the remaining commands run from `exvius/repo/ios-server`.

### 2. Tailscale

1. Create a Tailscale account, then install the **Tailscale** app on your iPhone and sign in with the same account.
2. In the [Tailscale admin console](https://login.tailscale.com/admin), go to **Settings → Keys → Generate auth key**. Leave it **not** reusable and **not** ephemeral. Copy the key.
3. Create the settings file and paste the key after `TS_AUTHKEY=`:

   ```bash
   cp .env.example .env          # Windows PowerShell: copy .env.example .env
   nano .env                     # Windows: notepad .env    macOS: open -e .env
   ```

   Leave `FFBE_DIR=../..` as it is to keep the data in your `exvius` folder, or set any other path.

The key is only used on the first start. It stays on your computer in `.env`, which git ignores, so it's never uploaded anywhere.

### 3. Build and download the game data

```bash
docker compose build
docker compose run --rm server fetch-data
```

`fetch-data` downloads about **14.6 GB**, checks every pack, unpacks it and deletes the download. If it stops for any reason, run it again; it picks up where it left off.

This also starts the Tailscale container for the first time, so a machine called `ffbe` appears in your Tailscale admin console.

### 4. Start the server

```bash
docker compose up -d
docker compose logs -f server
```

Wait for a line like:

```
[ios-server] ready. Certificate profile for the phone: http://100.x.y.z/ca.mobileconfig
```

Note that `100.x.y.z` address, then press Ctrl+C to stop watching the logs. The server keeps running in the background.

### 5. Tailscale admin console

1. **Machines → ffbe → ⋯ → Disable key expiry.** Otherwise the server drops off your tailnet after about six months.
2. **DNS → Nameservers → Add nameserver → Custom.**
   - Nameserver: the `100.x.y.z` address from step 4.
   - Turn on **Restrict to domain** and enter `gumi.sg`.
   - Save.
3. Add a second nameserver entry the same way, with the same address, restricted to `exvius.com`. It covers the game's notice pages: optional, but it makes those requests fail fast instead of hanging.

If you use custom Tailscale access rules, the phone must be allowed to reach `ffbe` on TCP 80 and 443 and UDP 53. The default policy already allows that.

### 6. iPhone: trust the certificate

1. In the Tailscale app, make sure you're connected and **Use Tailscale DNS settings** is on (it is by default).
2. In **Safari**, open `http://100.x.y.z/ca.mobileconfig` and tap **Allow**.
3. Open **Settings → Profile Downloaded → Install.** It's listed as "Exvius Offline server" and says "Not Verified". That's normal for a private certificate.
4. Open **Settings → General → About → Certificate Trust Settings** and turn on **Exvius Offline Root**. This step is easy to miss, and the game won't connect without it.
5. Test it in Safari: open `https://v900-lapis.gumi.sg/__exvius/hello`. A page saying **"Reachable. You can open the game."**, with no warning, means DNS and the certificate both work.

### 7. Play

1. Open the game. The first launch downloads the game's data from your server; keep the app open until it finishes.
2. After you've logged in once, **close the game fully and open it again** (swipe it away in the app switcher). The server's patched download lists only reach the phone during login, after the game has already decided what to fetch up front, so the second launch is the one that gets them. Without it, the first battle can crash.
3. Music downloads in the background. Until a track has arrived, that scene plays without music; sound effects still work. Leaving the game open on a menu for 10–15 minutes lets it catch up.

---

## Other hosts

The stack is plain Docker Compose, so it runs anywhere Docker does. A machine that's always on (a NAS or home server) means you can play any time without your PC being on.

- **Linux server:** same steps. Install Docker Engine and the Compose plugin.
- **Unraid:** install the **Docker Compose Manager** plugin from the Apps tab, then follow the same steps in the Unraid terminal. A good `FFBE_DIR` is `/mnt/user/appdata/ffbe`, with the repo cloned to `/mnt/user/appdata/ffbe/repo`.
- **Synology and other NAS systems:** need Docker (Container Manager) and SSH access to run `docker compose`. The Tailscale container needs `/dev/net/tun`, which some NAS systems only provide after enabling it.

---

## If it doesn't work

Watch the server while you open the game:

```bash
docker compose logs -f server
```

| What you see | What it means |
| --- | --- |
| Nothing at all when the game starts | The phone isn't reaching the server. Re-check step 5, and that the hello page in step 6 loads. |
| `TLS handshake failed from 100.…` | The phone doesn't trust the certificate. Check **Certificate Trust Settings** (step 6.4). |
| `OK POST …` lines | The game is talking to the server. |
| `CDN GET … -> 404` | The game asked for a file the server doesn't have. A few of these are normal; a long run of them during the first download is worth reporting. |
| The game crashes when the first battle starts | Close it fully and open it again (step 7.2). |
| A scene has no music | That track hasn't downloaded yet (step 7.3). |

**Logs from the game itself.** iOS hides apps' logs, so the server asks the game to upload its own error log. Each upload is saved in `FFBE_DIR/server/client-reports/`, and the server log shows a `CLIENT REPORT` line when one arrives. The game uploads at its next launch, so the newest report covers the session before it. To read one:

```bash
pip install cryptography
python3 devtools/decode_reports.py FFBE_DIR/server/client-reports/<file>.txt
```

The server also keeps every request it received for three days, in `FFBE_DIR/server/requests/`.

---

## Everyday use

| Task | Command |
| --- | --- |
| See this week's banners | `docker compose exec server python3 /app/ffbe.py rotation` |
| See the next four weeks | `docker compose exec server python3 /app/ffbe.py rotation 4` |
| Restart the replay from its start date | delete `FFBE_DIR/server/state/replay.json`, then `docker compose restart server` |
| Show the save's status | `docker compose exec server python3 /app/ffbe.py status` |
| Restart | `docker compose restart server` |
| Logs | `docker compose logs -f server` |
| Stop | `docker compose down` |
| Start the game over | `docker compose exec server python3 /app/ffbe.py new-game --yes` (the old save is backed up to `server/state/backups/`) |

**Your save** is in `FFBE_DIR/server/state/`. Back up that folder.

**Certificates** are in `FFBE_DIR/server/certs/`. They're made on your computer the first time the server starts and never leave it.

- The root certificate on your phone lasts ten years.
- The server certificate lasts about 13 months and renews itself; the container restarts once to do it.
- If you delete the `certs` folder, install the phone profile again (step 6).

**Updating** to a newer version of this branch:

```bash
git pull
docker compose build
docker compose run --rm server fetch-data   # only downloads data packs that changed
docker compose up -d
```

## Settings

Settings are environment variables in `docker-compose.yml`. After changing one, run `docker compose up -d`.

**Historical replay**

| Setting | What it controls |
| --- | --- |
| `EXVIUS_REPLAY` | `1` (default) follows Global's history: each week shows the summon sets released in that week's slice of history, the Vortex events that launched with them, and permanent summons and exchange shops limited to units released by then (NV EXVIUS appears with the NV era). `0` uses the random weekly rotation below. Needs `EXVIUS_SUMMON_ROTATION=1`. |
| `EXVIUS_REPLAY_START` | Where history starts in your first replay week. Default `2016-12-16` (Noctis). |
| `EXVIUS_REPLAY_PACE` | Historical weeks per real week, with optional changes by date. Default `3,2@2020-08-20`: three, then two from Global's first Neo Vision banner. |
| `EXVIUS_REPLAY_NV_ERA` | When NV EXVIUS appears among the permanent summons. Default `2020-08-20`. |
| `EXVIUS_REPLAY_NOTICES` | `1` (default) adds a "This week" notice to the News board for each replay week, listing its summons and Vortex events. `EXVIUS_REPLAY_NOTICE_WEEKS` (default `8`) is how many weeks stay listed. |
| `EXVIUS_NOTICE_ART` | `1` (default) lets the notice pages show unit sprites: the server downloads each unit's sprite from the FFBE wiki the first time a notice needs it and keeps it in `FFBE_DIR/server/ios-cache/notice-art/` (delete that folder to clear it). Summon and event banners come from your own data. `0` shows names only. |
| `EXVIUS_REPLAY_FULL_POOL` | Summons paid only with a ticket you can't buy over and over (the Early Bird's Guaranteed NV Summon Ticket, the once-only SP NV tickets, event and login tickets) ignore the replay's unit limit, so a held ticket is a real one-off chance at any unit, NV included. Tickets the Shop sells without limit keep the limit. This setting names more banners by id (default `9200107,9200108`). Ticket-paid banners appear on the summon screen whenever you hold the ticket. |
| `EXVIUS_REPLAY_MARQUEE` | `1` (default) fills the home screen's banner strip with the original banners of this week's Vortex events (the same art as the Vortex tiles, at most `EXVIUS_REPLAY_MARQUEE_MAX`, default `6`). Needs `MARQUEE_FLAG=1`, which turns the strip on; set `MARQUEE_FLAG` to `0` if the home screen misbehaves. Weeks with no dated events show no banners. |

Your first replay week is recorded in `FFBE_DIR/server/state/replay.json`. Changing the pace later re-times the whole replay from that week. Units you already own stay in your save. Holiday sets come out of the timeline and appear in the week before each real holiday and the holiday's own week. Each holiday brings the next original year that hasn't been shown (if it's less than a year ahead of history), plus any years the replay went past, older ones first. When history runs out, the random rotation takes over with every unit.

**Earned Lapis**

The original game's Lapis income assumed you'd buy Lapis. These settings raise what you earn by playing (Shop purchases are never touched). With the defaults, a full day of daily quests pays 975 Lapis, and every week brings a 10+1's worth of summon tickets.

| Setting | What it controls |
| --- | --- |
| `EXVIUS_LAPIS_MULTIPLIER` | Multiplies every Lapis amount earned by playing: mission challenges, event repeats, rank-ups, login and catch-up mails, quests. Default `1.5`; `1` is the stock game. |
| `EXVIUS_DAILY_QUEST_LAPIS` | Lapis paid by each daily quest (before the multiplier). Default `150`. `0` keeps the old gil/Lapis mix. |
| `EXVIUS_DAILY_ALL_BONUS` | Extra Lapis for finishing all of a day's daily quests (before the multiplier). Default `200`. |
| `EXVIUS_WEEKLY_GIFT` | Mailed once per summon week, as `kind:id:count` items. Default `23:50:10,23:70:1`: 10 Rare Summon Tickets and a Guaranteed Ticket (4★/5★/NV), usable with any banner's Ticket Summon button. `""` turns it off. |

**Other players**

| Setting | What it controls |
| --- | --- |
| `EXVIUS_PLAYERS` | How many made-up players exist (default `200`, gaming and anime handles). Find them under Friend > Suggestions (a new set daily) or search by id (910000001 and up). Friend requests are accepted at once, and Remove works. Each player lends a different unit every week, only from units released by the replay's point in history. `0` turns them off. |
| `EXVIUS_START_FRIENDS` | How many of them are already your friends in a new save (default `15`, enough for the "send gifts to 15 friends" daily quest). |
| `EXVIUS_PLAYER_SUGGESTIONS` | How many suggestions the Friend screen shows each day (default `10`). |

Your own hand-picked companions still come from `source/server/friends.yaml`.

**Summon rotation**

| Setting | What it controls |
| --- | --- |
| `EXVIUS_SUMMON_ROTATION` | `1` rotates banners weekly; `0` shows every banner at once. |
| `EXVIUS_ROTATION_HOLIDAYS` | `1` (default) keeps holiday summon sets (Christmas, Halloween, Valentine's Day, Easter) for the week before that holiday and the holiday's own week. Without the replay, it's one original year at a time, oldest first, so the newest and strongest holiday units come later. `0` mixes them into the normal pool. |
| `EXVIUS_VORTEX_ROTATION` | `1` (default) makes the Vortex follow the summon rotation: the permanent dungeons are always open, plus the events that originally launched alongside this week's summon sets, so an event's featured units, coins and tickets line up with the banners you can pull. `0` opens all 757 archived events at once. |
| `EXVIUS_VORTEX_EXTRA` | How many undated recurring Vortex events (Boss Rush, Cactuar Dunes, Challenge of the Brave, …) open each week. Default `2`. |
| `EXVIUS_ROTATION_TZ` | Time zone of the weekly change. Default `America/New_York`. |
| `EXVIUS_ROTATION_DAY` | Day of the change. 0 is Monday, 6 is Sunday. |
| `EXVIUS_ROTATION_HOUR` | Hour of the change, in 24-hour time. |
| `EXVIUS_ROTATION_SPECIAL` | How many sets with step-up, ticket or select banners appear each week. |
| `EXVIUS_ROTATION_FEATURED` | How many other featured sets appear each week. |
| `EXVIUS_ROTATION_FIRST_WEEK` | Without the replay: release sets for the first week, by release date. Default `2016-12-16` (Noctis). Later weeks are random, and nothing repeats until the whole pool has cycled. |

**Downloads and sound**

| Setting | What it controls |
| --- | --- |
| `EXVIUS_EARLY_RESOURCES` | Resource packs downloaded up front instead of in the background. The default, `resources_common.cpk,resources.cpk`, is what the first battle needs (about 50 MB). `all` downloads everything up front in one long download; `0` turns it off. |
| `EXVIUS_IOS_HCA_PLAIN` | `1` (default) removes the sound banks' HCA cipher, which is what makes the music play cleanly on the iPhone. |
| `EXVIUS_IOS_SOUND_REFETCH` | Set it to any new value to make the phone download every sound bank again. |
| `EXVIUS_IOS_TEXT` | `1` (default) adds the English names the stock app is missing, such as the Shop's local bundles and the special summon tickets. `0` turns it off. |
| `ANNIVERSARY_TICKET` | `0` (default here) stops the free 8th-Anniversary 10+1 ticket the engine otherwise mails every day. `1` turns it back on. Tickets you already received stay. |
| `EXVIUS_LAPIS_SHOP_EXCLUDE` | Products left out of the exchange shops that sell for Lapis, as `kind:id` pairs. The default, `10:900020401`, removes King Metal Minituars, which otherwise cost 3 Lapis each. Empty puts them back. |
| `EXVIUS_IOS_BANNER_FIT` | `1` (default) pads summon detail art to the shape of the frame the iPhone draws it in, so taller or wider images aren't squashed (the Android build does this with a hook). The sides are filled with a blurred, darkened copy of the art. Needs Pillow, which the image installs. Cached in `FFBE_DIR/server/ios-cache/banner-fit/`. |
| `EXVIUS_IOS_BANNER_FIT_NAMES` | `1` (iPhone default) names each summon detail image `<name>-fit1.png` in the summon tables. The phone keeps every banner image it has downloaded and never asks again, so without a new name it keeps the squashed copy. The server maps the name back to the real file. |
| `EXVIUS_BANNER_DEALS` | `1` (default) pays the extras printed on summon banner art that the banner data left out: free Trust Moogles with every 10+1, bonus coins and tickets, and from October 2020 a guaranteed 5★/NV unit plus a Summon Coin with every 11 summon. 107 banners, listed in `source/server/banner_deals.json`. `0` turns it off. |
| `EXVIUS_IOS_VORTEX_ART` | `1` (default) builds the Vortex banner pack the iPhone needs, so event tiles show their art (and the Enhance tab doesn't crash). It's built when the server starts and cached in `FFBE_DIR/server/ios-cache/` (about 240 MB). |

If you have original **iOS** sound banks, put them in `FFBE_DIR/data/native/common_lang/sound/<bgm or se>/ios/`, keeping their `Ver<N>_` file names. The server sends those as they are, ahead of the Android ones.

---

## How it was made to work

The preserved game data comes from the Android version, and the iPhone app was never meant to talk to anything but the real servers. These are the problems that came up, and what the server does about each. The details are in the code comments in [`source/server/`](../source/server/).

1. **Reaching the server.** The app has its server addresses built in, so the server has to be found under those names. A DNS responder answers only the game's domains, and Tailscale split DNS sends only those questions to it. The app accepts the private certificate once it's trusted in **Certificate Trust Settings**. Installing the profile alone isn't enough.
2. **Data tables failing to load (`MST_LOAD_FAILURE`).** The stock app ships with data tables of its own, and mixing them with the server's fails. The server advertises every table at its real version plus 200000 (`EXVIUS_TABLE_VERSION_OFFSET`), so the app replaces all of its own. Then the iPhone's decoder rejected tables that had been rebuilt with Windows (CRLF) line endings, which Android tolerates; the server converts them to LF as it sends them.
3. **Missing sound files.** The app asks for `…/sound/…/ios/…`, but the preserved data only has `…/android/…`. The bank format is the same on both, so the server answers iOS sound requests from the Android folder.
4. **Crash entering the first battle.** The opening battle loads two layout files from two resource packs that the game normally leaves near the end of its background download, so the battle started before they arrived. The server marks those packs for the up-front download (`ios_tables.py`). The phone only gets the changed list at login, which is why the second launch matters.
5. **Garbled music and sound effects.** Every Android sound bank uses CRI HCA cipher type 1, a fixed keyless scrambling table. The iPhone played the banks as loud noise, the same noise a decoder makes when it skips that table. The server removes the cipher as it sends each bank (`sound_compat.py`): it decrypts every audio frame, marks the file unencrypted and rewrites the checksums. The audio and the file size stay exactly the same. Because the phone never re-downloads a file it already has, the server also gives every sound file a new version number whenever these settings change.
6. **Names showing as codes.** The Android build fills in some names itself, with code hooks inside the app (for example the Shop's local bundles, `MST_BUNDLE_NAME_990000107`). The stock iPhone app has no hooks, so it showed the raw keys. The server adds those names to the game's own text tables instead, and gives the changed tables new versions so the phone downloads them (`ios_texts.py`). The same goes for everything else the Android hooks fill in (reconstructed abilities, monster names, event mode names) and for obtainable items that never had English text, such as the SP Summon Tickets' descriptions (`ios_text_items.json`).
7. **Blank Vortex tiles, and a crash on the Enhance tab.** Each Vortex tile's picture is loaded by name from the game's mounted data packs, and the archive's event banners only existed as loose PNG files, which the Android version hands to the game with in-app code. The server now rebuilds the game's own Vortex banner pack with those pictures added, gives it a new version, and puts it in the up-front download (`ios_art.py`).
8. **Seeing what the phone is doing.** iOS hides apps' logs, so the server enables the game's own crash-report upload and saves what it sends (`client_reports.py`). Every step above was diagnosed from those reports.

The weekly summon rotation is in `source/server/gacha_rotation.py`, the historical replay in `source/server/replay.py` (unit release dates in `unit_release.json`), and the News board notices in `source/server/replay_notices.py`. The notice rows use the layout the app's own notice reader expects, read from the Android build of the game.

---

## Removing everything

1. On the computer running the server, from `exvius/repo/ios-server`:

   ```bash
   docker compose down --rmi local
   docker image rm tailscale/tailscale:stable   # skip if anything else uses this image
   ```

   Then delete the whole `exvius` folder (or your `FFBE_DIR`). That removes the game data, your save, the certificates, the Tailscale state and this copy of the repo.
2. In the Tailscale admin console:
   - **Machines → ffbe → ⋯ → Remove.**
   - **DNS:** delete the nameserver entries for `gumi.sg` and `exvius.com`.
   - **Settings → Keys:** revoke the auth key if it's still listed.
3. On the iPhone: **Settings → General → VPN & Device Management → Exvius Offline server → Remove Profile.** This also removes the trusted certificate.

Nothing else on your computer, network or tailnet is changed.

## Credits

The game engine, the preserved data and the Android app are [Exvius Offline](https://github.com/Elvlin/exvius-offline) by Elvlin. This branch adds the iPhone server around it.

# Deal banners: research and build plan

Written 2026-11-07, at the end of the session that did the research. This is the starting point for the session that builds the missing deal banners. Read all of it before writing any banner data.

Operator's request (Brando): "I swear there were more banner deals and stuff in the game than we have now. Like step up summons where you got items and discounts along the way of the step up, or a special banner that went away after you did your first 10+1 pull of the banner." Then: "If we find absolutely zero history or answers I'd be open to us using or filling in blanks with ffbe Japan history."

He wants the missing deal banners built. He's fine with them landing in release order, but thinks building by type/mechanic in large batches is probably faster. He left the call to whoever reads this; section 9 gives a recommendation.

**Caveat on what follows.** The research ran in Chrome tabs whose crawled page text is gone, since those tabs were closed. The family counts in section 5 are rough keyword classifications of about 1,682 of the 3,247 archived news pages, so expect overlap and misses. The specific banner details in section 6 were read directly from pages. Re-fetch any page before authoring from it; section 7 says how.

---

## 1. Bottom line

- The deals were real. Nearly all of them started in **2018 or later**. Global had almost no deal banners in 2016–17.
- The replay starts at 2016-12-16 and moves 3 historical weeks per real week. The operator is around late Dec 2016 to Jan 2017 of history, so **nothing is missing for the weeks he has played so far.** The first gap (early-2018 free dailies) is about 20 real weeks away. The first regular step-up (Sephiroth, 2018-05-11) is roughly 25–30 weeks away.
- The server has about 745 banners, but only about 57 are special (non-featured). Of those, 13 are step-ups.
- The summon engine already handles most deal mechanics: step-ups with per-step prices and bonuses, lap limits, once-per-player, daily and weekly limits, guarantees, boxes, coins and exchange shops. **The gap is mostly data**, roughly 250–300 deal banners from 2018–2023, plus a few engine additions (section 4).

## 2. How banners live in this server (read the code to confirm)

Banner documents are in `source/server/`. Each is a JSON object with a `banners` list, loaded by `ffbe_gacha.all_banners()`. Later documents override earlier ones by id. Load order:

| File | Count | Id block | What it is |
|---|---|---|---|
| `gacha_catalogue.json` | 273 | 11–82xxxx (mostly 80xxxx/81xxxx) | Documented Global campaigns put on the client's shipped gacha ids |
| `gacha_community.json` | 369 | 91xxxxx | Global calendar from the FFBE wiki `Summon/<year>` pages (names, dates, units, art, rate sources) |
| `gacha_named.json` | 90 | 92xxxxx, 93xxxxx, one 94xxxxx | One per unused real Global banner image in the client cache (incl. the 2023–24 NV step-ups) |
| `gacha_authored.json` | 9 | low ids (1, 9, 24, 33, 45, 150…) | Hand-curated set (e.g. 150 "40M DL Step-Up", JP-sourced) |
| `gacha_standard.json` | 8 | 45, 46, 60xxx, 70xxx, 71xxx | Evergreen FREE-tab families, merged on top when `GACHA_STANDARD=1` |

After loading, `banner_deals.apply` overlays `banner_deals.json`: 107 banners whose art advertised extras the data lacked, such as "free Trust Moogles with every 10+1", Heroes coins, and "guaranteed 5★/NV + Summon Coin with every 11 summon" from Oct 2020. It only adds; existing data wins. **Check this file before authoring a banner; its bonus may already be there.**

Release dates and the replay:
- `gacha_archive._released(b)` reads `community.release` or `release` (YYYY-MM-DD).
- `gacha_rotation.pools()` groups banners into "sets" by release date.
- `replay.py` serves every set whose date falls in this week's slice of history. **A new banner needs a correct `release` date, and the replay then surfaces it automatically.**
- `replay.pool_cutoff` limits permanent summons to units released by the end of the slice (`unit_release.json`).
- Holiday sets run near the real holiday (`gacha_rotation.HOLIDAYS`).
- `python3 replay.py --weeks 8` previews the coming weeks.

Common fields:
- `id`, `type` (`normal` / `step` / `limited` / `select` / `box` / `free` / `friend`), `name`, `detail_id`, `exe_type`
- `schedule` (`disp_order`, `banner_type`, `window`; the window is a modern serving window, not the history date)
- `art`: `banner`, `detail_banner`, `detail_extra`, `anime_file`, `anime_name` (`gacha_moogle_normal/anime`, `gacha_moogle_rare/anime`), `img_btn`
- `pool.tiers[]`: `rarity`, `rate`, `units`, optional `featured_share`
- `tab` (`limited`…), `season`, `release`, `community{release, until, limited, units, unit_ids}`
- `provenance`, `source`, `sources[]` (`url`/`file` + `sha256`), `rate_source{url, scope, authored_details}`, `rate_notice`, `notes`

Good worked examples to copy the shape from:
- `gacha_catalogue.json` 801060 (2018-06-29 5★ Type Step-Up, Attack): 3 steps, `lap_limit` 1, step 2 carries its own `pool` with the doubled rainbow rate. See section 4: the pull ignores that `pool` today.
- `gacha_authored.json` 150 (40M DL Step-Up): ticket-cost steps, `bonus_rewards` and `bonus_choice` per step, guarantees.
- `gacha_named.json` 9200001 (2024 Rhus NV Premium Step-Up): Lapis steps 1000/3000/5000…, `guarantee{rarity, count}`, item bonuses per step.

Engine fields (in `player_state.py`; `roll_gacha` is at about line 4081, purchase checks at about 4058–4130, client rows at about 4380–4430):
- `steps[]`: `cost{kind: lapis|item, amount, item_id}`, `draws`, `guarantee{rarity, count, pool, unit_id, any_of}`, `guarantee_slots`, `bonus_rewards`, `bonus_choice[{rate, rewards}]`
- `lap_limit`, `purchase_limit` (per-player total), `daily_limit`, `weekly_limit`
- `secondary_offer` (the 10+1 button: its own cost/draws/guarantee/bonus)
- `reward_pool` (an explicit list of items or units instead of tiers), `boxes` (`gacha_box.py`), `selection`, `milestone_bonus`, `ticket_group_id`

Reward shapes:
- Trust Moogle: `{"kind": 10, "id": 904000101..105, "count": 1, "affinity_points": ["50", ""]}`, plus `affinity_info` for a unit-specific moogle
- Item: `{"kind": 20, "id": <item>, "count": n}`
- Kind 23 is used for the coins/tickets in banner 150

Tests: `source/exvius/test_summon_transactions.py` had 3 failures before this work. Keep it at those 3.

New banners should go in their **own document**, for example `gacha_deals.json` loaded in `all_banners()` alongside the others, with its own id block. 95xxxxx looks free; check first, and check that `id*10 + step` (the step detail ids) still fits the client's fields. Don't hand-edit the 5–8 MB generated files.

## 3. What already exists (the ~57 special banners)

- **Step-ups (13):**
  - 801060 / 801070 / 801080 and their calendar twins 9100125–27: 2018-06-29 5★ Type Step-Ups (Attack, Magic/Tank, Support/Healer)
  - 150: 40M DL Step-Up (JP-sourced, 2019-09)
  - 9200001–6: 2023–24 NV Premium step-ups
- **Once-per-player / one-off:** 2017 Lunar New Year, 20M DL free 10+1 (Feb 2017), 200k likes, Kelsus, 1st Anniversary.
- **Free daily:** some 2020 and 2024 free daily banners, and the standard FREE-tab families.
- **Featured summons:** every week has them (e.g. the 2018-05-11 Sephiroth and 2018-05-25 Cloud banners exist, **but only as plain featured summons**; their step-ups are missing).
- **Duplicates:** catalogue and community often hold the same banner twice (e.g. 800950 and 9100120). `campaign_identity` merges them for display. A new deal banner should not create a third copy of a featured summon; it is its own banner released the same day.

Checked 2026-11-07, Oct 2017 to Jun 2018: the only non-featured banners in that window are the three 2018-06-29 step-ups. Everything below for that window is missing.

## 4. Engine gaps (code, not data)

1. **Per-step pools and rates.** `player_state.summon_pool(banner)` uses only the banner's own `pool`/`reward_pool`, so a step's or offer's `pool` key is ignored (801060 step 2 already stores a 6% rainbow pool that is never used). This is needed for "rates rise each step" (Neo Value Step-Up, Raegen's 1.5× and 5× steps, the 2018 type step-ups). Small change: let `summon_pool` take the step/offer and prefer its `pool`. The Drop Rates page (`gacha_rates.py`) uses the same helpers, so it follows automatically.
2. **Leaving limited and collab units out of a pool.** Most deal banners said "units released up to <date>, excluding limited/collab units". The replay's `pool_cutoff` handles the date part for permanent summons. A banner-level rule such as `pool_rule: {"released_by": "2018-05-10", "exclude": ["limited", "collab"]}`, resolved at load time, would save writing unit lists by hand. Limited/collab flags: see `community.limited` and `gacha_archive.COLLABORATIONS`.
3. **Re-summon.** Re-roll a 10+1 up to 9 times, then keep one result. Only 3 banners; needs a pending-result state and a confirm. Lowest priority.
4. **Real-money summons** (the Feb 2018 5★ Guaranteed Cash Summon, some re-summons). There is no store here, so a stand-in price (Lapis or a ticket) is needed. **Operator decision.**
5. **Does a once-per-player banner disappear after use?** `ffbe_gacha` sends `purchase_limit` to the client (`1ovyP04j` = `"<limit>:0"`), and `roll_gacha` refuses past it. Whether the iPhone hides the banner or only greys it out is unverified. Global hid the "first 10+1" deals. If it doesn't hide, filter used-up once-per-player banners in `gacha_archive.visible_banners`.
6. **Rate-up events** (e.g. 2017-11-24 "3× rainbow rate", a notice, not a banner) aren't modelled at all. Rates are per banner. Optional, small.

## 5. Global's deal families (rough counts from the news crawl)

| Family | ~Count | Years | Mechanic | Engine support |
|---|---|---|---|---|
| Step-Up (regular, featured) | 29 | 2018-05 → 2023 | 3–5 steps, rising price or discount, item/unit per step, 5★/featured guarantee on last step, N rounds per player | yes; rising rates need gap 1 |
| NV Fragment Step-Up | 15+ | 2021–2023 | price falls each step, guarantees like 3/2/2/2, fragment select tickets | yes (tickets as items) |
| Neo Rainbow Revolution | 11 | 2020–2022 | 3 steps, 2–4 laps per player, moogles and tickets each step | yes |
| Treasure / Fortune summon | ~64 | 2019-11 → 2022 | **one 10+1 per player**, guaranteed 5★/NV, plus coin and ticket (the "went away after your first 10+1") | yes (`purchase_limit` 1); see gap 5 |
| All / 5 / 7 Rainbow summons | 11 | 2019 → | guaranteed rainbows in the 11 | yes (guarantee count) |
| Free daily / weekly / one-off | ~94 | 2017 → 2023 | free single or 10+1 once a day for N days | yes (`daily_limit`, cost 0) |
| Value summons | 7 | | discounted 10+1, limited count | yes |
| Box summons | 6 | | fixed box, pull until empty | yes (`boxes`) |
| Revival summons | 4 | | limited to 4, coin from step 3 | yes |
| Lucky Bonus summons | 3 | | limited to 24/18, box tickets | yes |
| Premium 10+1 | 3 | | 4★+ pool plus a ticket | yes |
| Exchange summons | 6 | | coin → pick | yes (exchange shops) |
| Celebration / anniversary | ~57 | each anniversary, DL milestones | mixes of the above | per banner |
| (Re)summon | 3 | | re-roll up to 9×, some real money | gap 3 (and 4) |
| 5★ Guaranteed Cash Summon | 1 | 2018-02-14 | once per player, real money | gap 4 |
| Special Rate Up | 1 | 2018-08 | 5% rainbow, limited to 5 | yes |
| Special FFXV Ticket Summon | 1 | 2018-10 | 5 tickets → a guaranteed FFXV 5★ | yes (ticket cost) |

## 6. Specific details read from pages

- **Early history (2016–17).** Few deals, mostly already in the server:
  - one-time free 10+1 (v2.0.0, Feb 2017 = 20M DL)
  - "Once a Day Limited Summon" (Mar 2017)
  - daily free summons
  - Fan Festa daily free summon for 10 days (Nov–Dec 2017)
  - 3× rainbow rate increase (2017-11-24; a rate event, gap 6)
  - Friend Point Trust Moogle summon (Feb 2018)
- **Missing early 2018** (confirmed absent from the data):
  - Lunar New Year: 14 days of free summons (Feb 2018)
  - 5★ Guaranteed Cash Summon (2018-02-14)
  - 30M DL: 19-day free daily summon (Mar 2018)
  - "FREE DAILY SUMMON" campaigns (Apr 2018 and May 2018)
- **First Global step-up: Sephiroth, May 2018 (2018-05-11).** 5 steps at 5000 Lapis each, a bonus item/unit each step, featured 5★ guaranteed at step 5, 3 rounds per player. **The per-step bonuses are only in the banner image.**
- **Cloud step-up, 2018-05-25.** Same era and format; details in images.
- **2018-06-29 Type step-ups.** Already in the server. Its `rate_source` is a reddit maintenance post: 3 steps, first step 3000, step 2 doubled rainbow, 10% trust bonus, final 5★ guarantee; the last two prices are guessed at 5000.
- **Raegen step-up, 2018-07-13.** Discounted, 1 round per player:

  | Step | Lapis | Units | Bonus |
  |---|---|---|---|
  | 1 | 500 | 1 | 1.5× rate |
  | 2 | 1000 | 2 | Trust Moogle 5% |
  | 3 | 1500 | 4 | 5★ 30% ticket |
  | 4 | 3000 | 6 | Trust Moogle 10% |
  | 5 | 5000 | 11 | 5× rate |

  This is the "discounts along the way" format the operator remembers.
- **Special Rate Up, 2018-08.** 5% rainbow, limited to 5 pulls.
- **Special FFXV Ticket Summon, 2018-10.** 5 tickets give a guaranteed FFXV 5★.
- **NV Cyber Monday Step-Up, 2020-11-30.** 5 steps, 1 per player, Super Trust Moogle exchange tickets at steps 1–4, guaranteed NV at step 5.
- **Neo Value Step-Up.** 1 per player, 4 steps, NV rate rising each step (gap 1).
- **NV Fragment Step-Up II.** Cost falls each step, guarantees of 3/2/2/2, fragment select tickets.
- **Pool rule** on most deal banners: units added up to date X, limited/collab units excluded (gap 2).

## 7. Sources and how to fetch them

1. **Official Global news pages, through the Wayback Machine** (best source: exact costs, limits, dates).
   - Host and path: `lapis-prod-staticnews-gumi-sg.akamaized.net/prod/en/content/*`.
   - List them with the CDX API, which returned 3,247 pages covering 2017–2023:
     `https://web.archive.org/cdx/search/cdx?url=lapis-prod-staticnews-gumi-sg.akamaized.net/prod/en/content/*&output=json&fl=timestamp,original&collapse=urlkey&filter=statuscode:200`
   - Fetch a page's raw archived bytes with `https://web.archive.org/web/<timestamp>id_/<original url>`. The `id_` suffix skips the Wayback toolbar.
   - Banner and step images are linked from those pages and archived the same way. **Step bonus items are often only in the images.**
2. **FFBE wiki (exvius.fandom.com).**
   - `Summon/<year>` pages (e.g. `https://exvius.fandom.com/wiki/Summon/2018`): the calendar the community and catalogue data came from. Banner names, dates, units and art files (`static.wikia.nocookie.net/exvius_gamepedia_en/images/...`).
   - The wiki news archive: about 3,160 entries, Dec 2017 to Dec 2021.
   - `https://exvius.fandom.com/wiki/Summon`
3. **reddit r/FFBraveExvius** weekly "Global news / maintenance" posts. The catalogue's `rate_source` already cites these; good for step costs and rates when the official page isn't archived.
4. **JP history** (operator allowed it as a last resort, for gaps only).
   - Banner 150 is already JP-sourced (`region: "jp"`).
   - JP sources were **not surveyed** this session. Candidates to check: the JP official news, the JP wikis, and Global/JP comparison posts on reddit.
   - Label anything taken from JP in `notes`/`rate_notice`, the way 150 does.

Access notes from this session:
- The sandbox shell can't reach these sites (network allowlist). Use WebFetch, or the operator's Claude in Chrome (he recommended it).
- In Chrome:
  - Do Wayback fetches from a tab on a `web.archive.org` page (same origin); from the fandom tab they failed cross-origin.
  - Fetch wiki pages from a fandom tab.
  - The tool blocks returning raw page text from `javascript_tool` ("Cookie/query string data"). Write the text into the page (`document.body.innerHTML = '<pre>…</pre>'`) and read it with `get_page_text`.
  - Keep each `await` under 40 s; the call times out at 45 s.
  - Crawled text lives only in the tab's `window`, so save extracted facts somewhere durable as you go.
- **Don't commit crawled page text or images into the repo.** Commit the extracted facts, with each page's URL and timestamp in `sources`. Banner art is the exception: fetch it into the art pipeline the way the other banners' art is handled (`summon_art.json`, `banner_art_index`).

## 8. What each banner needs

For each deal banner:

1. **Date and title.** `release` (and `community.until`), and the title as Global printed it.
2. **Costs and steps.** Cost per step or offer, draws, guarantees, bonuses (items, moogles, tickets, coins), lap/purchase/daily limits.
3. **Pool.** The featured units and rates, plus the pool rule. Use gap 2's rule where the banner says "units up to X".
4. **Art.** The banner image (Wayback news image or wiki file), plus step/detail images if any.
5. **Source tracking.** `sources`, `rate_source`, and `notes` listing anything guessed or taken from JP. Follow the existing style ("Unpreserved final two prices use 5000 Lapis each").
6. **Tickets and coins.** Any new item they need must exist in the client tables, or be swapped for an existing one. Check `F_ITEM_MST` and how 150 and 9200001 do it.

## 9. Recommended plan

I recommend building **by mechanic, in large batches**, as the operator suspected. The replay surfaces banners by their `release` date whenever they're added, so the order of building doesn't change what he sees, as long as each banner is in before the replay reaches its date.

1. **Engine first:** gaps 1 (per-step pools), 2 (pool rule) and 5 (hide used-up once-per-player banners, after checking). Each is small. Add tests next to `test_summon_transactions.py`.
2. **A loader** for a new `gacha_deals.json` (own id block), plus a builder script in `ios-server/devtools/` if it helps. One template per family keeps batches consistent.
3. **Families in this order** (earliest first-appearance first, so the near-term replay is covered early):
   1. early-2018 free dailies and one-offs (~6)
   2. regular step-ups (~29, from May 2018)
   3. Treasure/Fortune (~64)
   4. free daily/weekly (~94, rest)
   5. celebration (~57)
   6. Neo Rainbow Revolution, NV Fragment step-ups, rainbow, value, box, revival, lucky, premium, exchange
   7. last: re-summon and cash summon (need operator decisions)
4. **Per batch:** fetch the sources (section 7), author, run `python3 replay.py --weeks N` over the dates, check the Drop Rates page renders (`gacha_rates.page(id)`), keep the summon tests at 3 failures, push, and add a dated HANDOFF line.

Questions to put to the operator when you reach them (plain text):
- the stand-in price for the real-money summons
- whether re-summon is worth building
- whether JP data may fill a banner whose Global page and image are both lost

"""Weekly "New this week" notices on the in-game News board, for the historical replay (replay.py).

The News button opens InformationListScene, which sends NoticeUpdateRequest (`CQ4jTm2F`) and lists the
NoticeMst rows it holds in buckets 0 and 1. A reply group fills a bucket by its tag: `tN8f0PSB` is bucket
0 (NoticeMstResponse kinds 0-5 are tN8f0PSB, R17unt2e, 3BI1xSGW, VKA5urE1, oUk10RXm, fzm3je8p). The row
fields were read from NoticeMstResponse::readParam (libgame, Android build):

    td06MKEX notice id          i4Bb9ySk tab (1-4)            1fKgZk2I icon (0-5, inform_category*.png)
    5GNraZM0 notice type        15Y3fBmF caption, JSON {"en": "..."}   w7VR6ypY priority
    1d8R5ajV display date       VjJQ51uG / m8ivD4NX start / end         o6n5aQ8C / 9miE75sp "new" start / end
    5r8HSq1N / M9ZKJY3w open start / end    DSJpb89M open description   oIra47LK page type
    1X65WPLU url (opened when page type is 1)                            QLfe23bu read-flag index
    8amsKpQ2 popup flag         I2PbiZ1f / GTESVt57 popup start / end    52ihocTI hidden flag
    7DUC49n8 movie              qo3PECw6 mission id

Dates are "YYYY-MM-DD HH:MM:SS". The read mark is kept per display-date year and read-flag index
(exvius_actions.notice_state), so each week's notice has its own index.

Each notice opens /exvius/notices/<replay week>.html on the game's own host, served by capture_server.
Off switch: EXVIUS_REPLAY_NOTICES=0. EXVIUS_REPLAY_NOTICE_WEEKS (default 8) is how many weeks stay listed.
"""
from __future__ import annotations

import html
import json
import os
from datetime import date, timedelta

TAG = 'tN8f0PSB'
NOTICE_ID_BASE = 880000
INDEX_BASE = 500
HOST = 'https://v900-lapis.gumi.sg'


def enabled() -> bool:
    import replay
    return replay.enabled() and os.environ.get('EXVIUS_REPLAY_NOTICES', '1') == '1'


def _weeks_listed() -> int:
    try:
        return max(1, int(os.environ.get('EXVIUS_REPLAY_NOTICE_WEEKS', '8')))
    except ValueError:
        return 8


def _moment(index: int):
    """A time inside replay week `index` (real time)."""
    import gacha_rotation
    import replay
    number, start, _nxt = gacha_rotation.week()
    current = number - replay.anchor_week(number, record=False)
    return start + timedelta(days=7 * (index - current), hours=1), start + timedelta(days=7 * (index - current))


_SUMMARIES: dict = {}


def week_summary(index: int) -> dict | None:
    """What arrived in replay week `index`: its real start, slice of history, summons and Vortex events.
    Cached: a week's contents never change once the replay's week 0 is fixed."""
    import replay
    key = (index, replay.anchor_week(-1, record=False), os.environ.get('EXVIUS_REPLAY_PACE', ''))
    if key not in _SUMMARIES:
        _SUMMARIES[key] = _week_summary(index)
    return _SUMMARIES[key]


def _featured_units(banner: dict) -> list[str]:
    units = [str(u) for u in ((banner.get('community') or {}).get('unit_ids') or [])]
    pool = banner.get('pool')
    if isinstance(pool, dict):
        for tier in pool.get('tiers') or []:
            units += [str(u) for u in tier.get('featured') or [] if str(u) not in units]
    return units


def _unit_name(unit_id: str) -> str:
    if 'unit_names' not in _SUMMARY_CACHE:
        names = {}
        try:
            import data_paths
            with open(os.path.join(data_paths.TEXT_DIR, 'F_TEXT_UNITS_NAME.ndjson'), encoding='utf-8') as fh:
                for line in fh:
                    row = json.loads(line)
                    if row.get('v'):
                        names[row['key'][len('MST_UNIT_NAME_'):]] = str(row['v'][0]).strip()
        except (OSError, ValueError, ImportError):
            pass
        _SUMMARY_CACHE['unit_names'] = names
    return _SUMMARY_CACHE['unit_names'].get(str(unit_id), '')


_SUMMARY_CACHE: dict = {}


def _week_summary(index: int) -> dict | None:
    import event_archive
    import gacha_rotation
    import replay
    from ffbe_gacha import all_banners
    from player_state import unit_mst
    moment, start = _moment(index)
    win = replay.window(moment)
    if win['index'] != index or index < 0:
        return None
    current = gacha_rotation.plan(all_banners(), moment)
    holiday_keys = {key for keys in current['holiday_sets'].values() for key in keys}
    summons = []
    for key, members in current['sets']:
        banners = []
        for bid in members:
            banner = current['by_id'][bid]
            units = []
            for uid in _featured_units(banner):
                name = _unit_name(uid)
                if name:
                    units.append({'id': uid, 'name': name,
                                  'rarity': str((unit_mst(uid) or {}).get('9fW0TePj') or '')})
            banners.append({'id': bid, 'name': banner.get('name', bid),
                            'art': (banner.get('art') or {}).get('banner') or '', 'units': units})
        summons.append({'released': key, 'names': [b['name'] for b in banners], 'banners': banners,
                        'holiday': key in holiday_keys})
    art = _event_art()
    events, seen = [], set()
    for row in sorted(event_archive.weekly_events(now=moment), key=lambda r: (str(r.get('release')), str(r.get('area')))):
        if row.get('group') == 'permanent' or not row.get('release'):
            continue
        key = (row['release'], row['name'])
        if key in seen:
            continue
        seen.add(key)
        events.append({'released': row['release'], 'name': row['name'],
                       'kind': str(row.get('kind') or '').split('<br>')[0], 'art': art.get(str(row.get('area')), '')})
    return {'index': index, 'start': start, 'from': win['from'], 'to': win['to'] - timedelta(days=1),
            'finished': win['finished'], 'holiday': current.get('holiday'), 'summons': summons,
            'events': events}


def _caption(summary: dict) -> str:
    names = [name.replace(' Featured Summon', '') for entry in summary['summons'] for name in entry['names']]
    head = f"{summary['start']:%b} {summary['start'].day}: "
    if summary['holiday']:
        head += f"{summary['holiday']} summons! "
    if not names:
        return head + 'This week in history'
    text = head + names[0]
    if len(names) > 1:
        text += f' and {len(names) - 1} more'
    return text


def rows() -> list[dict]:
    import gacha_rotation
    import replay
    number, _start, _nxt = gacha_rotation.week()
    current = number - replay.anchor_week(number, record=False)
    out = []
    for index in range(max(0, current - _weeks_listed() + 1), current + 1):
        summary = week_summary(index)
        if not summary:
            continue
        begin = summary['start'].strftime('%Y-%m-%d %H:%M:%S')
        new_end = (summary['start'] + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        out.append({
            'td06MKEX': str(NOTICE_ID_BASE + index), '5GNraZM0': '0', 'i4Bb9ySk': '1', '1fKgZk2I': '1',
            '15Y3fBmF': json.dumps({'en': _caption(summary)}, ensure_ascii=False), 'w7VR6ypY': str(index),
            '1d8R5ajV': begin, 'VjJQ51uG': begin, 'm8ivD4NX': '2099-12-31 23:59:59',
            'o6n5aQ8C': begin, '9miE75sp': new_end, '5r8HSq1N': begin, 'M9ZKJY3w': '2099-12-31 23:59:59',
            'DSJpb89M': '', 'oIra47LK': '1', '1X65WPLU': f'{HOST}/exvius/notices/{index}.html',
            'QLfe23bu': str(INDEX_BASE + index), '8amsKpQ2': '0', 'I2PbiZ1f': '', 'GTESVt57': '',
            '7DUC49n8': '', 'qo3PECw6': '0', '52ihocTI': '0'})
    return out


def add_rows(spec):
    """Add this replay's weekly notices to a NoticeUpdateRequest reply."""
    if not enabled():
        return spec
    try:
        notices = rows()
    except Exception as exc:  # noqa: BLE001 -- the board just stays empty
        print(f'[replay-notices] skipped ({exc})', flush=True)
        return spec
    spec = dict(spec) if isinstance(spec, dict) else {}
    spec[TAG] = list(spec.get(TAG) or []) + notices
    return spec


def _day(value: date) -> str:
    return f'{value:%b} {value.day}, {value.year}'


def page(index: str) -> str | None:
    if not enabled():
        return None
    import gacha_rotation
    import replay
    from urllib.parse import quote
    number = gacha_rotation.week()[0]
    try:
        index = int(index)
    except (ValueError, TypeError):
        return None
    if index > number - replay.anchor_week(number, record=False):
        return None  # a week that hasn't happened yet
    summary = week_summary(index)
    if not summary:
        return None

    def src(kind: str, value: str) -> str:
        if kind == 'summon':
            # The path the summon list itself uses, so the CDN finds the file by name (a bare
            # /banner/<file> has no folder for its lookup to go on and was answered 404 on the phone).
            return '/banner/en/sd/static_banner/gacha/main/' + quote(value)
        if kind == 'event':
            return '/en/sd/area/' + quote(value)
        return '/exvius/notice-art/unit/' + quote(value) + '.png'
    return render(summary, src)


# The wiki answers a file it doesn't have with a 300x171 "not found" picture instead of an error.
_PLACEHOLDER = "if(this.naturalWidth==300&&this.naturalHeight==171)this.onerror();"
_NEXT_SPRITE = ("var a=(this.dataset.alt||'').split('|').filter(Boolean);"
                "if(a.length){this.dataset.alt=a.slice(1).join('|');this.src=a[0];}"
                "else{this.onerror=null;this.style.visibility='hidden';}")


def render(summary: dict, src) -> str:
    """The notice page for one replay week. `src(kind, value)` gives each picture's URL: kind 'summon'
    (a summon's banner art file), 'event' (an event's banner file) or 'unit' (a unit id, its sprite)."""
    esc = html.escape
    start = summary['start']
    parts = ['<header class="mast">',
             '<p class="eyebrow">Brave Exvius News</p>',
             f'<h1>Week of {start:%B} {start.day}</h1>']
    if summary['finished']:
        parts.append('<p class="era">Global\'s history is complete. Summons rotate weekly now.</p>')
    else:
        parts.append(f'<p class="era"><span>Global history</span> {_day(summary["from"])} &ndash; '
                     f'{_day(summary["to"])}</p>')
    parts.append('</header>')
    if summary['holiday']:
        parts.append(f'<p class="ribbon">{esc(summary["holiday"])} summons are here this week</p>')
    parts.append('<section><h2><span>New Summons</span></h2>')
    if not summary['summons']:
        parts.append('<p class="empty">No new summons this week.</p>')
    for entry in summary['summons']:
        when = date.fromisoformat(entry['released']) if entry['released'][:1].isdigit() else None
        for banner in entry['banners']:
            parts.append('<article class="summon">')
            if banner['art']:
                parts.append(f'<img class="art" src="{esc(src("summon", banner["art"]))}" alt="" '
                             f'width="640" height="160" loading="lazy" onerror="this.style.display=\'none\'">')
            title = banner['name'].replace(' Featured Summon', '')
            parts.append(f'<div class="cap"><h3>{esc(title)}</h3>'
                         + (f'<p class="date">Originally {_day(when)}</p>' if when else '') + '</div>')
            if banner['units']:
                parts.append('<ul class="units">')
                for unit in banner['units']:
                    stars = f'{unit["rarity"]}★ base' if unit['rarity'] and unit['rarity'] != '7' else (
                        'Neo Vision' if unit['rarity'] == '7' else '')
                    # If the server can't supply the sprite, the phone tries the wiki's copies itself.
                    alt = '|'.join(sprite_urls(unit['id']))
                    parts.append(f'<li><img src="{esc(src("unit", unit["id"]))}" alt="" loading="lazy" '
                                 f'data-alt="{esc(alt)}" onerror="{_NEXT_SPRITE}" onload="{_PLACEHOLDER}"><b>{esc(unit["name"])}</b>'
                                 f'<i>{stars}</i></li>')
                parts.append('</ul>')
            parts.append('</article>')
    parts.append('</section><section><h2><span>In the Vortex</span></h2>')
    if not summary['events']:
        parts.append('<p class="empty">No new events this week. The permanent Vortex areas are open as usual.</p>')
    for event in summary['events']:
        when = date.fromisoformat(event['released'])
        parts.append('<article class="event">')
        if event['art']:
            parts.append(f'<img class="art" src="{esc(src("event", event["art"]))}" alt="{esc(event["name"])}" '
                         f'width="640" height="240" loading="lazy" onerror="this.style.display=\'none\'">')
        parts.append(f'<div class="cap"><h3>{esc(event["name"])}</h3><p class="date">'
                     + (f'{esc(event["kind"])} &middot; ' if event['kind'] else '')
                     + f'{_day(when)}</p></div></article>')
    parts.append('</section><footer>Banners and sprites are the original game art.</footer>')
    return PAGE.replace('{{BODY}}', '\n'.join(parts))


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>This Week in Exvius</title>
<style>
/* One dark look, like the game's own menus: a night-blue sheet, gold rules and gilt headings. */
:root{--night:#0d1230;--sheet:#151b42;--ink:#f3ecd9;--muted:#b4abc9;--gold:#e8c46a;--gilt:#fff1bf;
--rose:#ff9db6;--line:rgba(232,196,106,.45);color-scheme:dark;
--display:"Cinzel","Trajan Pro",Georgia,"Times New Roman",serif;--body:"Avenir Next","Segoe UI",Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}
html{background:var(--night)}
body{margin:0;background:radial-gradient(120% 60% at 50% 0%,#2a2464 0%,var(--night) 70%) fixed,var(--night);
color:var(--ink);font:16px/1.45 var(--body);padding:18px max(16px,env(safe-area-inset-right,0px)) 36px max(16px,env(safe-area-inset-left,0px))}
.mast{text-align:center;padding:4px 0 14px;border-bottom:1px solid var(--line);margin-bottom:14px}
.eyebrow{margin:0;font:600 11px/1 var(--body);letter-spacing:.28em;text-transform:uppercase;color:var(--gold)}
h1{margin:8px 0 6px;font:700 25px/1.15 var(--display);color:var(--gilt);text-wrap:balance;
text-shadow:0 1px 0 #6b4c12,0 0 18px rgba(232,196,106,.25)}
.era{margin:0;color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.era span{color:var(--gold);letter-spacing:.08em;text-transform:uppercase;font-size:11px;margin-right:6px}
.ribbon{margin:0 0 16px;padding:9px 12px;text-align:center;font:700 14px/1.3 var(--display);letter-spacing:.04em;
color:#3b0a18;background:linear-gradient(90deg,#f6a5b8,#ffd7a3,#f6a5b8);border-radius:3px}
section{display:grid;gap:14px;margin-bottom:22px}
h2{display:flex;align-items:center;gap:10px;margin:4px 0 0;font:700 15px/1 var(--display);letter-spacing:.14em;
text-transform:uppercase;color:var(--gold)}
h2::before,h2::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,transparent,var(--line))}
h2::after{background:linear-gradient(90deg,var(--line),transparent)}
article{background:var(--sheet);border:1px solid var(--line);border-radius:4px;overflow:hidden}
.art{display:block;width:100%;height:auto;background:#0a0d22}
.cap{padding:9px 12px 10px}
h3{margin:0;font:600 15px/1.3 var(--body);color:var(--ink)}
.date{margin:2px 0 0;font-size:12px;color:var(--muted)}
.units{list-style:none;margin:0;padding:4px 8px 12px;display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));gap:8px 4px}
.units li{display:grid;justify-items:center;align-content:end;text-align:center;min-width:0;
background:radial-gradient(50% 9px at 50% 72px,rgba(232,196,106,.22),transparent) no-repeat}
.units img{height:76px;width:auto;max-width:100%;object-fit:contain;image-rendering:pixelated;filter:drop-shadow(0 3px 2px rgba(0,0,0,.6))}
.units b{font:600 12px/1.2 var(--body);color:var(--gilt);margin-top:4px;overflow-wrap:anywhere}
.units i{font:normal 11px/1.2 var(--body);color:var(--muted)}
.empty{margin:0;color:var(--muted);font-size:14px;text-align:center}
footer{text-align:center;color:var(--muted);font-size:11px;letter-spacing:.06em}
</style></head><body>
{{BODY}}
</body></html>"""


# ---- Home banners (the marquee on the home screen) ----------------------------------------------------
# In replay mode the home banners are the original event banners of this week's Vortex events: the same
# 640x240 images (from the FFBE wiki, event_art.json) the Vortex tiles use, already in the data overlay
# at en/sd/area/<file>. Each row's url ends in HomeBanner_<id>.png, the client's own cache name; the CDN
# handler maps that name back to the event art (marquee_file). Off switch: EXVIUS_REPLAY_MARQUEE=0.

MARQUEE_ID_BASE = 7000000
_MARQUEE_CACHE: dict = {}


def marquee_enabled() -> bool:
    import replay
    return replay.enabled() and os.environ.get('EXVIUS_REPLAY_MARQUEE', '1') == '1'


def _event_art() -> dict:
    if 'art' not in _MARQUEE_CACHE:
        here = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(os.path.join(here, 'event_art.json'), encoding='utf-8') as fh:
                events = json.load(fh).get('events') or {}
        except (OSError, ValueError):
            events = {}
        _MARQUEE_CACHE['art'] = {str(area): row.get('filename') for area, row in events.items()
                                 if row.get('filename')}
    return _MARQUEE_CACHE['art']


def marquee_entries() -> list[dict] | None:
    """This replay week's home banners, newest first, in banner_campaigns.json's entry shape.
    None when the replay marquee is off (the normal era selection applies)."""
    if not marquee_enabled():
        return None
    import event_archive
    import replay
    win = replay.window()
    if win['finished']:
        return None
    key = (win['index'], win['anchor'])
    if key in _MARQUEE_CACHE:
        return _MARQUEE_CACHE[key]
    try:
        limit = max(1, int(os.environ.get('EXVIUS_REPLAY_MARQUEE_MAX', '6')))
    except ValueError:
        limit = 6
    art = _event_art()
    rows = [r for r in event_archive.weekly_events() if r.get('group') != 'permanent' and r.get('release')]
    rows.sort(key=lambda r: (str(r['release']), str(r.get('area'))), reverse=True)
    out, seen = [], set()
    for row in rows:
        filename = art.get(str(row.get('area')))
        if not filename or filename in seen:
            continue
        seen.add(filename)
        banner_id = MARQUEE_ID_BASE + int(row['area'])
        out.append({'name': row['name'], 'start': row['release'],
                    'art': {'banner_id': banner_id, 'banner_version': 1, 'file': filename,
                            'store_path': f'homeMarquee/HomeBanner_{banner_id}.png'}})
        if len(out) >= limit:
            break
    _MARQUEE_CACHE[key] = out
    return out


def marquee_file(banner_id: str) -> str | None:
    """The event art (relative CDN path) behind a replay home banner's HomeBanner_<id>.png, or None."""
    try:
        area = int(banner_id) - MARQUEE_ID_BASE
    except ValueError:
        return None
    if area <= 0:
        return None
    filename = _event_art().get(str(area))
    return f'en/sd/area/{filename}' if filename else None


# ---- Unit sprites for the notice pages -----------------------------------------------------------------
# The game data keeps unit art inside packed sprite sheets, so the notice pages use the FFBE wiki's
# single-pose sprites ("Unit-<Name>-<rarity>.png", the same files the wiki shows on each unit's page).
# The server downloads one the first time a notice asks for it and keeps it in ios-cache/notice-art/.
# A unit the server can't fetch is retried after an hour; meanwhile the page has the phone try the wiki
# itself, and draws an empty space if that fails too.
# EXVIUS_NOTICE_ART=0 turns the downloads off (the pages then show names only).
WIKI_IMAGES = "https://static.wikia.nocookie.net/exvius_gamepedia_en/images"


def _art_dir() -> str:
    try:
        import ios_art
        base = ios_art.cache_dir()
    except Exception:  # noqa: BLE001
        base = os.path.join(os.environ.get("FFBE_SERVER_ROOT", "."), "ios-cache")
    path = os.path.join(base, "notice-art")
    os.makedirs(path, exist_ok=True)
    return path


def _wiki_url(filename: str) -> str:
    import hashlib
    from urllib.parse import quote
    name = filename.replace(" ", "_")
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    # format=original: without it the wiki's CDN answers WebP, which the server used to reject as "not a PNG"
    # and then gave up on the unit (why the sprites were blank on the phone, 2026-11-05).
    return f"{WIKI_IMAGES}/{digest[0]}/{digest[:2]}/{quote(name)}?format=original"


def _webp_to_png(data: bytes) -> bytes | None:
    try:
        import io
        from PIL import Image
        out = io.BytesIO()
        Image.open(io.BytesIO(data)).save(out, "PNG")
        return out.getvalue()
    except Exception:  # noqa: BLE001
        return None


def sprite_urls(unit_id: str) -> list[str]:
    """The wiki URLs that may hold this unit's sprite, best guess first."""
    from player_state import unit_mst
    unit_id = str(unit_id)
    name = _unit_name(unit_id) if unit_id.isdigit() else ''
    if not name:
        return []
    try:
        rarity = int((unit_mst(unit_id) or {}).get("9fW0TePj") or 5)
    except ValueError:
        rarity = 5
    tries = [7] if rarity >= 7 else [rarity + 1, rarity, rarity + 2, 7]
    return [_wiki_url(f"Unit-{name}-{stars}.png") for stars in dict.fromkeys(tries)]


def unit_sprite(unit_id: str) -> bytes | None:
    """PNG bytes of a unit's sprite, from the cache or (once) from the wiki."""
    import time as _time
    import urllib.request
    unit_id = str(unit_id)
    if not unit_id.isdigit():
        return None
    folder = _art_dir()
    path = os.path.join(folder, f"unit-{unit_id}.png")
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            return fh.read()
    miss = path + ".miss2"     # retried after an hour (older ".missing" markers are ignored)
    if os.path.isfile(miss) and _time.time() - os.path.getmtime(miss) < 3600:
        return None
    if os.environ.get("EXVIUS_NOTICE_ART", "1") != "1":
        return None
    urls = sprite_urls(unit_id)
    if not urls:
        return None
    name = _unit_name(unit_id)
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ExviusOffline notice art cache)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
        except Exception as exc:  # noqa: BLE001 -- try the next rarity
            print(f"NOTICE-ART unit {unit_id}: {url} -> {exc}", flush=True)
            continue
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            data = _webp_to_png(data) or data
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            with open(path, "wb") as fh:
                fh.write(data)
            return data
    with open(miss, "w", encoding="utf-8") as fh:
        fh.write(name)
    return None

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


def _week_summary(index: int) -> dict | None:
    import event_archive
    import gacha_rotation
    import replay
    from ffbe_gacha import all_banners
    moment, start = _moment(index)
    win = replay.window(moment)
    if win['index'] != index or index < 0:
        return None
    current = gacha_rotation.plan(all_banners(), moment)
    holiday_keys = {key for keys in current['holiday_sets'].values() for key in keys}
    summons = []
    for key, members in current['sets']:
        names = [current['by_id'][bid].get('name', bid) for bid in members]
        summons.append({'released': key, 'names': names, 'holiday': key in holiday_keys})
    events = []
    for row in event_archive.weekly_events(now=moment):
        if row.get('group') == 'permanent' or not row.get('release'):
            continue
        events.append((row['release'], row['name'], str(row.get('kind') or '').split('<br>')[0]))
    events = sorted(set(events))
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
    esc = html.escape
    parts = [f"<h1>Week of {summary['start']:%B} {summary['start'].day}</h1>"]
    if summary['finished']:
        parts.append('<p>The replay has reached the end of Global\'s history. Summons now rotate weekly.</p>')
    else:
        parts.append(f"<p class=sub>History: {_day(summary['from'])} to {_day(summary['to'])}</p>")
    if summary['holiday']:
        parts.append(f"<p class=tag>{esc(summary['holiday'])} summons are here this week.</p>")
    parts.append('<h2>Summons</h2>')
    if summary['summons']:
        parts.append('<ul>')
        for entry in summary['summons']:
            when = date.fromisoformat(entry['released']) if entry['released'][:1].isdigit() else None
            label = f"<span class=when>{_day(when)}</span>" if when else ''
            for name in entry['names']:
                parts.append(f'<li>{esc(name)} {label}</li>')
        parts.append('</ul>')
    else:
        parts.append('<p>No new summons this week.</p>')
    parts.append('<h2>Vortex</h2>')
    if summary['events']:
        parts.append('<ul>')
        for released, name, kind in summary['events']:
            detail = f' <span class=when>{esc(kind)}</span>' if kind else ''
            parts.append(f'<li>{esc(name)}{detail}</li>')
        parts.append('</ul>')
    else:
        parts.append('<p>No new events this week. The permanent Vortex areas are open as usual.</p>')
    body = '\n'.join(parts)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>This week</title><style>
body{{margin:0;padding:20px 22px 40px;background:#230b24;color:#fff5dc;font:17px Arial,sans-serif}}
h1{{font-size:23px;color:#ffe398;margin:0 0 6px}}h2{{font-size:19px;color:#ffe398;margin:24px 0 8px}}
.sub{{color:#d9c7a8;margin:0 0 12px}}.tag{{color:#ffb3c7;font-weight:bold}}
ul{{margin:0;padding-left:20px}}li{{margin:0 0 9px;line-height:1.4}}
.when{{display:block;color:#bfae92;font-size:14px}}</style></head><body>
{body}
</body></html>'''


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

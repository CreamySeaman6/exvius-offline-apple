"""Weekly summon rotation: permanent summons plus a few release sets that change every week.

Turned on with EXVIUS_SUMMON_ROTATION=1. When it is on, the summon screen shows:

  * every permanent summon (Standard, Rare, Premium 10+1, 5-star Guaranteed 10+1, Arena,
    EXVIUS, NV EXVIUS, 5+1 Ticket, Friend), always;
  * this week's sets. A set is every banner that shares one release date in the archive, so a
    featured banner arrives together with the step-up, ticket or select banners that launched
    beside it. Each week shows EXVIUS_ROTATION_SPECIAL sets that contain a step-up, ticket,
    select or box banner (default 1) and EXVIUS_ROTATION_FEATURED other sets (default 2).

The week changes at EXVIUS_ROTATION_DAY / EXVIUS_ROTATION_HOUR in EXVIUS_ROTATION_TZ (default
Sunday 22:00 America/New_York, daylight saving included). Each list of sets is shuffled with a
fixed seed and walked in order, so no set repeats until every set of its kind has appeared; then
the next cycle uses a fresh shuffle. The choice depends only on the date, so it needs no scheduled
job: the server works it out on every request.

EXVIUS_ROTATION_FIRST_WEEK lists release dates (set keys, e.g. 2016-12-16) to feature in the first
week the server serves summons; the week is recorded in state/summon_rotation.json. Those sets take
the first slots of their kind that week, and every later week is random as usual.

Preview from a shell:  python3 gacha_rotation.py --weeks 4
"""
from __future__ import annotations

import os
import random
from collections import OrderedDict
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None

ANCHOR = datetime(2026, 1, 4)  # a Sunday; week 0 of the rotation starts on the rotation day of this week
_LOGGED_WEEK = [None]


def enabled() -> bool:
    return os.environ.get('EXVIUS_SUMMON_ROTATION') == '1'


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def settings() -> dict:
    return {
        'tz': os.environ.get('EXVIUS_ROTATION_TZ', 'America/New_York'),
        # Python weekday numbers: Monday 0 ... Sunday 6.
        'day': _int_env('EXVIUS_ROTATION_DAY', 6) % 7,
        'hour': _int_env('EXVIUS_ROTATION_HOUR', 22) % 24,
        'special': max(0, _int_env('EXVIUS_ROTATION_SPECIAL', 1)),
        'featured': max(0, _int_env('EXVIUS_ROTATION_FEATURED', 2)),
        'seed': os.environ.get('EXVIUS_ROTATION_SEED', 'exvius-weekly'),
    }


def _now(cfg: dict, now: datetime | None) -> datetime:
    zone = ZoneInfo(cfg['tz']) if ZoneInfo else None
    if now is None:
        return datetime.now(zone)
    if now.tzinfo is None and zone is not None:
        return now.replace(tzinfo=zone)
    return now.astimezone(zone) if zone is not None else now


def week(now: datetime | None = None, cfg: dict | None = None) -> tuple[int, datetime, datetime]:
    """(week number, this week's start, next change) as local times in the rotation's time zone."""
    cfg = cfg or settings()
    local = _now(cfg, now)
    days_back = (local.weekday() - cfg['day']) % 7
    start = (local - timedelta(days=days_back)).replace(hour=cfg['hour'], minute=0, second=0, microsecond=0)
    if start > local:
        start -= timedelta(days=7)
    # Rebuild the start in its own zone so daylight-saving changes keep the wall-clock hour.
    start = datetime(start.year, start.month, start.day, cfg['hour'], tzinfo=local.tzinfo)
    anchor = ANCHOR + timedelta(days=(cfg['day'] - ANCHOR.weekday()) % 7)
    number = (start.date() - anchor.date()).days // 7
    nxt = start + timedelta(days=7)
    nxt = datetime(nxt.year, nxt.month, nxt.day, cfg['hour'], tzinfo=local.tzinfo)
    return number, start, nxt


def _kind(banner: dict) -> str:
    if banner.get('selection'):
        return 'select'
    if banner.get('steps'):
        return 'step-up'
    if banner.get('boxes'):
        return 'box'
    cost = banner.get('cost')
    cost = cost[0] if isinstance(cost, list) and cost else cost
    if isinstance(cost, dict) and cost.get('kind') in ('ticket', 'important', 'item'):
        return 'ticket'
    return 'featured'


def pools(banners: list) -> tuple[list, list, list, dict]:
    """(permanent ids, special sets, featured sets, banners by id), in the archive's own order.

    Uses the summon archive's de-duplication, so a banner and its calendar alias count once."""
    from gacha_archive import catalogue, permanent, _released, _standard_families
    by_id = {str(b['id']): b for b in banners}
    families = _standard_families()
    seen, ordered = set(), []
    for group in catalogue(banners):
        for bid in group['ids']:
            if bid not in seen:
                seen.add(bid)
                ordered.append(bid)
    fixed = [bid for bid in ordered if permanent(by_id[bid], families)]
    sets: OrderedDict[str, list] = OrderedDict()
    for bid in ordered:
        if bid in fixed:
            continue
        released = _released(by_id[bid])
        key = released.isoformat() if released else 'undated-' + bid
        sets.setdefault(key, []).append(bid)
    special, featured = [], []
    for key, ids in sets.items():
        entry = (key, ids)
        if any(_kind(by_id[bid]) != 'featured' for bid in ids):
            special.append(entry)
        else:
            featured.append(entry)
    return fixed, special, featured, by_id


def _pick(entries: list, per_week: int, number: int, seed: str, label: str) -> list:
    """Walk a shuffled cycle of `entries`, `per_week` at a time; reshuffle for every new cycle."""
    if not entries or per_week <= 0:
        return []
    count = len(entries)
    keys = sorted(entries, key=lambda entry: entry[0])
    chosen, used = [], set()
    for slot in range(per_week):
        position = number * per_week + slot
        cycle, index = divmod(position, count)
        order = list(range(count))
        random.Random(f'{seed}:{label}:{cycle}').shuffle(order)
        entry = keys[order[index]]
        if entry[0] not in used:
            used.add(entry[0])
            chosen.append(entry)
    return chosen


def _first_week_file() -> str:
    import data_paths
    return os.path.join(data_paths.STATE_DIR, 'summon_rotation.json')


def first_week(current: int, record: bool) -> int:
    """The rotation week this save started in. Recorded the first time banners are served, so the
    EXVIUS_ROTATION_FIRST_WEEK sets appear in the first week you actually play, whenever that is."""
    import json
    path = _first_week_file()
    try:
        with open(path, encoding='utf-8') as fh:
            return int(json.load(fh)['first_week'])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if record:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump({'first_week': current}, fh)
        except OSError:
            pass
    return current


def _pinned(cfg: dict) -> list:
    return [key.strip() for key in os.environ.get('EXVIUS_ROTATION_FIRST_WEEK', '').split(',') if key.strip()]


def plan(banners: list, now: datetime | None = None, record: bool = False, first: int | None = None) -> dict:
    """This week's rotation: its number, start and end, and the sets on offer."""
    cfg = settings()
    number, start, nxt = week(now, cfg)
    fixed, special, featured, by_id = pools(banners)
    picked_special = _pick(special, cfg['special'], number, cfg['seed'], 'special')
    picked_featured = _pick(featured, cfg['featured'], number, cfg['seed'], 'featured')
    pins = _pinned(cfg)
    if pins and number == (first if first is not None else first_week(number, record)):
        # The opening week: the chosen sets take the first slots of their kind; the rest stay random.
        pinned_special = [entry for entry in special if entry[0] in pins]
        pinned_featured = [entry for entry in featured if entry[0] in pins]
        keys = {entry[0] for entry in pinned_special + pinned_featured}
        picked_special = pinned_special + [e for e in picked_special if e[0] not in keys][
            :max(0, cfg['special'] - len(pinned_special))]
        picked_featured = pinned_featured + [e for e in picked_featured if e[0] not in keys][
            :max(0, cfg['featured'] - len(pinned_featured))]
        sets = pinned_special + pinned_featured + [e for e in picked_special + picked_featured if e[0] not in keys]
    else:
        sets = picked_special + picked_featured
    return {'week': number, 'starts': start, 'ends': nxt, 'permanent': fixed, 'sets': sets,
            'by_id': by_id, 'pool_sizes': {'special': len(special), 'featured': len(featured)}}


def rotation_ids(banners: list, now: datetime | None = None) -> list:
    """Banner ids to show this week: the permanent summons, then this week's sets."""
    current = plan(banners, now, record=True)
    ids = list(current['permanent'])
    for _key, members in current['sets']:
        ids.extend(bid for bid in members if bid not in ids)
    if _LOGGED_WEEK[0] != current['week']:
        _LOGGED_WEEK[0] = current['week']
        names = '; '.join(f"{key}: " + ', '.join(current['by_id'][bid].get('name', bid) for bid in members)
                          for key, members in current['sets'])
        print(f"summon rotation week {current['week']} "
              f"({current['starts']:%a %Y-%m-%d %H:%M %Z} to {current['ends']:%a %Y-%m-%d %H:%M %Z}): "
              f"{len(current['permanent'])} permanent + {names}", flush=True)
    return ids


def describe(banners: list, weeks: int = 1, now: datetime | None = None) -> str:
    cfg = settings()
    number, start, _nxt = week(now, cfg)
    first = first_week(number, record=False)
    lines = []
    for offset in range(weeks):
        moment = start + timedelta(days=7 * offset, hours=1)
        current = plan(banners, moment, first=first)
        lines.append(f"Week {current['week']}: {current['starts']:%a %b %d %I:%M %p %Z} "
                     f"to {current['ends']:%a %b %d %I:%M %p %Z}")
        if offset == 0:
            lines.append('  Always: ' + ', '.join(current['by_id'][b].get('name', b) for b in current['permanent']))
        for key, members in current['sets']:
            lines.append(f'  Set released {key}:')
            for bid in members:
                banner = current['by_id'][bid]
                lines.append(f"    [{_kind(banner)}] {banner.get('name', bid)} (id {bid})")
    sizes = plan(banners, now)['pool_sizes']
    lines.append(f"Pool: {sizes['special']} sets with step-up/ticket/select/box banners, "
                 f"{sizes['featured']} featured-only sets.")
    return '\n'.join(lines)


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description='Preview the weekly summon rotation.')
    parser.add_argument('--weeks', type=int, default=1, help='how many weeks to show, starting now')
    args = parser.parse_args(argv)
    for name, value in (('GACHA_ONLY', 'all'), ('GACHA_CAMPAIGN', 'all'), ('EXVIUS_SUMMON_ARCHIVE', '1'),
                        ('GACHA_STANDARD', '1'), ('GACHA_CATALOGUE', '1')):
        os.environ.setdefault(name, value)
    from ffbe_gacha import all_banners
    print(describe(all_banners(), max(1, args.weeks)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

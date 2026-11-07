"""Build source/server/gacha_deals.json from the hand-written specs in source/server/content/deal_specs.json.

The specs hold what Global's news pages printed for each deal banner, in short form; this script expands them to
full banner documents (the shape of gacha_catalogue.json / gacha_named.json) so the engine and the replay serve
them on their real dates. Run from the repo root with the game tables available (see HANDOFF "Testing locally"):

    python3 ios-server/devtools/build_deals.py

Spec fields (per banner):
  id            95xxxxx (the deal block; step detail ids are id*10+step)
  name          the title Global printed
  family        step_up | first_10_1 | free_daily | rate_up | ticket | celebration | ... (for notes and grouping)
  release/until YYYY-MM-DD (Global dates, PST/PDT day)
  featured      unit names with a raised share of their rarity (rate-up units)
  featured_share  share of the top tier the featured units take together (default 0.5)
  rates         [5star, 4star, 3star] (or [nv, 5star, 4star, 3star]) to override the era's rates
  pool_rule     default {"released_by": release - 1 day, "exclude": ["limited", "collab"]}; null for none
  pool_units    explicit unit names for a fixed pool (e.g. "6 chosen FFXV 5★ units")
  tier_units    {"5": [names]}: one tier drawn only from these units (a "specially selected 5★ pool")
  slots         [{"count": 1, "min_rarity": 4}]: extra guaranteed draws (the "+2" of a 9+2)
  reward_pool   [[rate, token], ...]: draws items instead of units (the free Lapis summons)
  min_rarity    drop tiers below this (e.g. 4 for a 4★+ pool)
  cost          {"lapis": n} | {"free": true} | {"item": [kind, id, amount]} for a single-offer banner
  draws         units per pull (single-offer banners)
  guarantee     {"rarity": 5} | {"units": [names]} | {"unit": name}
  bonus         reward tokens paid with every pull (see REWARDS)
  bonus_choice  [[weight, [tokens]], ...]: one of these paid with every pull
  steps         [{lapis|free|item, draws, guarantee, bonus, rainbow, featured_x}] for step-ups
  lap_limit / purchase_limit / daily_limit
  art           {"main": [capture, file], "detail": [capture, file]}: the list (640x160) and detail (640x392)
                news images by Wayback capture timestamp (or [_, full url]); a missing one gets a titled stand-in
  sources       [{"url", "archived"}] news pages read (Wayback captures)
  notes         what was guessed or taken from JP

Reward tokens: lapis:<n>, kmm (King Metal Minituar), <token>*<count>, moogle1/moogle3/moogle5/moogle10/moogle20 (Trust Moogles giving 1/5/5/10/20% to all), ticket5_10,
ticket5_30, ticket5_50 (5★ summon tickets), select5 (5★ Select Summon Ticket), rare (Rare Summon Ticket),
guar4/guar5 (Guaranteed 4★+/5★ tickets), super_moogle_ex (Super Trust Moogle Exchange Ticket), unit:<name>,
or a raw reward dict.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER = os.path.join(ROOT, 'source', 'server')
sys.path.insert(0, SERVER)

SPECS = os.path.join(SERVER, 'content', 'deal_specs.json')
OUT = os.path.join(SERVER, 'gacha_deals.json')

REWARDS = {
    'moogle1': {'kind': 10, 'id': 904000101, 'count': 1, 'affinity_points': ['10', '']},
    'moogle3': {'kind': 10, 'id': 904000103, 'count': 1, 'affinity_points': ['50', '']},
    'moogle5': {'kind': 10, 'id': 904000104, 'count': 1, 'affinity_points': ['50', '']},
    'moogle10': {'kind': 10, 'id': 904000105, 'count': 1, 'affinity_points': ['100', '']},
    'moogle20': {'kind': 10, 'id': 904000105, 'count': 1, 'affinity_points': ['200', '']},
    'moogle50': {'kind': 10, 'id': 904000105, 'count': 1, 'affinity_points': ['500', '']},
    'moogle100': {'kind': 10, 'id': 904000105, 'count': 1, 'affinity_points': ['1000', '']},
    'ticket5_10': {'kind': 23, 'id': 230, 'count': 1},
    'ticket5_30': {'kind': 23, 'id': 240, 'count': 1},
    'ticket5_50': {'kind': 23, 'id': 250, 'count': 1},
    'select5': {'kind': 23, 'id': 260, 'count': 1},
    'rare': {'kind': 23, 'id': 50, 'count': 1},
    'guar4': {'kind': 23, 'id': 70, 'count': 1},
    'guar5': {'kind': 23, 'id': 80, 'count': 1},
    'super_moogle_ex': {'kind': 20, 'id': 106211340, 'count': 1},
    'kmm': {'kind': 10, 'id': 900020401, 'count': 1},
}

# Global's summon rates by period (from the community calendar's rate sources, gacha_community.json).
ERAS = [
    ('2016-01-01', [(5, 0.01), (4, 0.19), (3, 0.80)]),
    ('2018-06-01', [(5, 0.03), (4, 0.19), (3, 0.78)]),
    ('2019-11-01', [(5, 0.05), (4, 0.19), (3, 0.76)]),
    ('2020-08-01', [(7, 0.0125), (5, 0.0875), (4, 0.45), (3, 0.45)]),
    ('2020-12-01', [(7, 0.02), (5, 0.08), (4, 0.45), (3, 0.45)]),
    ('2021-03-01', [(7, 0.03), (5, 0.12), (4, 0.425), (3, 0.425)]),
]

WINDOW = {'from': '2026-01-01 00:00:00', 'to': '2030-12-31 23:59:59'}


def era_rates(release: str):
    rates = ERAS[0][1]
    for start, tiers in ERAS:
        if release >= start:
            rates = tiers
    return rates


class Units:
    def __init__(self):
        import ffbe_gacha
        import player_state
        self.by_name: dict[str, list] = {}
        for rarity, ids in player_state.unit_roots_by_rarity().items():
            for uid in ids:
                self.by_name.setdefault(ffbe_gacha.unit_name(uid).lower(), []).append((int(rarity), uid))
        self.nv = self._nv_units()

    @staticmethod
    def _nv_units() -> set:
        """NV units: the explicit rarity-7 tier members of the community calendar (7★ awakenings excluded)."""
        with open(os.path.join(SERVER, 'gacha_community.json'), encoding='utf-8') as fh:
            banners = json.load(fh)['banners']
        out = set()
        for b in banners:
            for t in ((b.get('pool') or {}).get('tiers') or [] if isinstance(b.get('pool'), dict) else []):
                if int(t.get('rarity') or 0) == 7:
                    out |= {str(u) for u in (t.get('units') or []) + (t.get('featured') or [])}
        return out

    def known(self, name: str) -> bool:
        return name.lower() in self.by_name

    def root(self, name: str) -> tuple[int, str]:
        rows = self.by_name.get(name.lower())
        if not rows:
            raise SystemExit(f'unknown unit name: {name!r}')
        # The summonable form: an NV unit if it is one, else the lowest-rarity root (its base rarity).
        nv = [r for r in rows if r[1] in self.nv]
        return nv[0] if nv else min(rows)


def reward(token, units: Units) -> dict:
    if isinstance(token, dict):
        return token
    if token.startswith('lapis:'):
        return {'kind': 50, 'id': 1, 'count': int(token[6:])}
    if '*' in token:   # "moogle10*5": five of them
        name, times = token.split('*')
        return dict(reward(name, units), count=int(times))
    if token.startswith('unit:'):
        _rarity, uid = units.root(token[5:])
        return {'kind': 10, 'id': int(uid), 'count': 1}
    if token not in REWARDS:
        raise SystemExit(f'unknown reward token: {token!r}')
    return dict(REWARDS[token])


def cost(spec: dict) -> dict:
    if spec.get('free'):
        return {'kind': 'free', 'amount': 0}
    if 'lapis' in spec:
        return {'kind': 'lapis', 'amount': int(spec['lapis'])}
    if 'item' in spec:
        kind, item_id, amount = spec['item']
        return {'kind': 'item' if int(kind) == 20 else 'important', 'item_id': int(item_id), 'amount': int(amount)}
    raise SystemExit(f'no cost in {spec}')


def tiers(spec: dict, units: Units, rainbow=None, featured_x=None) -> dict:
    rates = spec.get('rates')
    if rates:
        rarities = [7, 5, 4, 3] if len(rates) == 4 else [5, 4, 3]
        base = list(zip(rarities, rates))
    else:
        base = era_rates(spec['release'])
    featured = [units.root(n) for n in spec.get('featured', []) if units.known(n)]
    share = float(spec.get('featured_share', 0.5))
    if featured_x:
        share = min(1.0, share * float(featured_x))
    explicit = [units.root(n) for n in spec.get('pool_units', [])]
    out = []
    top = None
    for rarity, rate in base:
        if rarity < int(spec.get('min_rarity', 0)):
            continue
        if rainbow is not None and rarity == base[0][0]:
            rate = float(rainbow)
        tier = {'rarity': rarity, 'rate': rate}
        named = (spec.get('tier_units') or {}).get(str(rarity))
        if explicit:
            tier['units'] = [u for r, u in explicit if r == rarity]
            if not tier['units']:
                continue
        elif named:
            # A selected pool: these units only, all "featured" so the limited/collab rule never drops one.
            tier['units'] = [units.root(n)[1] for n in named]
            tier['featured'] = list(tier['units'])
            tier['featured_share'] = 1.0
        elif rarity == 7:
            tier['units'] = sorted(units.nv)
        fids = [u for r, u in featured if r == rarity]
        if fids:
            tier['featured'] = fids
            tier['featured_share'] = share
        out.append(tier)
        top = top or tier
    # Rates of dropped tiers go to the remaining ones in proportion (a 4★+ pool keeps summing to 1).
    total = sum(t['rate'] for t in out)
    for t in out:
        t['rate'] = round(t['rate'] / total, 6)
    return {'tiers': out}


def guarantee(spec, units: Units, pool_tiers) -> dict:
    if not spec:
        return {}
    if 'unit' in spec:
        return {'unit_id': units.root(spec['unit'])[1]}
    if 'units' in spec:
        ids = [units.root(n) for n in spec['units']]
        rarity = max(r for r, _ in ids)
        return {'rarity': rarity, 'count': int(spec.get('count', 1)),
                'pool': {'tiers': [{'rarity': rarity, 'rate': 1, 'units': [u for _, u in ids]}]}}
    return {'rarity': int(spec['rarity']), 'count': int(spec.get('count', 1))}


NEWS_IMG = 'https://lapis-prod-staticnews-gumi-sg.akamaized.net/prod/en/img/'


def wb(entry) -> str:
    """[capture timestamp, news image name] -> its Wayback URL; a full URL passes through; None -> ''."""
    if not entry:
        return ''
    ts, name = entry
    if str(name).startswith('http'):
        return name
    return f'https://web.archive.org/web/{ts}id_/{NEWS_IMG}{name}'


def slots(spec_slots, pool) -> list:
    """Extra guaranteed draws (a 9+2's "4★+ guaranteed"): one list per slot from the banner's tiers."""
    out = []
    for slot in spec_slots:
        floor = int(slot.get('min_rarity', 4))
        tiers_ = [dict(t) for t in pool['tiers'] if int(t['rarity']) >= floor]
        total = sum(t['rate'] for t in tiers_) or 1
        for t in tiers_:
            t['rate'] = round(t['rate'] / total, 6)
        out.append({'count': int(slot.get('count', 1)), 'label': slot.get('label', f'{floor}★ or higher'),
                    'pool': {'tiers': tiers_}})
    return out


def build(spec: dict, units: Units) -> dict:
    bid = str(spec['id'])
    release = spec['release']
    pool = tiers(spec, units)
    steps = spec.get('steps') or []
    banner = {
        'id': bid,
        'type': 'step' if steps else ('free' if (spec.get('cost') or {}).get('free') else 'normal'),
        'name': spec['name'],
        'detail_id': bid + '1',
        'exe_type': 'primary',
        'gacha_layout': 2,
        'schedule': {'disp_order': 1, 'banner_type': 0, 'window': WINDOW},
        'pool': pool,
        'provenance': 'news',
        'source': 'global-news',
        'deal': spec.get('family', 'deal'),
        'tab': 'limited',
        'release': release,
        'community': {'release': release, 'until': spec.get('until', release), 'limited': True,
                      'units': [n for n in spec.get('featured', []) if units.known(n)],
                      'unit_ids': [units.root(n)[1] for n in spec.get('featured', []) if units.known(n)]},
        'campaign_identity': f'deal:{release}:{bid}',
        'name_override': True,
    }
    rule = spec.get('pool_rule', 'default')
    if rule == 'default':
        day = dt.date.fromisoformat(release) - dt.timedelta(days=1)
        rule = {'released_by': day.isoformat(), 'exclude': ['limited', 'collab']}
    if rule and not spec.get('pool_units'):
        banner['pool_rule'] = rule
    # Art: Global's list (main, 640x160) and detail (640x392) images, by Wayback URL. A missing one gets a
    # titled stand-in drawn on the server (deal_art.render). Files are named per banner, since Global reused
    # file names like en_mainbig.png for different summons.
    art = spec.get('art') or {}
    main_url, detail_url = wb(art.get('main')), wb(art.get('detail'))
    main_name, detail_name = f'deal-{bid}-main.png', f'deal-{bid}-detail.png'
    if not detail_url and main_url:
        detail_name, detail_url = main_name, main_url
    if not main_url and detail_url:
        main_name, main_url = detail_name, detail_url
    banner['art'] = {
        'banner': main_name, 'detail_banner': detail_name, 'detail_extra': [],
        'anime_file': 'gacha_animation',
        'anime_name': 'gacha_moogle_rare/anime' if steps or spec.get('guarantee') else 'gacha_moogle_normal/anime',
        'img_btn': 'gacha_btn_r',
        'urls': {main_name: main_url, detail_name: detail_url},
    }
    if steps:
        out_steps = []
        for step in steps:
            row = {'cost': cost(step), 'draws': int(step.get('draws', 11))}
            if step.get('rainbow') is not None or step.get('featured_x'):
                row['pool'] = tiers(spec, units, step.get('rainbow'), step.get('featured_x'))
            g = guarantee(step.get('guarantee'), units, pool)
            if g:
                row['guarantee'] = g
            if step.get('bonus'):
                row['bonus_rewards'] = [reward(t, units) for t in step['bonus']]
            if step.get('bonus_choice'):
                row['bonus_choice'] = [{'rate': float(rate), 'rewards': [reward(t, units) for t in tokens]}
                                       for rate, tokens in step['bonus_choice']]
            out_steps.append(row)
        banner['steps'] = out_steps
    else:
        banner['cost'] = cost(spec.get('cost') or {})
        banner['draws'] = int(spec.get('draws', 11))
        g = guarantee(spec.get('guarantee'), units, pool)
        if g:
            banner['guarantee'] = g
        if spec.get('slots'):
            banner['guarantee_slots'] = slots(spec['slots'], pool)
        if spec.get('reward_pool'):
            banner['reward_pool'] = [dict(reward(token, units), rate=float(rate))
                                     for rate, token in spec['reward_pool']]
        if spec.get('bonus'):
            banner['bonus_rewards'] = [reward(t, units) for t in spec['bonus']]
        if spec.get('bonus_choice'):
            banner['bonus_choice'] = [{'rate': float(rate), 'rewards': [reward(t, units) for t in tokens]}
                                      for rate, tokens in spec['bonus_choice']]
    for key in ('lap_limit', 'purchase_limit', 'daily_limit', 'weekly_limit'):
        if spec.get(key):
            banner[key] = int(spec[key])
    banner['sources'] = spec.get('sources', [])
    banner['rate_source'] = {
        'url': (spec.get('sources') or [{}])[0].get('url', ''),
        'scope': spec.get('scope', 'Costs, steps, bonuses, limits and pool rule as printed on the Global news page.'),
        'authored_details': spec.get('notes', ''),
    }
    if spec.get('notes'):
        banner['notes'] = spec['notes']
    if spec.get('region'):
        banner['region'] = spec['region']
        banner['rate_notice'] = spec.get('rate_notice', 'Details taken from FFBE Japan where Global\'s are lost.')
    return banner


def main() -> int:
    with open(SPECS, encoding='utf-8') as fh:
        specs = json.load(fh)
    units = Units()
    banners = []
    seen = set()
    for spec in specs['banners']:
        if str(spec['id']) in seen:
            raise SystemExit(f'duplicate id {spec["id"]}')
        seen.add(str(spec['id']))
        banners.append(build(spec, units))
    doc = {'_meta': {'note': 'GENERATED by ios-server/devtools/build_deals.py from content/deal_specs.json; '
                             'edit the specs, not this file.', 'count': len(banners)},
           'banners': banners}
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print(f'{len(banners)} deal banner(s) -> {os.path.relpath(OUT, ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

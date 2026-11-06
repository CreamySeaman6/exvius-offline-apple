"""Build source/server/content/exploration_encounters.json: the random battles of each exploration.

Input: source/server/content/exploration_wiki.json (the FFBE wiki's per-exploration monster lists with
per-zone counts, battles per zone and bosses), the battle index (content/battle), and the shipped text
tables (F_TEXT_MISSION, F_TEXT_DUNGEON_NAME, F_TEXT_MONSTER_NAME, from TEXT_DIR).

Run from source/server:  TEXT_DIR=<text_decoded> python3 ../../ios-server/devtools/build_exploration_encounters.py

For each exploration mission matched to a wiki record:
  * each wiki monster name -> the game's monster id with that English name, choosing the variant used by
    battle groups closest to the mission (longest common id prefix: the mission's own groups, then its
    dungeon's, then its region's);
  * per zone, a list of battles whose monsters add up to the wiki's counts in about the wiki's number of
    battles: real battle groups from the index made only of those monsters (closest groups first), then
    made-up groups (ids 900000001+) of one monster type, laid out like a real group with that monster;
  * a wiki page without counts gets every listed monster, in its battle count (less the boss) or
    DEFAULT_BATTLES battles.
The server puts zone N's battles on the encounter fields of zone N (battle_content.field_zone).
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
import battle_content as bc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(bc.__file__))
TEXT_DIR = os.environ.get('TEXT_DIR') or sys.exit('TEXT_DIR is not set')
DEFAULT_BATTLES = 15            # per zone, when the wiki gives no battle count
SYNTHETIC_BASE = 900000000
ALIASES = {'A-Type Magitek Armor+': 'Magitek Armor A-Type+', 'White Dragon (chest)': 'White Dragon',
           'Mini-Boss Chimera': 'Chimera', 'Ignis Fatuus': 'Ignus Fatuus'}
SKIP_NAMES = {'Red Butterfly encounter'}


def norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())


def text(name: str) -> dict[str, str]:
    out = {}
    with open(os.path.join(TEXT_DIR, name + '.ndjson'), encoding='utf-8') as fh:
        for line in fh:
            row = json.loads(line)
            out[row['key'].rsplit('_', 1)[1]] = row['v'][0]
    return out


def prefix(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def main():
    wiki = json.load(open(os.path.join(HERE, 'content', 'exploration_wiki.json'), encoding='utf-8'))
    src = bc._default_index_source()
    mission_names, dungeon_names, monster_names = text('F_TEXT_MISSION'), text('F_TEXT_DUNGEON_NAME'), text('F_TEXT_MONSTER_NAME')
    missions = {str(r['qo3PECw6']): r for r in src.load('F_MISSION_MST')}
    groups: dict[str, list[dict]] = {}
    for row in src.load('F_BATTLE_GROUP_MST'):
        groups.setdefault(str(row['2fY1IomW']), []).append(row)
    for rows in groups.values():
        rows.sort(key=lambda r: int(r['Z0EN6jSh']))
    have = ({str(m['xqartN26']) for m in src.load('F_MONSTER_MST')}
            & {str(p['xqartN26']) for p in src.load('F_MONSTER_PARTS_MST')})
    by_name: dict[str, set[str]] = {}
    for mid, name in monster_names.items():
        if mid in have:
            by_name.setdefault(norm(name), set()).add(mid)
    used_in: dict[str, list[str]] = {}
    for gid, rows in groups.items():
        for row in rows:
            used_in.setdefault(str(row['xqartN26']), []).append(gid)
    scenario = bc._scenario_groups()

    # wiki records by in-game mission name (events) and by page title (story)
    records: dict[str, list] = {}
    for page, section, battles, bosses, mons in wiki['events']:
        entry = {'page': page, 'section': section, 'battle': battles, 'zones': [], 'm': mons}
        records.setdefault(norm(section), []).append(entry)
        if section == 'Battle Info':
            records.setdefault(norm(page), []).append(entry)
    for page, rec in wiki['story'].items():
        info = rec['i'][0]
        zones = [int(n) for name, n in rec['z'] if n.isdigit() and (name.startswith('Zone') or name == 'Encounters')]
        entry = {'page': page, 'section': page, 'battle': info['battle'], 'zones': zones, 'm': info['m']}
        records.setdefault(norm(page.replace('/Exploration', ' - Exploration')), []).append(entry)
        records.setdefault(norm(page), []).append(entry)

    field_like = [m for m, r in missions.items()
                  if bc.resource_kind(m) == 'exploration' or str(r.get('Y4VoF8yu')) == '2']
    out, unresolved, next_gid = {}, {}, SYNTHETIC_BASE + 1
    synthetic: dict[str, list[dict]] = {}
    synthetic_key: dict[tuple, str] = {}
    for mid in sorted(field_like, key=int):
        name = mission_names.get(mid, '')
        dungeon = dungeon_names.get(str(missions[mid].get('U9iHsau3', '')), '')
        rec = None
        # The dungeon's name only for explorations named after it ("Zoldaad Castle - Exploration" is
        # the wiki's "Zoldaad Castle Grounds/Exploration") and the Six Realms; never for the trials,
        # expeditions and revisits that share a dungeon with an exploration.
        keys = [norm(name)]
        # Event pages with one exploration name the section "Battle Info": match on the page name,
        # with the mission's difficulty tag dropped ("Mystic Den - Exploration (HARD)").
        keys.append(norm(re.sub(r'\s*\((HARD|EASY|Hard|Easy)\)$', '', name)))
        # (Realm of the Dragon King's areas are "<area> - Base" in game and "<area>" on the wiki.)
        if 'Exploration' in name or name == 'The Six Realms' or name.endswith(' - Base'):
            keys += [norm(dungeon + ' - Exploration'), norm(dungeon)]
        # Quest explorations the wiki describes as another exploration without its chests.
        if name in wiki.get('same_as', {}):
            keys.append(norm(wiki['same_as'][name]))
        for key in keys:
            if key and key in records:
                rec = records[key][0]
                break
        if rec is None:
            unresolved[mid] = {'name': name or '?', 'dungeon': dungeon}
            continue
        species, missing = {}, []
        for wname, counts in rec['m']:
            if wname in SKIP_NAMES:
                continue
            ids = by_name.get(norm(ALIASES.get(wname, wname)), set())
            if not ids:
                missing.append(wname)
                continue
            best = max(ids, key=lambda i: (max((prefix(g, mid) for g in used_in.get(i, [])), default=0),
                                           len(used_in.get(i, [])), -int(re.sub(r'\D', '', i) or 0)))
            if wname in species:      # a name listed twice (e.g. Rursan Reaver (1)/(2)): add counts
                species[wname]['counts'] = [a + b for a, b in zip(species[wname]['counts'], counts)] or counts
            else:
                species[wname] = {'id': best, 'counts': list(counts)}
        if not species:
            unresolved[mid] = {'name': name, 'dungeon': dungeon, 'wiki': rec['page'],
                               'reason': 'no listed monster exists in the battle data', 'missing': missing}
            continue
        nzones = max((len(s['counts']) for s in species.values()), default=0)
        if any(not s['counts'] for s in species.values()):
            nzones = 0      # counts for only some monsters (Kilika Woods' one Mini Mogcaptor): treat as none
        total = int(rec['battle']) - 1 if str(rec['battle']).isdigit() and int(rec['battle']) > 1 else None
        if nzones == 0:
            # a count given for only some monsters is kept as that many single-monster battles
            zone_plan = [(0, {s: (v['counts'][0] if v['counts'] else None) for s, v in species.items()},
                          total or DEFAULT_BATTLES)]
        else:
            per_zone = rec['zones'] if len(rec['zones']) == nzones else None
            monsters_in = [sum(s['counts'][z] for s in species.values() if len(s['counts']) > z) for z in range(nzones)]
            if per_zone is None:
                whole = total if total else sum(round(m / 2) for m in monsters_in)
                per_zone = [max(1, round(whole * m / max(1, sum(monsters_in)))) for m in monsters_in]
            zone_plan = []
            for z in range(nzones):
                counts = {s: v['counts'][z] for s, v in species.items() if len(v['counts']) > z and v['counts'][z] > 0}
                if counts:
                    zone_plan.append((z + 1 if nzones > 1 else 0, counts, per_zone[z]))
        ids = {s: v['id'] for s, v in species.items()}
        id_species = {v: k for k, v in ids.items()}
        zones_out = []
        for zone, counts, battles in zone_plan:
            fixed = {s: n for s, n in counts.items() if n is not None} if None in counts.values() else {}
            allowed = {ids[s] for s in counts if s not in fixed}
            cands = [g for g, rows in groups.items() if g not in scenario
                     and all(str(r['xqartN26']) in allowed for r in rows)]
            cands.sort(key=lambda g: (-prefix(g, mid), g))
            chosen: list[str] = []
            if None in counts.values():
                for s, n in fixed.items():
                    chosen += [('synthetic', s, 1)] * n
                counts = {s: None for s in counts if s not in fixed}
                local = [g for g in cands if prefix(g, mid) >= 3] or cands[:12]
                pool = local[:max(1, len(local))]
                covered = {id_species[str(r['xqartN26'])] for g in pool for r in groups[g]}
                for s in counts:
                    if s not in covered:
                        pool.append(None)
                        chosen.append(('synthetic', s, 2))
                real = [g for g in pool if g]
                i = 0
                while len(chosen) < battles and real:
                    chosen.append(real[i % len(real)])
                    i += 1
                while len(chosen) < battles:
                    chosen.append(('synthetic', list(counts)[len(chosen) % len(counts)], 2))
            else:
                remaining = dict(counts)
                while len(chosen) < battles and any(remaining.values()):
                    # the group size that keeps the rest on course for the wiki's battle count
                    target = sum(remaining.values()) / (battles - len(chosen))
                    best, best_score = None, None
                    for g in cands:
                        need = Counter(id_species[str(r['xqartN26'])] for r in groups[g])
                        over = sum(max(0, n - remaining.get(s, 0)) for s, n in need.items())
                        if over:
                            continue
                        # closest size to the target, then the most plentiful leftovers, then the closest group
                        scarce = max(remaining[s] for s in need)
                        score = (-abs(len(groups[g]) - target), scarce, prefix(g, mid))
                        if best_score is None or score > best_score:
                            best, best_score = g, score
                    if best is None:
                        break
                    chosen.append(best)
                    for r in groups[best]:
                        remaining[id_species[str(r['xqartN26'])]] -= 1
                left = battles - len(chosen)
                for s, n in sorted(remaining.items(), key=lambda x: -x[1]):
                    while n > 0:
                        slots = max(1, min(3, n, round(n / max(1, left)) if left > 0 else 3))
                        chosen.append(('synthetic', s, slots))
                        n -= slots
                        left -= 1
            final = []
            for c in chosen:
                if isinstance(c, tuple):
                    _, s, size = c
                    key = (ids[s], size)
                    if key not in synthetic_key:
                        gid = str(next_gid)
                        next_gid += 1
                        synthetic_key[key] = gid
                        synthetic[gid] = layout(gid, ids[s], size, groups, used_in)
                    final.append(synthetic_key[key])
                else:
                    final.append(c)
            zones_out.append({'zone': zone, 'battles': final})
        out[mid] = {'name': name, 'wiki': rec['page'], 'section': rec['section'],
                    'monsters': {s: ids[s] for s in ids}, 'missing': missing, 'zones': zones_out}

    doc = {'note': 'Built by ios-server/devtools/build_exploration_encounters.py from content/exploration_wiki.json '
                   'and the battle index. zones[].zone: 0 = every encounter field, N = the fields of zone N. '
                   'battles: battle group ids, one per battle (repeats are separate battles).',
           'missions': out, 'groups': synthetic, 'unresolved': unresolved}
    path = os.path.join(HERE, 'content', 'exploration_encounters.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=0)
    print(f'{len(out)} missions, {len(synthetic)} made-up groups, {len(unresolved)} unresolved -> {path}')


def layout(gid: str, monster: str, size: int, groups, used_in) -> list[dict]:
    """A made-up group of `size` copies of `monster`, positioned like a real group with that monster."""
    template = None
    for g in used_in.get(monster, []):
        rows = groups[g]
        if len(rows) == size:
            template = rows
            break
    if template is None:
        for rows in groups.values():
            if len(rows) == size and all(r['xqartN26'] == rows[0]['xqartN26'] for r in rows):
                template = rows
                break
    base = template or [{'MxLFKZ13': '190,320', '3t7pZM5V': '0', 'WJdBp9f0': '1', 'm9BvFk2X': '1'}] * size
    return [{'2fY1IomW': gid, 'xqartN26': monster, 'MxLFKZ13': base[i]['MxLFKZ13'], 'Z0EN6jSh': str(i + 1),
             '3t7pZM5V': base[i].get('3t7pZM5V', '0'), 'WJdBp9f0': base[i].get('WJdBp9f0', '1'),
             'm9BvFk2X': base[i].get('m9BvFk2X', '1')} for i in range(size)]


if __name__ == '__main__':
    main()

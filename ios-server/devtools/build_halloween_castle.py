"""Rebuild the battles of Return to the Halloween Castle (Global, 2017-10-20) for the Vortex.

The shipped tables keep the event's missions, rewards and challenges (Castle Dungeon 9190001-9190003,
Castle Inner Chamber 9210001-9210003), the original Global monster ids and names (900010339-900010377),
the three bosses' skill sets and AI scripts, and every monster's animated sprite (Global monster pack,
monster_sg_common.cpk). What was never shipped is the server side: wave formations and monster stats.

- Bosses (Inner Chamber): original ids, sprites, AI and skill sets; stats, resistances and actions per
  turn from the wiki's boss infoboxes; skill rows rebuilt from the Global datamine (aEnigmatic/ffbe
  monster_skills.json), the same way source/exvius/reconstruct_event_battles.py does it.
- Castle Dungeon: original ids and names, the wiki's roster per difficulty; the combat profile (AI,
  skills, resistances) from a same-species monster, stats scaled to Global's King Mog events of mid 2017
  at the same energy cost (Henne Mines, In the Name of Love, Castle Hein). Formations are local.
- The Castle Keep (key-spending stages) has no mission rows in the shipped tables and is not rebuilt; its
  rewards are sold for Skeleton Keys in the Skeleton Key Exchange (content/event_shops.json) instead.

Run from source/server with the env of HANDOFF.md "Testing locally" (MST_DIR, TEXT_DIR, FFBE_DATA):

    python3 ../../ios-server/devtools/build_halloween_castle.py <monster_skills.json>

Writes source/server/event_encounters_added.json (merged by battle_content.event_encounter).
"""
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())
import battle_content  # noqa: E402
from battle_content import IndexSource, derive_mission, PARTS_TOKENS, PARTS_DEFAULTS  # noqa: E402
from player_state import _load_ndjson  # noqa: E402

ELEMENTS = ('fire', 'ice', 'lightning', 'water', 'wind', 'earth', 'light', 'dark')
WIKI = 'https://exvius.fandom.com/wiki/Return_to_the_Halloween_Castle'
WIKI_REVISION = 277583
OUT = 'event_encounters_added.json'

# Original Global part id -> (name, same-species donor in the JP battle index, dictionary/graphic id).
MOBS = {
    '900010366': ('Zombie', '112021000', '1120210'),
    '900010367': ('Ghoul', '212181000', '1120220'),
    '900010368': ('Revenant', '112023006', '1120230'),
    '900010369': ('Mage', '105021000', '1050210'),
    '900010370': ('Shadow', '105022003', '1050220'),
    '900010371': ('Ghost', '105023000', '1050230'),
    '900010373': ('Woodwatcher', '111011012', '1110110'),
    '900010374': ('Mammon', '111012000', '1110120'),
    '900010375': ('Treant', '111013025', '1110130'),
}
# Pumpkin Kid and Pumpkin Rider are Global-only: their 2016 profiles (event_encounters.json, Night of
# the Pumpkin) serve as the combat profile, under the 2017 ids.
GLOBAL_PROFILES = {'900010372': ('Pumpkin Kid', '9000203', '900010149'),
                   '900010376': ('Pumpkin Rider', '9000303', '900010152')}

# Stats by tier: (level, hp, mp, atk, def, mag, spr, actions). Calibrated on Global's mid-2017 King Mog
# events at 10 / 20 / 25 energy (regular enemies L15 1-2k HP, L40 30-70k, L70 150-200k; bosses ~5k,
# ~100k, ~450k).
STATS = {
    '900010366': (15, 1600, 60, 65, 25, 25, 25, '1,1'),
    '900010367': (15, 1900, 60, 75, 25, 25, 25, '1,1'),
    '900010368': (20, 6000, 100, 95, 35, 60, 35, '1,2'),
    '900010369': (40, 30000, 400, 140, 40, 160, 60, '1,1'),
    '900010370': (40, 38000, 300, 170, 45, 140, 45, '1,1'),
    '900010371': (40, 34000, 400, 120, 40, 170, 70, '1,1'),
    '900010372': (45, 110000, 500, 230, 60, 200, 60, '1,2'),
    '900010373': (70, 160000, 600, 290, 60, 120, 60, '1,1'),
    '900010374': (70, 150000, 800, 260, 60, 260, 70, '1,1'),
    '900010375': (70, 190000, 800, 300, 80, 220, 70, '1,1'),
    '900010376': (75, 480000, 1500, 350, 90, 300, 80, '2,2'),
}

# Bosses: wiki Boss Infobox (original Global values), original AI and skill set.
BOSSES = {
    '900010377': {'name': 'Skeleton Wright', 'dictionary': '10000020', 'ai': '900010377', 'set': '900010377',
                  'level': 70, 'hp': 3500000, 'mp': 50000, 'atk': 350, 'def': 25, 'mag': 250, 'spr': 25,
                  'res': (10, 10, 10, -30, 10, 10, -30, 100), 'breaks': '0,100,0,100,100,100,100',
                  'actions': '4,5'},
    '900010339': {'name': 'Pumpking Reaper', 'dictionary': '10000002', 'ai': '900000000', 'set': '900010339',
                  'level': 99, 'hp': 38000000, 'mp': 80000, 'atk': 750, 'def': 25, 'mag': 625, 'spr': 32,
                  'res': (30, 30, 30, 30, 30, 30, -20, 100), 'breaks': '50,100,100,100,100,100,100',
                  'actions': '4,5'},
    '900010340': {'name': 'Skeleton King', 'dictionary': '10000021', 'ai': '900010340', 'set': '900010340',
                  'level': 99, 'hp': 48750000, 'mp': 100000, 'atk': 700, 'def': 35, 'mag': 450, 'spr': 30,
                  'res': (30, 30, 30, -30, 30, 30, -30, 100), 'breaks': '0,100,0,100,100,100,100',
                  'actions': '6,7'},
}

# Waves per mission (wiki roster; the formations are local). The last wave of each holds the boss.
WAVES = {
    '9190001': [['900010366', '900010367'], ['900010367', '900010366', '900010367'], ['900010368']],
    '9190002': [['900010369', '900010370'], ['900010370', '900010371', '900010370'],
                ['900010369', '900010371', '900010369'], ['900010372']],
    '9190003': [['900010373', '900010374'], ['900010375', '900010373'], ['900010374', '900010375', '900010374'],
                ['900010375', '900010373', '900010375'], ['900010376']],
    '9210001': [['900010377']],
    '9210002': [['900010339']],
    '9210003': [['900010340']],
}
# Skeleton Keys (item 1209000838) drop in the Castle Dungeon, as on Global (wiki: "drop Skeleton Key"), and
# are spent in the Skeleton Key Exchange (content/event_shops.json). Floor bosses always drop the floor's
# original key reward (1/2/3); other waves have a 35% chance, with a Hi-Potion as the fallback drop.
KEY = '20:1209000838'
KEY_DROPS = {'900010368': KEY + ':1:100', '900010372': KEY + ':2:100', '900010376': KEY + ':3:100'}
MOB_DROP = KEY + ':1:35,20:101000200:1:60'
UNIT_EXP = {'9190001': 156, '9190002': 266, '9190003': 728, '9210001': 10000, '9210002': 18000, '9210003': 20000}


def client_rows(table, key):
    rows = [json.loads(line) for line in open(os.path.join(os.environ['MST_DIR'], table + '.ndjson'), encoding='utf-8')]
    return {row[key]: row for row in rows}


def recover_skills(set_row, raw_skills, templates):
    """Global datamine skills -> F_MONSTER_SKILL_MST rows (reconstruct_event_battles.recover_skills)."""
    out = {}
    for sid in set_row['7qxLC5hP'].split(','):
        if not sid:
            continue
        original = raw_skills[sid]
        kind = {'Physical': '1', 'Magic': '2', 'Hybrid': '3', 'None': '4'}[original['attack_type']]
        effects = original['effects_raw']
        row = dict(templates[kind], **{
            '6E5u1xrs': sid, 'G4L0YIB2': original['name'].replace(' ', ' '), '8cY9hejo': '0',
            'oPD4yL58': '@'.join(str(e[0]) for e in effects),
            'a4hXTIm0': '@'.join(str(e[1]) for e in effects),
            '2kq0BpnD': '@'.join(str(e[2]) for e in effects),
            'PI18xnkD': '@'.join('0' for _ in effects),
            'Ha9G5sCS': '@'.join(','.join(str(v) for v in e[3]) for e in effects),
            '7irj9hAb': ','.join(str(int(flag)) for flag in original['flags'])})
        text = str(original.get('effects', '')).casefold()
        row['Jn6BbR2P'] = ','.join('1' if re.search(r'\b' + e + r'\b[^.;]*damage', text) else '0' for e in ELEMENTS)
        out[sid] = row
    return out


class Source(battle_content.Source):
    def __init__(self, base, tables):
        self.base, self.tables = base, tables

    def load(self, table):
        return self.tables[table] if table in self.tables else self.base.load(table)


def main():
    raw_skills = json.load(open(sys.argv[1], encoding='utf-8'))
    base = IndexSource()
    index_parts = {}
    for row in base.load('F_MONSTER_PARTS_MST'):
        index_parts.setdefault(row['xqartN26'], []).append(row)
    dictionary = client_rows('F_MONSTER_DICTIONARY_MST', 'V9j8wJcC')
    client_ai = set(client_rows('F_AI_MST', '8a6gAwN9'))
    client_sets = client_rows('F_MONSTER_SKILL_SET_MST', 'A5x02C6a')
    templates = {kind: next(r for r in base.load('F_MONSTER_SKILL_MST')
                            if r['Isb1GDe2'] == kind and r.get('5w1o9DPV') == '0') for kind in '1234'}
    encounters = json.load(open('event_encounters.json', encoding='utf-8'))['missions']
    missions = _load_ndjson('F_MISSION_MST.ndjson', 'qo3PECw6')

    profiles, monsters, provenance, skills = {}, {}, {}, {}
    for pid, (name, donor, graphic) in MOBS.items():
        row = copy.deepcopy(index_parts[donor][0])
        assert len(index_parts[donor]) == 1 and row['8a6gAwN9'] in client_ai, donor
        assert row['A5x02C6a'] in ('', '0') or row['A5x02C6a'] in client_sets, donor
        profiles[pid] = row
        monsters[pid] = {'xqartN26': pid, 'G4L0YIB2': name, 'V9j8wJcC': graphic}
        provenance[pid] = {'enemy': name, 'donor': donor, 'dictionary': graphic,
                           'basis': 'Original Global id and name; same-species combat profile; '
                                    'stats scaled to mid-2017 King Mog events at the same energy cost'}
    for pid, (name, mission, source_pid) in GLOBAL_PROFILES.items():
        bundle = encounters[mission]['bundle']
        row = copy.deepcopy(next(p for p in bundle['bV34YIJQ'] if p['xqartN26'] == source_pid))
        profiles[pid] = row
        graphic = next(m for m in bundle['wbet57nF'] if m['xqartN26'] == source_pid)['V9j8wJcC']
        monsters[pid] = {'xqartN26': pid, 'G4L0YIB2': name, 'V9j8wJcC': graphic}
        provenance[pid] = {'enemy': name, 'donor': source_pid, 'dictionary': graphic,
                           'basis': 'Original Global id, name and sprite; 2016 Global profile; '
                                    'stats scaled to mid-2017 King Mog events at the same energy cost'}
    for pid, (level, hp, mp, atk, df, mag, spr, actions) in STATS.items():
        row = profiles[pid]
        row.update({'xqartN26': pid, 'G4L0YIB2': monsters[pid]['G4L0YIB2'], '7wV3QZ80': str(level),
                    'fh31sk7B': str(hp), 'PC97pWQj': str(max(mp, int(row.get('PC97pWQj') or 0))),
                    '9NBV1XCS': str(atk), 'Pn5w9dfh': str(df), '84FJM3PD': str(mag), 'T8xMDAZ4': str(spr),
                    '4Y2DGP7m': actions, 'e56NZY42': '0', 'ATM35pjf': '0',
                    '9BetM2Ds': KEY_DROPS.get(pid, MOB_DROP), 'm28pD1GM': '', '3frn4ILX': ''})
        row['a9qg8vnP'] = dictionary.get(monsters[pid]['V9j8wJcC'], {}).get('a9qg8vnP', row.get('a9qg8vnP'))
    template = next(p for p in encounters['9000401']['bundle']['bV34YIJQ'] if p['xqartN26'] == '900010153')
    for pid, spec in BOSSES.items():
        assert spec['ai'] in client_ai and spec['set'] in client_sets, pid
        row = copy.deepcopy(template)
        vector = row['hn42BL3Q'].split(',')
        vector[:8] = [str(v) for v in spec['res']]
        row.update({'xqartN26': pid, 'G4L0YIB2': spec['name'], '7wV3QZ80': str(spec['level']),
                    'fh31sk7B': str(spec['hp']), 'PC97pWQj': str(spec['mp']), '9NBV1XCS': str(spec['atk']),
                    'Pn5w9dfh': str(spec['def']), '84FJM3PD': str(spec['mag']), 'T8xMDAZ4': str(spec['spr']),
                    'hn42BL3Q': ','.join(vector), 'D9Nb7jgd': '100,100,100,100,100,100,100,100',
                    'Rcqa1Zt7': spec['breaks'], '4Y2DGP7m': spec['actions'], '8a6gAwN9': spec['ai'],
                    'A5x02C6a': spec['set'], 'jmKe42Yg': '0', 'e56NZY42': '0', 'ATM35pjf': '0',
                    'a9qg8vnP': dictionary[spec['dictionary']]['a9qg8vnP'], '3frn4ILX': '', '9BetM2Ds': ''})
        profiles[pid] = row
        monsters[pid] = {'xqartN26': pid, 'G4L0YIB2': spec['name'], 'V9j8wJcC': spec['dictionary']}
        skills.update(recover_skills(client_sets[spec['set']], raw_skills, templates))
        provenance[pid] = {'enemy': spec['name'], 'donor': None, 'dictionary': spec['dictionary'],
                           'published_stats': {k: spec[k] for k in ('level', 'hp', 'mp', 'atk', 'def', 'mag', 'spr')},
                           'basis': 'Original Global id, sprite, AI script and skill set; wiki boss infobox stats; '
                                    'skills from the Global datamine (aEnigmatic/ffbe monster_skills.json)'}

    sets = base.load('F_MONSTER_SKILL_SET_MST') + [client_sets[s['set']] for s in BOSSES.values()] + [
        client_sets[p['A5x02C6a']] for p in profiles.values()
        if p['A5x02C6a'] not in ('', '0') and p['A5x02C6a'] in client_sets]
    skill_rows = base.load('F_MONSTER_SKILL_MST') + list(skills.values())
    out = {}
    for mid, waves in WAVES.items():
        mission = missions[mid]
        assert int(mission['8xi6Xvyk']) == len(waves), mid
        phases, lotteries, groups = [], [], []
        for wave, foes in enumerate(waves, 1):
            gid = f'179{mid[-5:]}{wave:02d}'
            phases.append({'qo3PECw6': mid, '6v7y3QcJ': str(wave), 'gou39JeI': '2', '6uIYE15X': gid,
                           'DYTx1Is3': mission['DYTx1Is3'], 'YS9kfCX7': mission['6w4xiIsS']})
            lotteries.append({'c2gnh6Jd': gid, 'ixDq7yJ8': '1', '2fY1IomW': gid})
            for slot, pid in enumerate(foes, 1):
                groups.append({'2fY1IomW': gid, 'xqartN26': pid,
                               'MxLFKZ13': '170,310' if len(foes) == 1 else f'{170 if slot % 2 else 100},{250 + 60 * slot}',
                               'Z0EN6jSh': str(slot), '3t7pZM5V': '2', 'WJdBp9f0': '1', 'm9BvFk2X': '1'})
        used = list(dict.fromkeys(pid for foes in waves for pid in foes))
        # Experience: the wiki's unit EXP and the mission's own rank EXP, shared over every enemy body.
        count = sum(len(foes) for foes in waves)
        mission_profiles = []
        for pid in used:
            row = dict(profiles[pid])
            row['B6H34Mea'] = str(UNIT_EXP[mid] // count)
            row['7UR4J2SE'] = str(int(mission.get('7UR4J2SE') or 0) // count)
            mission_profiles.append(row)
        tables = {'F_MISSION_PHASE_MST': phases, 'F_BATTLE_LOTTERY_MST': lotteries, 'F_BATTLE_GROUP_MST': groups,
                  'F_MONSTER_MST': [monsters[pid] for pid in used], 'F_MONSTER_PARTS_MST': mission_profiles,
                  'F_MONSTER_SKILL_SET_MST': sets, 'F_MONSTER_SKILL_MST': skill_rows}
        bundle = derive_mission(int(mid), Source(base, tables))
        bundle['bV34YIJQ'] = [{t: p.get(t, PARTS_DEFAULTS.get(t, '')) for t in PARTS_TOKENS}
                              for p in bundle['bV34YIJQ']]
        bundle['1IfDqR4n'] = [mission]
        out[mid] = {'bundle': bundle, 'enemies': [provenance[pid] for pid in used],
                    'identity_source': 'Original Global mission, monster ids, sprites and boss AI; wiki roster',
                    'source_page': 'Return to the Halloween Castle', 'source_revision': WIKI_REVISION,
                    'source_url': WIKI}
    document = {'version': 1,
                'provenance': 'Local reconstruction of Global events whose battles were never shipped. '
                              'See ios-server/devtools/build_halloween_castle.py.',
                'missions': out,
                'local_monster_names': {pid: m['G4L0YIB2'] for pid, m in monsters.items()}}
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(document, fh, ensure_ascii=False, separators=(',', ':'))
        fh.write('\n')
    for mid, entry in out.items():
        b = entry['bundle']
        print(mid, missions[mid]['G4L0YIB2'], 'waves', len(b['an6TB4WS']), 'monsters', len(b['wbet57nF']),
              'skills', len(b['Wp39QX52']))


if __name__ == '__main__':
    main()

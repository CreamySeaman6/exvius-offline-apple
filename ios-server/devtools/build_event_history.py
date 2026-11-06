"""Build source/server/event_history.json: Global run dates for archived events, plus events the archive lacks.

Run from source/server with MST_DIR pointing at static/mst_decoded (see HANDOFF.md, "Event history").
"""
import json
import os
from datetime import date

# Read 2026-11-06 from exvius.fandom.com/wiki/Update_Schedule, section "Global Update History":
# area(s);extra Global dates (YYMMDD) not already the archive's release date (within 3 days).
SCHEDULE = """\
1199;230406 230504 230713 240815
9961;240815
898;170907 170929 180125 180517 180614 180712 180830 180927 181018 181122 181220 190131 190301 190321 230831
899;160714 160825 160923 161027 161124 161208 170118 170309 170412 170518 170608 170720 170817 171122 171221 180329 180621 180712 180719 180823 180913 181004 190404 200319 200507 200603 200806 200910 201203 210204 210311
963;190711 190912 191024 200514 200721 200730 240822
743;170119 170414
3279;230323
906;161230
3282;240229
708;170203
722;170317
402;180706 190808 200625
6373;240328
911;170406
724;170427
3264;220317
401;170622
1899;211028 220113 220217 220623 220714 220812 220908 221020 221110 221208 230112 230209
222;180504
718;190419
707;161104
705;161014
709 6193;161124
721;161118
726;180329
727;190612
731;190719
713;170217
717;170505
744;180525
745;180601
714;180907
715;180907
9917;180816 180920 181011 181108 181212 190103 190214 190321 190418 190516 190620 190628 190809 190906 191017 191107 191205 200206 200319 201008 201112 201210 210204 210415
781;190125
782 1016;190201
704;161202
706;170113
710;170303
1108;200130
956;200206
723;170420
3035;190312
3021;200819
1050 3076 3127 9903;200702 210326
3125;210326
3126;210326
1033;211021
1034;211028
3227;210121
3247;200318
4002;210222
1058;200506
1064;200603
1069 9904;200715
1070;201008
1076;200812
1077 9912;200902
7170;220310
6371;240328
6370;240328
"""

WIKI = 'https://static.wikia.nocookie.net/exvius_gamepedia_en/images/'
# Events Global ran that the archive lacks, whose missions the game tables still hold and whose battles the
# server can build (checked mission by mission). Dates are Global's (same schedule).
ADDED = [
    # area, name, group, first run, later runs, kind, dungeons, wiki page, banner (path under WIKI)
    ('711', 'Memories from the Aquapolis', 'season1', '2017-01-06', ['2017-07-14'], 'FFBE - Exploration Event',
     ['71101'], 'Memories_from_the_Aquapolis', '1/1c/Banner-Memories_from_the_Aquapolis.png'),
    ('712', 'The Auracite Chosen', 'season1', '2017-03-24', [], 'Final Fantasy Tactics - Exchange Event',
     ['71201'], 'The_Auracite_Chosen', '7/77/Banner-The_Auracite_Chosen.png'),
    ('746', 'Guardian of the Order', 'season2', '2017-11-03', [], 'FFBE - Story Event',
     [f'746{n:02d}' for n in range(1, 11)], 'Guardian_of_the_Order', 'a/a1/Banner-Guardian_of_the_Order.png'),
    ('749', 'The Web-Weaving Princess', 'season2', '2017-12-01', [], 'Final Fantasy XV - Exploration Event',
     ['74901'], 'The_Web-Weaving_Princess', '4/47/Banner-The_Web-Weaving_Princess.png'),
    ('747', 'King of Darkness', 'season2', '2017-12-08', [], 'raid',
     ['74701'], 'King_of_Darkness', '4/43/Banner-King_of_Darkness.png'),
    ('797', 'Dracotaur Lancer', 'season2', '2018-05-25', [], 'raid',
     ['79701'], 'Dracotaur_Lancer', '1/1e/Banner-Dracotaur_Lancer.png'),
    ('703', 'Orbonne Monastery Vaults', 'season1', '2016-09-30', ['2018-07-20'],
     'Final Fantasy Tactics - Exchange Event', ['70301'], 'Orbonne_Monastery_Vaults',
     'a/ab/Banner-Orbonne_Monastery_Vaults.png'),
    # Return to the Halloween Castle: battles rebuilt by build_halloween_castle.py
    # (event_encounters_added.json). The Castle Keep has no mission rows and is not included.
    ('919', 'Return to the Halloween Castle', 'season1', '2017-10-20', ['2018-10-26'], 'FFBE - Unique Event',
     ['91900'], 'Return_to_the_Halloween_Castle', '1/1c/Banner-Halloween_Dungeon.png'),
    ('921', 'Return to the Halloween Castle', 'season1', '2017-10-20', ['2018-10-26'], 'FFBE - Unique Event',
     ['92100'], 'Return_to_the_Halloween_Castle', '0/02/Banner-Inner_Chamber.png'),
]


# Ranked events the archive lists as permanent, with the periods Global actually ran them (PST), read
# 2026-11-06 from the wiki: "Dark Visions - The Advent of Chaos" 1-32 (Category:Dark Visions - The Advent of
# Chaos; event periods) and Category:Clash of Wills (each boss's event period). The Dark Visions areas run in
# area order (checked against each run's area elements); the Clash of Wills areas by their boss names.
DARK_VISIONS = """\
920 200423 200429
922 200528 200603
924 200625 200705
925 200716 200722
926 200820 200826
927 200924 201007
928 201029 201111
929 201126 201209
934 201224 210106
935 210128 210210
936 210225 210310
938 210325 210407
939 210422 210505
941 210527 210609
942 210722 210804
944 210826 210908
945 211007 211020
946 211202 211215
949 220106 220119
953 220310 220323
955 220512 220525
959 220804 220817
9918 221110 221123
9919 230105 230119
9925 230202 230215
9926 230302 230315
9931 230406 230419
9934 230504 230517
9937 230713 230802
9945 230928 231011
9949 231207 231220
9953 240201 240214
"""
CLASH_OF_WILLS = """\
7100 210701 210714 The Empress from Beyond
7101 210812 210825 Dragon from Across Time
7102 210909 210922 Brawler from Another World
7103 211021 211103 Tower of Unknown Origin
7104 211021 211103 Hydra of Unknown Origin
9500 211223 220105 Tree of Unknown Origin
9501 220127 220209 Fragment of the Beast
9502 220224 220309 Fragment of the Egg
9503 220324 220406 Dragon Spirit of Unknown Origin
9504 220421 220504 Nightmare of Unknown Origin
9505 220526 220608 Trickster of Unknown Origin
9506 220630 220713 Assimilator of Unknown Origin
9507 220630 220713 Manticore of Unknown Origin
9508 220818 220831 Amphibian of Unknown Origin
9509 220915 220928 Kappa of Unknown Origin
9510 221027 221109 Champion of Unknown Origin
9511 221124 221207 Automaton of Unknown Origin
9512 221222 230104 Gingerbread Man of Unknown Origin
9513 230119 230201 Hare of Unknown Origin
9514 230216 230301 Moth of Unknown Origin
9515 230316 230405 Shogun of Unknown Origin
9516 230420 230503 Moon of Unknown Origin
9517 230518 230601 Wolf of Unknown Origin
9518 230629 230712 Dark Swordswoman from Beyond
9519 230720 230802 Harpy of Unknown Origin
9520 230824 230906 Metal Dragon from Across Time
9521 230921 231011 Songstress of Unknown Origin
9522 231026 231108 Dog Spirit of Unknown Origin
9523 231123 231206 Warmachine of Unknown Origin
9524 231221 240103 Yeti of Unknown Origin
9525 240125 240207 Shinobi of Unknown Origin
9526 240215 240306 Sun Dragon of Unknown Origin
9527 240321 240410 Sea Serpent of Unknown Origin
9528 240418 240508 Centaur of Unknown Origin
9529 240627 240731 Evil Deity of Unknown Origin
"""


def iso(token):
    return f'20{token[:2]}-{token[2:4]}-{token[4:]}'


def main():
    archive = {e['area']: e for e in json.load(open('event_archive.json', encoding='utf-8'))['events']}
    runs, skipped = {}, []
    for line in SCHEDULE.strip().splitlines():
        areas, dates = line.split(';')
        for area in areas.split():
            release = archive[area].get('release')
            keep = []
            for d in map(iso, dates.split()):
                if release:
                    gap = abs((date.fromisoformat(d) - date.fromisoformat(release)).days)
                    # Same day a year apart, or a few weeks off: a typo on one side, not a rerun.
                    if gap <= 45 or (d[5:] == release[5:] and gap in (365, 366)):
                        skipped.append(f'{area} {d} (archive {release})')
                        continue
                keep.append(d)
            if keep:
                runs[area] = sorted(set(keep))
    missions = [json.loads(line) for line in open(os.path.join(os.environ['MST_DIR'], 'F_MISSION_MST.ndjson'),
                                                    encoding='utf-8')]
    added = []
    for area, name, group, first, later, kind, dungeons, page, banner in ADDED:
        assert area not in archive, area
        ids = sorted((m['qo3PECw6'] for m in missions if m['U9iHsau3'] in dungeons),
                     key=lambda mid: (dungeons.index(next(m['U9iHsau3'] for m in missions if m['qo3PECw6'] == mid)), int(mid)))
        assert ids, area
        added.append({
            'area': area, 'name': name, 'group': group, 'release': first, 'kind': kind, 'collaboration': None,
            'dungeons': dungeons, 'missions': ids, 'first_dungeon': dungeons[0], 'first_mission': ids[0],
            'banner_title': 'File:' + banner.rsplit('/', 1)[1].replace('_', ' '),
            'filename': f'event_{area}.png',
            'source_page': 'https://exvius.fandom.com/wiki/' + page,
            'date_source': 'https://exvius.fandom.com/wiki/Update_Schedule#Global_Update_History',
            'art_url': WIKI + banner + '/revision/latest',
        })
        if later:
            runs[area] = later
    windows = {}
    for line in (DARK_VISIONS + CLASH_OF_WILLS).strip().splitlines():
        area, start, end = line.split()[:3]
        assert archive[area]['group'] == 'permanent', area
        windows[area] = [[iso(start), iso(end)]]
    doc = {
        'version': 1,
        'provenance': {
            'runs': 'Global run dates (first runs, reruns, updates) from the Brave Exvius wiki, Update Schedule, '
                    'section "Global Update History", read 2026-11-06. Only dates the archive does not already '
                    'carry as its release date. Dates that look like a typo of the release date (within 45 days, '
                    'or the same day one year apart) are left out.',
            'added': 'Global events missing from event_archive.json whose missions are in the shipped tables and '
                     'whose battles the server builds (every mission checked). Left out for lack of battle data: '
                     'Lunar New Year (907/908, Jan 2017), The Spearmaiden (701), Eternal Winter (923). '
                     'Return to the Halloween Castle (919/921) is included with locally rebuilt battles '
                     '(build_halloween_castle.py); its Castle Keep has no mission rows.',
            'skipped_runs': skipped,
            'windows': 'Periods (first day, last day, PST) Global ran ranked events the archive lists as permanent: '
                       'Dark Visions - The Advent of Chaos 1-32 and Clash of Wills, from the Brave Exvius wiki '
                       '(the event pages\' Event Period), read 2026-11-06. The Vortex shows them only then.',
        },
        'runs': runs,
        'added': added,
        'windows': windows,
    }
    with open('event_history.json', 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print(len(runs), 'areas with runs;', len(added), 'added;', len(skipped), 'skipped:', skipped)


if __name__ == '__main__':
    main()

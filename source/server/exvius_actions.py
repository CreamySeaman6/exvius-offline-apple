"""Player actions the recorded corpus never answered (logs/sweep-unhandled-requests-20261025.md).

The server's default reply only echoes the request, so these actions changed nothing in the save. Each
handler here keys on its own request id (source/server/endpoints.json), reads the fields the client's
`createBody` writes (source/docs/analysis/unhandled_request_fields.json, from
harness/extract_request_fields.py) and applies the change to the one player state. A reply that should
refresh the client's lists carries the unit group, so `apply_to_reply` projects every player group.
"""
from collections import Counter
import json
from exvius_raid_progress import personal_raid_menu
from ffbe_friends import local_friend_action

from ffbe_state import State, _note

UNIT_GROUP = "B71MekS8"        # UserUnitInfoResponse; its presence makes apply_to_reply project all groups


def _request(plaintext):
    if not plaintext:
        return None
    try:
        req = json.JSONDecoder().raw_decode(plaintext)[0]
    except ValueError:
        return None
    return req if isinstance(req, dict) else None


def _node(req, group):
    rows = req.get(group) if req else None
    return rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else None


def _refresh(spec):
    out = dict(spec) if isinstance(spec, dict) else {}
    out.setdefault(UNIT_GROUP, [])
    return out


def _mst(name, key):
    from player_state import _load_ndjson
    return _load_ndjson(name, key)


def item_sell(spec, req):
    """Use the shop transaction path, including equipment's separate ownership store."""
    from exvius_actions_shops import item_sell as sell
    return sell(spec, req)


def mission_restart(spec, req):
    """MissionReStartRequest (a continue): the client spends F_DEFINE_MST CONTINUE_COST Lapis (100)."""
    row = _mst("F_DEFINE_MST.ndjson", "AK8Nn7ta").get("CONTINUE_COST") or {}
    cost = int(row.get("YjIUDJ97") or 100)
    paid = State.player.spend_lapis(cost)
    print(f"mission: continue {'paid' if paid else 'NOT paid (balance)'} {cost} lapis", flush=True)
    return _refresh(spec)


def unit_class_up(spec, req):
    """UnitClassUpRequest (awakening): group `sWc7EH69`, `og2GHy49` = the base unit. F_UNIT_CLASS_UP_MST
    names the next rarity (`t74crqAL`), its gil (`7UR4J2SE`) and materials (`KCk8u0am`). The reply is
    UnitClassUpResponse on the same tag (UserUnitClassUpResult: og2GHy49 unit, 5u7VYNEX new unit,
    KCk8u0am materials, WbGYcN17/02CI3bpE element info, p9Xj4Anc all-kigen flag)."""
    node = _node(req, "sWc7EH69")
    iid = str(node.get("og2GHy49") or "") if node else ""
    unit = next((u for u in State.player.data["roster"] if str(u["instance_id"]) == iid), None)
    if unit is None:
        _note(f"unit-class-up: unit {iid or '?'} not in the roster")
        return spec
    step = _mst("F_UNIT_CLASS_UP_MST.ndjson", "3HriTp6B").get(str(unit["master_id"]))
    if not step:
        _note(f"unit-class-up: no F_UNIT_CLASS_UP_MST row for {unit['master_id']}")
        return spec
    materials = str(step.get("KCk8u0am") or "")
    gil = int(step.get("7UR4J2SE") or 0)
    rows = [m.split(":") for m in materials.split(",") if m.count(":") == 2]
    if any(State.player.item_count(int(k), i) < int(c) for k, i, c in rows) or \
            int(State.player.currencies.get("gil", 0)) < gil:
        _note(f"unit-class-up: {unit['master_id']} lacks materials or gil; not awakened")
        return spec
    for k, i, c in rows:
        State.player.spend_item(int(k), i, int(c))
    State.player.spend_currency("gil", gil)
    before = unit["master_id"]
    unit["master_id"] = str(step["t74crqAL"])
    unit = State.player.renew_unit_instance(iid)
    State.player.record_archive({'TOTAL_UNIT_CLASS_UP': 1})
    State.player.dirty = True
    print(f"unit: awakened {iid} {before} -> {unit['master_id']} for {gil} gil + {materials}", flush=True)
    out = _refresh(spec)
    out["sWc7EH69"] = [{"og2GHy49": iid, "5u7VYNEX": unit['instance_id'], "KCk8u0am": materials, "WbGYcN17": "",
                        "02CI3bpE": "", "p9Xj4Anc": "0"}]
    return out


def _parse_rewards(text):
    rows = []
    for entry in str(text or "").split(","):
        parts = entry.split(":")
        if len(parts) == 3 and all(p.isdigit() for p in parts) and int(parts[2]) > 0:
            rows.append({"kind": int(parts[0]), "id": int(parts[1]), "count": int(parts[2])})
    return rows


def unit_equip(spec, req):
    from exvius_actions_expedition import _retain_owned_equipment, _wire_loadouts

    player = State.player
    rows = req.get("Er92Kdhm")
    if player.mode == "frozen" or not isinstance(rows, list):
        return _refresh(spec)
    roster = {str(unit["instance_id"]): unit for unit in player.data["roster"]}
    gear = {row["J1YX9kmM"]: int(row["Qy5EvcK1"]) for row in player.equip_item_rows()}
    materia = {row["H5jBL0Vf"]: int(row["Qy5EvcK1"]) for row in player.materia_rows()}
    cards = {str(card["user_vc_id"]) for card in player.data.get("vision_cards", [])}
    loadouts = {}
    try:
        for row in rows:
            decoded, _ = _wire_loadouts(row, roster)
            for iid, fields in decoded.items():
                for field, values in fields.items():
                    if field in ("equipment", "shift_equipment", "materia", "shift_materia"):
                        owned = materia if "materia" in field else gear
                        counts = Counter(values if "materia" in field else values.values())
                        if any(item != "0" and count > owned.get(item, 0) for item, count in counts.items()):
                            raise ValueError("unowned equipment or materia")
                    if field in ("vision_card", "shift_vision_card") and values and values not in cards:
                        # Native vision-card strings carry the master id as well as the instance id.
                        if not cards.intersection(values.split("-")):
                            raise ValueError("unowned vision card")
                if str(row.get("xBi3L6yR", "1")) == "1":
                    loadouts.setdefault(iid, {}).update(fields)
    except (AttributeError, TypeError, ValueError):
        _note("unit-equip: invalid equipment update")
        return _refresh(spec)
    if any(any(roster[iid].get(key) != value for key, value in fields.items())
           for iid, fields in loadouts.items()):
        # Older saves infer the starter copies from the worn slots. Keep those
        # copies in inventory before replacing or clearing the slots.
        _retain_owned_equipment()
        for iid, fields in loadouts.items():
            roster[iid].update(fields)
        player.dirty = True
    return _refresh(spec)


def sacrifice(spec, req, group="6kvFj2Kw"):
    """Consume eligible units only after resolving the fragment rewards for the full batch."""
    from exvius_actions_shops import deployed_unit_ids
    from player_state import unit_mst

    player = State.player
    nodes = req.get(group)
    if player.mode == "frozen" or not isinstance(nodes, list) or not nodes:
        return spec
    table = _mst("F_SACRIFICE_MST.ndjson", "woghJa61")
    deployed = deployed_unit_ids(player)
    ids, rewards, result = set(), [], []
    for node in nodes:
        iid = str(node.get("og2GHy49", "")) if isinstance(node, dict) else ""
        unit = player.roster_row(iid)
        if not unit or iid in ids or iid in deployed or unit.get("favourite"):
            return _refresh(spec)
        master = unit_mst(unit["master_id"]) or {}
        row = table.get(str(unit["master_id"])) or table.get(master.get("woghJa61"))
        if not row:
            return _refresh(spec)
        # The native picker can send pure NV units through SacrificeRequest.
        # The unit's master row determines its rewards for either request.
        items = str(row.get("1swM3H4T") or row.get("q1PJQ3eE") or "")
        unit_rewards = _parse_rewards(items)
        prism = str(row.get("tL6G9egd") or "0")
        if group == "4Ncra9DF":
            prism = "0"
        if prism != "0":
            unit_rewards.insert(0, {"kind": 20, "id": int(prism), "count": 1})
        if not unit_rewards or any(not player._can_credit(reward) for reward in unit_rewards):
            return _refresh(spec)
        ids.add(iid)
        rewards.extend(unit_rewards)
        result.append({"og2GHy49": iid, "ijEey5f7": str(node.get("ijEey5f7", "1")),
                       "tL6G9egd": prism, "1swM3H4T": items})
    if len(ids) >= len(player.data["roster"]):
        return _refresh(spec)
    player.drop_units(ids)
    player._grant_items(rewards)
    out = _refresh(spec)
    out[group] = result
    _note(f"unit-convert: granted rewards for {len(ids)} unit(s)")
    return out


HANDLERS = {
    "7kG0JAvE": lambda spec, req: local_friend_action(spec, req, 'detail'),
    "3siZRSU4": lambda spec, req: local_friend_action(spec, req, 'search'),
    "iAs67PhJ": lambda spec, req: local_friend_action(spec, req, 'suggest'),
    "1oE3Fwn4": lambda spec, req: local_friend_action(spec, req, 'favorite'),
    "g0BjrU5D": personal_raid_menu,  # RoutineRaidMenuUpdateRequest
    "pB3st6Tg": unit_equip,         # UnitEquipRequest
    "7tWdn9zH": sacrifice,                                             # SacrificeRequest
    "x94MnujU": lambda spec, req: sacrifice(spec, req, "4Ncra9DF"),   # NvSacrificeRequest
    "d9Si7TYm": item_sell,          # ItemSellRequest
    "GfI4LaU3": mission_restart,    # MissionReStartRequest
    "zf49XKg8": unit_class_up,      # UnitClassUpRequest
}


# The other action families (Codex-implemented from source/docs/analysis/action_research/, reviewed here).
# Friend list and reinforcement replies retain their established projection.
FAMILIES = ("exvius_actions_arena", "exvius_actions_expedition", "exvius_actions_modes", "exvius_actions_shops",
            "exvius_gacha_select", "gacha_box")
KEEP_EXISTING = {"u7Id4bMg", "AJhnI37s"}
_merged = []


def _all_handlers():
    if not _merged:
        import importlib
        for name in FAMILIES:
            try:
                module = importlib.import_module(name)
            except ImportError:
                continue
            for rid, handler in module.HANDLERS.items():
                if rid not in KEEP_EXISTING and rid not in HANDLERS:
                    HANDLERS[rid] = handler
        _merged.append(True)
    return HANDLERS


def serve_actions(spec, reply_id, plaintext):
    handler = _all_handlers().get(str(reply_id))
    if State.player is None:
        return spec
    from exvius_colosseum import project
    if handler is None:
        return project(spec)
    req = _request(plaintext)
    if req is None:
        return project(spec)
    return project(handler(spec, req))

"""English text the stock iPhone app is missing, added to the localized text tables it downloads.

The Android build answers some text lookups itself: hooks in `source/exvius/summon_menu.js` replace
`TextManager::getText` results for keys the shipped tables never had. The local Shop bundles
(`MST_BUNDLE_NAME_990000xxx`), the JP special-summon tickets (`MST_ITEM_NAME_1062130x0`) and banners the
shipped `F_TEXT_GACHA` doesn't name. The iPhone app has no hooks, so it printed the raw keys (seen live
2026-11-05 in the Shop's Bundles list). This module puts the same text into the tables themselves:

- each text table is one or more lines of base64 AES-ECB, each decrypting to `KEY^text^text...` records;
  missing keys are appended as one more line, in the table's own record shape;
- the patched table gets a new version number (`Ver<N>_<token>.dat`), and the localized-text index
  (`F_LOCALIZED_TEXT_MST`) is served with that version and the patched file's MD5 and size, which is how
  the app picks text files;
- `ios_tables.py` routes the requests here and raises the index's own advertised version.

Existing records are only replaced where the Android hook replaces them too (a banner's `name_override`).
Explanations are added only for banners with none.
"""
from __future__ import annotations

import base64
import glob
import hashlib
import json
import os
import re
import zlib

INDEX = ("F_LOCALIZED_TEXT_MST", "i5QEJpua", "R8PYPnJ9")
TABLES = {
    "F_TEXT_BUNDLE": ("4OBhnBKu", "3VkESseA"),
    "F_TEXT_ITEM_NAME": ("VhkhtvDn", "xDkegMbe"),
    "F_TEXT_GACHA": ("ZJz5QwAy", "Ab2Kb6yJ"),
}
_HERE = os.path.dirname(os.path.abspath(__file__))

# The JP special summons' ticket items (F_ITEM_MST 106213030-080) have no Global English name
# (same list as summon_menu.js).
TICKET_NAMES = {
    "106213040": "SP Summon Ticket",
    "106213050": "4★/5★/NV SP Summon Ticket",
    "106213030": "5★/NV SP Summon Ticket",
    "106213060": "Bonus Summon Ticket",
    "106213070": "Boss Rush Summon Ticket",
    "106213080": "Brave Ability Box Ticket",
}

_CACHE: dict = {}


def enabled() -> bool:
    return os.environ.get("EXVIUS_IOS_TEXT", "1") == "1"


def _clean(text: str) -> str:
    return " ".join(str(text).replace("^", " ").split())


def additions() -> dict[str, dict[str, tuple[str, bool]]]:
    """`{table: {key: (text, replace_existing)}}`."""
    if "additions" in _CACHE:
        return _CACHE["additions"]
    out: dict[str, dict[str, tuple[str, bool]]] = {name: {} for name in TABLES}
    bundles = {"990000001": "2,000 Friend Points"}
    try:
        with open(os.path.join(_HERE, "global_bundles.json"), encoding="utf-8") as fh:
            for bundle in json.load(fh).get("bundles", []):
                bundles[str(bundle["id"])] = str(bundle["name"])
    except (OSError, ValueError, KeyError):
        pass
    for bid, name in bundles.items():
        out["F_TEXT_BUNDLE"]["MST_BUNDLE_NAME_" + bid] = (_clean(name), False)
        out["F_TEXT_BUNDLE"]["MST_BUNDLE_DESC_" + bid] = (_clean(name), False)
    for iid, name in TICKET_NAMES.items():
        out["F_TEXT_ITEM_NAME"]["MST_ITEM_NAME_" + iid] = (name, False)
    try:
        from ffbe_gacha import all_banners, missing_gacha_names
        banners = all_banners()
        for gid, name in missing_gacha_names(banners).items():
            out["F_TEXT_GACHA"]["MST_GACHA_NAME_" + gid] = (_clean(name), True)
        for b in banners:
            gid = str(b["id"])
            text = ("Choose a unit or prism from the selection list." if b.get("selection") else
                    f"{len(b['steps'])}-step summon. Review each step's contents above." if b.get("steps") else
                    f"Summon {b.get('draws', 1)} reward(s). The button shows the cost. "
                    "See Drop Rates for the reward list.")
            out["F_TEXT_GACHA"]["MST_GACHA_EXPLAIN_LONG_" + gid] = (text, False)
            out["F_TEXT_GACHA"]["MST_GACHA_EXPLAIN_SHORT_" + gid] = (text, False)
    except Exception as exc:  # noqa: BLE001 -- bundles and tickets still get their names
        print(f"[ios-texts] banner names skipped ({exc})", flush=True)
    _CACHE["additions"] = out
    return out


def bump() -> int:
    """Added to each patched text table's version and to the index's advertised version."""
    if not enabled():
        return 0
    if "bump" not in _CACHE:
        blob = json.dumps(additions(), sort_keys=True, ensure_ascii=False).encode("utf-8")
        _CACHE["bump"] = 1000 + zlib.crc32(blob) % 1000
    return _CACHE["bump"]


def _ecb(key_text: str, decrypt: bool, data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from ffbe_crypto import key16
    cipher = Cipher(algorithms.AES(key16(key_text)), modes.ECB())
    op = cipher.decryptor() if decrypt else cipher.encryptor()
    return op.update(data) + op.finalize()


def _pad(data: bytes, layers: int) -> bytes:
    for _ in range(layers):
        n = 16 - len(data) % 16
        data += bytes([n]) * n
    return data


def patch_text(raw: bytes, key_text: str, entries: dict[str, tuple[str, bool]]) -> tuple[bytes, int]:
    """A text table with `entries` applied. Returns (bytes with LF line endings, records added or changed)."""
    out, seen, changed = [], set(), 0
    columns, shape_layers = None, None
    for line in raw.decode("ascii").splitlines():
        line = line.strip()
        if not line:
            continue
        plain = _ecb(key_text, True, base64.b64decode(line))
        layers = 0
        while plain and 1 <= plain[-1] <= 16 and plain[-plain[-1]:] == bytes([plain[-1]]) * plain[-1]:
            plain = plain[:-plain[-1]]
            layers += 1
        records = plain.decode("utf-8").split("\n")
        touched = False
        for i, record in enumerate(records):
            fields = record.rstrip("\r").split("^")
            if len(fields) < 2:
                continue
            if columns is None:
                columns, shape_layers = len(fields) - 1, layers
            seen.add(fields[0])
            entry = entries.get(fields[0])
            if entry and entry[1] and any(value != entry[0] for value in fields[1:]):
                records[i] = "^".join([fields[0]] + [entry[0]] * (len(fields) - 1)) + record[len(record.rstrip("\r")):]
                touched = True
                changed += 1
        if touched:
            line = base64.b64encode(_ecb(key_text, False, _pad("\n".join(records).encode("utf-8"), layers))).decode("ascii")
        out.append(line)
    if columns is None:
        raise ValueError("no text records found")
    missing = [key for key in sorted(entries) if key not in seen]
    if missing:
        plain = "".join("^".join([key] + [entries[key][0]] * columns) + "\n" for key in missing).encode("utf-8")
        out.append(base64.b64encode(_ecb(key_text, False, _pad(plain, shape_layers))).decode("ascii"))
        changed += len(missing)
    return ("\n".join(out) + "\n").encode("ascii"), changed


def _index_source(*roots):
    for root in roots:
        if root:
            hits = glob.glob(os.path.join(root, "mst", f"Ver*_{INDEX[1]}.dat"))
            if hits:
                return max(hits, key=lambda p: int(re.search(r"Ver(\d+)_", os.path.basename(p)).group(1)))
    return None


def _index_rows(raw: bytes):
    from ffbe_crypto import cbc_decrypt, key16
    for line in raw.decode("ascii").splitlines():
        line = line.strip()
        if not line:
            continue
        plain = cbc_decrypt(key16(INDEX[2]), line)
        pad = plain[-1]
        double = 1 <= pad <= 16 and plain[-pad:] == bytes([pad]) * pad
        yield line, json.loads(plain[:-pad] if double else plain), double


def _base_versions(*roots) -> dict[str, int]:
    src = _index_source(*roots)
    if not src:
        return {}
    return {row["a4hXTIm0"]: int(row["00zAYGYS"]) for _, row, _ in _index_rows(open(src, "rb").read())
            if row.get("a4hXTIm0") in TABLES and str(row.get("00zAYGYS", "")).isdigit()}


def patched_table(name: str, *roots) -> tuple[bytes, int, int] | None:
    """(bytes, records changed, served version) of one patched text table, cached."""
    cache_key = ("table", name, bump())
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    base = _base_versions(*roots).get(name)
    if base is None:
        return None
    token, key_text = TABLES[name]
    for root in roots:
        path = os.path.join(root or "", "localized_texts", "en", f"Ver{base}_{token}.dat")
        if root and os.path.isfile(path):
            data, changed = patch_text(open(path, "rb").read(), key_text, additions()[name])
            _CACHE[cache_key] = (data, changed, base + bump())
            return _CACHE[cache_key]
    return None


def patched_index(raw: bytes, *roots) -> tuple[bytes, list[str]]:
    from ffbe_crypto import cbc_encrypt, key16
    out, done = [], []
    for line, row, double in _index_rows(raw):
        name = row.get("a4hXTIm0")
        if name in TABLES:
            patched = patched_table(name, *roots)
            if patched:
                data, _, version = patched
                row.update({"00zAYGYS": str(version), "zptmZGqa": hashlib.md5(data).hexdigest(),
                            "MLOSu5E0": str(len(data))})
                line = cbc_encrypt(key16(INDEX[2]), json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                                   double_pad=double)
                done.append(name)
        out.append(line)
    return ("\n".join(out) + "\n").encode("ascii"), done


_TEXT_PATH = re.compile(r"(^|/)localized_texts/en/Ver(\d+)_([A-Za-z0-9]{8})\.dat$")
_INDEX_PATH = re.compile(r"(^|/)mst/Ver\d+_" + INDEX[1] + r"\.dat$")


def wants(rel: str) -> bool:
    if not bump():
        return False
    if _INDEX_PATH.search(rel):
        return True
    m = _TEXT_PATH.search(rel)
    return bool(m) and any(m.group(3) == token for token, _ in TABLES.values())


def serve(rel: str, *roots) -> tuple[bytes | None, str | None]:
    try:
        if _INDEX_PATH.search(rel):
            src = _index_source(*roots)
            if not src:
                return None, None
            data, done = patched_index(open(src, "rb").read(), *roots)
            return data, f"{os.path.basename(src)}, text version(s) raised for {', '.join(done) or 'nothing'}"
        m = _TEXT_PATH.search(rel)
        name = next(n for n, (token, _) in TABLES.items() if token == m.group(3))
        patched = patched_table(name, *roots)
        if not patched or int(m.group(2)) != patched[2]:
            return None, None  # an older version: serve the shipped file as is
        data, changed, _ = patched
        return data, f"{name}, {changed} English text record(s) added for the iPhone"
    except Exception as exc:  # noqa: BLE001 -- fall back to the shipped file
        return None, f"iPhone text patch failed ({exc})"

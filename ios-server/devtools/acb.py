"""Minimal CRI @UTF reader: print an ACB's waveform encode types and key fields."""
import struct
import sys
from collections import Counter


def utf(buf, off=0):
    assert buf[off:off + 4] == b'@UTF', buf[off:off + 4]
    size = struct.unpack('>I', buf[off + 4:off + 8])[0]
    t = buf[off + 8:off + 8 + size]
    rows_off, str_off, data_off, name_off = struct.unpack('>HIII', t[2:16])
    rows_off += 0  # relative to t
    ncols, row_len, nrows = struct.unpack('>HHI', t[16:24])

    def cstr(o):
        s = t[str_off + o:t.index(b'\0', str_off + o)]
        return s.decode('utf-8', 'replace')
    cols = []
    p = 24
    sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 0xA: 4, 0xB: 8}
    fmts = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f', 0xA: '>I', 0xB: '>II'}

    def read(typ, q):
        v = struct.unpack(fmts[typ], t[q:q + sizes[typ]])
        if typ == 0xA:
            return cstr(v[0])
        if typ == 0xB:
            return t[data_off + v[0]:data_off + v[0] + v[1]]
        return v[0]
    for _ in range(ncols):
        flags = t[p]
        p += 1
        name = cstr(struct.unpack('>I', t[p:p + 4])[0])
        p += 4
        storage, typ = flags & 0xF0, flags & 0x0F
        const = None
        if storage == 0x30:
            const = read(typ, p)
            p += sizes[typ]
        cols.append((name, storage, typ, const))
    rows = []
    for r in range(nrows):
        q = 8 + rows_off + r * row_len  # rows_off is relative to after the 8-byte header... adjust below
        q = rows_off + 8 + r * row_len - 8
        row = {}
        for name, storage, typ, const in cols:
            if storage == 0x50:
                row[name] = read(typ, q)
                q += sizes[typ]
            elif storage == 0x30:
                row[name] = const
            else:
                row[name] = None
        rows.append(row)
    return rows


d = open(sys.argv[1], 'rb').read()
root = utf(d)[0]
print('root keys:', [k for k in root if 'Version' in k or 'Name' in k][:10])
for k in ('Name', 'Version', 'VersionString'):
    if k in root:
        print(' ', k, root[k] if not isinstance(root[k], bytes) else root[k][:60])
waves = utf(root['WaveformTable']) if root.get('WaveformTable') else []
print('waveforms:', len(waves))
print('EncodeType:', Counter(w.get('EncodeType') for w in waves), 'Streaming:', Counter(w.get('Streaming') for w in waves),
      'SamplingRate:', Counter(w.get('SamplingRate') for w in waves))
print('first waveform:', {k: v for k, v in waves[0].items()} if waves else None)

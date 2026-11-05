"""List the files inside a CRI CPK archive (handles the XOR-obfuscated @UTF tables)."""
import struct
import sys


def unmask(b):
    if b[:4] == b'@UTF':
        return b
    m, t = 0x655F, 0x4115
    out = bytearray(len(b))
    for i, c in enumerate(b):
        out[i] = c ^ (m & 0xFF)
        m = (m * t) & 0xFFFFFFFF
    return bytes(out)


SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 0xA: 4, 0xB: 8}
FMTS = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f', 0xA: '>I', 0xB: '>II'}


def utf(b):
    assert b[:4] == b'@UTF', b[:8]
    size = struct.unpack('>I', b[4:8])[0]
    t = b[8:8 + size]
    rows_off, str_off, data_off, _ = struct.unpack('>HIII', t[2:16])
    ncols, row_len, nrows = struct.unpack('>HHI', t[16:24])

    def cstr(o):
        return t[str_off + o:t.index(b'\0', str_off + o)].decode('utf-8', 'replace')

    def read(typ, q):
        v = struct.unpack(FMTS[typ], t[q:q + SIZES[typ]])
        if typ == 0xA:
            return cstr(v[0])
        if typ == 0xB:
            return t[data_off + v[0]:data_off + v[0] + v[1]]
        return v[0]
    cols, p = [], 24
    for _ in range(ncols):
        flags = t[p]
        name = cstr(struct.unpack('>I', t[p + 1:p + 5])[0])
        p += 5
        st, ty = flags & 0xF0, flags & 0x0F
        const = None
        if st == 0x30:
            const = read(ty, p)
            p += SIZES[ty]
        cols.append((name, st, ty, const))
    rows = []
    for r in range(nrows):
        q = rows_off + r * row_len
        row = {}
        for name, st, ty, const in cols:
            if st == 0x50:
                row[name] = read(ty, q)
                q += SIZES[ty]
            elif st == 0x30:
                row[name] = const
        rows.append(row)
    return rows


def listing(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'CPK ', d[:4]
    hsize = struct.unpack('<I', d[8:12])[0]
    head = utf(unmask(d[16:16 + hsize]))[0]
    toc_off = head.get('TocOffset')
    out = []
    if toc_off:
        tsize = struct.unpack('<I', d[toc_off + 8:toc_off + 12])[0]
        for row in utf(unmask(d[toc_off + 16:toc_off + 16 + tsize])):
            name = (row.get('DirName') or '') + '/' + (row.get('FileName') or '')
            out.append((name.lstrip('/'), row.get('FileSize'), row.get('ExtractSize')))
    return head, out


if __name__ == '__main__':
    for path in sys.argv[1:]:
        head, files = listing(path)
        print(f'== {path}: {len(files)} files, toc={head.get("TocOffset")} itoc={head.get("ItocOffset")}')
        for name, size, ext in files:
            print(f'   {name} {size} {ext}')

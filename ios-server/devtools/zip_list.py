"""List a remote zip's entries using HTTP range requests (reads only the central directory)."""
import io
import json
import sys
import urllib.request
import zipfile
from collections import Counter


class RemoteFile(io.RawIOBase):
    def __init__(self, url):
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req) as resp:
            self.url = resp.geturl()
            self.size = int(resp.headers['Content-Length'])
        self.pos = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b''
        end = min(self.size, self.pos + n) - 1
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{end}'})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        self.pos += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def main():
    manifest = json.load(open(sys.argv[1]))
    out = {}
    for pack in manifest['packs']:
        zf = zipfile.ZipFile(io.BufferedReader(RemoteFile(pack['url']), buffer_size=1 << 20))
        names = zf.namelist()
        tops = Counter('/'.join(n.split('/')[:3]) for n in names)
        out[pack['id']] = {'count': len(names), 'tops': tops.most_common(12)}
        print(pack['id'], len(names), tops.most_common(8), flush=True)
    json.dump(out, open(sys.argv[2], 'w'), indent=1)


if __name__ == '__main__':
    main()

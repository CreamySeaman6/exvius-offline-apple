"""Send the iPhone's own InitializeRequest to a local server and check the advertised table versions."""
import json
import ssl
import sys
import time
import urllib.request

sys.path.insert(0, sys.argv[1] + '/server')
import ffbe_crypto as c

port, ca = int(sys.argv[2]), sys.argv[3]
plain = json.dumps({"LhVz6aD2": [{"9qh17ZUf": "Rain", "6Nf5risL": "0", "40w6brpQ": "0", "jHstiL12": "0",
                                  "io30YcLA": "iPhone18,2_ios27.0.1", "K1G4fBjF": "1",
                                  "1WKh6Xqe": "ver.9100", "64anJRhx": "2026-11-04 17:57:27", "Y76dKryw": "US",
                                  "6e4ik6kA": "00000000-0000-0000-0000-000000000001",
                                  "NggnPgQC": "00000000-0000-0000-0000-000000000000"}],
                    "c402FmRD": [{"kZdGGshD": "0"}], "Euv8cncS": [{"K2jzG6bp": "1"}],
                    "c1qYg84Q": [{"a4hXTIm0": "F_APP_VERSION_IOS", "wM9AfX6I": "1167"},
                                 {"a4hXTIm0": "F_RSC_VERSION", "wM9AfX6I": "0"},
                                 {"a4hXTIm0": "F_MST_VERSION", "wM9AfX6I": "0"}]}).encode()
table = json.load(open(sys.argv[1] + '/server/endpoints.json'))['by_class']
ep = table['InitializeRequest']
envelope = json.dumps({
    "TEAYk6R1": {"z5hB3P01": ep["request_id"], "ytHoz4E2": str(int(time.time() * 1000)), "9K0Pzcpd": "1167"},
    "t7n6cVWf": {"qrVcDe48": c.cbc_encrypt(c.key16(ep['encode_key']), plain, double_pad=True)}}).encode()
url = f"https://v900-lapis.gumi.sg:{port}/lapisProd/app/php/gme/actionSymbol/{ep['url_token']}.php"
req = urllib.request.Request(url, data=envelope, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, context=ssl.create_default_context(cafile=ca), timeout=30) as r:
    raw = r.read()
inner = json.loads(raw)["t7n6cVWf"]
inner = inner[0] if isinstance(inner, list) else inner
out = c.cbc_decrypt(c.key16(ep['encode_key']), inner["qrVcDe48"])
pad = out[-1]
if 1 <= pad <= 16 and out[-pad:] == bytes([pad]) * pad:
    out = out[:-pad]
reply = json.loads(out)
rows = {r['a4hXTIm0']: r['wM9AfX6I'] for r in reply.get('c1qYg84Q', [])}
print(len(rows), 'rows')
for name in ('F_RSC_VERSION', 'F_MST_VERSION', 'F_DEFINE_MST', 'F_TEXT_TEXT_EN', 'F_MISSION_MST',
             'F_RESOURCE_VERSION_MST_LOCALIZE', 'F_RESOURCE_MST'):
    print(' ', name, rows.get(name))
print('below offset:', sorted(n for n, v in rows.items() if int(v) < 100000))

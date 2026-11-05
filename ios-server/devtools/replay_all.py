"""Replay captured iPhone requests (plaintext) to a local server; print switch rows of type 100/101 in each reply."""
import glob, json, ssl, sys, time, urllib.request
sys.path.insert(0, sys.argv[1] + '/server')
import ffbe_crypto as c
port, ca, files = int(sys.argv[2]), sys.argv[3], sys.argv[4:]
ctx = ssl.create_default_context(cafile=ca)
def walk(o, path, hits):
    if isinstance(o, dict):
        if '5opcUT9t' in o and 'juA0Z4m7' in o:
            hits.append((path, o['5opcUT9t'], o['juA0Z4m7']))
        for k, v in o.items(): walk(v, path + '/' + k, hits)
    elif isinstance(o, list):
        for v in o: walk(v, path, hits)
for f in files:
    d = json.load(open(f))
    ep, plain = d['endpoint'], d.get('plaintext')
    if not plain or not ep: continue
    env = json.dumps({"TEAYk6R1": {"z5hB3P01": ep["request_id"], "ytHoz4E2": str(int(time.time()*1000)), "9K0Pzcpd": "1167"},
                      "t7n6cVWf": {"qrVcDe48": c.cbc_encrypt(c.key16(ep['encode_key']), plain.encode(), double_pad=True)}}).encode()
    url = f"https://v900-lapis.gumi.sg:{port}/lapisProd/app/php/gme/actionSymbol/{ep['url_token']}.php"
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, data=env, headers={"Content-Type": "application/json"}), context=ctx, timeout=60).read()
        inner = json.loads(raw)["t7n6cVWf"]; inner = inner[0] if isinstance(inner, list) else inner
        out = c.cbc_decrypt(c.key16(ep['encode_key']), inner["qrVcDe48"])
        reply = json.JSONDecoder().raw_decode(out.decode('utf-8', 'replace'))[0]
    except Exception as e:
        print(ep['class'], 'ERR', e); continue
    hits = []; walk(reply, '', hits)
    print(ep['class'], [(p, t, b) for p, t, b in hits if t in ('100', '11', '101')])

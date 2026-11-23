import urllib.request, urllib.parse, json, pathlib, re, hashlib
from pypdf import PdfReader

OUT = pathlib.Path("/root/marfagenez/_dip26_txt")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36"}
KEYS = ["repair cost limit", "cost per unit time", "expected cost rate", "mean cost rate",
        "C(T)", "c(T)", "Weibull", "preventive maintenance", "replacement"]
PKG = pathlib.Path("/root/marfagenez/_dip26_harvest.json")


def get(url, timeout=45):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def wayback(url):
    enc = urllib.parse.quote(url, safe="")
    try:
        j = json.loads(get("http://archive.org/wayback/available?url=" + enc, 40))
    except Exception:
        return None
    c = (j.get("archived_snapshots") or {}).get("closest")
    if not c or not c.get("available"):
        return None
    u = c["url"]
    return re.sub(r"/web/(\d+)/", r"/web/\1id_/", u)


def extract(data, slug):
    pdf = OUT / (slug + ".pdf")
    pdf.write_bytes(data)
    rd = PdfReader(str(pdf))
    parts = []
    for i, p in enumerate(rd.pages):
        try:
            parts.append(p.extract_text() or "")
        except Exception:
            pass
    t = "\n".join(parts)
    (OUT / (slug + ".txt")).write_text(t, encoding="utf-8")
    return t


pool = json.load(open("/root/marfagenez/_dip26_pool2.json"))
res = json.load(open(PKG)) if PKG.exists() else {}
for wid, v in pool.items():
    doi = v["doi"].replace("https://doi.org/", "")
    slug = "h_" + re.sub(r"[^a-z0-9]+", "_", doi.lower())[:40]
    if slug in res:
        continue
    got = None
    for u in v["urls"]:
        if not u or not u.lower().startswith("http"):
            continue
        for cand in (u, wayback(u)):
            if not cand:
                continue
            try:
                data = get(cand, 50)
                if not data[:4] == b"%PDF":
                    continue
                t = extract(data, slug)
                got = (cand, len(t))
                break
            except Exception:
                continue
        if got:
            break
    if not got:
        res[slug] = {"doi": doi, "title": v["title"], "status": "nosource", "hits": {}}
        print(slug, "nosource")
        continue
    t = (OUT / (slug + ".txt")).read_text(encoding="utf-8", errors="replace").lower()
    hits = {k: t.count(k.lower()) for k in KEYS}
    res[slug] = {"doi": doi, "title": v["title"], "year": v["year"], "status": "ok",
                 "chars": got[1], "src": got[0][:140], "hits": hits}
    print(slug, got[1], {k: n for k, n in hits.items() if n})
    PKG.write_text(json.dumps(res, indent=1))
PKG.write_text(json.dumps(res, indent=1))
ok = [r for r in res.values() if r["status"] == "ok"]
print("OK", len(ok), "of", len(res))

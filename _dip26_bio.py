import urllib.request, urllib.parse, json, pathlib, re
from pypdf import PdfReader

KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
OUT = pathlib.Path("/root/marfagenez/_dip26_txt")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36"}


def get(url, timeout=50):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


QUERIES = [
    "optimal moult duration model cost feather replacement",
    "optimal replacement interval worn tissue cost model biology",
    "protein turnover cost benefit optimal degradation rate model",
]
cands = {}
for q in QUERIES:
    u = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
         + "&filter=is_oa:true&per-page=12&mailto=research@example.org&api_key=" + KEY)
    try:
        r = json.loads(get(u, 90))
    except Exception as e:
        print("QERR", e)
        continue
    print("===", q, r["meta"]["count"])
    for w in r["results"]:
        if not w.get("doi"):
            continue
        urls = []
        for L in w.get("locations") or []:
            if L.get("is_oa"):
                for k in ("pdf_url", "landing_page_url"):
                    if L.get(k):
                        urls.append(L[k])
        cands[w["doi"]] = {"title": w.get("title"), "year": w.get("publication_year"), "urls": urls}
        print("  ", w.get("publication_year"), (w.get("title") or "")[:95], "|", w["doi"], "| urls", len(urls))


def wayback(url):
    enc = urllib.parse.quote(url, safe="")
    try:
        j = json.loads(get("http://archive.org/wayback/available?url=" + enc, 30))
    except Exception:
        return None
    c = (j.get("archived_snapshots") or {}).get("closest")
    if not c or not c.get("available"):
        return None
    return re.sub(r"/web/(\d+)/", r"/web/\1id_/", c["url"])


ok = 0
for doi, v in list(cands.items())[:14]:
    slug = "b_" + re.sub(r"[^a-z0-9]+", "_", doi.replace("https://doi.org/", "").lower())[:38]
    if (OUT / (slug + ".txt")).exists():
        continue
    got = False
    for u in v["urls"]:
        for cand in (u, wayback(u)):
            if not cand:
                continue
            try:
                data = get(cand, 45)
                if data[:4] != b"%PDF":
                    continue
                p = OUT / (slug + ".pdf")
                p.write_bytes(data)
                rd = PdfReader(str(p))
                t = "\n".join((pg.extract_text() or "") for pg in rd.pages)
                (OUT / (slug + ".txt")).write_text(t, encoding="utf-8")
                low = t.lower()
                print("OK", slug, len(t), "|", v["title"][:70],
                      "| pt=", low.count("per unit time"), "opt=", low.count("optimal"),
                      "int=", low.count("interval"), "weib=", low.count("weibull"))
                got = True
                ok += 1
                break
            except Exception:
                continue
        if got:
            break
    if not got:
        print("--", slug, "nosource", v["title"][:60])
print("fetched", ok)

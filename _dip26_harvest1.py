import urllib.request, urllib.parse, json, pathlib

KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36"}


def get(url, timeout=60, headers=None):
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


QUERIES = [
    "repair cost limit replacement policy",
    "cumulative repair cost limit optimal replacement",
    "imperfect preventive maintenance cost rate model",
    "Barlow Proschan preventive maintenance cost",
    "Weibull failure replacement cost per unit time optimal",
    "age replacement policy optimal interval cost derivativ",
]
pool = {}
for q in QUERIES:
    u = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
         + "&filter=is_oa:true&per-page=20&mailto=research@example.org&api_key=" + KEY)
    try:
        r = json.loads(get(u, 90))
    except Exception as e:
        print("QERR", q, e)
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
        if w.get("open_access", {}).get("oa_url"):
            urls.append(w["open_access"]["oa_url"])
        pool[w["id"]] = {"doi": w["doi"], "title": w.get("title"), "year": w.get("publication_year"),
                         "urls": list(dict.fromkeys(urls)), "query": q}

pathlib.Path("/root/marfagenez/_dip26_pool2.json").write_text(json.dumps(pool, indent=1))
print("POOL2", len(pool))

import urllib.request, urllib.parse, json, pathlib

UA = {"User-Agent": "marfagenez-research/1.0 (mailto:research@example.org)"}
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/"


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


QUERIES = [
    '"protein turnover" AND "optimal" AND "cost" AND "damage"',
    '"repair or replace" AND "cell" AND "cost"',
    '"maintenance" AND "replacement" AND "optimal" AND "interval" AND "biological"',
    '"moult" AND "model" AND "energy" AND "interval"',
    '"wearing out" AND "replacement" AND "optimal" AND "life history"',
]
seen = {}
for q in QUERIES:
    u = (BASE + "search?query=" + urllib.parse.quote(q) + "&format=json&pageSize=12&resultType=core")
    try:
        r = json.loads(get(u, 60))
    except Exception as e:
        print("ERR", q, e)
        continue
    print("===", q, "hits", r.get("hitCount"))
    for it in (r.get("resultList") or {}).get("result") or []:
        pmcid = it.get("pmcid")
        if not pmcid:
            continue
        t = (it.get("title") or "")[:110]
        if pmcid in seen:
            continue
        seen[pmcid] = {"title": t, "year": it.get("pubYear"), "doi": it.get("doi")}
        print("  ", pmcid, it.get("pubYear"), "|", t)
pathlib.Path("/root/marfagenez/_dip26_pmc2.json").write_text(json.dumps(seen, indent=1))
print("PMC2", len(seen))

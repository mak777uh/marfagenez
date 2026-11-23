import urllib.request, urllib.parse, json, pathlib, re

UA = {"User-Agent": "marfagenez-research/1.0 (mailto:research@example.org)"}
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/"


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


QUERIES = [
    '"moult" AND "cost per unit time"',
    '"optimal" AND "replacement" AND "cost per unit time" AND "wear"',
    '"feather" AND "replacement" AND "optimal interval" AND "cost"',
    '"renewal" AND "tissue" AND "optimal" AND "cost of failure"',
    '"molt" AND "optimal" AND "interval" AND "cost"',
]
seen = {}
for q in QUERIES:
    u = (BASE + "search?query=" + urllib.parse.quote(q)
         + "&format=json&pageSize=15&resultType=core")
    try:
        r = json.loads(get(u, 60))
    except Exception as e:
        print("ERR", q, e)
        continue
    n = r.get("hitCount")
    print("===", q, "hits", n)
    for it in (r.get("resultList") or {}).get("result") or []:
        pmcid = it.get("pmcid")
        title = (it.get("title") or "")[:100]
        if not pmcid:
            continue
        seen[pmcid] = {"title": title, "year": it.get("pubYear"), "doi": it.get("doi"), "q": q}
        print("  ", pmcid, it.get("pubYear"), "|", title)
pathlib.Path("/root/marfagenez/_dip26_pmc.json").write_text(json.dumps(seen, indent=1), encoding="utf-8")
print("PMC", len(seen))

import json, os, subprocess, sys, urllib.parse

ROOT = "/root/marfagenez"
KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
CURL = "/mnt/c/Windows/System32/curl.exe"

QUERIES = [
    "lipid turnover rate membrane half-life",
    "ATP cost of lipid synthesis membrane maintenance energy",
    "membrane tension cell growth division",
    "vesicle division content loss membrane surface area",
    "osmotic stress membrane repair permeability",
    "lipid bilayer stability permeability energetic cost",
]

def get(url):
    p = subprocess.run([CURL, "-sS", url], capture_output=True, text=True, timeout=120)
    return p.stdout

pool = {}
log = []
for q in QUERIES:
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q) +
           "&per_page=20&select=id,doi,title,publication_year,abstract_inverted_index&api_key=" + KEY)
    body = get(url)
    try:
        data = json.loads(body)
    except Exception as e:
        log.append({"query": q, "error": str(e), "raw_head": body[:300]})
        continue
    n = 0
    for w in data.get("results", []):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        inv = w.get("abstract_inverted_index")
        if not doi:
            continue
        if doi not in pool:
            pool[doi] = {"doi": doi, "title": w.get("title"), "year": w.get("publication_year"),
                         "inv": inv, "queries": [q]}
            n += 1
        else:
            pool[doi]["queries"].append(q)
    log.append({"query": q, "returned": len(data.get("results", [])), "new": n})

def abstract(inv):
    if not inv:
        return ""
    pos = {}
    for tok, idxs in inv.items():
        for i in idxs:
            pos[i] = tok
    return " ".join(pos[i] for i in sorted(pos))

for doi, rec in pool.items():
    rec["abstract"] = abstract(rec.pop("inv"))

os.makedirs(ROOT + "/literature/dips/reports", exist_ok=True)
json.dump({"pool": pool, "log": log}, open(ROOT + "/literature/dips/reports/_dip12_pool.json", "w"),
          ensure_ascii=False, indent=1)

for l in log:
    print(l)
print("unique:", len(pool), "with abstract:", sum(1 for r in pool.values() if r["abstract"]))

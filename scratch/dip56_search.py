import json, os, urllib.request, urllib.parse

KEY = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
BASE = "https://api.openalex.org/works"
OUT = "/root/marfagenez/scratch/dip56_search.json"

def inv2text(inv):
    if not inv:
        return ""
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))

def search(q, n=6):
    params = {"search": q, "per-page": n, "mailto": "dip-research@example.org"}
    if KEY:
        params["api_key"] = KEY
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "dip-researcher/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    res = []
    for w in d.get("results", []):
        res.append({
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "year": w.get("publication_year"),
            "title": w.get("title"),
            "cited": w.get("cited_by_count"),
            "oa": (w.get("open_access") or {}).get("oa_url"),
            "pmcid": (w.get("ids") or {}).get("pmcid"),
            "abstract": inv2text(w.get("abstract_inverted_index")),
        })
    return res

queries = json.load(open('/root/marfagenez/scratch/dip56_queries.json'))
store = {}
for key, q in queries.items():
    try:
        store[key] = {"q": q, "results": search(q)}
    except Exception as e:
        store[key] = {"q": q, "error": repr(e)}

json.dump(store, open(OUT, "w"), ensure_ascii=False, indent=1)
for key, v in store.items():
    print("=== " + key + " :: " + v["q"])
    if "error" in v:
        print("  ERROR", v["error"])
        continue
    for r in v["results"]:
        print("  %s | %s | %s | cit=%s | %s" % (r["doi"], r["year"], (r["title"] or "")[:95], r["cited"], (r["pmcid"] or "")))
        if r["abstract"]:
            print("      ABS:", r["abstract"][:320].replace("\n", " "))

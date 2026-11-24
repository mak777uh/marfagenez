import json, sys, time, urllib.request, urllib.parse

KEY = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
BASE = "https://api.openalex.org/works"

def inv2text(inv):
    if not inv:
        return ""
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))

def search(q, n=6, tries=4):
    params = {"search": q, "per-page": n, "mailto": "dip-research@example.org"}
    if KEY:
        params["api_key"] = KEY
    url = BASE + "?" + urllib.parse.urlencode(params)
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dip-researcher/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.loads(r.read().decode())
            out = []
            for w in d.get("results", []):
                out.append({
                    "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "year": w.get("publication_year"),
                    "title": w.get("title"),
                    "cited": w.get("cited_by_count"),
                    "pmcid": (w.get("ids") or {}).get("pmcid"),
                    "abstract": inv2text(w.get("abstract_inverted_index")),
                })
            return out
        except Exception as e:
            last = e
            time.sleep(3 * (t + 1))
    raise last

qf = sys.argv[1]
queries = json.load(open(qf))
store = {}
for key, q in queries.items():
    try:
        store[key] = {"q": q, "results": search(q)}
    except Exception as e:
        store[key] = {"q": q, "error": repr(e)}
    time.sleep(1)
out = sys.argv[2]
json.dump(store, open(out, "w"), ensure_ascii=False, indent=1)
for key, v in store.items():
    print("=== " + key + " :: " + v["q"])
    if "error" in v:
        print("  ERROR", v["error"]); continue
    for r in v["results"]:
        print("  %s | %s | %s | cit=%s | %s" % (r["doi"], r["year"], (r["title"] or "")[:95], r["cited"], (r["pmcid"] or "")))
        if r["abstract"]:
            print("      ABS:", r["abstract"][:340].replace("\n", " "))

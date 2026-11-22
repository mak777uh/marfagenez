import json, subprocess, urllib.parse, textwrap

ROOT = "/root/marfagenez"
KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
CURL = "/mnt/c/Windows/System32/curl.exe"
pool = json.load(open(ROOT + "/literature/dips/reports/_dip12_pool.json"))
P = pool["pool"]

def ab(inv):
    pos = {}
    for t, ids in (inv or {}).items():
        for i in ids:
            pos[i] = t
    return " ".join(pos[i] for i in sorted(pos))

# look at a few pool abstracts of interest
for d in ["10.7554/elife.20437", "10.1073/pnas.1222254110", "10.1021/ja310382d", "10.1083/jcb.47.3.745"]:
    r = P.get(d)
    if r:
        print(f"\n### {d} | {r['year']} | {r['title']}\n" + textwrap.fill(r['abstract'], 150))

QUERIES = [
    "energy cost membrane area synthesis ATP per square micrometer",
    "membrane lipid synthesis rate measured molecules per second",
    "division septum membrane surface area inheritance daughter cell",
]
for q in QUERIES:
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q) +
           "&per_page=15&select=id,doi,title,publication_year,abstract_inverted_index&api_key=" + KEY)
    body = subprocess.run([CURL, "-sS", url], capture_output=True, text=True, timeout=120).stdout
    try:
        data = json.loads(body)
    except Exception as e:
        print("ERR", q, e); continue
    print("\n== ", q)
    for w in data.get("results", []):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        a = ab(w.get("abstract_inverted_index"))
        print(f"{w.get('publication_year')} {doi} | {(w.get('title') or '')[:110]}")
        if doi not in P:
            P[doi] = {"doi": doi, "title": w.get("title"), "year": w.get("publication_year"),
                      "abstract": a, "queries": [q]}
        if a:
            print("    " + textwrap.fill(a[:400], 140).replace("\n", "\n    "))

json.dump(pool, open(ROOT + "/literature/dips/reports/_dip12_pool.json", "w"), ensure_ascii=False, indent=1)

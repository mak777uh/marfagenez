import json, subprocess, urllib.parse

ROOT = "/root/marfagenez"
KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
CURL = "/mnt/c/Windows/System32/curl.exe"

QUERIES = [
    "phospholipid synthesis ATP requirement per molecule energetics",
    "membrane surface area growth rate lipid synthesis rate cell",
    "lipid vesicle division efficiency membrane loss daughter",
    "membrane permeability proton leak energy cost cell",
]

def get(url):
    p = subprocess.run([CURL, "-sS", url], capture_output=True, text=True, timeout=120)
    return p.stdout

pool = json.load(open(ROOT + "/literature/dips/reports/_dip12_pool.json"))
P = pool["pool"]

for q in QUERIES:
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q) +
           "&per_page=20&select=id,doi,title,publication_year,abstract_inverted_index&api_key=" + KEY)
    body = get(url)
    try:
        data = json.loads(body)
    except Exception as e:
        print("ERR", q, e, body[:200]); continue
    new = 0
    for w in data.get("results", []):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        if not doi or doi in P:
            continue
        inv = w.get("abstract_inverted_index")
        pos = {}
        for tok, idxs in (inv or {}).items():
            for i in idxs:
                pos[i] = tok
        P[doi] = {"doi": doi, "title": w.get("title"), "year": w.get("publication_year"),
                  "abstract": " ".join(pos[i] for i in sorted(pos)), "queries": [q]}
        new += 1
        print(f"{w.get('publication_year')} {doi}\n    {(w.get('title') or '')[:150]}\n    A[{len(P[doi]['abstract'])}]: {P[doi]['abstract'][:280]}")
    print(f"== {q}: +{new}")

json.dump(pool, open(ROOT + "/literature/dips/reports/_dip12_pool.json", "w"), ensure_ascii=False, indent=1)
print("total", len(P))

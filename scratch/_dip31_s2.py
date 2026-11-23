import urllib.request, urllib.parse, json, time
KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()

def get(url):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "api_key=" + KEY, headers={"User-Agent": "marfagenez-dip31"})
    return json.load(urllib.request.urlopen(req, timeout=60))

def abstract(w):
    inv = w.get("abstract_inverted_index")
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))

Q = [
 "proteasome Michaelis-Menten degradation kinetics substrate",
 "autophagy saturation kinetics degradation capacity",
 "aggregate clearance Michaelis-Menten kinetics protein",
 "proteasome capacity saturated overload degradation rate",
 "clearance half-life aggregate load concentration dependence",
]
out = json.load(open("/root/marfagenez/_dip31_pool.json"))
for q in Q:
    url = ("https://api.openalex.org/works?filter=has_abstract:true,title_and_abstract.search:"
           + urllib.parse.quote(q) + "&per_page=25&sort=relevance_score:desc&mailto=research@marfagenez.local")
    try:
        d = get(url)
    except Exception as e:
        print("ERR", q, e)
        continue
    print(q, "->", d["meta"]["count"])
    for w in d.get("results", []):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        if not doi:
            continue
        if doi not in out:
            out[doi] = {"title": w.get("title"), "year": w.get("publication_year"), "doi": doi,
                        "abstract": abstract(w), "cited": w.get("cited_by_count"),
                        "venue": (((w.get("primary_location") or {}).get("source") or {}).get("display_name"))}
    time.sleep(0.3)
json.dump(out, open("/root/marfagenez/_dip31_pool.json", "w"), ensure_ascii=False, indent=1)
print("pool", len(out))

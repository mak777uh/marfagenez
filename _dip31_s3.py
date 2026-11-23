import urllib.request, urllib.parse, json, time, re
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
 '"proteasome capacity" saturation',
 '"autophagic capacity" aggregates',
 'protein degradation proteasome "Michaelis-Menten"',
 'saturable clearance amyloid beta transport Km',
 'degradation capacity overload proteostasis aggregates',
]
out = json.load(open("/root/marfagenez/_dip31_pool.json"))
for q in Q:
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
           + "&per_page=25&filter=has_abstract:true&sort=relevance_score:desc&mailto=research@marfagenez.local")
    try:
        d = get(url)
    except Exception as e:
        print("ERR", q, e)
        continue
    print("==", q, "->", d["meta"]["count"])
    for w in d.get("results", []):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        if not doi:
            continue
        ab = abstract(w)
        if doi not in out:
            out[doi] = {"title": w.get("title"), "year": w.get("publication_year"), "doi": doi,
                        "abstract": ab, "cited": w.get("cited_by_count"),
                        "venue": (((w.get("primary_location") or {}).get("source") or {}).get("display_name"))}
        low = ab.lower()
        if any(k in low for k in ["saturat", "km", "vmax", "michaelis", "half-life", "half life"]):
            print("  *", w.get("publication_year"), doi, "|", (w.get("title") or "")[:100])
    time.sleep(0.3)
json.dump(out, open("/root/marfagenez/_dip31_pool.json", "w"), ensure_ascii=False, indent=1)
print("pool", len(out))

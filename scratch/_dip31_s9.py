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

FILTERS = [
 'has_abstract:true,title.search:proteasome,abstract.search:kinetic',
 'has_abstract:true,title.search:autophagy,abstract.search:saturation',
 'has_abstract:true,title.search:aggregate,abstract.search:clearance',
 'has_abstract:true,title.search:proteolysis,abstract.search:saturable',
 'has_abstract:true,title.search:degradation,abstract.search:"Km value"',
]
STRICT = re.compile(r"((km|vmax)\b[^.]{0,60}\d)|(\d[^.]{0,60}(saturat|plateau|half-saturat|maximal (rate|velocity)))", re.I)
out = json.load(open("/root/marfagenez/_dip31_pool.json"))
seen = set()
for f in FILTERS:
    url = ("https://api.openalex.org/works?filter=" + urllib.parse.quote(f, safe=":,\"")
           + "&per_page=40&sort=relevance_score:desc&mailto=research@marfagenez.local")
    try:
        d = get(url)
    except Exception as e:
        print("ERR", f, e); continue
    print("==", f, "->", d["meta"]["count"])
    for w in d.get("results", []):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        if not doi:
            continue
        ab = abstract(w)
        if doi not in out:
            out[doi] = {"title": w.get("title"), "year": w.get("publication_year"), "doi": doi,
                        "abstract": ab, "cited": w.get("cited_by_count"),
                        "venue": (((w.get("primary_location") or {}).get("source") or {}).get("display_name"))}
        if doi in seen:
            continue
        sents = re.split(r"(?<=[.;])\s+", ab)
        hits = [s for s in sents if STRICT.search(s)]
        if hits:
            seen.add(doi)
            print("  *", w.get("publication_year"), doi, "|", (w.get("title") or "")[:88])
            for s in hits[:3]:
                print("       ", s[:300])
    time.sleep(0.3)
json.dump(out, open("/root/marfagenez/_dip31_pool.json", "w"), ensure_ascii=False, indent=1)
print("pool", len(out))

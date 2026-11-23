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
 'saturable clearance denatured albumin scavenger receptor Km',
 'chaperone-mediated autophagy substrate Km saturation',
 'autophagic degradation aggregated protein saturation load',
 'proteasome oxidized protein degradation saturation Km',
 'ERAD capacity saturation substrate load degradation',
 'receptor-mediated endocytosis aggregated protein clearance Vmax Km',
]
KW = re.compile(r"(saturat|half-life|half life|michaelis|vmax|\bkm\b|capacity|clearance rate|plateau)", re.I)
out = json.load(open("/root/marfagenez/_dip31_pool.json"))
seen = set()
for q in Q:
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
           + "&per_page=30&filter=has_abstract:true&sort=relevance_score:desc&mailto=research@marfagenez.local")
    try:
        d = get(url)
    except Exception as e:
        print("ERR", q, e); continue
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
        if doi in seen:
            continue
        sents = re.split(r"(?<=[.;])\s+", ab)
        hits = [s for s in sents if KW.search(s) and re.search(r"\d", s)]
        if hits:
            seen.add(doi)
            print("  *", w.get("publication_year"), doi, "|", (w.get("title") or "")[:88])
            for s in hits[:2]:
                print("       ", s[:280])
    time.sleep(0.3)
json.dump(out, open("/root/marfagenez/_dip31_pool.json", "w"), ensure_ascii=False, indent=1)
print("pool", len(out))

import urllib.request, urllib.parse, json, time
KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
DOIS = [
 "10.1523/jneurosci.2236-04.2004",
 "10.4049/jimmunol.123.5.2040",
 "10.1083/jcb.98.1.22",
 "10.1021/bi00131a033",
 "10.1021/bi00260a012",
 "10.1371/journal.pone.0207836",
]

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

out = {}
for doi in DOIS:
    url = "https://api.openalex.org/works/https://doi.org/" + doi
    try:
        w = get(url)
    except Exception as e:
        print("FAIL", doi, e)
        continue
    ab = abstract(w)
    out[doi] = {"title": w.get("title"), "year": w.get("publication_year"), "doi": doi,
                "abstract": ab, "cited": w.get("cited_by_count"),
                "venue": (((w.get("primary_location") or {}).get("source") or {}).get("display_name")),
                "type": w.get("type")}
    print("OK", doi, "|", w.get("publication_year"), "|", w.get("title")[:80], "| abstract chars:", len(ab))
    time.sleep(0.3)
json.dump(out, open("/root/marfagenez/_dip31_verified.json", "w"), ensure_ascii=False, indent=1)

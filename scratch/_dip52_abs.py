import json, sys, urllib.parse, urllib.request, pathlib

KEY = pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "marfagenez-dip (mailto:dip@marfagenez.local)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def recon(inv):
    if not inv:
        return ""
    pos = {}
    for tok, idxs in inv.items():
        for i in idxs:
            pos[i] = tok
    return " ".join(pos[i] for i in sorted(pos))

dois = json.loads(sys.argv[1])
out = []
for d in dois:
    url = "https://api.openalex.org/works/https://doi.org/" + d + "?api_key=" + KEY
    try:
        w = get(url)
    except Exception as e:
        print("MISS", d, e); continue
    ab = recon(w.get("abstract_inverted_index"))
    rec = {"doi": (w.get("doi") or "").replace("https://doi.org/", ""),
           "title": w.get("title"), "year": w.get("publication_year"),
           "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
           "oa": (w.get("open_access") or {}).get("oa_status"),
           "oaurl": (w.get("open_access") or {}).get("oa_url"),
           "cited": w.get("cited_by_count"),
           "abstract": ab}
    out.append(rec)
    print("=" * 100)
    print(d, "|", rec["year"], "|", rec["oa"], "|", rec["venue"])
    print(rec["title"])
    print(ab if ab else "(no abstract)")
pathlib.Path("/root/marfagenez/scratch/_dip52_abs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

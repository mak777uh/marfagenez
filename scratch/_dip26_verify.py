import json, pathlib, urllib.request, time

KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
UA = {"User-Agent": "marfagenez/1.0 (mailto:research@example.org)"}

DOIS = ["10.13189/ujme.2020.080601", "10.1016/j.ress.2005.03.012", "10.17929/tqs.8.51",
        "10.1214/16-BJPS317", "10.5784/15-0-417", "10.17531/ein.2022.3.15",
        "10.1093/plphys/kiag481"]
out = {}
for doi in DOIS:
    u = "https://api.openalex.org/works/https://doi.org/" + doi + "?api_key=" + KEY + "&mailto=research@example.org"
    try:
        w = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
        out[doi] = {"title": w.get("title"), "year": w.get("publication_year"),
                    "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                    "type": w.get("type"), "oa": (w.get("open_access") or {}).get("is_oa"),
                    "authors": [a["author"]["display_name"] for a in (w.get("authorships") or [])][:3]}
        print(doi, "|", out[doi]["year"], "|", out[doi]["title"], "|", out[doi]["venue"])
    except Exception as e:
        print(doi, "FAIL", str(e)[:90])
        out[doi] = {"error": str(e)[:90]}
    time.sleep(0.3)
pathlib.Path("/root/marfagenez/_dip26_dois.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

# look at existing gap atom convention
atoms = pathlib.Path("/root/marfagenez/literature/map/atoms.jsonl")
if atoms.exists():
    n = 0
    for line in atoms.read_text(encoding="utf-8").splitlines():
        if '"gap"' in line:
            a = json.loads(line)
            if a.get("kind") == "gap" and n < 2:
                print("GAP SAMPLE", json.dumps(a, ensure_ascii=False)[:1200])
                n += 1

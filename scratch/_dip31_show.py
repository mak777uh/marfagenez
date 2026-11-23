import json, sys
p = json.load(open("/root/marfagenez/_dip31_pool.json"))
for doi in sys.argv[1:]:
    w = p.get(doi)
    if not w:
        print("MISSING", doi); continue
    print("=" * 100)
    print(doi, "|", w["year"], "|", w["title"])
    print(w["abstract"])

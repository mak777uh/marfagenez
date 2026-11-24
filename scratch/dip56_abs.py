import json, glob, sys
want = [w.lower() for w in sys.argv[1:]]
seen = {}
for f in glob.glob("/root/marfagenez/scratch/dip56_search*.json"):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    for k, v in d.items():
        for r in v.get("results", []):
            doi = (r.get("doi") or "").lower()
            if doi in want and doi not in seen:
                seen[doi] = r
for w in want:
    r = seen.get(w)
    print("=====", w)
    if not r:
        print("  (not found in stored results)")
        continue
    print("  T:", r["title"], "|", r["year"], "| cit", r["cited"])
    print("  ABS:", r["abstract"][:2200])

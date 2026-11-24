import json

P = "/root/marfagenez/literature/dips/reports/dip-2026-11-24-56.jsonl"
KINDS = {"mechanism","formula","measurement","condition","contradiction","gap","definition"}
REQ = ["atom","statement","domain","kind","mechanism","formula","symbols","conditions","works","confidence","locator_status","tags","notes"]
ok = True
rows = [json.loads(l) for l in open(P) if l.strip()]
atoms = set()
for r in rows:
    miss = [k for k in REQ if k not in r]
    if miss:
        ok = False; print("MISSING", r.get("atom"), miss)
    if r["kind"] not in KINDS:
        ok = False; print("BAD KIND", r["atom"], r["kind"])
    if r["domain"] != "membranes.bioenergetics":
        ok = False; print("BAD DOMAIN", r["atom"])
    if r["confidence"] != "medium" or r["locator_status"] != "verified":
        ok = False; print("BAD CONF/STATUS", r["atom"])
    if r["atom"] in atoms:
        ok = False; print("DUP ATOM", r["atom"])
    atoms.add(r["atom"])
    for w in r["works"]:
        for k in ("doi","locator","access","quote"):
            if k not in w or not w[k]:
                ok = False; print("BAD WORK", r["atom"], k)
        n = len(w["quote"].split())
        if n < 10 or n > 30:
            ok = False; print("BAD QUOTE LEN", r["atom"], n)
print("cells:", len(rows), "| unique atoms:", len(atoms), "| structural ok:", ok)
print()
for r in rows:
    w = r["works"][0]
    print("%s [%s] %s" % (r["atom"], r["kind"], w["doi"]))
    print("   Q(%d words): %s" % (len(w["quote"].split()), w["quote"]))
    print("   LOC:", w["locator"], "| access:", w["access"])
    print()

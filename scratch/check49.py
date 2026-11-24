import json

p = "/root/marfagenez/literature/dips/reports/dip-2026-11-23-49.jsonl"
rows = [json.loads(l) for l in open(p)]
print("rows", len(rows))
dois = set()
for r in rows:
    assert r["domain"] == "reliability.maintenance", r["atom"]
    assert r["confidence"] == "medium"
    assert r["locator_status"] == "verified"
    for w in r["works"]:
        dois.add(w["doi"])
        assert len(w["quote"].split()) >= 9, (r["atom"], w["quote"])
    print(r["atom"], "|", r["kind"], "|", len(r["statement"]), "chars |", len(r["works"]), "works |", r["tags"][:3])
print("unique DOIs", len(dois))
for d in sorted(dois):
    print(" ", d)

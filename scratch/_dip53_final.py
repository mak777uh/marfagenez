import json, pathlib
p = pathlib.Path("/root/marfagenez/literature/dips/reports/dip-2026-11-23-53.jsonl")
rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
allowed = {"mechanism","formula","measurement","condition","contradiction","gap","definition"}
for r in rows:
    q = r["works"][0]["quote"]
    wc = len(q.split())
    assert r["kind"] in allowed
    assert set(["atom","statement","domain","kind","mechanism","formula","symbols","conditions","works","confidence","locator_status","tags","notes"]).issubset(r)
    assert r["domain"] == "bio.integration" and r["confidence"] == "medium" and r["locator_status"] == "verified"
    print(r["atom"], r["kind"], "quote_words=%d" % wc, r["works"][0]["doi"])
print("rows", len(rows))

import json, subprocess, urllib.parse, pathlib
KEY = pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()
CURL = "/mnt/c/Windows/System32/curl.exe"
qs = ['"Deborah number" mucus rheology',
      '"Deborah number" blood relaxation time measurement',
      'mucus viscoelastic relaxation time Deborah number airway']
for q in qs:
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
        "search": q, "per-page": "12", "api_key": KEY,
        "select": "doi,title,publication_year,abstract_inverted_index,open_access"})
    out = subprocess.run([CURL, "-sL", "-m", "60", url], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    d = json.loads(out)
    print("=====", q)
    for w in d.get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        pos = sorted((i, t) for t, ids in inv.items() for i in ids)
        ab = " ".join(t for _, t in pos)
        import re
        if re.search(r"Deborah", ab, re.I):
            print(w.get("publication_year"), (w.get("doi") or "")[:45], (w.get("title") or "")[:85], "OA" if (w.get("open_access") or {}).get("is_oa") else "")
            print("   ", ab[:400])

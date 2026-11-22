import json, subprocess, textwrap, unicodedata, re

KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
CURL = "/mnt/c/Windows/System32/curl.exe"

def ab(inv):
    pos = {}
    for t, ids in (inv or {}).items():
        for i in ids:
            pos[i] = t
    return " ".join(pos[i] for i in sorted(pos))

for doi in ["10.1042/bj1010618", "10.1073/pnas.2318412121", "10.1016/j.chembiol.2016.03.007",
            "10.1085/jgp.50.6.1765", "10.1021/ja202406v"]:
    url = ("https://api.openalex.org/works/https://doi.org/" + doi +
           "?api_key=" + KEY + "&select=id,doi,title,publication_year,abstract_inverted_index")
    body = subprocess.run([CURL, "-sS", url], capture_output=True, text=True, timeout=120).stdout
    try:
        w = json.loads(body)
    except Exception:
        print("BAD", doi, body[:120]); continue
    a = ab(w.get("abstract_inverted_index"))
    print(f"\n=== {doi} | {w.get('publication_year')} | {w.get('title')}")
    print(f"    abstract chars: {len(a)}")
    print(textwrap.fill(a, 140))

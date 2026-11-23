import json, sys, urllib.parse, urllib.request, os

KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()

def search(q, n=8, extra=""):
    params = {
        "search": q,
        "per-page": str(n),
        "mailto": "marfagenez@proton.me",
        "api_key": KEY,
    }
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params) + extra
    req = urllib.request.Request(url, headers={"User-Agent": "marfagenez-dip/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

if __name__ == "__main__":
    for q in sys.argv[1:]:
        print("=" * 20, q)
        try:
            d = search(q)
        except Exception as e:
            print("ERR", e)
            continue
        for w in d.get("results", []):
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
            print(w.get("publication_year"), "|", (w.get("title") or "")[:105], "|", w.get("doi"), "|", src, "| cites", w.get("cited_by_count"))

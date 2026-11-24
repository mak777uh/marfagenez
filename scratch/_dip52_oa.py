import json, sys, urllib.parse, urllib.request, os, pathlib

KEY = pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "marfagenez-dip (mailto:dip@marfagenez.local)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def search(q, n=10, extra=""):
    base = "https://api.openalex.org/works?"
    params = {"search": q, "per_page": n,
              "select": "id,doi,title,publication_year,open_access,type",
              "api_key": KEY}
    url = base + urllib.parse.urlencode(params) + extra
    d = get(url)
    out = []
    for w in d.get("results", []):
        out.append({"doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "title": w.get("title"), "year": w.get("publication_year"),
                    "oa": (w.get("open_access") or {}).get("oa_status"),
                    "oaurl": (w.get("open_access") or {}).get("oa_url")})
    return out

if __name__ == "__main__":
    qs = json.loads(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    for q in qs:
        print("### " + q)
        try:
            for r in search(q, n):
                print(f"  {r['doi']}  [{r['year']}] [{r['oa']}]  {r['title'][:120]}")
        except Exception as e:
            print("  ERR", e)

import json, sys, urllib.parse, urllib.request

UA = {"User-Agent": "marfagenez-dip/1.0 (mailto:marfagenez@proton.me)"}

def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def search(q, n=12, oa=True):
    if oa:
        q = "(%s) AND (OPEN_ACCESS:y) AND (HAS_FT:y)" % q
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": q, "format": "json", "resultType": "lite", "pageSize": str(n), "sort": "CITED desc"})
    d = json.loads(get(url))
    print("HITS", d.get("hitCount"))
    for r in d.get("resultList", {}).get("result", []):
        print(r.get("pubYear"), "|", (r.get("title") or "")[:100], "|", r.get("doi"), "|", r.get("pmcid"), "|", (r.get("journalTitle") or "")[:40])

if __name__ == "__main__":
    for q in sys.argv[1:]:
        print("=" * 15, q)
        try:
            search(q)
        except Exception as e:
            print("ERR", e)

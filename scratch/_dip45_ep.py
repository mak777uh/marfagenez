import json, subprocess, urllib.parse, sys


def curl(url):
    r = subprocess.run(["curl", "-s", "-m", "60", url], capture_output=True, text=True)
    return r.stdout


def search(q, n=8):
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?" +
           urllib.parse.urlencode({"query": q, "format": "json",
                                   "pageSize": str(n), "resultType": "lite"}))
    raw = curl(url)
    try:
        d = json.loads(raw)
    except Exception:
        print("PARSE FAIL", q, raw[:200]); return
    print("### %s -> %s" % (q, d.get("hitCount")))
    for r in d.get("resultList", {}).get("result", []):
        print("  ", r.get("pubYear"), r.get("pmcid"), r.get("doi"), "|",
              (r.get("title") or "")[:95])
    print()


if __name__ == "__main__":
    for q in sys.argv[1:]:
        search(q)

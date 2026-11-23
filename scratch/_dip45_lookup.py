import json, subprocess, urllib.parse, sys

def curl(url):
    r = subprocess.run(["curl", "-s", "-m", "60", url], capture_output=True, text=True)
    return r.stdout

def lookup(doi):
    q = 'DOI:"%s"' % doi
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": q, "format": "json", "resultType": "core", "pageSize": "3"})
    try:
        d = json.loads(curl(url))
    except Exception:
        print("FAIL", doi); return
    for r in d.get("resultList", {}).get("result", []):
        print("===", doi)
        print("pmcid:", r.get("pmcid"), "| pmid:", r.get("pmid"), "| year:", r.get("pubYear"))
        print("title:", r.get("title"))
        print("journal:", (r.get("journalInfo") or {}).get("journal", {}).get("title"))
        print("OA:", r.get("isOpenAccess"), "| inEPMC:", r.get("inEPMC"))
        print()

if __name__ == "__main__":
    for d in sys.argv[1:]:
        lookup(d)

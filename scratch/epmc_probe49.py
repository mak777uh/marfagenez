import json, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "marfagenez-dip/1.0 (mailto:marfagenez@proton.me)"}

def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def epmc_search(q, n=10):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": q, "format": "json", "resultType": "core", "pageSize": str(n)})
    return json.loads(get(url))

def find_pmcid(doi):
    d = epmc_search('DOI:"%s"' % doi, 3)
    out = []
    for r in d.get("resultList", {}).get("result", []):
        out.append((r.get("pmcid"), r.get("pmid"), r.get("isOpenAccess"), r.get("title"), r.get("id")))
    return out

def fulltext(pmcid):
    return get("https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid).decode("utf-8", "replace")

def strip(x):
    x = re.sub(r"<[^>]+>", " ", x)
    x = re.sub(r"\s+", " ", x)
    return x

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "pmc":
        for doi in sys.argv[2:]:
            print("DOIPMC", doi, find_pmcid(doi))
    elif mode == "grep":
        pmcid = sys.argv[2]
        pats = sys.argv[3:]
        xml = fulltext(pmcid)
        txt = strip(xml)
        print("LEN", len(txt))
        for pat in pats:
            print("-" * 10, pat)
            for m in re.finditer(pat, txt, re.I):
                s = max(0, m.start() - 350); e = min(len(txt), m.end() + 350)
                print("...", txt[s:e].strip(), "...")
                print()
    elif mode == "save":
        pmcid = sys.argv[2]
        open("/root/marfagenez/scratch/%s.txt" % pmcid, "w").write(strip(fulltext(pmcid)))
        print("saved", pmcid)

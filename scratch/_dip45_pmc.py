import json, subprocess, urllib.parse, sys, re, os

KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()


def curl(url):
    r = subprocess.run(["curl", "-s", "-m", "60", url], capture_output=True, text=True)
    return r.stdout


def openalex_work(doi):
    url = ("https://api.openalex.org/works/https://doi.org/" +
           urllib.parse.quote(doi, safe="") + "?" + urllib.parse.urlencode({"api_key": KEY}))
    try:
        return json.loads(curl(url))
    except Exception:
        return None


def pmcid_from_openalex(w):
    out = []
    for loc in w.get("locations") or []:
        for k, v in (loc.get("source") or {}).items():
            pass
        ids = loc.get("ids") or {}
        if ids.get("pmcid"):
            out.append(ids["pmcid"].split("/")[-1])
    if w.get("ids", {}).get("pmcid"):
        out.insert(0, w["ids"]["pmcid"].split("/")[-1])
    return list(dict.fromkeys(out))


def pmcid_from_epmc(doi):
    q = 'DOI:"%s"' % doi
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?" +
           urllib.parse.urlencode({"query": q, "format": "json", "resultType": "lite", "pageSize": "5"}))
    try:
        d = json.loads(curl(url))
        return [r["pmcid"] for r in d.get("resultList", {}).get("result", []) if r.get("pmcid")]
    except Exception:
        return []


def fulltext(pmcid):
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid)
    return curl(url)


def strip_tags(xml):
    xml = re.sub(r"<ref-list.*?</ref-list>", " ", xml, flags=re.S)
    xml = re.sub(r"<xref[^>]*>.*?</xref>", "", xml, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", xml)
    t = re.sub(r"&lt;", "<", t); t = re.sub(r"&gt;", ">", t)
    t = re.sub(r"&amp;", "&", t); t = re.sub(r"&#x[0-9a-fA-F]+;", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def sentence_hits(text, patterns, maxn=40):
    sents = re.split(r"(?<=[.!?])\s+", text)
    hits = []
    for s in sents:
        low = s.lower()
        if not re.search(r"\d", s):
            continue
        if any(p in low for p in patterns):
            hits.append(s.strip())
        if len(hits) >= maxn:
            break
    return hits


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "resolve":
        for doi in sys.argv[2:]:
            w = openalex_work(doi)
            ids = pmcid_from_openalex(w) if w else []
            ep = pmcid_from_epmc(doi)
            print(doi, "| openalex:", ids, "| epmc:", ep,
                  "| title:", (w or {}).get("display_name", "")[:80])
    elif mode == "ft":
        # ft <pmcid> <pattern1,pattern2,...>
        pmcid = sys.argv[2]
        pats = [p.strip().lower() for p in sys.argv[3].split(",")]
        xml = fulltext(pmcid)
        if not xml or "fullTextXML" in xml and len(xml) < 500:
            print("NO FULLTEXT", pmcid, xml[:200]); sys.exit(0)
        if "<body" not in xml:
            print("NO BODY", pmcid, "len", len(xml)); sys.exit(0)
        txt = strip_tags(xml)
        print("LEN", len(txt))
        for s in sentence_hits(txt, pats, maxn=int(sys.argv[4]) if len(sys.argv) > 4 else 40):
            print("-", s)

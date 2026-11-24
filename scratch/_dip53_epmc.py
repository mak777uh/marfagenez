import json, re, subprocess, urllib.parse, pathlib, time, html

ROOT = pathlib.Path("/root/marfagenez")
CURL = "/mnt/c/Windows/System32/curl.exe"
CACHE = ROOT / "scratch" / "_dip53_xml"
CACHE.mkdir(exist_ok=True)

def curl(url, timeout=90):
    r = subprocess.run([CURL, "-sL", "-m", str(timeout), url], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout

def epmc_search(query, page=100):
    params = {"query": query, "format": "json", "pageSize": str(page), "resultType": "lite"}
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(params)
    txt = curl(url)
    try:
        d = json.loads(txt)
    except Exception:
        print("SEARCH ERR", txt[:200]); return []
    return d.get("resultList", {}).get("result", [])

def fulltext(pmcid):
    f = CACHE / f"{pmcid}.xml"
    if f.exists() and f.stat().st_size > 2000:
        return f.read_text(encoding="utf-8", errors="replace")
    txt = curl(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML", 120)
    if len(txt) < 2000 or "<body" not in txt:
        txt2 = curl(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmcid}&retmode=xml", 120)
        if len(txt2) > len(txt): txt = txt2
    f.write_text(txt, encoding="utf-8")
    return txt

TAG = re.compile(r"<[^>]+>")

def sections(xml):
    """Yield (section_title, plain_text) preserving section boundaries."""
    # split by sec tags roughly
    parts = re.split(r"(<sec[ >])", xml)
    out = []
    # simpler: iterate over <title> inside sec is hard; use block split on </sec>
    chunks = re.split(r"</sec>", xml)
    for ch in chunks:
        m = re.findall(r"<title>(.*?)</title>", ch, re.S)
        title = TAG.sub(" ", m[-1]).strip() if m else ""
        body = TAG.sub(" ", ch)
        body = html.unescape(re.sub(r"\s+", " ", body)).strip()
        out.append((title, body))
    return out

def sentences(text):
    # keep sentence-ish spans
    return re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text)

TERMS = ["Damk", "P[eé]clet", "Deborah", "Thiele", "Biot", "Sherwood", "Knudsen"]

def scan(xml, terms=TERMS, maxhits=6):
    hits = []
    for title, body in sections(xml):
        for sent in sentences(body):
            if not re.search(r"\d", sent): continue
            for t in terms:
                if re.search(t, sent, re.I):
                    hits.append({"section": title, "sentence": sent.strip()[:600]})
                    break
            if len(hits) >= maxhits: break
        if len(hits) >= maxhits: break
    return hits

if __name__ == "__main__":
    import sys
    q = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    res = epmc_search(q)
    print(len(res), "hits")
    for r in res[:n]:
        print(r.get("pubYear"), r.get("pmcid"), r.get("doi"), "|", (r.get("title") or "")[:100])

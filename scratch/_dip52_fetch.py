import json, sys, pathlib, re, urllib.request, urllib.parse

KEY = pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()
OUT = pathlib.Path("/root/marfagenez/scratch/dip52")
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("content-type", "")


def oa_meta(doi):
    url = "https://api.openalex.org/works/https://doi.org/" + doi + "?api_key=" + KEY
    req = urllib.request.Request(url, headers={"User-Agent": "dip52"})
    with urllib.request.urlopen(req, timeout=60) as r:
        w = json.load(r)
    return w


def text_of(blob, ctype, name):
    if blob[:4] == b"%PDF" or "pdf" in ctype:
        import pymupdf
        doc = pymupdf.open(stream=blob, filetype="pdf")
        return "\n".join(p.get_text() for p in doc)
    s = blob.decode("utf-8", "replace")
    if "<" in s[:2000]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(s, "lxml")
        for t in soup(["script", "style", "nav", "footer", "header"]):
            t.decompose()
        return soup.get_text("\n")
    if s.lstrip().startswith("<?xml"):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(s, "xml")
        return soup.get_text("\n")
    return s


def grab(doi, urls):
    for u in urls:
        try:
            blob, ct = fetch(u)
            if len(blob) < 5000:
                print("   small", len(blob), u); continue
            t = text_of(blob, ct, u)
            if len(t) < 4000:
                print("   shorttext", len(t), u); continue
            p = OUT / (doi.replace("/", "_") + ".txt")
            p.write_text(t, encoding="utf-8")
            print(f"   OK {len(t)} chars <- {u[:90]}")
            return p
        except Exception as e:
            print("   fail", type(e).__name__, str(e)[:70], u[:80])
    return None


if __name__ == "__main__":
    dois = json.loads(sys.argv[1])
    for doi in dois:
        print("==", doi)
        try:
            w = oa_meta(doi)
        except Exception as e:
            print("   no meta", e); continue
        oa = (w.get("open_access") or {})
        urls = []
        cand = [oa.get("oa_url")] if oa.get("oa_url") else []
        for loc in (w.get("locations") or []):
            if loc.get("pdf_url"):
                cand.append(loc["pdf_url"])
            if loc.get("landing_page_url"):
                cand.append(loc["landing_page_url"])
        ids = w.get("ids") or {}
        for k in ("pmcid", "pmid"):
            if ids.get(k):
                cand.append(ids[k])
        # Elsevier/PMC routes
        for c in list(cand):
            if isinstance(c, str) and c.startswith("PMC"):
                n = c.replace("PMC", "")
                urls.append(f"https://www.ebi.ac.uk/europepmc/webservices/rest/PMC{n}/fullTextXML")
                urls.append(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={n}&retmode=xml")
        urls += [c for c in cand if isinstance(c, str) and c.startswith("http")]
        seen = []
        for u in urls:
            if u not in seen:
                seen.append(u)
        grab(doi, seen[:8])

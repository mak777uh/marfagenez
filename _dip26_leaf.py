import urllib.request, urllib.parse, json, pathlib, re
from pypdf import PdfReader

OUT = pathlib.Path("/root/marfagenez/_dip26_txt")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36"}
KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def wayback(url):
    enc = urllib.parse.quote(url, safe="")
    try:
        j = json.loads(get("http://archive.org/wayback/available?url=" + enc, 30))
    except Exception:
        return None
    c = (j.get("archived_snapshots") or {}).get("closest")
    if not c or not c.get("available"):
        return None
    return re.sub(r"/web/(\d+)/", r"/web/\1id_/", c["url"])


dois = ["10.1093/aob/mci050"]
for doi in dois:
    meta = json.loads(get("https://api.openalex.org/works/https://doi.org/" + doi + "?api_key=" + KEY, 60))
    urls = []
    for L in meta.get("locations") or []:
        if L.get("is_oa"):
            for k in ("pdf_url", "landing_page_url"):
                if L.get(k):
                    urls.append(L[k])
    print(doi, "|", meta.get("title"), "|", meta.get("publication_year"), "| urls", len(urls))
    slug = "b_leaf_turnover"
    for u in urls:
        for cand in (u, wayback(u)):
            if not cand:
                continue
            try:
                data = get(cand, 50)
                if data[:4] != b"%PDF":
                    continue
                p = OUT / (slug + ".pdf")
                p.write_bytes(data)
                rd = PdfReader(str(p))
                t = "\n".join((pg.extract_text() or "") for pg in rd.pages)
                (OUT / (slug + ".txt")).write_text(t, encoding="utf-8")
                print("OK", slug, len(t), cand[:90])
                raise SystemExit
            except SystemExit:
                raise
            except Exception as e:
                continue
    print("FAIL", doi)

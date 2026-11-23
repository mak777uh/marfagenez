import urllib.request, pathlib, sys

OUT = pathlib.Path("/root/marfagenez/_dip26_txt")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36"}
from pypdf import PdfReader


def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        dest.write_bytes(r.read())


def extract(pdf, txt):
    rd = PdfReader(str(pdf))
    parts = []
    for i, p in enumerate(rd.pages):
        try:
            parts.append("\n[[page %d]]\n" % (i + 1) + (p.extract_text() or ""))
        except Exception:
            parts.append("\n[[page %d ERR]]\n" % (i + 1))
    txt.write_text("".join(parts), encoding="utf-8")
    return len("".join(parts))


JOBS = {
    "rairo93": "http://web.archive.org/web/20250518100758id_/https://www.rairo-ro.org/articles/ro/pdf/1993/03/ro1993270303371.pdf",
    "rairo80": "http://web.archive.org/web/20230322222157id_/https://www.rairo-ro.org/articles/ro/pdf/1980/03/ro1980140302491.pdf",
    "hindawi_delayed": "http://web.archive.org/web/20231118064338id_/https://downloads.hindawi.com/journals/mpe/2015/528726.pdf",
}
for slug, url in JOBS.items():
    pdf = OUT / (slug + ".pdf")
    txt = OUT / (slug + ".txt")
    try:
        fetch(url, pdf)
        n = extract(pdf, txt)
        print(slug, "OK", n)
    except Exception as e:
        print(slug, "FAIL", str(e)[:120])

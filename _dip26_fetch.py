import urllib.request, json, pathlib
from pypdf import PdfReader

OUT = pathlib.Path("/root/marfagenez/_dip26_txt")
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}


def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    dest.write_bytes(data)
    return len(data)


def extract(pdf, txt):
    try:
        rd = PdfReader(str(pdf))
        parts = []
        for i, p in enumerate(rd.pages):
            try:
                parts.append("\n[[page %d]]\n" % (i + 1) + (p.extract_text() or ""))
            except Exception:
                parts.append("\n[[page %d ERR]]\n" % (i + 1))
        t = "".join(parts)
        txt.write_text(t, encoding="utf-8")
        return len(t)
    except Exception as e:
        return "ERR " + str(e)


cands = json.load(open("/root/marfagenez/_dip26_pick.json"))
for slug, d in cands.items():
    txt = OUT / (slug + ".txt")
    if txt.exists() and txt.stat().st_size > 2000:
        print(slug, "cached", txt.stat().st_size)
        continue
    ok = False
    last = ""
    for u in d["urls"]:
        pdf = OUT / (slug + ".pdf")
        try:
            n = fetch(u, pdf)
        except Exception as e:
            last = str(e)[:80]
            print(slug, "dl fail", last)
            continue
        r = extract(pdf, txt)
        print(slug, "dl", n, "txt", r)
        ok = True
        break
    if not ok:
        print(slug, "NO SOURCE", last)

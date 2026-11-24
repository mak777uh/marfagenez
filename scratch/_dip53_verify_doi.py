import importlib.util, json, re, html, subprocess, urllib.parse, pathlib
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
KEY = pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()
CURL = "/mnt/c/Windows/System32/curl.exe"

WORKS = {
 "PMC13583149": "10.1002/cnm.70212",
 "PMC12978645": "10.1093/ismeco/ycag029",
 "PMC12092104": "10.1098/rsif.2025.0010",
 "PMC13319206": "10.1038/s42003-026-10531-2",
 "PMC13593633": "10.1007/s11095-026-04129-w",
 "PMC5466690": "10.1038/s41598-017-03341-4",
 "PMC4361863": "10.1038/srep09190",
 "PMC6412255": "10.3390/mi10020078",
 "PMC5515263": "10.1038/npjbiofilms.2016.12",
 "PMC12779220": "10.1002/bit.70095",
 "PMC12988972": "10.1007/s00253-026-13779-0",
 "PMC13522592": "10.1038/s41598-026-67006-x",
}

def plain(pmc):
    xml = e.fulltext(pmc)
    t = re.sub(r"<[^>]+>", " ", xml)
    t = html.unescape(re.sub(r"\s+", " ", t))
    return t

def norm(s):
    s = s.replace("\u00ad", "").replace("\u2019", "'").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()

res = {}
for pmc, doi in WORKS.items():
    url = "https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi) + "?api_key=" + KEY
    out = subprocess.run([CURL, "-sL", "-m", "60", url], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    try:
        d = json.loads(out)
        res[pmc] = {"doi": doi, "title": d.get("title"), "year": d.get("publication_year"),
                    "venue": (((d.get("primary_location") or {}).get("source")) or {}).get("display_name")}
    except Exception:
        res[pmc] = {"doi": doi, "error": out[:150]}
    print(pmc, doi, "->", res[pmc].get("title"), res[pmc].get("year"), res[pmc].get("error", ""))

pathlib.Path("/root/marfagenez/scratch/_dip53_works.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))

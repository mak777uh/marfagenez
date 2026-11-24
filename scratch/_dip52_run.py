"""One-shot pipeline for DIP-52: fetch candidate full texts, dump number-bearing sentences."""
import importlib.util, pathlib, re, sys, json

spec = importlib.util.spec_from_file_location("f", "/root/marfagenez/scratch/_dip52_fetch.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

DOIS = [
    "10.1371/journal.pone.0022881",
    "10.1111/j.1752-4571.2007.00011.x",
    "10.1093/molbev/msx185",
    "10.1111/eva.12127",
    "10.1111/jeb.14237",
    "10.1098/rstb.2012.0083",
    "10.1038/s41467-019-10924-4",
    "10.1007/s12080-021-00522-w",
    "10.1111/eva.12362",
    "10.1073/pnas.1316145111",
    "10.1038/ncomms12349",
    "10.1098/rspb.2016.1690",
]

OUT = pathlib.Path("/root/marfagenez/scratch/dip52")
for doi in DOIS:
    p = OUT / (doi.replace("/", "_") + ".txt")
    if p.exists() and p.stat().st_size > 4000:
        print("have", doi)
        continue
    print("==", doi)
    try:
        w = f.oa_meta(doi)
    except Exception as e:
        print("   no meta", e)
        continue
    oa = w.get("open_access") or {}
    cand = []
    if oa.get("oa_url"):
        cand.append(oa["oa_url"])
    for loc in (w.get("locations") or []):
        if loc.get("pdf_url"):
            cand.append(loc["pdf_url"])
        if loc.get("landing_page_url"):
            cand.append(loc["landing_page_url"])
    ids = w.get("ids") or {}
    urls = []
    for k in ("pmcid", "pmid"):
        v = ids.get(k)
        if v and str(v).startswith("PMC"):
            n = str(v).replace("PMC", "")
            urls.append(f"https://www.ebi.ac.uk/europepmc/webservices/rest/PMC{n}/fullTextXML")
            urls.append(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={n}&retmode=xml")
            urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{n}/")
    urls += [c for c in cand if isinstance(c, str) and c.startswith("http")]
    seen, ordered = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); ordered.append(u)
    f.grab(doi, ordered[:8])

KW = re.compile(r"(rate of environmental change|environmental change|per generation|per year|per decade|"
                r"°C|uC|km|generation|\bpH\b|mM|critical rate|velocity|lag|extinction|fitness|"
                r"warming|salt|CO2)", re.I)
NUM = re.compile(r"\d")

def sents(t):
    t = re.sub(r"\s+", " ", t)
    return re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", t)

lines = []
for p in sorted(OUT.glob("*.txt")):
    t = p.read_text(encoding="utf-8", errors="replace")
    lines.append("#" * 100)
    lines.append("### FILE " + p.name + f"  ({len(t)} chars)")
    seen = set()
    for s in sents(t):
        s = s.strip()
        if len(s) < 45 or len(s) > 360:
            continue
        if not NUM.search(s) or not KW.search(s):
            continue
        if s in seen:
            continue
        seen.add(s)
        lines.append("  * " + s)

win = pathlib.Path("/mnt/c/Users/Admin/Documents/Qoder/2026-10-18/82ab86cd/findings.txt")
win.write_text("\n".join(lines), encoding="utf-8")
print("WROTE", win, len(lines), "lines,", len(list(OUT.glob('*.txt'))), "texts")

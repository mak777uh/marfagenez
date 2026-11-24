import json, subprocess, urllib.parse, pathlib, time

ROOT = pathlib.Path("/root/marfagenez")
KEY = pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()
CURL = "/mnt/c/Windows/System32/curl.exe"
OUT = ROOT / "scratch" / "_dip53_pool.json"

QUERIES = [
    '"Damkohler number" somite OR limb OR zebrafish OR embryogenesis',
    '"Peclet number" interstitial flow cartilage OR tumor OR tissue value',
    '"Peclet number" embryo gradient advection diffusion value',
    '"Thiele modulus" Pseudomonas OR Staphylococcus biofilm measured',
    '"Deborah number" blood relaxation time value',
    '"Biot number" cryopreservation tissue OR organ value',
    '"Knudsen number" trachea OR lung OR biology',
    '"Sherwood number" insect OR egg OR stomata OR leaf',
    '"Damkohler number" blood clotting OR enzyme OR receptor',
    '"Peclet number" bone OR osteocyte OR lacuna',
]

def fetch(q, per=20):
    params = {"search": q, "per-page": str(per), "api_key": KEY,
              "select": "id,doi,title,publication_year,primary_location,abstract_inverted_index,cited_by_count,type"}
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    r = subprocess.run([CURL, "-s", "-m", "60", url], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception as e:
        print("ERR", q, e, r.stdout[:200]); return {"results": []}

def abstract(inv):
    if not inv: return ""
    pos = []
    for w, idxs in inv.items():
        for i in idxs: pos.append((i, w))
    pos.sort()
    return " ".join(w for _, w in pos)

pool = json.loads(OUT.read_text()) if OUT.exists() else {}
for q in QUERIES:
    if q in pool: continue
    d = fetch(q)
    res = []
    for w in d.get("results", []):
        src = (((w.get("primary_location") or {}).get("source")) or {}).get("display_name")
        res.append({"doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "title": w.get("title"), "year": w.get("publication_year"),
                    "venue": src, "cites": w.get("cited_by_count"),
                    "abstract": abstract(w.get("abstract_inverted_index"))})
    pool[q] = res
    print(f"{len(res):3d}  {q}")
    time.sleep(0.3)
OUT.write_text(json.dumps(pool, ensure_ascii=False, indent=1))
print("saved")

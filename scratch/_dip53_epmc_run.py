import json, sys, pathlib, time
sys.path.insert(0, "/root/marfagenez/scratch")
import importlib.util
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

QUERIES = {
 "Da": '("Damkohler number" OR "Damköhler number") AND (biofilm OR tissue OR embryo OR cell OR blood) AND OPEN_ACCESS:y',
 "Pe": '("Peclet number" OR "Péclet number") AND (embryo OR tissue OR morphogen OR interstitial OR biofilm) AND OPEN_ACCESS:y',
 "De": '("Deborah number") AND (blood OR mucus OR saliva OR biofilm OR mucus) AND OPEN_ACCESS:y',
 "Th": '("Thiele modulus") AND (biofilm OR bioreactor OR cell OR enzyme OR immobilized) AND OPEN_ACCESS:y',
 "Bi": '("Biot number") AND (tissue OR cryopreservation OR organ OR skin OR tumor) AND OPEN_ACCESS:y',
 "Sh": '("Sherwood number") AND (biofilm OR leaf OR insect OR blood OR bioreactor) AND OPEN_ACCESS:y',
 "Kn": '("Knudsen number") AND (trachea OR lung OR insect OR biology OR biofilm) AND OPEN_ACCESS:y',
}
out = {}
for k, q in QUERIES.items():
    res = e.epmc_search(q, 100)
    rows = []
    for r in res:
        rows.append({"pmcid": r.get("pmcid"), "doi": r.get("doi"), "title": r.get("title"),
                     "year": r.get("pubYear"), "journal": r.get("journalTitle"),
                     "oa": r.get("isOpenAccess")})
    out[k] = rows
    print(f"{len(rows):3d} {k}")
    time.sleep(0.3)
pathlib.Path("/root/marfagenez/scratch/_dip53_epmc.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

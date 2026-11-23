import json, pathlib

pool = json.load(open("/root/marfagenez/_dip26_pool.json"))
by_doi = {}
for v in pool.values():
    d = (v.get("doi") or "").lower().replace("https://doi.org/", "")
    urls = list(v.get("pdf_urls") or [])
    if v.get("oa_url"):
        urls.append(v["oa_url"])
    by_doi[d] = {"title": v["title"], "year": v["year"], "urls": urls}

want = {
    "ageext93": "10.1051/ro/1993270303371",
    "pmsum80": "10.1051/ro/1980140302491",
    "ermm_age": "10.2991/ermm-14.2014.101",
    "ermm_repl": "10.2991/ermm-14.2014.100",
    "mdpi_app": "10.3390/app131810210",
    "mdpi_math": "10.3390/math7080716",
    "srsp23": "10.26408/srsp-2023-11",
    "bjps_costlimit": "10.1214/16-bjps317",
    "hindawi_delayed": "10.1155/2015/528726",
    "iop_1": "10.1088/1757-899x/1043/2/022012",
    "jomase_idg": "10.36842/jomase.v70i1.593",
    "tqs_series": "10.17929/tqs.8.51",
    "ein_warranty": "10.17531/ein.2015.3.6",
    "apm_warranty": "10.1016/j.apm.2016.01.022",
}
pick = {}
for slug, doi in want.items():
    e = by_doi.get(doi)
    if not e:
        pick[slug] = {"doi": doi, "urls": [], "note": "not in pool"}
        continue
    pick[slug] = {"doi": doi, "title": e["title"], "year": e["year"], "urls": e["urls"]}
    print(slug, doi, "urls", len(e["urls"]), (e["title"] or "")[:60])
pathlib.Path("/root/marfagenez/_dip26_pick.json").write_text(json.dumps(pick, indent=1), encoding="utf-8")

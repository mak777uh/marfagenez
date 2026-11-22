import json,pathlib
p=json.loads(pathlib.Path("_dip18_pool.json").read_text())
want=["10.1145/1970386.1970387","10.1109/sc41405.2020.00081","10.1145/2600212.2600219",
"10.1587/transinf.2017pap0002","10.1109/wicsa.2014.49","10.48550/arxiv.2103.08191",
"10.1109/reconfig.2011.37","10.3390/buildings15071057","10.1109/sp.2015.59",
"10.1007/s00446-015-0258-3","10.48550/arxiv.2102.06896","10.1145/2901318.2901339",
"10.1145/3385412.3385998","10.1109/access.2020.3011813","10.5281/zenodo.17799427",
"10.1145/3635161","10.63125/g9c9cp41","10.48550/arxiv.2401.00134"]
for w in want:
    d=p.get(w)
    if not d: print("MISSING",w); continue
    print("###",w,"|",d["year"],"|",d["title"])
    print(d["abstract"])
    print()

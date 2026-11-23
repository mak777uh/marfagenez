import urllib.request, json, time
K=open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
BASE="https://api.openalex.org/works"
def get(url):
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(url, timeout=90))
        except Exception as e:
            print("ERR", e); time.sleep(2)
    return None
QUERIES=[
 "age replacement policy expected cost per unit time optimization",
 "repair cost limit replacement policy optimal threshold",
 "optimal preventive maintenance interval Barlow Proschan",
 "imperfect preventive maintenance periodic cost model age reduction",
 "Weibull shape parameter maintenance cost rate optimal interval",
 "replacement model cumulative cost per unit time derivative",
 "cost limit policy minimal repair replacement decision model",
 "preventive maintenance schedule expected cost rate renewal reward theorem",
]
pool={}
for q in QUERIES:
    u=BASE+"?search="+urllib.parse.quote(q)+"&per-page=25&mailto=research@example.org&api_key="+K
    r=get(u)
    if not r: continue
    print("=== ", q, r["meta"]["count"])
    for w in r["results"]:
        d=w.get("doi")
        if not d: continue
        oa=w.get("open_access") or {}
        locs=[]
        for L in (w.get("locations") or []):
            if L.get("is_oa") and L.get("pdf_url"):
                locs.append(L["pdf_url"])
        key=(w.get("title") or "")[:60]
        pool[w["id"]]={"doi":d,"title":w.get("title"),"year":w.get("publication_year"),
            "is_oa":oa.get("is_oa"),"oa_url":oa.get("oa_url"),"pdf_urls":locs,
            "venue":(w.get("primary_location") or {}).get("source",{}) or {},
            "abstract":w.get("abstract_inverted_index"),"queries":[q]}
        if not pool[w["id"]]["queries"] or q not in pool[w["id"]]["queries"]:
            pool[w["id"]].setdefault("queries",[])
open("/root/marfagenez/_dip26_pool.json","w").write(json.dumps(pool,indent=1))
print("POOL", len(pool), "with pdf:", sum(1 for v in pool.values() if v["pdf_urls"]))

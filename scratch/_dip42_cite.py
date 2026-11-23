import json,urllib.request,urllib.parse,time,re
KEY=open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
BASE="https://api.openalex.org/works"
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"marfagenez-dip/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode())
def inv2txt(inv):
    if not inv: return ""
    pos=[]
    for w,ps in inv.items():
        for p in ps: pos.append((p,w))
    pos.sort(); return " ".join(w for _,w in pos)
SEEDS=["10.1021/ja900919c","10.1038/nchem.1127","10.1073/pnas.1203212109","10.1126/science.1089904"]
pool={}
for s in SEEDS:
    cursor="*"; got=0
    while got<200:
        url=BASE+"?"+urllib.parse.urlencode({"filter":"cites:"+s+",has_abstract:true","per-page":100,"cursor":cursor,"mailto":"dip@marfagenez.local","api_key":KEY})
        try: d=get(url)
        except Exception as e:
            print("ERR",s,e); break
        for w in d["results"]:
            doi=(w.get("doi") or "").replace("https://doi.org/","").lower()
            if not doi or doi in pool: continue
            pool[doi]={"doi":doi,"title":w.get("display_name"),"year":w.get("publication_year"),"cn":w.get("cited_by_count"),"seed":s,"abstract":inv2txt(w.get("abstract_inverted_index"))}
        got+=len(d["results"]); cursor=d["meta"].get("next_cursor")
        if not cursor or not d["results"]: break
        time.sleep(1)
    print("seed",s,"total",got)
json.dump(list(pool.values()),open("_dip42_cite.json","w"),indent=1)
print("POOL",len(pool))

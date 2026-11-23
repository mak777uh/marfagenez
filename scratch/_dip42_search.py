import json,urllib.request,urllib.parse,time,re,sys
KEY=open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
BASE="https://api.openalex.org/works"
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"marfagenez-dip/1.0 (mailto:dip@marfagenez.local)"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode())
def inv2txt(inv):
    if not inv: return ""
    pos=[]
    for w,ps in inv.items():
        for p in ps: pos.append((p,w))
    pos.sort()
    return " ".join(w for _,w in pos)
QS=[
 "fatty acid vesicle growth and division critical size",
 "giant unilamellar vesicle self-division surface area to volume ratio",
 "protocell membrane growth rate lipid incorporation kinetics",
 "spontaneous division of vesicles efficiency percentage",
 "vesicle division inhibited by salt concentration magnesium",
]
pool={}
for q in QS:
    url=BASE+"?"+urllib.parse.urlencode({"search":q,"per-page":25,"sort":"relevance_score:desc","mailto":"dip@marfagenez.local","api_key":KEY})
    try: d=get(url)
    except Exception as e:
        print("ERR",q,e); continue
    print("Q:",q,"->",d["meta"]["count"])
    for w in d["results"]:
        doi=(w.get("doi") or "").replace("https://doi.org/","").lower()
        if not doi: continue
        ab=inv2txt(w.get("abstract_inverted_index"))
        pool.setdefault(doi,{"doi":doi,"title":w.get("display_name"),"year":w.get("publication_year"),"queries":[q],"abstract":ab})
        if q not in pool[doi]["queries"]: pool[doi]["queries"].append(q)
    time.sleep(1)
json.dump(list(pool.values()),open("_dip42_pool1.json","w"),indent=1)
print("POOL",len(pool))

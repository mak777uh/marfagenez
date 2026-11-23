import json,urllib.request,urllib.parse,time,re
KEY=open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"marfagenez-dip/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode())
def inv2txt(inv):
    if not inv: return ""
    pos=[(p,w) for w,ps in inv.items() for p in ps]
    pos.sort(); return " ".join(w for _,w in pos)
MB="https://api.openalex.org/works?mailto=dip@marfagenez.local&api_key="+KEY+"&"
SEEDS=["10.1021/ja900919c","10.1038/nchem.1127","10.1073/pnas.1203212109","10.1126/science.1089904","10.1002/anie.202014174"]
related=set()
for s in SEEDS:
    try:
        d=get(MB+"https://api.openalex.org/works/https://doi.org/"+s)
        rw=d.get("related_works") or []
        print("seed",s,"related",len(rw),"cit",d.get("cited_by_count"))
        for u in rw: related.add(u.rsplit("/",1)[-1])
    except Exception as e: print("ERR",s,e)
    time.sleep(1)
pool={}
ids=list(related)
for i in range(0,len(ids),50):
    chunk=ids[i:i+50]
    url=MB+urllib.parse.urlencode({"filter":"openalex_id:"+"|".join(chunk),"per-page":50})
    try: d=get(url)
    except Exception as e: print("ERR chunk",e); continue
    for w in d["results"]:
        doi=(w.get("doi") or "").replace("https://doi.org/","").lower()
        if not doi: continue
        pool[doi]={"doi":doi,"title":w.get("display_name"),"year":w.get("publication_year"),"cn":w.get("cited_by_count"),"abstract":inv2txt(w.get("abstract_inverted_index"))}
    time.sleep(1)
dup=set(open("_dip42_dups.txt").read().split())
out=[p for p in pool.values() if p["doi"] not in dup and p["abstract"]]
out.sort(key=lambda x:-(x["cn"] or 0))
json.dump(out,open("_dip42_rel.json","w"),indent=1)
print("POOL",len(pool),"KEEP",len(out))
for p in out:
    ab=p["abstract"]
    if not re.search(r"divi|grow|fission|bud|proliferat|reproduc",ab,re.I): continue
    if len(re.findall(r"\d",ab))<3: continue
    print("###",p["doi"],p["year"],"cit",p["cn"]); print("T:",p["title"]); print("A:",ab[:650]); print()

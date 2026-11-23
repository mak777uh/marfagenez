import json,urllib.request,urllib.parse,time,re
KEY=open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
BASE="https://api.openalex.org/works"
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"marfagenez-dip/1.0"})
    with urllib.request.urlopen(req,timeout=60) as r: return json.loads(r.read().decode())
def inv2txt(inv):
    if not inv: return ""
    pos=[]
    for w,ps in inv.items():
        for p in ps: pos.append((p,w))
    pos.sort(); return " ".join(w for _,w in pos)
QS=[
 "coupled growth and division of model protocell membranes",
 "self-reproduction of giant vesicles proliferation",
 "oleic acid vesicle growth membrane area increase",
 "division of synthetic cells osmotic stress without proteins",
 "programmed vesicle division cycles repeated growth",
]
pool={}
for q in QS:
    url=BASE+"?"+urllib.parse.urlencode({"filter":"title_and_abstract.search:"+q,"per-page":25,"mailto":"dip@marfagenez.local","api_key":KEY})
    try: d=get(url)
    except Exception as e:
        print("ERR",q,e); continue
    print("Q:",q,"->",d["meta"]["count"])
    for w in d["results"]:
        doi=(w.get("doi") or "").replace("https://doi.org/","").lower()
        if not doi: continue
        ab=inv2txt(w.get("abstract_inverted_index"))
        if doi not in pool: pool[doi]={"doi":doi,"title":w.get("display_name"),"year":w.get("publication_year"),"cn":w.get("cited_by_count"),"queries":[q],"abstract":ab}
    time.sleep(1)
dup=set(open("_dip42_dups.txt").read().split())
out=[]
for p in pool.values():
    if p["doi"] in dup: print("DUP-skip",p["doi"]); continue
    ab=p["abstract"] or ""
    if not ab: continue
    if not re.search(r"divi|grow|fission|bud|proliferat|reproduc",ab,re.I): continue
    out.append(p)
out.sort(key=lambda x:-(x["cn"] or 0))
json.dump(out,open("_dip42_pool2.json","w"),indent=1)
print("POOL",len(pool),"KEEP",len(out))
for p in out[:30]:
    print("###",p["doi"],p["year"],"cit",p["cn"]); print("T:",p["title"]); print("A:",(p["abstract"] or "")[:600]); print()

import json,re
pool=json.load(open("_dip16_pool.json"))
skip={"10.3390/life15050724","10.1126/science.1089904","10.1021/ja900919c","10.1126/science.1100757","10.1038/ncomms9352","10.1186/s13322-014-0006-2","10.1016/0303-2647(86)90008-0"}
kw={"divid":3,"division":3,"grow":2,"growth":2,"content":2,"leak":3,"loss":2,"permeab":3,"nutrient":2,"cost":2,"coacerv":3,"compet":3,"osmo":3,"fatty acid":2,"vesicle":2,"lipid":2,"surface area":2,"yield":2,"encapsulat":2}
out=[]
for d,w in pool.items():
    if d in skip: continue
    t=((w["title"] or "")+" "+w["abstract"]).lower()
    s=sum(v for k,v in kw.items() if k in t)
    nums=len(re.findall(r"[0-9]+(?:\.[0-9]+)?\s*%|[0-9]+\.[0-9]+|[0-9]+\s*(?:fold|mM|uM|nm)",w["abstract"]))
    out.append((s+nums*0.7,s,nums,w["year"],d,w["title"]))
out.sort(reverse=True)
print("CAND",len(out))
for i,row in enumerate(out[:50]):
    sc,s,n,y,d,t=row
    print("%02d|%s|n=%d|%s|%s"%(i,y,n,d,(t or "?")[:95]))
